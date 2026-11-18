#!/usr/bin/env python3
"""Récupère les nouvelles offres Community Manager (stage + alternance) via l'API France Travail.

Usage : python3 scripts/recuperer_offres.py [nombre_de_jours]   (par défaut : 3 derniers jours)
Ajoute les nouvelles offres à offres.json (à la racine du site), sans doublons,
et retire les offres de plus de 30 jours.
Les clés API viennent des variables d'environnement FT_CLIENT_ID et FT_CLIENT_SECRET
(Secrets GitHub), jamais de ce fichier.
"""
import json, os, sys, re, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone

DOSSIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=%2Fpartenaire"
SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
RECHERCHES = ["community manager", "social media manager", "chargé de communication digitale"]

SECTEURS = [  # (mot-clé dans le secteur / l'entreprise / le texte, secteur du site)
    ("agence", "Agence de communication"), ("publicit", "Agence de communication"), ("conseil en relations publiques", "Agence de communication"),
    ("cosm", "Beauté & cosmétique"), ("parfum", "Beauté & cosmétique"), ("beauté", "Beauté & cosmétique"),
    ("habillement", "Mode & luxe"), ("textile", "Mode & luxe"), ("luxe", "Mode & luxe"), ("mode", "Mode & luxe"), ("chaussure", "Mode & luxe"),
    ("édition", "Médias & presse"), ("presse", "Médias & presse"), ("radio", "Médias & presse"), ("télévision", "Médias & presse"), ("média", "Médias & presse"),
    ("logiciel", "Tech & start-up"), ("informatique", "Tech & start-up"), ("programmation", "Tech & start-up"), ("start", "Tech & start-up"),
    ("sport", "Sport"), ("culturel", "Culture & événementiel"), ("spectacle", "Culture & événementiel"), ("événement", "Culture & événementiel"),
    ("restauration", "Food & restauration"), ("alimentaire", "Food & restauration"), ("boisson", "Food & restauration"),
    ("hôtel", "Tourisme & hôtellerie"), ("tourisme", "Tourisme & hôtellerie"), ("voyage", "Tourisme & hôtellerie"),
    ("commerce de détail", "Retail & e-commerce"), ("vente à distance", "Retail & e-commerce"), ("commerce", "Retail & e-commerce"),
    ("santé", "Santé & bien-être"), ("pharma", "Santé & bien-être"), ("médical", "Santé & bien-être"),
    ("association", "Associatif & public"), ("administration", "Associatif & public"), ("enseignement", "Associatif & public"),
    ("banque", "Banque & assurance"), ("assurance", "Banque & assurance"), ("financ", "Banque & assurance"),
]


def lire_config():
    cfg = {k: os.environ.get(k, "").strip() for k in ("FT_CLIENT_ID", "FT_CLIENT_SECRET", "DEPARTEMENT")}
    if not cfg["FT_CLIENT_ID"] or not cfg["FT_CLIENT_SECRET"]:
        sys.exit("ERREUR : ajoute FT_CLIENT_ID et FT_CLIENT_SECRET dans les Secrets du dépôt GitHub")
    return cfg


def jeton(cfg):
    motif = ""
    for scope in ("api_offresdemploiv2 o2dsoffre", "api_offresdemploiv2"):
        data = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": cfg["FT_CLIENT_ID"].strip(),
            "client_secret": cfg["FT_CLIENT_SECRET"].strip(),
            "scope": scope,
        }).encode()
        req = urllib.request.Request(TOKEN_URL, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)["access_token"]
        except urllib.error.HTTPError as e:
            try:
                corps = json.loads(e.read().decode("utf-8", "replace"))
                motif = f"{e.code} {corps.get('error', '')} : {corps.get('error_description', '')}"
            except ValueError:
                motif = str(e.code)
            print(f"Essai avec le scope « {scope} » refusé ({motif})", file=sys.stderr)
    sys.exit(f"ERREUR connexion France Travail ({motif}). invalid_client = clés incorrectes ; invalid_scope = l'API « Offres d'emploi v2 » n'est pas ajoutée à ton application.")


def chercher(tok, mots, debut, fin, departement):
    params = {"motsCles": mots, "minCreationDate": debut, "maxCreationDate": fin, "range": "0-149"}
    if departement:
        params["departement"] = departement
    url = SEARCH_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + tok, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            if r.status == 204:
                return []
            return json.load(r).get("resultats", [])
    except urllib.error.HTTPError as e:
        print(f"Avertissement : recherche « {mots} » refusée ({e.code})", file=sys.stderr)
        return []


def type_contrat(o):
    nature = (o.get("natureContrat") or "").lower()
    texte = " ".join([o.get("intitule") or "", o.get("description") or "", o.get("typeContratLibelle") or ""]).lower()
    if "apprentissage" in nature or "professionnalisation" in nature or re.search(r"alternan|apprenti|contrat pro", texte):
        return "alternance"
    if re.search(r"\bstage\b|stagiaire|\binternship\b", texte):
        return "stage"
    return None  # CDI/CDD classiques : ignorés


def secteur(o):
    texte = " ".join([o.get("secteurActiviteLibelle") or "", (o.get("entreprise") or {}).get("nom") or ""]).lower()
    for mot, nom in SECTEURS:
        if mot in texte:
            return nom
    return "Autre"


def main():
    jours = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    cfg = lire_config()
    tok = jeton(cfg)
    fin = datetime.now(timezone.utc).replace(microsecond=0)
    debut = fin - timedelta(days=jours)
    iso = lambda d: d.strftime("%Y-%m-%dT%H:%M:%SZ")
    vues, offres = set(), []
    for mots in RECHERCHES:
        for o in chercher(tok, mots, iso(debut), iso(fin), cfg.get("DEPARTEMENT", "")):
            if o.get("id") in vues:
                continue
            vues.add(o.get("id"))
            t = type_contrat(o)
            if not t:
                continue
            desc = re.sub(r"\s+", " ", o.get("description") or "").strip()
            offres.append({
                "id": "ft-" + o["id"],
                "titre": o.get("intitule") or "Community Manager",
                "entreprise": (o.get("entreprise") or {}).get("nom") or "",
                "lieu": (o.get("lieuTravail") or {}).get("libelle") or "",
                "type": t,
                "secteur": secteur(o),
                "description": desc[:600],
                "url": (o.get("origineOffre") or {}).get("urlOrigine") or f"https://candidat.francetravail.fr/offres/recherche/detail/{o['id']}",
                "source": "France Travail",
                "date": (o.get("dateCreation") or iso(fin))[:10],
            })
    chemin = os.path.join(DOSSIER, "offres.json")
    try:
        existantes = json.load(open(chemin, encoding="utf-8"))
    except (OSError, ValueError):
        existantes = []
    limite = (fin - timedelta(days=30)).strftime("%Y-%m-%d")
    gardees = [o for o in existantes if (o.get("date") or "9999") >= limite]
    ids = {o.get("id") for o in gardees}
    urls = {o.get("url") for o in gardees}
    cles = {((o.get("entreprise") or "").lower(), (o.get("titre") or "").lower()) for o in gardees if o.get("entreprise")}
    ajout = []
    for o in offres:
        cle = (o["entreprise"].lower(), o["titre"].lower())
        if o["id"] in ids or o["url"] in urls or (o["entreprise"] and cle in cles):
            continue
        ajout.append(o); ids.add(o["id"]); urls.add(o["url"]); cles.add(cle)
    toutes = sorted(gardees + ajout, key=lambda o: o.get("date") or "", reverse=True)
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(toutes, f, ensure_ascii=False, indent=2)
    print(f"{len(ajout)} nouvelles offres ajoutées, {len(existantes) - len(gardees)} anciennes retirées, {len(toutes)} au total.")


if __name__ == "__main__":
    main()

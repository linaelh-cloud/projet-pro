#!/usr/bin/env python3
"""Récupère les nouvelles offres Community Manager (stage + alternance).

Sources :
  - Adzuna (regroupe les offres de nombreux sites d'emploi) : ADZUNA_APP_ID, ADZUNA_APP_KEY
  - France Travail (facultatif, si l'accès est accordé)     : FT_CLIENT_ID, FT_CLIENT_SECRET
Les clés viennent des Secrets GitHub (variables d'environnement), jamais de ce fichier.
Une source sans clé ou refusée est sautée ; le robot échoue seulement si aucune source ne marche.

Usage : python3 scripts/recuperer_offres.py [nombre_de_jours]   (par défaut : 3 derniers jours)
Ajoute les nouvelles offres à offres.json, sans doublons, et retire celles de plus de 30 jours.
"""
import json, os, sys, re, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone

DOSSIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=%2Fpartenaire"
SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
ADZUNA_URL = "https://api.adzuna.com/v1/api/jobs/fr/search/1"
ADZUNA_RECHERCHES = [("community manager alternance", "alternance"), ("community manager apprentissage", "alternance"), ("community manager stage", "stage"), ("social media manager alternance", "alternance"), ("social media manager stage", "stage")]
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


def jeton(cfg):
    import base64
    motif = ""
    cid, sec = cfg["FT_CLIENT_ID"].strip(), cfg["FT_CLIENT_SECRET"].strip()
    print(f"Clés lues : identifiant de {len(cid)} caractères (commence par PAR_ : {cid.startswith('PAR_')}), clé secrète de {len(sec)} caractères.", file=sys.stderr)
    essais = [
        ("api_offresdemploiv2 o2dsoffre", "corps"),
        (f"api_offresdemploiv2 o2dsoffre application_{cid}", "corps"),
        ("api_offresdemploiv2 o2dsoffre", "basic"),
    ]
    for scope, mode in essais:
        champs = {"grant_type": "client_credentials", "scope": scope}
        entetes = {"Content-Type": "application/x-www-form-urlencoded"}
        if mode == "corps":
            champs.update({"client_id": cid, "client_secret": sec})
        else:
            entetes["Authorization"] = "Basic " + base64.b64encode(f"{cid}:{sec}".encode()).decode()
        data = urllib.parse.urlencode(champs).encode()
        scope = f"{scope.split(' application_')[0]}{' + application' if 'application_' in scope else ''} / {mode}"
        req = urllib.request.Request(TOKEN_URL, data=data, headers=entetes)
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
    raise RuntimeError(f"connexion France Travail ({motif})). L'accès à l'API Offres d'emploi n'est peut-être pas encore accordé.")


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


def type_contrat(texte, nature="", indice=None):
    texte, nature = texte.lower(), nature.lower()
    if "apprentissage" in nature or "professionnalisation" in nature or re.search(r"alternan|apprenti|contrat pro", texte):
        return "alternance"
    if re.search(r"\bstage\b|stagiaire|\binternship\b|\bintern\b", texte):
        return "stage"
    if indice and not re.search(r"\bcdi\b|\bcdd\b|freelance|indépendant", texte):
        return indice
    return None  # CDI/CDD classiques : ignorés


PERTINENT = re.compile(r"community|social media|réseaux sociaux|reseaux sociaux|communication|content|contenu|brand|influence|digital|marketing|cm\\b", re.I)


def pertinent(titre):
    return bool(PERTINENT.search(titre or ""))


def nettoyer(t):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t or "")).strip()


def secteur(o):
    texte = " ".join([o.get("secteurActiviteLibelle") or "", (o.get("entreprise") or {}).get("nom") or ""]).lower()
    for mot, nom in SECTEURS:
        if mot in texte:
            return nom
    return "Autre"


def source_france_travail(jours, fin):
    cid, sec = os.environ.get("FT_CLIENT_ID", "").strip(), os.environ.get("FT_CLIENT_SECRET", "").strip()
    if not cid or not sec:
        print("France Travail : pas de clés, source sautée.")
        return None
    tok = jeton({"FT_CLIENT_ID": cid, "FT_CLIENT_SECRET": sec})
    iso = lambda d: d.strftime("%Y-%m-%dT%H:%M:%SZ")
    debut = fin - timedelta(days=jours)
    vues, offres = set(), []
    for mots in RECHERCHES:
        for o in chercher(tok, mots, iso(debut), iso(fin), os.environ.get("DEPARTEMENT", "").strip()):
            if o.get("id") in vues:
                continue
            vues.add(o.get("id"))
            t = type_contrat(" ".join([o.get("intitule") or "", o.get("description") or "", o.get("typeContratLibelle") or ""]), o.get("natureContrat") or "")
            if not t:
                continue
            offres.append({
                "id": "ft-" + o["id"],
                "titre": o.get("intitule") or "Community Manager",
                "entreprise": (o.get("entreprise") or {}).get("nom") or "",
                "lieu": (o.get("lieuTravail") or {}).get("libelle") or "",
                "type": t,
                "secteur": secteur(o),
                "description": nettoyer(o.get("description"))[:600],
                "url": (o.get("origineOffre") or {}).get("urlOrigine") or f"https://candidat.francetravail.fr/offres/recherche/detail/{o['id']}",
                "source": "France Travail",
                "date": (o.get("dateCreation") or iso(fin))[:10],
            })
    print(f"France Travail : {len(offres)} offres stage/alternance.")
    return offres


def source_adzuna(jours, fin):
    app_id, app_key = os.environ.get("ADZUNA_APP_ID", "").strip(), os.environ.get("ADZUNA_APP_KEY", "").strip()
    if not app_id or not app_key:
        print("Adzuna : pas de clés, source sautée.")
        return None
    vues, offres, erreurs = set(), [], 0
    for mots, indice in ADZUNA_RECHERCHES:
        params = {"app_id": app_id, "app_key": app_key, "what": mots, "results_per_page": 50,
                  "max_days_old": max(jours, 1), "sort_by": "date", "content-type": "application/json"}
        req = urllib.request.Request(ADZUNA_URL + "?" + urllib.parse.urlencode(params), headers={"Accept": "application/json", "User-Agent": "projet-pro/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                resultats = json.load(r).get("results", [])
        except urllib.error.HTTPError as e:
            erreurs += 1
            print(f"Adzuna : recherche « {mots} » refusée ({e.code}). Vérifie ADZUNA_APP_ID et ADZUNA_APP_KEY.", file=sys.stderr)
            continue
        for o in resultats:
            oid = str(o.get("id"))
            if oid in vues:
                continue
            vues.add(oid)
            titre, desc = nettoyer(o.get("title")), nettoyer(o.get("description"))
            t = type_contrat(titre + " " + desc, "", indice)
            if not t:
                continue
            entreprise = nettoyer((o.get("company") or {}).get("display_name"))
            offres.append({
                "id": "az-" + oid,
                "titre": titre or "Community Manager",
                "entreprise": entreprise,
                "lieu": nettoyer((o.get("location") or {}).get("display_name")),
                "type": t,
                "secteur": secteur({"secteurActiviteLibelle": (o.get("category") or {}).get("label") or "", "entreprise": {"nom": entreprise}}),
                "description": desc[:600],
                "url": o.get("redirect_url") or "",
                "source": "Adzuna",
                "date": (o.get("created") or fin.strftime("%Y-%m-%d"))[:10],
            })
    if erreurs == len(ADZUNA_RECHERCHES):
        raise RuntimeError("Adzuna refuse toutes les recherches : clés incorrectes ?")
    print(f"Adzuna : {len(offres)} offres stage/alternance.")
    return offres


def main():
    jours = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    fin = datetime.now(timezone.utc).replace(microsecond=0)
    offres, reussies, echecs = [], 0, []
    for nom, source in (("Adzuna", source_adzuna), ("France Travail", source_france_travail)):
        try:
            res = source(jours, fin)
        except Exception as e:  # une source en panne ne bloque pas les autres
            echecs.append(nom)
            print(f"{nom} : échec ({e})", file=sys.stderr)
            continue
        if res is not None:
            reussies += 1
            offres.extend(res)
    chemin = os.path.join(DOSSIER, "offres.json")
    try:
        existantes = json.load(open(chemin, encoding="utf-8"))
    except (OSError, ValueError):
        existantes = []
    limite = (fin - timedelta(days=30)).strftime("%Y-%m-%d")
    gardees = [o for o in existantes if (o.get("date") or "9999") >= limite and pertinent(o.get("titre"))]
    ids = {o.get("id") for o in gardees}
    urls = {o.get("url") for o in gardees}
    cles = {((o.get("entreprise") or "").lower(), (o.get("titre") or "").lower()) for o in gardees if o.get("entreprise")}
    ajout = []
    for o in offres:
        if not pertinent(o["titre"]):
            continue
        cle = (o["entreprise"].lower(), o["titre"].lower())
        if o["id"] in ids or o["url"] in urls or (o["entreprise"] and cle in cles):
            continue
        ajout.append(o); ids.add(o["id"]); urls.add(o["url"]); cles.add(cle)
    toutes = sorted(gardees + ajout, key=lambda o: o.get("date") or "", reverse=True)
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(toutes, f, ensure_ascii=False, indent=2)
    print(f"{len(ajout)} nouvelles offres ajoutées, {len(existantes) - len(gardees)} anciennes retirées, {len(toutes)} au total.")
    if reussies == 0:
        sys.exit("ERREUR : aucune source d'offres n'a fonctionné. Ajoute ADZUNA_APP_ID et ADZUNA_APP_KEY dans les Secrets GitHub.")


if __name__ == "__main__":
    main()

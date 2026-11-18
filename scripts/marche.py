#!/usr/bin/env python3
"""Compte le marché du métier « Community Manager » (code ROME E1101) à partir des offres.

Canal : API Adzuna (agrégateur d'offres, clé gratuite) — https://developer.adzuna.com
Clés  : ADZUNA_APP_ID et ADZUNA_APP_KEY (Secrets GitHub), jamais dans ce fichier.

Une extraction par jour au maximum (si le CSV du jour existe déjà, le script s'arrête).
Ce qu'il écrit :
  data/offres_AAAA-MM-JJ.csv    toutes les offres de la requête principale, datées
  data/variantes.csv            nombre d'offres par intitulé, une ligne par jour (historique)
  data/historique.csv           volume, contrats, salaires affichés : une ligne par jour
  data/marche.json              les chiffres de la dernière extraction, lus par le site

Usage : python3 scripts/marche.py
"""
import csv, json, os, re, sys, time, urllib.parse, urllib.request, urllib.error
from collections import Counter
from datetime import datetime, timezone

DOSSIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(DOSSIER, "data")
URL = "https://api.adzuna.com/v1/api/jobs/fr/search/{page}"

REQUETE = "community manager"            # requête principale (phrase exacte)
PAGES = 6                                # 6 pages x 50 = 300 offres au plus
VARIANTES = ["community manager", "social media manager", "chargé de communication digitale",
             "content manager", "brand content manager", "chargé de communication",
             "responsable communication digitale", "influence manager"]

# Compétences et outils cherchés dans le titre + l'extrait de description (insensible à la casse)
MOTS = {
    "Réseaux": {"Instagram": r"instagram", "TikTok": r"tik ?tok", "LinkedIn": r"linkedin",
                "Facebook": r"facebook", "YouTube": r"youtube", "X / Twitter": r"twitter|\bx\b \(|réseau x",
                "Pinterest": r"pinterest", "Snapchat": r"snapchat", "Twitch": r"twitch"},
    "Outils": {"Canva": r"canva", "Suite Adobe": r"adobe|photoshop|illustrator|indesign|premiere|after effects",
               "CapCut": r"capcut", "Figma": r"figma", "Meta Business Suite": r"meta business|business suite|business manager",
               "Hootsuite / Agorapulse / Swello": r"hootsuite|agorapulse|swello|later\b|buffer",
               "Google Analytics": r"google analytics|\bga4\b", "WordPress": r"wordpress", "Shopify": r"shopify",
               "HubSpot": r"hubspot", "Mailchimp / Brevo": r"mailchimp|brevo|sendinblue", "Notion": r"notion",
               "Excel": r"excel", "ChatGPT / IA générative": r"chatgpt|ia générative|intelligence artificielle|\bia\b|\bai\b"},
    "Compétences": {"Création de contenu": r"création de contenu|créer du contenu|contenus?", "Rédaction": r"rédaction|rédiger|rédactionnel",
                    "Vidéo / Reels": r"vidéo|video|reels?|montage", "Photo": r"photo", "Stratégie social media": r"stratégie",
                    "Publicité (Ads)": r"\bads\b|publicité|sponsoris|campagnes? payantes|social ads",
                    "Influence": r"influence|influenceu", "SEO": r"\bseo\b|référencement", "Modération / animation": r"modér|animation|animer",
                    "Veille": r"veille", "Reporting / KPI": r"reporting|kpi|statistiques|analyse", "Newsletter / emailing": r"newsletter|emailing|e-mailing",
                    "Événementiel": r"événement|evenement|salon", "Anglais": r"anglais|english"},
}


def appel(params, page=1, essais=3):
    q = dict(params, app_id=os.environ["ADZUNA_APP_ID"].strip(), app_key=os.environ["ADZUNA_APP_KEY"].strip())
    q["content-type"] = "application/json"
    url = URL.format(page=page) + "?" + urllib.parse.urlencode(q)
    for i in range(essais):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "projet-pro/1.0"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and i < essais - 1:
                time.sleep(3 * (i + 1)); continue
            raise
    return {}


def nettoyer(t):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t or "")).strip()


def annuel(x):
    """Ramène un salaire affiché à un montant annuel brut : horaire (< 100) x 1 607 h, mensuel (< 10 000) x 12."""
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    if x <= 0:
        return None
    if x < 100:
        x *= 1607
    elif x < 10000:
        x *= 12
    return x if 5000 <= x <= 150000 else None


def contrat(o):
    texte = (o.get("title", "") + " " + o.get("description", "")).lower()
    if re.search(r"alternan|apprenti|contrat pro", texte):
        return "Alternance"
    if re.search(r"\bstage\b|stagiaire|internship", texte):
        return "Stage"
    ct = (o.get("contract_type") or "").lower()
    if ct == "permanent":
        return "CDI"
    if ct == "contract":
        return "CDD / mission"
    if re.search(r"freelance|indépendant|auto-entrepreneur", texte):
        return "Freelance"
    return "Non précisé"


def main():
    if not os.environ.get("ADZUNA_APP_ID") or not os.environ.get("ADZUNA_APP_KEY"):
        sys.exit("ERREUR : ADZUNA_APP_ID et ADZUNA_APP_KEY manquants (Secrets GitHub).")
    os.makedirs(DATA, exist_ok=True)
    maintenant = datetime.now(timezone.utc)
    jour = maintenant.strftime("%Y-%m-%d")
    fichier_jour = os.path.join(DATA, f"offres_{jour}.csv")
    if os.path.exists(fichier_jour) and "--forcer" not in sys.argv:
        print(f"Extraction du {jour} déjà faite : rien à refaire.")
        return

    # 1. Variantes d'intitulé : combien d'offres pour chaque appellation (phrase exacte)
    variantes = {}
    for v in VARIANTES:
        rep = appel({"title_only": v, "results_per_page": 1})
        variantes[v] = int(rep.get("count") or 0)
        time.sleep(0.5)

    # 2. Offres de la requête principale
    offres, total = [], 0
    for p in range(1, PAGES + 1):
        rep = appel({"title_only": REQUETE, "results_per_page": 50, "sort_by": "date"}, page=p)
        total = int(rep.get("count") or total)
        res = rep.get("results") or []
        offres.extend(res)
        if len(res) < 50:
            break
        time.sleep(0.5)

    lignes = []
    offres = [o for o in offres if re.search(r"community\s*manag|\bcm\b", nettoyer(o.get("title")).lower())]
    for o in offres:
        area = (o.get("location") or {}).get("area") or []
        affiche = str(o.get("salary_is_predicted", "1")) == "0"
        lignes.append({
            "date_extraction": jour, "canal": "Adzuna", "requete": f'title_only="{REQUETE}", pays=fr',
            "id": o.get("id"), "intitule": nettoyer(o.get("title")),
            "entreprise": nettoyer((o.get("company") or {}).get("display_name")),
            "region": area[1] if len(area) > 1 else "", "departement": area[2] if len(area) > 2 else "",
            "lieu": nettoyer((o.get("location") or {}).get("display_name")),
            "contrat": contrat(o), "temps": o.get("contract_time") or "",
            "salaire_min": o.get("salary_min") or "", "salaire_max": o.get("salary_max") or "",
            "salaire_affiche": "oui" if affiche and o.get("salary_min") else "non",
            "date_publication": (o.get("created") or "")[:10], "categorie": (o.get("category") or {}).get("label", ""),
            "extrait_description": nettoyer(o.get("description")), "url": o.get("redirect_url") or "",
        })

    with open(fichier_jour, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0].keys()) if lignes else ["date_extraction"])
        w.writeheader(); w.writerows(lignes)

    # 3. Lecture : volume, géographie, contrats, salaires affichés, compétences, entreprises
    n = len(lignes)
    regions = Counter(l["region"] or "Non précisé" for l in lignes)
    deps = Counter(l["departement"] for l in lignes if l["departement"])
    contrats = Counter(l["contrat"] for l in lignes)
    entreprises = Counter(l["entreprise"] for l in lignes if l["entreprise"])
    teletravail = sum(1 for l in lignes if re.search(r"télétravail|teletravail|remote|full remote|hybride", (l["intitule"] + " " + l["extrait_description"]).lower()))
    auvergne = sum(1 for l in lignes if "auvergne" in l["region"].lower())
    pdd = sum(1 for l in lignes if "puy-de-d" in l["departement"].lower())

    salaires = {}
    for c in contrats:
        vals = []
        for l in lignes:
            if l["contrat"] == c and l["salaire_affiche"] == "oui":
                mn, mx = annuel(l["salaire_min"]), annuel(l["salaire_max"] or l["salaire_min"])
                if mn and mx:
                    vals.append((mn + mx) / 2)
        if vals:
            vals.sort()
            salaires[c] = {"nb": len(vals), "min": round(vals[0]), "mediane": round(vals[len(vals) // 2]), "max": round(vals[-1])}
    nb_affiches = sum(1 for l in lignes if l["salaire_affiche"] == "oui")

    comptes = {}
    for groupe, mots in MOTS.items():
        c = {}
        for nom, motif in mots.items():
            c[nom] = sum(1 for l in lignes if re.search(motif, (l["intitule"] + " " + l["extrait_description"]).lower()))
        comptes[groupe] = sorted(([k, v] for k, v in c.items() if v), key=lambda x: -x[1])

    marche = {
        "date": jour, "heure_utc": maintenant.strftime("%H:%M"), "canal": "Adzuna (API officielle, agrégateur d'offres)",
        "requete": f'title_only="{REQUETE}" (mots dans le titre), pays = France, tri par date, {PAGES} pages de 50 au plus ; puis titre vérifié (« community manag… » ou « CM »)',
        "total_annonce": total, "nb_analysees": n,
        "variantes": sorted(([k, v] for k, v in variantes.items()), key=lambda x: -x[1]),
        "regions": regions.most_common(13), "departements": deps.most_common(10),
        "auvergne": auvergne, "puy_de_dome": pdd, "teletravail": teletravail,
        "contrats": contrats.most_common(), "salaires": salaires, "nb_salaires_affiches": nb_affiches,
        "competences": comptes, "entreprises": entreprises.most_common(15),
    }
    with open(os.path.join(DATA, "marche.json"), "w", encoding="utf-8") as f:
        json.dump(marche, f, ensure_ascii=False, indent=1)

    # 4. Historique : une ligne par jour, pour voir le marché bouger
    hist = os.path.join(DATA, "historique.csv")
    neuf = not os.path.exists(hist)
    with open(hist, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if neuf:
            w.writerow(["date", "canal", "requete", "total_annonce", "nb_analysees", "alternance", "stage", "cdi", "cdd_mission", "salaires_affiches", "ia_citee"])
        ia = dict(comptes["Outils"]).get("ChatGPT / IA générative", 0)
        w.writerow([jour, "Adzuna", REQUETE, total, n, contrats.get("Alternance", 0), contrats.get("Stage", 0), contrats.get("CDI", 0), contrats.get("CDD / mission", 0), nb_affiches, ia])
    var = os.path.join(DATA, "variantes.csv")
    neuf = not os.path.exists(var)
    with open(var, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if neuf:
            w.writerow(["date", "canal", "intitule", "nb_offres"])
        for k, v in variantes.items():
            w.writerow([jour, "Adzuna", k, v])
    print(f"{jour} : {total} offres annoncées pour « {REQUETE} », {n} analysées, {nb_affiches} avec salaire affiché.")


if __name__ == "__main__":
    main()

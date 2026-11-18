#!/usr/bin/env python3
"""Le marché caché : les entreprises du Puy-de-Dôme (63) qui pourraient avoir besoin d'un Community Manager.

Canal : API « Recherche d'entreprises » de l'État (recherche-entreprises.api.gouv.fr), gratuite, sans clé.
Filtres : siège dans le 63, entreprise active, codes d'activité NAF proches du métier.
RGPD : on ne garde que des données d'entreprise (nom, SIREN, activité, commune, effectif, date de création).
Les entrepreneurs individuels (nature juridique 1000, dont le nom est celui d'une personne) et
les dirigeants ne sont PAS enregistrés.

Une extraction par semaine au maximum. Écrit data/entreprises_63.csv et data/entreprises_63.json.
Usage : python3 scripts/entreprises.py [--forcer]
"""
import csv, json, os, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta

DOSSIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(DOSSIER, "data")
API = "https://recherche-entreprises.api.gouv.fr/search"
NAF = {
    "73.11Z": "Agences de publicité",
    "70.21Z": "Conseil en relations publiques et communication",
    "73.12Z": "Régie publicitaire de médias",
    "74.10Z": "Activités spécialisées de design",
    "59.11B": "Production de films institutionnels et publicitaires",
}
EFFECTIF = {"00": "0 salarié", "01": "1-2", "02": "3-5", "03": "6-9", "11": "10-19", "12": "20-49", "21": "50-99",
            "22": "100-199", "31": "200-249", "32": "250-499", "41": "500-999", "42": "1000-1999", "51": "2000-4999",
            "52": "5000-9999", "53": "10000+", "NN": "Non renseigné", None: "Non renseigné"}


def get(params):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "projet-pro/1.0"})
    for i in range(3):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.load(r)
        except Exception:
            time.sleep(2 * (i + 1))
    return {"results": [], "total_pages": 0}


def main():
    os.makedirs(DATA, exist_ok=True)
    meta = os.path.join(DATA, "entreprises_63.json")
    if os.path.exists(meta) and "--forcer" not in sys.argv:
        try:
            ancienne = json.load(open(meta, encoding="utf-8"))["date"]
            if datetime.now(timezone.utc) - datetime.fromisoformat(ancienne + "T00:00:00+00:00") < timedelta(days=7):
                print(f"Base des entreprises du 63 déjà à jour ({ancienne}).")
                return
        except (KeyError, ValueError):
            pass
    jour = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lignes, vus = [], set()
    for code, libelle in NAF.items():
        page, pages = 1, 1
        while page <= pages and page <= 20:
            rep = get({"activite_principale": code, "departement": "63", "etat_administratif": "A", "per_page": 25, "page": page})
            pages = rep.get("total_pages") or 0
            for e in rep.get("results", []):
                siege = e.get("siege") or {}
                if e.get("siren") in vus or str(e.get("nature_juridique")) == "1000":
                    continue
                if not str(siege.get("code_postal") or "").startswith("63"):
                    continue
                vus.add(e.get("siren"))
                lignes.append({
                    "date_extraction": jour, "canal": "API Recherche d'entreprises (data.gouv)",
                    "nom": e.get("nom_complet") or "", "siren": e.get("siren") or "",
                    "naf": code, "activite": libelle,
                    "commune": siege.get("libelle_commune") or "", "code_postal": siege.get("code_postal") or "",
                    "effectif": EFFECTIF.get(e.get("tranche_effectif_salarie"), "Non renseigné"),
                    "date_creation": e.get("date_creation") or "",
                    "categorie": e.get("categorie_entreprise") or "",
                    "fiche": f"https://annuaire-entreprises.data.gouv.fr/entreprise/{e.get('siren')}",
                })
            page += 1
            time.sleep(0.3)
    ordre = {v: i for i, v in enumerate(EFFECTIF.values())}
    lignes.sort(key=lambda l: (-ordre.get(l["effectif"], 0) if l["effectif"] != "Non renseigné" else 1, l["nom"]))
    with open(os.path.join(DATA, "entreprises_63.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0].keys()) if lignes else ["date_extraction"])
        w.writeheader(); w.writerows(lignes)
    par_naf = {}
    for l in lignes:
        par_naf[l["activite"]] = par_naf.get(l["activite"], 0) + 1
    communes = {}
    for l in lignes:
        communes[l["commune"]] = communes.get(l["commune"], 0) + 1
    avec_salaries = [l for l in lignes if l["effectif"] not in ("0 salarié", "Non renseigné")]
    json.dump({"date": jour, "canal": "API Recherche d'entreprises (recherche-entreprises.api.gouv.fr)",
               "requete": "siège dans le 63, entreprises actives, NAF " + ", ".join(NAF), "total": len(lignes),
               "avec_salaries": len(avec_salaries), "par_activite": sorted(par_naf.items(), key=lambda x: -x[1]),
               "communes": sorted(communes.items(), key=lambda x: -x[1])[:10],
               "exemples": avec_salaries[:25]}, open(meta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{jour} : {len(lignes)} entreprises du 63 ({len(avec_salaries)} avec salariés).")


if __name__ == "__main__":
    main()

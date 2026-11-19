#!/usr/bin/env python3
"""Faire parler la base du 63 : quelles entreprises de la liste recrutent en ce moment ?

Méthode : on récupère les offres d'emploi publiées dans le Puy-de-Dôme (tous métiers, API Adzuna),
puis on cherche le nom de chaque entreprise de data/entreprises_63.json parmi les employeurs de ces offres.
Une entreprise « recrute » si elle a au moins une offre publiée, quel que soit le poste.

Clés : ADZUNA_APP_ID et ADZUNA_APP_KEY (Secrets GitHub).
Écrit data/recrutent_63.json (lu par le site) et data/recrutent_63_AAAA-MM-JJ.csv (daté).
Une fois par jour au maximum.
"""
import csv, json, os, re, sys, time, unicodedata, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timezone

DOSSIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(DOSSIER, "data")
URL = "https://api.adzuna.com/v1/api/jobs/fr/search/{page}"
PAGES = 20  # 20 pages x 50 = les 1 000 offres les plus récentes du département
FORMES = r"\b(SARL|SAS|SASU|SA|EURL|SNC|SCOP|SCI|EI|GROUPE|STE|SOCIETE|AGENCE|LA|LE|LES|L|DE|DU|DES|ET)\b"


def norm(t):
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().upper()
    t = re.sub(r"[^A-Z0-9 ]", " ", t)
    t = re.sub(FORMES, " ", t)
    return re.sub(r"\s+", " ", t).strip()


GENERIQUES = {"COMMUNICATION", "DESIGN", "PUBLICITE", "MEDIA", "MEDIAS", "CONSEIL", "STUDIO", "PRODUCTION", "PRODUCTIONS",
              "CREATION", "CREATIONS", "GRAPHIQUE", "DIGITAL", "MARKETING", "IMPRESSION", "EVENEMENT", "EVENEMENTS", "WEB", "FILMS"}


def noms(nom):
    """Le nom principal et les noms entre parenthèses (enseignes), normalisés."""
    morceaux = [nom.split("(")[0]] + [x for p in re.findall(r"\(([^)]*)\)", nom) for x in p.split("/")]
    return {n for n in (norm(m) for m in morceaux) if len(n) >= 4 and n not in GENERIQUES
            and not all(w in GENERIQUES for w in n.split())}


def appel(page):
    q = {"app_id": os.environ["ADZUNA_APP_ID"].strip(), "app_key": os.environ["ADZUNA_APP_KEY"].strip(),
         "where": "Puy-de-Dôme", "results_per_page": 50, "sort_by": "date", "content-type": "application/json"}
    req = urllib.request.Request(URL.format(page=page) + "?" + urllib.parse.urlencode(q),
                                 headers={"Accept": "application/json", "User-Agent": "projet-pro/1.0"})
    for i in range(3):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and i < 2:
                time.sleep(3 * (i + 1)); continue
            raise
    return {}


def main():
    if not os.environ.get("ADZUNA_APP_ID") or not os.environ.get("ADZUNA_APP_KEY"):
        sys.exit("ERREUR : clés Adzuna manquantes.")
    jour = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sortie = os.path.join(DATA, "recrutent_63.json")
    if os.path.exists(sortie) and "--forcer" not in sys.argv:
        try:
            if json.load(open(sortie, encoding="utf-8")).get("date") == jour:
                print("Recruteurs du 63 déjà calculés aujourd'hui."); return
        except ValueError:
            pass
    base = json.load(open(os.path.join(DATA, "entreprises_63.json"), encoding="utf-8"))["toutes"]

    offres, total = [], 0
    for p in range(1, PAGES + 1):
        rep = appel(p)
        total = int(rep.get("count") or total)
        res = rep.get("results") or []
        offres.extend(res)
        if len(res) < 50:
            break
        time.sleep(0.5)
    employeurs = {}
    for o in offres:
        e = (o.get("company") or {}).get("display_name") or ""
        employeurs.setdefault(norm(e), []).append({"titre": re.sub(r"<[^>]+>", "", o.get("title") or ""), "url": o.get("redirect_url") or "",
                                                   "date": (o.get("created") or "")[:10]})

    trouve, lignes = {}, []
    for ent in base:
        cands = noms(ent["nom"])
        for emp, liste in employeurs.items():
            if not emp:
                continue
            # Égalité exacte, ou un nom d'au moins deux mots retrouvé en entier dans l'autre
            if any(c == emp
                   or (len(c.split()) >= 2 and re.search(r"\b" + re.escape(c) + r"\b", emp))
                   or (len(emp.split()) >= 2 and re.search(r"\b" + re.escape(emp) + r"\b", c)) for c in cands):
                trouve.setdefault(ent["siren"], []).extend(liste)
        if ent["siren"] in trouve:
            for o in trouve[ent["siren"]]:
                lignes.append({"date_extraction": jour, "siren": ent["siren"], "entreprise": ent["nom"], "offre": o["titre"], "date_publication": o["date"], "url": o["url"]})

    json.dump({"date": jour, "canal": "Adzuna (API officielle)",
               "requete": f'where="Puy-de-Dôme", tous métiers, tri par date, {PAGES} pages de 50 au plus',
               "total_annonce": total, "nb_analysees": len(offres), "nb_employeurs": len([e for e in employeurs if e]),
               "recrutent": {s: v[:5] for s, v in trouve.items()}},
              open(sortie, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(os.path.join(DATA, f"recrutent_63_{jour}.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date_extraction", "siren", "entreprise", "offre", "date_publication", "url"])
        w.writeheader(); w.writerows(lignes)
    print(f"{jour} : {len(offres)} offres du 63 analysées, {len(employeurs)} employeurs, {len(trouve)} entreprises de la base recrutent.")


if __name__ == "__main__":
    main()

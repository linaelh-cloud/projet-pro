# Projet Pro : Community Manager, le métier compté

Séminaires métiers · M2 Marketing Opérationnel & Digital · IAE Clermont Auvergne · 2026-2027
Lina El Hamzaoui

**Le site : https://linaelh-cloud.github.io/projet-pro/**

Ce site rend compte du métier que je vise, **Community Manager**, à partir des offres d'emploi, et il est aussi l'outil qui cherche à ma place : une veille automatique récupère chaque jour les offres et met le site à jour, sans mon ordinateur.

## Le métier ciblé

| | |
|---|---|
| Intitulé principal | Community Manager |
| Variantes suivies | Social media manager, chargé·e de communication digitale, content manager, brand content manager, chargé·e de communication, responsable communication digitale, influence manager |
| Code ROME | **E1101** · Animation de site multimédia (répertoire ROME de France Travail, via Métierscope) |
| Contrat recherché | Alternance ou stage |

### Les questions que je pose au marché

1. Combien d'offres, où, et quelle part en Auvergne et dans le Puy-de-Dôme ?
2. Ce métier recrute-t-il surtout en alternance et en stage, ou en CDI ?
3. Quels salaires sont affichés, et combien d'offres n'en affichent pas ?
4. Quels réseaux, outils et compétences reviennent, et lesquels ma formation ne me donne pas ?
5. Qui recrute : les offres publiées, et les entreprises du 63 qui ne publient pas ?

## Ce que contient le site

| Onglet | Contenu |
|---|---|
| Mon métier compté | Variantes d'intitulé, volume, régions, contrats, salaires affichés, compétences et outils comptés, historique, acteurs, ma position et mes 3 actions datées |
| Offres du jour | Les nouvelles offres de stage et d'alternance, filtrables, avec un bouton pour postuler |
| Lettre de motivation | Prépare une lettre adaptée à une annonce avec Claude |
| Mes candidatures | Suivi de mes candidatures par secteur et par statut (enregistré dans mon navigateur uniquement) |
| Comment c'est fait | La chaîne complète, les canaux, les scripts, la règle RGPD et les limites |

## Comment le site est fait

```
API Adzuna + API Recherche d'entreprises
        → scripts Python (scripts/)
        → données datées (data/)
        → GitHub Actions (toutes les 3 heures, ordinateur éteint)
        → GitHub Pages (ce site)
```

### Les canaux

| Canal | Usage | État |
|---|---|---|
| [API Adzuna](https://developer.adzuna.com) (agrégateur, clé gratuite) | Offres du jour et comptage du marché | Actif |
| [API Recherche d'entreprises](https://recherche-entreprises.api.gouv.fr) (data.gouv, sans clé) | Entreprises du Puy-de-Dôme proches du métier (marché caché) | Actif |
| API France Travail « Offres d'emploi v2 » | Canal commun du cours | Accès demandé le 18/11/2026 : l'API n'est plus en libre-service. Le script `recuperer_offres.py` l'utilisera dès que l'accès sera accordé |
| LinkedIn, Indeed, Apec | Recherche manuelle uniquement | Leurs conditions d'utilisation interdisent le scraping : aucun robot |

### Les scripts

| Fichier | Rôle | Fréquence |
|---|---|---|
| `scripts/recuperer_offres.py` | Nouvelles offres de stage et d'alternance → `offres.json` (onglet Offres du jour) | Toutes les 3 heures |
| `scripts/marche.py` | Extraction datée du marché → `data/offres_AAAA-MM-JJ.csv`, `data/historique.csv`, `data/variantes.csv`, `data/marche.json` | Une fois par jour |
| `scripts/entreprises.py` | Entreprises du 63 → `data/entreprises_63.csv` et `.json` | Une fois par semaine |
| `.github/workflows/offres.yml` | Le robot GitHub Actions qui lance les scripts et enregistre les données par un commit | Toutes les 3 heures (et bouton « Run workflow ») |

Relancer une extraction à la main : onglet **Actions** du dépôt → **Offres du jour** → **Run workflow**.

### Les requêtes

- **Comptage du marché** (`marche.py`) : API Adzuna, pays France, `title_only="community manager"`, tri par date, 6 pages de 50 au plus. Les titres sont ensuite vérifiés (« community manag… » ou « CM »). Chaque variante est comptée avec `title_only=<intitulé>`.
- **Offres du jour** (`recuperer_offres.py`) : API Adzuna, mots-clés « community manager alternance / apprentissage / stage » et « social media manager alternance / stage », annonces des 3 derniers jours.
- **Marché caché** (`entreprises.py`) : API Recherche d'entreprises, siège dans le département 63, entreprises actives, codes NAF 73.11Z (agences de publicité), 70.21Z (conseil en relations publiques et communication), 73.12Z (régie publicitaire), 74.10Z (design), 59.11B (films institutionnels et publicitaires).

### Les limites

- Adzuna regroupe beaucoup de sites, mais pas tous. Son compteur repose sur des mots du titre et inclut des doublons.
- Les compétences sont comptées dans le titre et l'extrait de description fourni par l'API, pas dans l'annonce complète : les chiffres sont des minimums.
- Les salaires sont des **salaires affichés** par une minorité d'offres, ramenés à un montant annuel brut (horaire × 1 607 h, mensuel × 12). Ce ne sont pas les salaires réels du métier.
- Le type de contrat est déduit du texte (« alternance », « stage ») ou de la donnée Adzuna.
- Le code NAF ne dit pas si une entreprise a besoin d'un community manager : la base du 63 est une liste de cibles à vérifier.

## Règle RGPD pour les contacts

- Seules des **données d'entreprise** sont enregistrées (nom, SIREN, activité, commune, effectif, date de création). Les noms des dirigeants et les entrepreneurs individuels, dont le nom est celui d'une personne, sont exclus.
- Les professionnels sont contactés **à la main** sur LinkedIn, en lien avec leur fonction et pour une finalité claire : ma candidature. Aucun e-mail ni téléphone personnel n'est collecté. Chacun peut refuser le contact.
- Aucun fichier n'est constitué pour être revendu ou partagé.
- Mes candidatures restent dans mon navigateur : elles ne sont pas publiées sur GitHub.
- Les clés des API sont dans les **Secrets** de GitHub, jamais dans le code.

## Professionnels repérés sur LinkedIn

Repérés à la main, dans des entreprises qui recrutent cet intitulé (prénom, fonction et entreprise uniquement) :

1. _à compléter_
2. _à compléter_
3. _à compléter_

## Ma position et mes 3 actions datées

Le métier recrute surtout en alternance et en stage, et surtout en Île-de-France ; en Auvergne, les offres publiées sont rares, mais le marché caché du Puy-de-Dôme compte plus de 300 entreprises de communication, de publicité et de design. La vidéo courte et TikTok sont au cœur des annonces : c'est ce que je dois prouver.

| Date | Action | Preuve |
|---|---|---|
| Avant le 15/12/2026 | Contacter 15 entreprises du 63 choisies dans la base du marché caché | Suivi dans l'onglet Mes candidatures |
| Avant le 31/01/2027 | Créer un portfolio de 10 vidéos courtes (Reels, TikTok) montées sur CapCut | Lien vers le portfolio |
| Avant le 28/02/2027 | Obtenir une certification Google Analytics | Certificat Google Skillshop |

## Sources

- Apec, *L'IA dans les métiers du commercial et du marketing*, mars 2026 : https://www.apec.fr/tendances-emploi-cadre/evolution-des-metiers-et-competences/quel-impact-de-l-ia-sur-les-competences-des-metiers-du-commercial-et-du-marketing-.html
- Cours *Séminaires métiers*, V. Favarin : https://metier.iae-mod.fr

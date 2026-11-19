# Mon Projet Pro : Community Manager, le métier compté

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
| Contrat recherché | Stage de 3 à 6 mois à partir de janvier 2027 (Master 2), ou alternance |

### Les questions que je pose au marché

1. Combien d'offres, où, et quelle part en Auvergne et dans le Puy-de-Dôme ?
2. Ce métier recrute-t-il surtout en alternance et en stage, ou en CDI ?
3. Quels salaires sont affichés, et combien d'offres n'en affichent pas ?
4. Quels réseaux, outils et compétences reviennent, et lesquels ma formation ne me donne pas ?
5. Qui recrute : les offres publiées, et les entreprises du 63 qui ne publient pas ?

## Ce que contient le site

| Onglet | Contenu |
|---|---|
| Mon métier compté | 1. Intitulés et code métier · 2. Le marché en chiffres · 3. Compétences recherchées (et ce que ma formation ne me donnera pas) · 4. Évolution du métier · 5. Les recruteurs (dont le marché caché du 63) · 6. Bilan et plan d'action. Chaque chiffre a sa source et ses limites, dans un menu « Source et limites » |
| Offres du jour | Les nouvelles offres de stage et d'alternance trouvées par la veille, filtrables, dépliables, avec un bouton pour postuler |
| Lettre de motivation | Écrit sur la page une lettre adaptée à une offre (API Gemini), à partir de mon CV en PDF, du lien de l'annonce et de ce que je veux mettre en avant |
| Mes candidatures | Suivi de mes candidatures par secteur et par statut (enregistré dans mon navigateur uniquement) |
| Méthodologie | La chaîne complète, les canaux, les scripts, la règle RGPD et les limites |

## Comment le site est fait

```
API Adzuna + API Recherche d'entreprises (+ API Gemini pour la lettre)
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
| API Gemini de Google (offre gratuite, clé personnelle) | Rédaction de la lettre de motivation | Actif : la clé reste dans mon navigateur ; téléphone, e-mail et adresse sont masqués avant l'envoi |
| API France Travail « Offres d'emploi v2 » | Canal commun du cours | Accès demandé : l'API n'est plus en libre-service. Le script `recuperer_offres.py` l'utilisera dès que l'accès sera accordé |
| LinkedIn, Indeed, Apec | Recherche manuelle uniquement | Leurs conditions d'utilisation interdisent le scraping : aucun robot |

### Les scripts

| Fichier | Rôle | Fréquence |
|---|---|---|
| `scripts/recuperer_offres.py` | Nouvelles offres de stage et d'alternance → `offres.json` (onglet Offres du jour) | Toutes les 3 heures |
| `scripts/marche.py` | Extraction datée du marché → `data/offres_AAAA-MM-JJ.csv`, `data/historique.csv`, `data/variantes.csv`, `data/competences.csv` (mots comptés par date), `data/marche.json` | Une fois par jour |
| `scripts/entreprises.py` | Entreprises du 63 → `data/entreprises_63.csv` et `.json` | Une fois par semaine |
| `scripts/recrutent.py` | Fait parler la base : compare les 330 entreprises du 63 aux employeurs des 1 000 offres les plus récentes du département (Adzuna) → `data/recrutent_63.json` et `data/recrutent_63_AAAA-MM-JJ.csv` | Une fois par jour |
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
- Aucun contact nominatif n'est collecté : ni e-mail, ni téléphone, ni nom de personne.
- Aucun fichier n'est constitué pour être revendu ou partagé.
- Mes candidatures et mon CV restent dans mon navigateur : ils ne sont pas publiés sur GitHub.
- Pour la lettre de motivation, mon téléphone, mon e-mail et mon adresse sont remplacés par des repères avant l'envoi à Gemini, puis remis dans la lettre.
- Les clés des API sont dans les **Secrets** de GitHub, jamais dans le code.

## Le métier en bref (extraction du 19/11/2026)

| | |
|---|---|
| Le volume | 1 176 annonces en France avec « community manager » dans le titre |
| Les contrats | 62 % des offres analysées sont des alternances ou des stages |
| La géographie | 43 % des offres sont en Île-de-France |
| La compétence la plus citée | Modération et animation de communauté (35 % des offres) |
| L'intitulé voisin | « Chargé de communication », presque autant d'offres (1 161) |
| Le marché caché | 330 entreprises de communication, publicité et design dans le Puy-de-Dôme, aucune avec une offre publiée |

Ces chiffres sont mis à jour automatiquement sur le site.

## Ma position et mes 3 actions datées

Community Manager est un métier qui s'ouvre par le stage et l'alternance, centré sur l'animation de communauté et la création de contenu. Les offres se concentrent à Paris : en Auvergne, je vais chercher les entreprises directement, sans attendre une annonce.

| Date | Action | Preuve |
|---|---|---|
| Avant le 15/12/2026 | Contacter 15 entreprises du 63 choisies dans la base du marché caché | Suivi dans l'onglet Mes candidatures |
| Avant le 31/01/2027 | Créer un portfolio de 10 vidéos courtes (Reels, TikTok) montées sur CapCut | Lien vers le portfolio |
| Avant le 28/02/2027 | Obtenir une certification Google Analytics | Certificat Google Skillshop |

## Sources

- Apec, *L'IA dans les métiers du commercial et du marketing*, mars 2026 : https://www.apec.fr/tendances-emploi-cadre/evolution-des-metiers-et-competences/quel-impact-de-l-ia-sur-les-competences-des-metiers-du-commercial-et-du-marketing-.html
- Cours *Séminaires métiers*, V. Favarin : https://metier.iae-mod.fr

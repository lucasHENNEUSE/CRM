# CRM — POC 2

## Contexte du projet

Ce dépôt correspond au travail mené dans le cadre du POC 2 du projet CRM.

Le POC 2 s’appuie actuellement sur le fichier `Entreprises entites stagiaires.csv`, analysé dans un notebook EDA puis transformé par l’ETL POC 2 en plusieurs sorties JSON structurées.

Le travail mené dans ce cadre couvre notamment :

* la préparation des fichiers source ;
* l’analyse exploratoire des données ;
* la transformation des données dans des formats structurés ;
* l’alimentation de MongoDB comme zone de staging intermédiaire ;
* la préparation de l’intégration progressive des données dans le CRM Django / CremeCRM ;
* la stabilisation de cette chaîne de traitement pour la suite du projet.

En amont, un travail de réorganisation du dépôt a été engagé afin de rendre le projet plus lisible, plus maintenable et plus simple à reprendre pour la suite.

## Objectifs du POC 2

Le POC 2 a pour objectifs de :

* poursuivre la mise en place de la chaîne de traitement des données autour du CRM ;
* valider les différentes étapes de transformation, d’import et d’export ;
* préparer l’intégration progressive des données dans l’environnement Django / CremeCRM ;
* intégrer les contacts dans la page Contacts d’origine de CremeCRM, avec des rôles ou champs permettant le filtrage métier ;
* préparer une base de travail qui pourra accueillir des tests alignés avec la cible POC 2 ;
* disposer d’une base de travail exploitable pour la suite du projet.

## Contenu du dépôt

Le dépôt est organisé autour de quatre ensembles principaux :

* `creme_crm/`, qui contient le socle applicatif Django / CremeCRM ;
* les dossiers `project_*`, qui regroupent les éléments propres au projet ;
* `logs/`, qui contient les fichiers de logs générés localement ;
* `pytest.ini`, qui conserve une configuration pytest du projet.

Cette organisation permet de distinguer clairement le code applicatif, les scripts projet, les données, les notebooks, la documentation, les traces techniques d’exécution et la configuration pytest.

## Organisation du dépôt

```text
CRM/
├── README.md
├── pytest.ini
├── creme_crm/
├── project_scripts/
│   ├── preparation/
│   ├── ETL/
│   ├── imports/
│   ├── exports/
│   ├── cleaning/
│   └── simulation/
├── project_data/
│   ├── raw/
│   ├── intermediate/
│   ├── processed/
│   └── exports/
├── project_notebooks/
├── project_docs/
└── logs/
```

## Rôle des dossiers

### `creme_crm/`

Ce dossier contient le code applicatif Django / CremeCRM.

Il conserve notamment :

* les apps Django ;
* `manage.py` ;
* les fichiers directement liés au fonctionnement de l’application.

Exemple :

* `creme_crm/creme/persons/fix_contact_addresses.py`

### `project_scripts/`

Ce dossier contient les scripts du projet, rangés par rôle.

* `project_scripts/preparation/` : préparation et transformation des fichiers source ;
* `project_scripts/ETL/` : scripts ETL du projet ;
* `project_scripts/imports/` : alimentation de MongoDB et préparation de l’intégration CRM ;
* `project_scripts/exports/` : extraction de données ;
* `project_scripts/cleaning/` : nettoyage et correction de données ;
* `project_scripts/simulation/` : orchestration, relance locale et scripts de pilotage.

### `project_data/`

Ce dossier contient les données du projet.

* `project_data/raw/` : données brutes ;
* `project_data/intermediate/` : données intermédiaires ;
* `project_data/processed/` : données transformées ou prêtes à usage ;
* `project_data/exports/` : fichiers produits par la chaîne de traitement lorsqu’un export est nécessaire.

### `project_notebooks/`

Ce dossier contient les notebooks d’analyse et d’exploration de données.

### `project_docs/`

Ce dossier contient la documentation propre au projet : notes de travail, documents de cadrage, synthèses et éléments utiles à la reprise du dépôt.

### `logs/`

Ce dossier contient les fichiers de logs générés localement par les scripts du projet.

Il peut contenir notamment :

* les logs techniques ;
* les logs liés aux traitements de données.

Les fichiers `.log` générés dans ce dossier ne sont pas destinés à être versionnés dans Git.

### `pytest.ini`

Ce fichier contient une configuration `pytest` conservée dans le dépôt.

Les tests spécifiques alignés avec la cible actuelle du POC 2 seront ajoutés ou réorganisés lorsque l’intégration dans la page Contacts sera stabilisée.

## Scripts réorganisés

Les scripts ont été reclassés selon leur fonction dans la chaîne de traitement des données.

### Scripts de préparation

`repare_csv.py`
Transforme un fichier Excel source en fichier CSV nettoyé, avec suppression de doublons.
Emplacement cible : `project_scripts/preparation/repare_csv.py`

`gen_json_complet.py`
Transforme le fichier CSV préparé en JSON structuré, destiné à alimenter la suite de la chaîne de traitement.
Emplacement cible : `project_scripts/preparation/gen_json_complet.py`

### Scripts ETL

`ETL_poc1.py`
Ancien pipeline du POC 1, conservé comme trace ou référence technique.
Emplacement : `project_scripts/ETL/ETL_poc1.py`

`ETL_poc2.py`
Script ETL de référence du POC 2. Il produit les JSON structurés dans `project_data/processed/`.
Emplacement : `project_scripts/ETL/ETL_poc2.py`

### Scripts d’import

`load_poc2_to_mongo.py`
Charge les cinq JSON du POC 2 depuis `project_data/processed/` vers la base MongoDB `crm_poc2`, dans les collections `entites`, `contacts_crm`, `adresses`, `taxe_events` et `suivi_pedagogique`. Le script vide puis recharge uniquement ces cinq collections.
Emplacement : `project_scripts/imports/load_poc2_to_mongo.py`

`gen_mongo.py`
Lit le fichier `contacts_mongo.json`, enrichit les documents avec des statuts, puis alimente la collection Mongo `prospects_bruts`.
Emplacement cible : `project_scripts/imports/gen_mongo.py`

`split_and_import.py`
Lit les données structurées et répartit les contacts dans les collections Mongo `prospects_taxe` et `prospects_emailing`.
Emplacement cible : `project_scripts/imports/split_and_import.py`

`import_mongo.py`
Lit les documents présents dans MongoDB puis crée ou met à jour les contacts et adresses dans le CRM via Django.
Emplacement cible : `project_scripts/imports/import_mongo.py`

`deploy_to_crm.py`
Met à jour dans la base du CRM les statuts et la visibilité de contacts déjà présents, à partir des collections Mongo.
Emplacement cible : `project_scripts/imports/deploy_to_crm.py`

Les scripts `gen_mongo.py`, `split_and_import.py`, `import_mongo.py` et `deploy_to_crm.py` sont liés au POC 1 et à l’ancien flux. Ils ne doivent pas être repris tels quels pour la cible actuelle du POC 2.

### Scripts d’export

Les scripts d’export ci-dessous appartiennent à l’ancien flux POC 1 et ne définissent pas les fonctionnalités actuelles du POC 2.

`export_emailing.py`
Extrait depuis MongoDB les contacts concernés par l’emailing et génère un fichier JSON d’export.
Emplacement cible : `project_scripts/exports/export_emailing.py`

`export_taxe.py`
Extrait depuis MongoDB les contacts concernés par la taxe et génère un fichier JSON d’export.
Emplacement cible : `project_scripts/exports/export_taxe.py`

### Script de nettoyage

`cleanup_contacts.py`
Analyse les contacts présents dans la base du CRM, détecte les doublons d’emails et supprime les fiches en double.
Emplacement cible : `project_scripts/cleaning/cleanup_contacts.py`

### Script de simulation / relance

`main.py`
Orchestre plusieurs étapes techniques de relance de l’environnement : nettoyage du cache, dépendances, migrations, population, génération des médias, lancement du serveur et génération des logs locaux.
Emplacement cible : `project_scripts/simulation/main.py`

### Script conservé côté applicatif Django

`fix_contact_addresses.py`
Corrige et migre des données d’adresse sur les contacts, puis met à jour la configuration d’affichage de la vue Contact.
Emplacement conservé dans l’application : `creme_crm/creme/persons/fix_contact_addresses.py`

### Script supprimé

`update_view.py`
Ce script modifiait la configuration de la vue Contact en ajoutant certains champs.
Statut : supprimé.

## Données

Le dossier `project_data/` regroupe les fichiers manipulés par la chaîne de traitement du projet.

Il est organisé en plusieurs sous-dossiers correspondant aux différentes étapes de transformation des données.

### `project_data/raw/`

Ce dossier contient les fichiers source bruts, tels qu’ils sont fournis au projet.

Il contient notamment :

* les fichiers Excel source ;
* les fichiers CSV source ;
* plus généralement, les données d’entrée avant tout traitement.

### `project_data/intermediate/`

Ce dossier contient les fichiers intermédiaires produits au cours du projet.

Il regroupe les fichiers générés à des étapes de travail intermédiaires, avant obtention d’un format final ou stabilisé.

Les fichiers de ce dossier correspondent à des étapes de travail intermédiaires et ne constituent pas les données POC 2 stabilisées.

### `project_data/processed/`

Ce dossier contient les données POC 2 transformées et stabilisées, prêtes à être chargées dans la zone de staging MongoDB :

* `poc2_entites.json`
* `poc2_contacts_crm.json`
* `poc2_adresses.json`
* `poc2_taxe_events.json`
* `poc2_suivi_pedagogique.json`

### `project_data/exports/`

Ce dossier est réservé aux exports générés par les traitements du projet lorsqu’un fichier doit être produit pour consultation, transmission ou réutilisation.

Les sorties stabilisées du POC 2 actuel sont documentées dans `project_data/processed/`.

### Logique d’ensemble

L’organisation de `project_data/` suit la progression habituelle du projet :

1. dépôt des fichiers source dans `raw/` ;
2. production de fichiers intermédiaires dans `intermediate/` ;
3. consolidation de données stabilisées dans `processed/` ;
4. production éventuelle de fichiers de sortie dans `exports/`.

Cette séparation permet de mieux suivre le cycle de vie des données et d’éviter de mélanger fichiers bruts, fichiers de travail et fichiers de sortie.

## Versionnement des données

Les données présentes dans `project_data/` ne sont pas destinées à être versionnées par défaut.

La règle retenue dans le projet est la suivante :

* les données de travail ne sont pas versionnées ;
* seule la structure des dossiers est conservée dans le dépôt ;
* la documentation expliquant le rôle des dossiers et l’ordre des traitements doit être versionnée.

Cela concerne en particulier :

* `project_data/raw/`
* `project_data/intermediate/`
* `project_data/processed/`
* `project_data/exports/`

Cette décision s’explique par le fait que ces dossiers peuvent contenir des fichiers :

* volumineux ;
* régénérables ;
* susceptibles d’évoluer souvent ;
* parfois sensibles selon leur contenu ;
* peu adaptés à un suivi dans Git.

## Logs

Le projet utilise un dossier `logs/` à la racine pour centraliser les traces d’exécution locales.

Deux fichiers principaux sont prévus :

* `logs_technique.log`
* `logs_data.log`

Ces fichiers sont générés localement par le script de relance et ne sont pas destinés à être versionnés dans Git.

## Exécution locale

Le projet s’appuie sur deux éléments techniques :

* l’environnement Django / CremeCRM, qui correspond au CRM lui-même ;
* une base MongoDB locale, utilisée comme zone de staging intermédiaire pour stabiliser les données POC 2 avant leur intégration dans CremeCRM, et non comme modèle applicatif final.

Selon les scripts exécutés, il peut donc être nécessaire de travailler à la fois avec Django et avec MongoDB.

### MongoDB local

Docker Compose est le mode principal de lancement de MongoDB pour le projet CRM.

Dans l’environnement Docker Compose actuel du projet, MongoDB est configuré sur le port `27018`.

Commande de démarrage :

```bash
docker compose up -d mongodb
```

Chargement des données POC 2 :

```bash
MONGODB_URI="mongodb://localhost:27018/" python project_scripts/imports/load_poc2_to_mongo.py
```

Le script `load_poc2_to_mongo.py` utilise par défaut le port standard MongoDB `27017`.

La variable d’environnement `MONGODB_URI` permet d’adapter la connexion selon l’environnement local, notamment au port `27018` configuré par Docker Compose dans ce projet.

### Django local

Les scripts liés au CRM s’appuient sur l’environnement Django contenu dans `creme_crm/`.

Dans certains cas, il est nécessaire de forcer le `PYTHONPATH` pour garantir que Python charge correctement les modules du projet local.

Exemple :

```bash
PYTHONPATH=./creme_crm python ./creme_crm/creme/manage.py migrate --settings=creme.dev_settings
```

### Paramètres de développement

Le travail local s’appuie sur :

* `creme.dev_settings`
* la base SQLite locale `./creme_crm/db.sqlite3`

Ces paramètres permettent de travailler sur un environnement local de développement, indépendant d’un environnement de production.

### MongoDB Compass

`MongoDB Compass` peut être utilisé comme outil de confort pour visualiser la base MongoDB locale, vérifier les collections et contrôler certains imports. Il ne remplace pas le service MongoDB lancé par Docker Compose.

Connexions possibles :

* avec le Docker Compose actuel du projet :

  ```text
  mongodb://localhost:27018/
  ```

* si MongoDB est lancé sur le port standard :

  ```text
  mongodb://localhost:27017/
  ```

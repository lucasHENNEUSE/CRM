# CRM — POC 2

## Contexte du projet

Ce dépôt correspond au travail mené dans le cadre du POC 2 du projet CRM.

Après une première phase de mise en place réalisée dans le POC 1, ce second POC vise à poursuivre le travail engagé sur la chaîne de traitement des données et sur leur intégration dans l’environnement CRM. Le projet a vocation à s’appuyer sur un fichier de 100 contacts ainsi que sur plusieurs étapes de transformation permettant de préparer, structurer, importer et exploiter ces données.

Le travail mené dans ce cadre couvre notamment :

* la préparation des fichiers source ;
* la transformation des données dans des formats intermédiaires ;
* l’alimentation de MongoDB ;
* l’intégration des données dans le CRM Django / CremeCRM ;
* la vérification du bon fonctionnement global de cette chaîne ;
* la structuration progressive des logs et des tests du projet.

En amont, un travail de réorganisation du dépôt a été engagé afin de rendre le projet plus lisible, plus maintenable et plus simple à reprendre pour la suite.

## Objectifs du POC 2

Le POC 2 a pour objectifs de :

* poursuivre la mise en place de la chaîne de traitement des données autour du CRM ;
* valider les différentes étapes de transformation, d’import et d’export ;
* vérifier l’intégration correcte des données dans l’environnement Django / CremeCRM ;
* structurer les outils de suivi technique du projet, notamment les logs et les tests ;
* disposer d’une base de travail exploitable pour la suite du projet.

## Contenu du dépôt

Le dépôt est organisé autour de quatre ensembles principaux :

* `creme_crm/`, qui contient le socle applicatif Django / CremeCRM ;
* les dossiers `project_*`, qui regroupent les éléments propres au projet ;
* `logs/`, qui contient les fichiers de logs générés localement ;
* `pytest.ini`, qui centralise la configuration des tests du projet.

Cette organisation permet de distinguer clairement le code applicatif, les scripts projet, les données, les notebooks, la documentation, les traces techniques d’exécution et la configuration des tests.

## Organisation du dépôt

```text
CRM/
├── README.md
├── pytest.ini
├── creme_crm/
├── project_scripts/
│   ├── preparation/
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

On y laisse :

* les apps Django ;
* `manage.py` ;
* les fichiers directement liés au fonctionnement de l’application.

Exemple :

* `creme_crm/creme/persons/fix_contact_addresses.py`

### `project_scripts/`

Ce dossier contient les scripts du projet, rangés par rôle.

* `project_scripts/preparation/` : préparation et transformation des fichiers source ;
* `project_scripts/imports/` : alimentation de MongoDB et du CRM ;
* `project_scripts/exports/` : extraction de données ;
* `project_scripts/cleaning/` : nettoyage et correction de données ;
* `project_scripts/simulation/` : orchestration, relance locale et scripts de pilotage.

### `project_data/`

Ce dossier contient les données du projet.

* `project_data/raw/` : données brutes ;
* `project_data/intermediate/` : données intermédiaires ;
* `project_data/processed/` : données transformées ou prêtes à usage ;
* `project_data/exports/` : fichiers produits par la chaîne de traitement.

### `project_notebooks/`

Ce dossier contient les notebooks d’analyse et d’exploration de données.

### `project_docs/`

Ce dossier contient la documentation propre au projet : notes de travail, documents de cadrage, synthèses et éléments utiles à la reprise du dépôt.

### `logs/`

Ce dossier contient les fichiers de logs générés localement par les scripts du projet.

On y retrouve notamment :

* les logs techniques ;
* les logs liés aux traitements de données.

Les fichiers `.log` générés dans ce dossier ne sont pas destinés à être versionnés dans Git.

### `pytest.ini`

Ce fichier contient la configuration de `pytest` utilisée pour les tests du projet.

Il permet notamment de définir :

* les paramètres de journalisation des tests ;
* le module de configuration Django utilisé ;
* les conventions de détection des fichiers de test.

## Scripts réorganisés

Les scripts ont été reclassés selon leur fonction dans la chaîne de traitement des données.

### Scripts de préparation

`repare_csv.py`
Transforme un fichier Excel source en fichier CSV nettoyé, avec suppression de doublons.
Emplacement cible : `project_scripts/preparation/repare_csv.py`

`gen_json_complet.py`
Transforme le fichier CSV préparé en JSON structuré, destiné à alimenter la suite de la chaîne de traitement.
Emplacement cible : `project_scripts/preparation/gen_json_complet.py`

### Scripts d’import

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

### Scripts d’export

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
Statut : supprimé

## Données

Le dossier `project_data/` regroupe les fichiers manipulés par la chaîne de traitement du projet.

Il est organisé en plusieurs sous-dossiers correspondant aux différentes étapes de transformation des données.

### `project_data/raw/`

Ce dossier contient les fichiers source bruts, tels qu’ils sont fournis au projet.

On y place notamment :

* les fichiers Excel source ;
* les fichiers CSV source ;
* plus généralement, les données d’entrée avant tout traitement.

### `project_data/intermediate/`

Ce dossier contient les fichiers intermédiaires produits au cours du projet.

Il regroupe les fichiers générés à des étapes de travail intermédiaires, avant obtention d’un format final ou stabilisé.

Exemples actuels :

* `contacts_emailing_oui.json`
* `contacts_taxe_oui.json`

### `project_data/processed/`

Ce dossier est réservé aux données transformées, consolidées ou stabilisées pour le travail interne du projet.

Il permet de distinguer :

* les fichiers intermédiaires encore provisoires ;
* les fichiers considérés comme plus aboutis dans la chaîne de traitement.

Ce dossier pourra être alimenté selon l’évolution des besoins du POC 2.

### `project_data/exports/`

Ce dossier contient les fichiers produits par la chaîne de traitement du projet et destinés à être réutilisés, transmis ou exploités en sortie.

Exemples actuels :

* `contacts.csv`
* `contacts_mongo.json`

### Logique d’ensemble

L’organisation de `project_data/` suit la progression habituelle du projet :

1. dépôt des fichiers source dans `raw/` ;
2. production de fichiers intermédiaires dans `intermediate/` ;
3. consolidation éventuelle de données stabilisées dans `processed/` ;
4. production de fichiers de sortie dans `exports/`.

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

## Tests

Le projet s’appuie sur deux niveaux de tests pour l’application `persons` :

* les tests embarqués par le socle applicatif CremeCRM ;
* les tests spécifiques au POC 2.

Les tests spécifiques au projet sont placés dans :

* `creme_crm/creme/persons/tests/poc2/`

Cette organisation permet :

* de conserver les tests natifs de l’application ;
* d’ajouter des tests propres au projet sans modifier la structure d’origine ;
* d’isoler les fixtures et les scénarios spécifiques au POC 2.

Les fichiers de tests actuellement ajoutés dans ce sous-dossier couvrent notamment :

* la normalisation et la validation des contacts ;
* la détection des doublons ;
* les filtres métier liés au mailing et à la taxe ;
* certaines vues spécifiques, comme les routes protégées, les vues de liste, l’AJAX de suppression et l’envoi d’email de masse.

La configuration de `pytest` est centralisée dans le fichier `pytest.ini` à la racine du dépôt.

## Exécution locale

Le projet s’appuie sur deux éléments techniques :

* l’environnement Django / CremeCRM, qui correspond au CRM lui-même ;
* une base MongoDB locale, utilisée dans une partie de la chaîne de traitement des données.

Selon les scripts exécutés, il peut donc être nécessaire de travailler à la fois avec Django et avec MongoDB.

### MongoDB local

Plusieurs scripts du projet utilisent une base MongoDB locale pour stocker ou relire des données intermédiaires avant leur intégration dans le CRM.

Dans le cadre du projet, cette base est utilisée sur le port `27018`.

Commande de démarrage :

```bash
mongod --dbpath ~/mongodb-data-crm --port 27018 --bind_ip 127.0.0.1
```

Le terminal dans lequel cette commande est lancée doit rester ouvert pendant toute l’exécution des scripts qui utilisent MongoDB.

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

`MongoDB Compass` peut être utilisé pour visualiser la base MongoDB locale, vérifier les collections et contrôler certains imports.

Il faut cependant distinguer :

* `mongod`, qui correspond au serveur MongoDB à lancer ;
* `MongoDB Compass`, qui est un outil graphique de consultation.

Compass peut donc servir à explorer la base, mais ne remplace pas le lancement du serveur MongoDB.

 
"""

                       CHÂINE DE TRAITEMENT DES DONNÉES (ETL)


Ce script automatise la collecte, la mise au propre et le rangement des données 
de prospection. Son objectif est de prendre des informations brutes issues d'un 
fichier de travail, de les standardiser, puis de les stocker de manière organisée 
dans une base de données afin qu'elles soient prêtes à l'emploi.

Le processus se déroule en 3 grandes étapes successives :

1. L'EXTRACTION (Extract) :
   Le script va chercher le document source d'origine (un fichier tableur). 
   Il effectue un premier nettoyage de sécurité en supprimant toutes les fiches 
   identiques ou contenant des adresses électroniques doublonnées. Cela évite 
   de traiter plusieurs fois la même entreprise.

2. LA TRANSFORMATION (Transform) :
   Chaque ligne conservée est analysée en détail. Les informations textuelles 
   sont lissées (retrait des espaces inutiles, uniformisation des écritures). 
   Le script sépare les données pour créer un dossier propre par contact (nom, 
   adresse, entreprise, emails). C'est aussi à ce moment que sont appliquées 
   les règles de gestion : le script détermine automatiquement si le contact 
   est d'accord pour recevoir des e-mails promotionnels et s'il est concerné 
   par les taxes d'apprentissage.

3. LE CHARGEMENT (Load) :
   Une fois tous les dossiers construits en mémoire, le script se connecte à 
   la base de données. Il efface les anciennes listes pour repartir sur une 
   base saine, puis il enregistre les nouveaux dossiers. Enfin, il joue le rôle 
   d'aiguilleur : il crée une liste globale (brute) et distribue les fiches 
   dans deux listes spécialisées distinctes (une liste dédiée aux opérations 
   de "Taxe" et une autre dédiée aux campagnes d' "Emailing").

Utilisation :
Il suffit de lancer ce script pour que toute la chaîne s'exécute d'un coup, 
depuis la lecture du fichier initial jusqu'au classement final en base de données.

"""

import os  # Permet d'interagir avec le système d'exploitation (gestion des fichiers)
import re  # Permet de rechercher et d'extraire du texte grâce à des modèles de recherche
from pathlib import Path  # Permet de manipuler les chemins de fichiers de façon moderne et simple
import pandas as pd  # Permet de lire, manipuler et nettoyer des tableaux de données
import numpy as np  # Outil de calcul mathématique (utilisé ici pour identifier les valeurs manquantes)
from pymongo import MongoClient  # Permet d'ouvrir une connexion avec la base de données MongoDB

# --- CONFIGURATION DES CHEMINS ET CONSTANTES ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # Calcule le dossier racine du projet (remonte de deux niveaux)
DATA_ROOT = PROJECT_ROOT / "project_data"  # Définit l'emplacement du dossier principal des données
INTERMEDIATE_DATA_ROOT = DATA_ROOT / "intermediate"  # Définit le sous-dossier contenant les fichiers de travail
RAW_DATA_ROOT = DATA_ROOT / "raw"  # Définit le sous-dossier contenant les fichiers sources bruts

# Dictionnaire de correspondance pour associer un mot-clé textuel à un choix de consentement précis
STATUS_MAP = {
    "MAILING": {"newsletter": None, "emailing": False, "publicite": False, "raison": "refus_emailing"},
    "DESINSCRIPTION": {"newsletter": False, "emailing": False, "publicite": False, "raison": "desinscription"},
    "NC": {"newsletter": None, "emailing": None, "publicite": None, "raison": "non_communique"},
}
# Formule de détection pour extraire automatiquement une adresse e-mail valide au milieu d'un texte brute
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


# --- OUTILS DE NETTOYAGE DES TEXTES ---
def normalize_text(value):
    """ Uniformise le texte reçu pour faciliter les comparaisons futures. """
    if value is None or pd.isna(value):  # Si la case contient un marqueur "vide" ou n'existe pas
        return ""  # On renvoie un texte vide pour éviter les erreurs de lecture
    return str(value).strip().upper()  # Convertit en texte, retire les espaces sur les côtés et met en majuscules


def clean_val(val):
    """ Garantit la propreté d'une valeur isolée. """
    if pd.isna(val):  # Si la valeur est un indicateur technique de case vide ("NaN")
        return None  # On la transforme en un "vide" universel standardisé (None)
    return val  # Sinon, on renvoie la valeur d'origine inchangée


def run_pure_etl():
    """ Lance toute la chaîne automatique : Lecture -> Nettoyage -> Rangement. """
    print("=== DÉBUT DU PIPELINE PURE ETL ===")  # Affiche un message d'information dans la console
    
   
    # 1. Extraction
    
    source_excel = RAW_DATA_ROOT / "Classeur2.xlsx"  # Construit le chemin vers le fichier Excel source (dossier raw)
        
    if not source_excel.exists():  # Si le fichier est introuvable
        print(f"ERREUR : Le fichier Excel est introuvable ({source_excel})")  # Affiche une alerte claire
        return  # Arrête immédiatement l'exécution du script

    print(f"\n[1/3] LECTURE : Ouverture du fichier Excel et chasse aux doublons...")  # Alerte sur le début de la lecture
    try:
        df = pd.read_excel(source_excel)  # Charge l'intégralité du fichier Excel dans un tableau virtuel en mémoire
    except Exception as e:  # Si une erreur survient (fichier verrouillé, corrompu...)
        print(f"Erreur de lecture : {e}")  # Affiche l'explication du problème rencontrée
        return  # Arrête le script pour éviter de travailler sur du vide

    count_before = len(df)  # Compte et mémorise le nombre initial de lignes présentes dans le tableau
    df = df.drop_duplicates()  # Supprime instantanément toutes les lignes qui sont des copies parfaites (100% identiques)

    # Parcourt les noms des colonnes pour trouver celle qui s'appelle "email" (sans tenir compte des espaces ni des majuscules)
    email_col = next((c for c in df.columns if str(c).lower().strip() == 'email'), None)
    if email_col:  # Si une colonne dédiée aux e-mails a bien été détectée dans le tableau
        s_emails = df[email_col].astype(str).str.strip().str.lower()  # Crée une liste temporaire d'emails nettoyés (minuscules et sans espaces)
        is_dup = s_emails.duplicated(keep='first')  # Marque comme "doublon" toutes les apparitions répétées d'une même adresse
        is_empty = s_emails.isin(['nan', 'none', ''])  # Marque comme "vide" les adresses invalides ou manquantes
        df = df[~(is_dup & ~is_empty)]  # Filtre le tableau : supprime les lignes ayant un email doublon, sauf si cet email est vide
    
    print(f" -> Lignes lues : {count_before} | Lignes conservées : {len(df)}")  # Affiche le bilan du dédoublonnage


  
    # 2. Transformation
    
    print("\n[2/3] TRI : Création des fiches clients et calcul des autorisations...")  # Informe du début du traitement des données
    documents = []  # Crée une liste vide destinée à recevoir toutes les futures fiches clients structurées

    for _, row in df.iterrows():  # Démarre une boucle pour analyser le tableau ligne par ligne, de haut en bas
        raw_coord = str(clean_val(row.get("Coordonnée.Coordonnée")) or "")  # Récupère le texte brut de la colonne Coordonnées
        email_match = EMAIL_PATTERN.search(raw_coord)  # Utilise la formule magique pour chercher un e-mail caché dans ce texte brute
        
        norm_coord = normalize_text(raw_coord)  # Nettoie et passe le texte de la coordonnée en majuscules pour l'analyse
        consent_data = None  # Initialise le bloc de consentement à "vide" par défaut
        for status_key, mapping in STATUS_MAP.items():  # Parcourt la liste des mots-clés (MAILING, DESINSCRIPTION, etc.)
            if status_key in norm_coord:  # Si le mot-clé est détecté à l'intérieur du texte de la coordonnée
                consent_data = mapping.copy()  # On duplique le paramétrage correspondant défini en haut du script
                consent_data["source_text"] = status_key  # On note quel mot-clé précis a déclenché cette règle de gestion
                break  # On quitte la recherche dès qu'un mot-clé valide a été validé

        # Analyse le statut de l'entreprise vis-à-vis de la taxe
        assujetti = clean_val(row.get("Assujetti.Entité"))  # Récupère la valeur brute indiquant si l'entité est soumise à la taxe
        is_in_taxe = "OUI" if assujetti in [True, 1, "True", "true", "OUI", "oui"] else "NON"  # Traduit cette valeur en un "OUI" ou "NON" catégorique

        # Analyse le droit d'envoyer des e-mails marketing
        raw_text_upper = raw_coord.upper()  # Met le texte brut d'origine en majuscules pour sécuriser l'analyse
        if (
            (consent_data and consent_data.get("emailing") is False)  # Si le mot-clé trouvé interdit formellement les emails
            or "PAS DE CAMPAGNE" in raw_text_upper  # OU si la phrase explicite "PAS DE CAMPAGNE" est présente
            or "DESINSCRIPTION" in raw_text_upper  # OU si le mot "DESINSCRIPTION" apparaît
        ):
            is_in_emailing = "NON"  # Alors cette fiche est taguée "NON" pour les futures campagnes de communication
        else:
            is_in_emailing = "OUI"  # Sinon, en l'absence de refus explicite, elle est taguée positivement à "OUI"

        # Construit l'arborescence complète et finale de la fiche client (le dictionnaire structuré)
        doc = {
            "entite": {
                "code": clean_val(row.get("Code.Entité")),  # Extrait le matricule ou code unique de l'entreprise
                "libelle": clean_val(row.get("Libellé.Entité")),  # Extrait le nom officiel de l'établissement
                "assujetti_taxe": assujetti,  # Conserve la valeur brute d'origine liée aux taxes
            },
            "adresse": {
                "ligne1": clean_val(row.get("Rue (ligne 1).Adresse")),  # Extrait le numéro et la rue
                "ville": clean_val(row.get("Nom.Ville")),  # Extrait le nom de la commune
                "code_postal": clean_val(row.get("Code postal.Ville")),  # Extrait le code postal associé
            },
            "contact": {
                "nom": clean_val(row.get("Nom.Individu")),  # Extrait le nom de famille de l'interlocuteur
                "prenom": clean_val(row.get("Prénom.Individu")),  # Extrait son prénom
            },
            "education_et_taxe": {
                "nb_stagiaires": clean_val(row.get("Nombre de stage (sans contrat pro)")),  # Extrait le volume de stagiaires formés
                "montant_taxe": clean_val(row.get("Montant global.Taxe versement")),  # Extrait la somme financière versée
            },
            "coordonnees": {
                "email": email_match.group(0).lower() if email_match else None,  # Enregistre l'email isolé en minuscules s'il existe
                "raw": raw_coord if raw_coord != "" else None  # Sauvegarde la chaîne brute complète pour archive historique
            },
            "consent": consent_data,  # Intègre le dossier de consentement détaillé (calculé précédemment)
            "status": "new",  # Ajoute une étiquette indiquant que cette fiche est toute nouvelle et non traitée
            "is_in_taxe": is_in_taxe,  # Injecte le raccourci "OUI/NON" pour le ciblage des taxes
            "is_in_emailing": is_in_emailing  # Injecte le raccourci "OUI/NON" pour le ciblage marketing
        }
        documents.append(doc)  # Ajoute la fiche client nouvellement créée dans notre grande liste en mémoire

    print(f" -> Création en mémoire de {len(documents)} fiches clients.")  # Affiche le volume de fiches prêtes à l'envoi


   
    # 3. Enregistrer
    
    print("\n[3/3] RANGEMENT : Connexion à la base de données et répartition...")  # Alerte sur le début de la phase de stockage
    try:
        client = MongoClient("mongodb://localhost:27018/")  # Ouvre le tuyau de connexion vers le serveur de base de données (Port 27018)
        db = client["poc_aggregation"]  # Sélectionne (ou crée) le projet nommé "poc_aggregation"
        
        # Gestion de la collection principale (Tiroir général brut)
        col_bruts = db["prospects_bruts"]  # Sélectionne l'emplacement de stockage des données brutes
        col_bruts.delete_many({})  # Supprime instantanément tout l'ancien contenu de ce tiroir pour éviter les mélanges
        if documents:  # S'il y a bien des fiches clients prêtes dans notre liste en mémoire
            col_bruts.insert_many(documents)  # Envoie et enregistre d'un seul coup toutes les fiches dans la base générale
        print(f" -> Tiroir général 'prospects_bruts' mis à jour.")  # Valide le succès du stockage global

        # Sélection des sous-tiroirs thématiques
        col_taxe = db["prospects_taxe"]  # Cible l'espace de stockage des entreprises concernées par la taxe
        col_emailing = db["prospects_emailing"]  # Cible l'espace de stockage destiné aux campagnes de courriels

        col_taxe.delete_many({})  # Vide l'ancien contenu lié aux taxes
        col_emailing.delete_many({})  # Vide l'ancien contenu lié à la communication numérique

        # Utilise des filtres pour ventiler intelligemment les fiches selon les choix calculés à l'étape 2
        list_taxe = [d for d in documents if d["is_in_taxe"] == "OUI"]  # Extrait uniquement les dossiers marqués "OUI" pour la taxe
        list_emailing = [d for d in documents if d["is_in_emailing"] == "OUI"]  # Extrait uniquement les dossiers marqués "OUI" pour les e-mails

        if list_taxe:  # Si la liste filtrée pour les taxes contient au moins une entreprise
            col_taxe.insert_many(list_taxe)  # Enregistre cette sélection dans le tiroir thématique "prospects_taxe"
        if list_emailing:  # Si la liste filtrée pour la communication contient au moins un contact
            col_emailing.insert_many(list_emailing)  # Enregistre cette sélection dans le tiroir thématique "prospects_emailing"

        print(f" -> Tiroir 'Taxe' : {len(list_taxe)} fiches rangées.")  # Affiche le nombre de lignes archivées pour la taxe
        print(f" -> Tiroir 'Emailing' : {len(list_emailing)} fiches rangées.")  # Affiche le nombre de lignes archivées pour la pub
        
    except Exception as e:  # Si une panne réseau ou un problème de droits coupe l'accès à la base de données
        print(f"ERREUR lors de l'enregistrement en base de données : {e}")  # Signale précisément l'incident rencontré
        return  # Sort proprement de la fonction

    print("\n=== TRAITEMENT AUTOMATIQUE TERMINÉ AVEC SUCCÈS ===")  # Clôture festive annonçant que l'ETL s'est déroulé sans encombres


if __name__ == "__main__":
    run_pure_etl()  # Condition finale : si ce fichier est exécuté directement, il lance immédiatement l'action globale
    run_pure_etl()  # Condition finale : si ce fichier est exécuté directement, il lance immédiatement l'action globale

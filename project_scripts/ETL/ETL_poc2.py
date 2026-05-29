
# PIPELINE ETL (ALIGNÉ SUR LES RÉSULTATS DE L'EDA)

"""
Ce script ETL sert à nettoyer le fichier brut des stagiaires et à le préparer proprement pour notre base MongoDB.

Pour comprendre les choix qu'on a faits ici, voici le résumé de ce qu'on a trouvé pendant l'analyse (l'EDA) et comment on l'a réglé:

1. Les lignes parasites: Le fichier CSV commence par 21 lignes de texte inutiles et utilise un encodage 'latin-1'.
Du coup, on saute ces lignes au démarrage pour ne pas charger de données cassées.

2. Les doublons : On a repéré exatement 910 lignes en trop (des copies parfaites).
Le script les supprime donc automatiquement pour repartir sur une base saine.

3. Le problème des cases vides (NaN) : Les cases vides de Pandas font planter le format Json standart. 
On les transform toutes en 'None' (ce qui donne des 'null' en JSON) pour éviter les erreurs d'import dans MongoDB.

4. Le casse-tête des adresses : Les lignes d'adresse 2,3 et 4 sont vides la plupart du temps (plus de 56% de vides).
On a choisi de les fusionner en une seule ligne propre et sans résidus de texte pour simplifier le stockage.

5. Pas de coordonnées : L'analyse a montré qu'on n'a aucun email ni numéro de téléphone pour l'instant.
On crée quand même la structure dans le Json avec des valeurs vides (null) pour qu'on puisse enrichir ces données facilement plus tard.

"""

import json
import os
import pandas as pd

# Configurations des fichiers
file_path = "../../project_data/raw/Entreprises entites stagiaires.csv"
output_path = "../../project_data/exports/contacts_Poc2.json"


# 1. Extraction

print("=== ÉTAPE 1 : EXTRACTION ===")

# LIEN EDA : L'analyse textuelle brute a révélé 21 lignes de préambule parasite 
# et un encodage 'latin-1' nécessaire pour ne pas faire planter les accents (ex: 'Évènement').
df_raw = pd.read_csv(file_path, encoding="latin-1", sep=";", skiprows=21)
print(f"[OK] Extraction réussie de {df_raw.shape[0]} lignes brutes.")


# 2. Transformation

print("\n=== ÉTAPE 2 : TRANSFORMATION (NETTOYAGE & STRUCTURATION) ===")

# --- A. Traitement des Doublons ---
# LIEN EDA : L'EDA a détecté exactement 910 doublons parfaits de contenu métier.
# L'ETL applique donc un filtre strict pour les éliminer en ignorant l'index technique.
colonnes_metier = df_raw.columns.difference(["Unnamed: 0"])
df_cleaned = df_raw.drop_duplicates(subset=colonnes_metier, keep="first").copy()
# Remplacer tous les NaN de Pandas par None (qui devient null en JSON)
df_cleaned = df_cleaned.replace({pd.NA: None, float('nan'): None}).where(pd.notna(df_cleaned), None)

nb_supprimes = df_raw.shape[0] - df_cleaned.shape[0]
print(f"[OK] Correction Doublons : {nb_supprimes} lignes supprimées (910 attendues).")
print(f"     Lignes saines conservées : {df_cleaned.shape[0]}")


# --- B. Structuration NoSQL (MongoDB) & Nettoyage des champs ---
print("     Dénormalisation des lignes en documents imbriqués...")
documents_transformes = []

for _, row in df_cleaned.iterrows():
    
    # LIEN EDA : L'EDA a prouvé que les lignes d'adresse 2, 3 et 4 étaient vides à plus de 56%.
    # L'ETL les fusionne en une seule chaîne propre en éliminant les valeurs textuelles "nan".
    complements = [
        row.get("Rue (ligne 2).Adresse"),
        row.get("Rue (ligne 3).Adresse"),
        row.get("Rue (ligne 4).Adresse")
    ]
    complement_propre = " ".join(
        str(v).strip() for v in complements 
        if pd.notna(v) and str(v).strip() and str(v).lower() != "nan"
    )

    # LIEN EDA : L'EDA a mis en évidence l'absence TOTALE de colonnes de coordonnées directes 
    # (pas de mail, pas de téléphone). L'ETL adapte le schéma cible de MongoDB en isolant 
    # les données pédagogiques/taxes et en initialisant les coordonnées à 'None' pour enrichissement.
    doc = {
        "entite": {
            "code": row.get("Code.Entité"),
            "libelle": row.get("Libellé.Entité"),
            "type": row.get("Code.Type d'entité"),
            "assujetti_taxe": "Oui" if row.get("Assujetti.Entité") == "Vrai" else "Non"
        },
        "adresse": {
            "ligne1": row.get("Rue (ligne 1).Adresse"),
            "complement": complement_propre if complement_propre else None,
            "code_postal": row.get("Code postal.Ville"),
            "ville": row.get("Nom.Ville"),
            "type_adresse": row.get("Code.Type d'adresse")
        },
        "contact": {
            "fonction": row.get("Code.Fonctions"), # Profils DIRECTION/DIRECTION_RH validés par l'EDA
            "nom": row.get("Nom.Individu"),
            "prenom": row.get("Prénom.Individu")
        },
        "suivi_pedagogique_et_taxe": {
            "nb_stages": int(row["Nombre de stage (sans contrat pro)"]) if pd.notna(row.get("Nombre de stage (sans contrat pro)")) else 0,
            "noms_stagiaires": row.get("Noms des stagiaires"),
            "nb_contrat_pro": int(row["Nombre de contrat pro"]) if pd.notna(row.get("Nombre de contrat pro")) else 0,
            "noms_alternants": row.get("Noms des alternants contrats pro"),
            "nb_apprentissage": int(row["Nombre apprentissage"]) if pd.notna(row.get("Nombre apprentissage")) else 0,
            "noms_apprentis": row.get("Noms des apprentis"),
            "type_evenement": row.get("Code.Type d'événement"),
            "montant_taxe_versee": row.get("Montant global.Taxe versement"),
            "date_evenement": row.get("Début.Événement")
        },
        "coordonnees": {
            "email": None,       # Volontairement à vide suite au constat de l'EDA
            "telephone": None    # Structure prête pour la phase d'enrichissement
        },
        "consent": None
    }
    documents_transformes.append(doc)

print("[OK] Transformation des données au format Document validée.")


# 3.Enregistrer

print("\n=== ÉTAPE 3 : CHARGEMENT ===")

# Transfert des dictionnaires vers le fichier JSON final
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(documents_transformes, f, ensure_ascii=False, indent=4)

print(f"[OK] Pipeline terminé. Fichier généré : {output_path}")
print(f"     => {len(documents_transformes)} documents nettoyés prêts pour l'import MongoDB.")
import pandas as pd
import json
import re
import os
import numpy as np

def generate_full_json_from_csv(csv_filename):
    # --- 1. GESTION DU CHEMIN ---
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_dir, csv_filename)
    
    if not os.path.exists(csv_path):
        print(f"ERREUR : Le fichier '{csv_filename}' est introuvable dans {base_dir}")
        return

    # --- 2. CHARGEMENT ---
    df = pd.read_csv(csv_path)

    # --- 3. CONFIGURATION ---
    # Détection de "MAILING" (gère E-MAILING et MAILING)
    STATUS_MAP = {
        "MAILING": {"newsletter": None, "emailing": False, "publicite": False, "raison": "refus_emailing"},
        "DESINSCRIPTION": {"newsletter": False, "emailing": False, "publicite": False, "raison": "desinscription"},
        "NC": {"newsletter": None, "emailing": None, "publicite": None, "raison": "non_communique"},
    }
    EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

    def normalize_text(value):
        if value is None or pd.isna(value): return ""
        text = str(value).strip().upper()
        return text

    # Fonction de sécurité pour transformer les NaN en None (null)
    def clean_val(val):
        if pd.isna(val):
            return None
        return val

    documents = []

    # --- 4. TRANSFORMATION ---
    for _, row in df.iterrows():
        raw_coord = str(clean_val(row.get("Coordonnée.Coordonnée")) or "")
        email_match = EMAIL_PATTERN.search(raw_coord)
        
        norm_coord = normalize_text(raw_coord)
        consent_data = None
        for status_key, mapping in STATUS_MAP.items():
            if status_key in norm_coord:
                consent_data = mapping.copy()
                consent_data["source_text"] = status_key
                break

        doc = {
            "entite": {
                "code": clean_val(row.get("Code.Entité")),
                "libelle": clean_val(row.get("Libellé.Entité")),
                "assujetti_taxe": clean_val(row.get("Assujetti.Entité")),
            },
            "adresse": {
                "ligne1": clean_val(row.get("Rue (ligne 1).Adresse")),
                "ville": clean_val(row.get("Nom.Ville")),
                # --- RÉCUPÉRATION AVEC TON NOM DE COLONNE PRÉCIS ---
                "code_postal": clean_val(row.get("Code postal.Ville")),
            },
            "contact": {
                "nom": clean_val(row.get("Nom.Individu")),
                "prenom": clean_val(row.get("Prénom.Individu")),
            },
            "education_et_taxe": {
                "nb_stagiaires": clean_val(row.get("Nombre de stage (sans contrat pro)")),
                "montant_taxe": clean_val(row.get("Montant global.Taxe versement")),
            },
            "coordonnees": {
                "email": email_match.group(0).lower() if email_match else None,
                "raw": raw_coord if raw_coord != "" else None
            },
            "consent": consent_data
        }
        documents.append(doc)

    # --- 5. EXPORT FINAL ---
    output_file = os.path.join(base_dir, "contacts_mongo.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(documents, f, ensure_ascii=False, indent=4)
    
    print(f"Succès ! Fichier JSON généré avec la colonne 'Code postal.Ville' et détection Mailing.")

if __name__ == "__main__":
    generate_full_json_from_csv("contacts.csv")
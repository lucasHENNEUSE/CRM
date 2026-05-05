import pandas as pd
import os

# On définit les chemins
base_dir = os.path.dirname(os.path.abspath(__file__))
# On cible le fichier Excel
source = os.path.join(base_dir, "Classeur2.xlsx")
destination = os.path.join(base_dir, "contacts.csv")

if os.path.exists(source):
    try:
        print(f"Lecture du fichier Excel : {source}...")
        # Lecture du fichier Excel (.xlsx)
        df = pd.read_excel(source)
        
        # SUPPRESSION DES DOUBLONS
        count_before = len(df)
        print(f" -> Lignes avant traitement : {count_before}")

        # 1. Suppression des doublons exacts (lignes strictement identiques)
        df = df.drop_duplicates()

        # 2. Suppression intelligente sur l'email (si la colonne existe)
        email_col = next((c for c in df.columns if str(c).lower().strip() == 'email'), None)
        if email_col:
            print(f" -> Dédoublonnage sur la colonne '{email_col}'...")
            # Normalisation (minuscule + trim)
            s_emails = df[email_col].astype(str).str.strip().str.lower()
            # On supprime les doublons d'emails, sauf s'ils sont vides (nan/none)
            is_dup = s_emails.duplicated(keep='first')
            is_empty = s_emails.isin(['nan', 'none', ''])
            df = df[~(is_dup & ~is_empty)]

        print(f" -> Lignes après nettoyage : {len(df)} (Supprimés : {count_before - len(df)})")

        # Sauvegarde en CSV propre (UTF-8)
        df.to_csv(destination, index=False, encoding='utf-8')
        
        print("-" * 30)
        print(f"SUCCÈS ! Excel converti en CSV.")
        print(f"Fichier créé : {destination}")
        print("-" * 30)
        
    except Exception as e:
        print(f"Erreur lors de la lecture de l'Excel : {e}")
        print("Vérifie que le fichier n'est pas ouvert dans Excel en même temps.")
else:
    print(f"Fichier introuvable : {source}")
    print(f"Fichiers dans le dossier : {os.listdir(base_dir)}")
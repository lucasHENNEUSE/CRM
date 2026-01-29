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
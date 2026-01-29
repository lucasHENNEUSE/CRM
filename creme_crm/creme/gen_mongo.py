import pymongo
import json
import os
import sys

def import_contacts_to_mongo():
    # --- GESTION DU CHEMIN ---
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, "contacts_mongo.json")

    # 1. Connexion à MongoDB
    client = pymongo.MongoClient("mongodb://localhost:27018/") 
    db = client["poc_aggregation"]
    collection = db["prospects_bruts"]

    # 2. Vérification du fichier
    if not os.path.exists(file_path):
        print(f"Erreur : Fichier introuvable !")
        print(f"Le script a cherché ici : {file_path}")
        return

    print(f"--- Lecture du fichier complet : {file_path} ---")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 3. Ajout des statuts OUI/NON sans rien supprimer d'autre
    for doc in data:
        # --- AJOUT INDISPENSABLE POUR import_mongo.py ---
        doc["status"] = "new" 
        
        # Statut TAXE (OUI/NON)
        assujetti = doc.get("entite", {}).get("assujetti_taxe")
        doc["is_in_taxe"] = "OUI" if assujetti in [True, 1, "True", "true"] else "NON"

        # Statut E-MAILING (OUI/NON)
        consent = doc.get("consent")
        raw_text = str(doc.get("coordonnees", {}).get("raw", "")).upper()
        
        if (consent and consent.get("emailing") is False) or "PAS DE CAMPAGNE" in raw_text or "DESINSCRIPTION" in raw_text:
            doc["is_in_emailing"] = "NON"
        else:
            doc["is_in_emailing"] = "OUI"

    # 4. Insertion de l'intégralité des données dans MongoDB
    if data:
        collection.delete_many({}) 
        collection.insert_many(data)
        print(f" Succès ! {len(data)} contacts importés.")
        print("Toutes les infos (Excel + statuts OUI/NON + status: new) sont dans MongoDB.")

if __name__ == "__main__":
    import_contacts_to_mongo()
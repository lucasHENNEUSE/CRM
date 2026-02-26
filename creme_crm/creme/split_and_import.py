import pymongo
import json
import os

def dispatcher_contacts():
    # 1. Chemins
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, "contacts_mongo.json")

    # 2. Connexion MongoDB
    client = pymongo.MongoClient("mongodb://localhost:27018/") 
    db = client["poc_aggregation"]
    
    # On définit les deux collections séparées
    col_taxe = db["prospects_taxe"]
    col_emailing = db["prospects_emailing"]

    if not os.path.exists(file_path):
        print(f"Erreur : Le fichier {file_path} n'existe pas.")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    list_taxe = []
    list_emailing = []

    for doc in data:
        # --- LOGIQUE TAXE ---
        assujetti = doc.get("entite", {}).get("assujetti_taxe")
        doc["is_in_taxe"] = "OUI" if assujetti in [True, 1, "True", "true"] else "NON"

        # --- LOGIQUE EMAILING ---
        consent = doc.get("consent")
        raw_text = str(doc.get("coordonnees", {}).get("raw", "")).upper()
        if (consent and consent.get("emailing") is False) or "PAS DE CAMPAGNE" in raw_text:
            doc["is_in_emailing"] = "NON"
        else:
            doc["is_in_emailing"] = "OUI"

        # --- DISPATCHING ---
        # Si le contact est OUI pour la taxe, on l'ajoute à la liste taxe
        if doc["is_in_taxe"] == "OUI":
            list_taxe.append(doc)
        
        # Si le contact est OUI pour l'emailing, on l'ajoute à la liste emailing
        if doc["is_in_emailing"] == "OUI":
            list_emailing.append(doc)

    # 3. Nettoyage des anciennes données et insertion des nouvelles
    if list_taxe:
        col_taxe.delete_many({})
        col_taxe.insert_many(list_taxe)
        print(f" {len(list_taxe)} contacts triés dans 'prospects_taxe'")

    if list_emailing:
        col_emailing.delete_many({})
        col_emailing.insert_many(list_emailing)
        print(f" {len(list_emailing)} contacts triés dans 'prospects_emailing'")

if __name__ == "__main__":
    dispatcher_contacts()
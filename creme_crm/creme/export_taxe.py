import pymongo
import json
import os

def export_taxe_oui():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(base_dir, "contacts_taxe_oui.json")

    client = pymongo.MongoClient("mongodb://localhost:27018/") 
    db = client["poc_aggregation"]
    collection = db["prospects_bruts"]

    query = {"is_in_taxe": "OUI"}

    # Correction de la projection selon ton image
    projection = {
        "_id": 0,
        "nom": "$contact.nom",
        "prenom": "$contact.prenom",
        "email": "$coordonnees.email"
    }

    contacts = list(collection.find(query, projection))

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(contacts, f, indent=4, ensure_ascii=False)
    
    print(f"Extraction Taxe terminée : {len(contacts)} contacts exportés dans {output_path}")

if __name__ == "__main__":
    export_taxe_oui()
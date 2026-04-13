from pathlib import Path
import pymongo
import json


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = PROJECT_ROOT / "project_data"
EXPORTS_ROOT = DATA_ROOT / "exports"


def export_taxe_oui():
    EXPORTS_ROOT.mkdir(parents=True, exist_ok=True)
    output_path = EXPORTS_ROOT / "contacts_taxe_oui.json"

    client = pymongo.MongoClient("mongodb://localhost:27018/")
    db = client["poc_aggregation"]
    collection = db["prospects_bruts"]

    query = {"is_in_taxe": "OUI"}

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

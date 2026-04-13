from pathlib import Path
import pymongo
import json


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = PROJECT_ROOT / "project_data"
INTERMEDIATE_DATA_ROOT = DATA_ROOT / "intermediate"


def import_contacts_to_mongo():
    file_path = INTERMEDIATE_DATA_ROOT / "contacts_mongo.json"

    client = pymongo.MongoClient("mongodb://localhost:27018/")
    db = client["poc_aggregation"]
    collection = db["prospects_bruts"]

    if not file_path.exists():
        print("Erreur : Fichier introuvable !")
        print(f"Le script a cherché ici : {file_path}")
        return

    print(f"--- Lecture du fichier complet : {file_path} ---")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for doc in data:
        doc["status"] = "new"

        assujetti = doc.get("entite", {}).get("assujetti_taxe")
        doc["is_in_taxe"] = "OUI" if assujetti in [True, 1, "True", "true"] else "NON"

        consent = doc.get("consent")
        raw_text = str(doc.get("coordonnees", {}).get("raw", "")).upper()

        if (
            (consent and consent.get("emailing") is False)
            or "PAS DE CAMPAGNE" in raw_text
            or "DESINSCRIPTION" in raw_text
        ):
            doc["is_in_emailing"] = "NON"
        else:
            doc["is_in_emailing"] = "OUI"

    if data:
        collection.delete_many({})
        collection.insert_many(data)
        print(f"Succès ! {len(data)} contacts importés.")
        print("Toutes les infos (Excel + statuts OUI/NON + status: new) sont dans MongoDB.")


if __name__ == "__main__":
    import_contacts_to_mongo()

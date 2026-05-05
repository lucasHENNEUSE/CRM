from pathlib import Path
import pymongo
import json


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = PROJECT_ROOT / "project_data"
INTERMEDIATE_DATA_ROOT = DATA_ROOT / "intermediate"


def dispatcher_contacts():
    file_path = INTERMEDIATE_DATA_ROOT / "contacts_mongo.json"

    client = pymongo.MongoClient("mongodb://localhost:27018/")
    db = client["poc_aggregation"]

    col_taxe = db["prospects_taxe"]
    col_emailing = db["prospects_emailing"]

    if not file_path.exists():
        print(f"Erreur : Le fichier {file_path} n'existe pas.")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    list_taxe = []
    list_emailing = []

    for doc in data:
        assujetti = doc.get("entite", {}).get("assujetti_taxe")
        doc["is_in_taxe"] = "OUI" if assujetti in [True, 1, "True", "true"] else "NON"

        consent = doc.get("consent")
        raw_text = str(doc.get("coordonnees", {}).get("raw", "")).upper()
        if (consent and consent.get("emailing") is False) or "PAS DE CAMPAGNE" in raw_text:
            doc["is_in_emailing"] = "NON"
        else:
            doc["is_in_emailing"] = "OUI"

        if doc["is_in_taxe"] == "OUI":
            list_taxe.append(doc)

        if doc["is_in_emailing"] == "OUI":
            list_emailing.append(doc)

    if list_taxe:
        col_taxe.delete_many({})
        col_taxe.insert_many(list_taxe)
        print(f"{len(list_taxe)} contacts triés dans 'prospects_taxe'")

    if list_emailing:
        col_emailing.delete_many({})
        col_emailing.insert_many(list_emailing)
        print(f"{len(list_emailing)} contacts triés dans 'prospects_emailing'")


if __name__ == "__main__":
    dispatcher_contacts()

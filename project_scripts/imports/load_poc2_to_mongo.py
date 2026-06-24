from pathlib import Path
import json
import os

from pymongo import MongoClient


# Utiliser une variable d'environnement pour adapter facilement la connexion MongoDB.
# Par défaut, le script utilise le port standard MongoDB 27017.
# Exemple si MongoDB tourne sur 27018 :
# MONGODB_URI="mongodb://localhost:27018/" python project_scripts/imports/load_poc2_to_mongo.py
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")

# Utiliser une base MongoDB dédiée au POC2 pour éviter tout mélange avec le POC1.
DATABASE_NAME = "crm_poc2"

# Associer explicitement chaque fichier JSON POC2 à sa collection MongoDB cible.
# Cette correspondance garantit une logique simple : 5 JSON validés -> 5 collections métier.
JSON_TO_COLLECTION = {
    "poc2_entites.json": "entites",
    "poc2_contacts_crm.json": "contacts_crm",
    "poc2_adresses.json": "adresses",
    "poc2_taxe_events.json": "taxe_events",
    "poc2_suivi_pedagogique.json": "suivi_pedagogique",
}


def load_json_file(file_path):
    """Lire un fichier JSON et vérifier qu'il contient une liste d'objets."""
    assert file_path.exists(), f"Fichier introuvable : {file_path}"

    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    assert isinstance(data, list), (
        f"Le fichier {file_path.name} ne contient pas une liste JSON"
    )

    assert len(data) > 0, (
        f"Le fichier {file_path.name} ne contient aucun objet"
    )

    return data


def reload_collection(database, collection_name, data):
    """Vider une collection ciblée, insérer les données, puis vérifier le volume."""
    collection = database[collection_name]

    # Vider uniquement la collection ciblée.
    # Attention : cela ne supprime pas toute la base crm_poc2.
    collection.delete_many({})

    collection.insert_many(data)

    json_count = len(data)
    mongo_count = collection.count_documents({})

    # Comparer le volume lu dans le JSON avec le volume réellement présent dans MongoDB.
    # Cette vérification permet de détecter immédiatement un chargement incomplet.
    assert mongo_count == json_count, (
        f"Volume incorrect dans {collection_name} : "
        f"{mongo_count} documents MongoDB au lieu de {json_count} objets JSON"
    )

    return mongo_count


def main():
    project_root = Path(__file__).resolve().parents[2]
    processed_dir = project_root / "project_data" / "processed"

    assert processed_dir.exists(), (
        f"Dossier processed introuvable : {processed_dir}"
    )

    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=3000)

    # Tester rapidement la connexion MongoDB avant de commencer le chargement.
    # Si MongoDB n'est pas lancé ou si le port est incorrect, le script s'arrête ici.
    client.admin.command("ping")

    database = client[DATABASE_NAME]

    print("Chargement MongoDB POC2")
    print(f"Base cible : {DATABASE_NAME}")
    print(f"Dossier source : {processed_dir}")
    print()

    summary = []

    for json_file_name, collection_name in JSON_TO_COLLECTION.items():
        file_path = processed_dir / json_file_name

        data = load_json_file(file_path)
        mongo_count = reload_collection(database, collection_name, data)

        summary.append({
            "json_file": json_file_name,
            "collection": collection_name,
            "json_count": len(data),
            "mongo_count": mongo_count,
        })

        print(
            f"{json_file_name} -> {collection_name} : "
            f"{len(data)} objets JSON / {mongo_count} documents MongoDB"
        )

    client.close()

    print()
    print("Récapitulatif du chargement :")

    for item in summary:
        print(
            f"- {item['collection']} : "
            f"{item['json_count']} lus / {item['mongo_count']} présents"
        )

    print()
    print("Chargement MongoDB POC2 terminé avec succès.")


if __name__ == "__main__":
    main()
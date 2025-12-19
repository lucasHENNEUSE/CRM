import os
import django
from pymongo import MongoClient

# 1. Initialisation de l'environnement Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'creme.dev_settings')
django.setup()

from creme.creme_core.models import Person

# 2. Connexion à MongoDB
client = MongoClient('localhost', 27017)
db = client['big_data_crm']
collection = db['prospects_bruts']

def import_from_mongo_to_creme():
    # On récupère un document dans MongoDB (ex: un prospect scrapé sur le web)
    prospect_data = collection.find_one({"status": "new"})
    
    if prospect_data:
        # 3. On crée le contact dans le squelette Creme CRM
        new_person = Person.objects.create(
            first_name=prospect_data.get('prenom', 'Inconnu'),
            last_name=prospect_data.get('nom', 'Anonyme')
        )
        
        print(f" Succès : {new_person} transféré du Big Data vers le CRM.")
        
        # On marque le document comme traité dans MongoDB
        collection.update_one({"_id": prospect_data["_id"]}, {"$set": {"status": "imported"}})
    else:
        print("Alerte : Aucun nouveau prospect trouvé dans MongoDB.")

if __name__ == "__main__":
    import_from_mongo_to_creme()
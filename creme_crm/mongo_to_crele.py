import os
import django
import time
from pymongo import MongoClient

# --- INITIALISATION DJANGO ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'creme.dev_settings')
django.setup()

from creme.creme_core.models import Person

# --- CONNEXION MONGODB (Port 27017 sécurisé) ---
client = MongoClient('mongodb://localhost:27017/')
db = client['poc_aggregation']
collection = db['prospects_bruts']

def run_import_test():
    print("--- Démarrage du test d'importation Big Data ---")
    
    # 1. On cherche un document "prêt" dans Mongo
    document = collection.find_one({"status": "ready"})
    
    if not document:
        print(" Aucun document trouvé avec le status 'ready' dans MongoDB.")
        return

    # 2. Mesure de performance (pour ton comparatif)
    start_time = time.time()

    try:
        # 3. Création native dans le moteur Creme CRM
        new_contact = Person.objects.create(
            first_name=document.get('first_name', 'Inconnu'),
            last_name=document.get('last_name', 'Anonyme')
        )
        
        execution_time = (time.time() - start_time) * 1000 # En millisecondes
        
        # 4. Mise à jour du status dans Mongo
        collection.update_one({"_id": document["_id"]}, {"$set": {"status": "processed"}})
        
        print(f" Contact '{new_contact}' créé avec succès !")
        print(f" Temps d'exécution (Django Native) : {execution_time:.2f} ms")
        
    except Exception as e:
        print(f" Erreur lors du transfert : {e}")

if __name__ == "__main__":
    run_import_test()
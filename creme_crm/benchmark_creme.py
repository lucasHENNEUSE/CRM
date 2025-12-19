import os
import django
import time
from pymongo import MongoClient

# --- 1. CONFIGURATION DJANGO ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'creme.dev_settings')
django.setup()

# --- 2. IMPORTS DES MODÈLES (Correction de l'indentation) ---
try:
    from creme.creme_core.models.persons import Person
except ImportError:
    from creme.creme_core.models import Person

# --- 3. CONNEXION MONGODB (Port 27018) ---
client = MongoClient('mongodb://localhost:27018/')
db = client['poc_aggregation']
collection = db['prospects_bruts']

def generate_fake_data(count=100):
    """Génère des données de test dans MongoDB"""
    print(f"📦 Génération de {count} prospects dans MongoDB...")
    collection.delete_many({"metadata.source": "stress_test"})
    prospects = [
        {
            "first_name": f"Prenom_{i}",
            "last_name": f"Nom_{i}",
            "status": "ready",
            "metadata": {"source": "stress_test", "index": i}
        } for i in range(count)
    ]
    collection.insert_many(prospects)
    print(" MongoDB est prêt.")

def run_benchmark():
    """Importe les données et mesure le temps"""
    prospects_to_import = list(collection.find({"status": "ready"}))
    total = len(prospects_to_import)
    
    if total == 0:
        print(" Aucun prospect prêt pour le benchmark.")
        return

    print(f" Importation de {total} contacts vers le CRM...")
    start_time = time.time()

    for p in prospects_to_import:
        try:
            Person.objects.create(
                first_name=p['first_name'],
                last_name=p['last_name']
            )
            collection.update_one({"_id": p["_id"]}, {"$set": {"status": "processed"}})
        except Exception as e:
            print(f" Erreur insertion : {e}")

    duration = time.time() - start_time
    
    print("\n" + "="*30)
    print(" RÉSULTATS DU BENCHMARK CREME CRM")
    print("="*30)
    print(f" Temps total       : {duration:.2f} secondes")
    print(f" Vitesse moyenne    : {total/duration:.2f} contacts/sec")
    print("="*30)

if __name__ == "__main__":
    generate_fake_data(100)
    run_benchmark()
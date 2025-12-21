import os
import sys
import django
from pymongo import MongoClient

# --- 1. CONFIGURATION DU CHEMIN ET DE DJANGO ---
# On remonte d'un dossier pour que le module 'creme' soit reconnu
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Chargement des réglages de Crème CRM
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'creme.settings')
django.setup()

# Imports spécifiques à l'architecture de Crème CRM
from creme.creme_core.models import CremeUser as User  # L'utilisateur pour la propriété des fiches
from creme.persons.models import Contact               # Le modèle pour les individus

# --- 2. CONNEXION À MONGODB ---
# Configuration basée sur tes captures MongoDB Compass
client = MongoClient('localhost', 27018)
db = client['poc_aggregation']
collection = db['prospects_bruts']

def import_from_mongo_to_creme():
    print("🚀 Début de l'importation massive...")

    # Récupération de l'administrateur (nécessaire pour créer des fiches dans Crème)
    admin_user = User.objects.filter(is_superuser=True).first()
    
    if not admin_user:
        print("❌ Erreur : Aucun administrateur trouvé dans la base SQLite.")
        return

    # On récupère tous les prospects marqués comme "new" dans MongoDB
    prospects_a_traiter = collection.find({"status": "new"})
    
    count = 0
    for data in prospects_a_traiter:
        try:
            # Création de la fiche dans Crème CRM
            # On récupère 'prenom' et 'nom' depuis ton document MongoDB
            new_contact = Contact.objects.create(
                user=admin_user, 
                first_name=data.get('prenom', 'Inconnu'),
                last_name=data.get('nom', 'Anonyme'),
            )
            
            # Mise à jour du statut dans MongoDB pour ne pas l'importer deux fois
            collection.update_one(
                {"_id": data["_id"]}, 
                {"$set": {"status": "imported"}}
            )
            
            print(f"✅ Importé : {new_contact.first_name} {new_contact.last_name}")
            count += 1
            
        except Exception as e:
            print(f"⚠️ Erreur sur le document {data.get('_id')} : {e}")

    print(f"\n✨ Terminé ! {count} contacts ont été transférés avec succès.")

if __name__ == "__main__":
    import_from_mongo_to_creme()
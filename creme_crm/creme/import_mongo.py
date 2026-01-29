import os
import sys
import django
from pymongo import MongoClient

# --- 1. CONFIGURATION DJANGO ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'creme.settings')
django.setup()

from creme.creme_core.models import CremeUser as User
from creme.persons.models import Contact

# --- 2. CONNEXION MONGODB ---
client = MongoClient('localhost', 27018)
db = client['poc_aggregation']
collection = db['prospects_bruts']

def transfer_to_creme():
    print(" Transfert ciblé vers les champs de l'interface CRM...")

    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        print(" Erreur : Administrateur Crème CRM introuvable.")
        return

    # On récupère les 6799 documents 'new'
    prospects = collection.find({"status": "new"})
    
    count = 0
    for data in prospects:
        try:
            # Extraction des données structurées
            info_contact = data.get('contact', {})
            info_adresse = data.get('adresse', {})
            info_entite = data.get('entite', {})
            coords = data.get('coordonnees', {})

            nom = info_contact.get('nom')
            if not nom or str(nom).strip().lower() == 'false':
                continue

            # --- CRÉATION AVEC LES BONS INTITULÉS ---
            # On utilise les champs standards de base de Crème
            new_contact = Contact.objects.create(
                user=admin_user, 
                last_name=str(nom).strip(),
                first_name=str(info_contact.get('prenom') or '').strip(),
                
                # Champs de l'interface pour les coordonnées
                email=coords.get('email'),
                # Si tu as des téléphones dans 'raw', on pourrait les extraire ici
                # phone=coords.get('telephone'), 

                # Pour l'adresse, si 'address' ne passe pas, Crème utilise souvent 
                # un système de 'Address Entity'. Pour ne pas bloquer l'import, 
                # on met l'essentiel dans la Description et le reste en clair.
                description=(
                    f" Entreprise : {info_entite.get('libelle')}\n"
                    f" Adresse : {info_adresse.get('ligne1')}, {info_adresse.get('code_postal')} {info_adresse.get('ville')}\n"
                    f" Assujetti Taxe : {data.get('is_in_taxe')}\n"
                    f" E-mailing autorisé : {data.get('is_in_mailing')}"
                )
            )

            # Mise à jour MongoDB
            collection.update_one(
                {"_id": data["_id"]}, 
                {"$set": {"status": "imported"}}
            )

            count += 1
            if count % 100 == 0:
                print(f" {count} fiches créées dans l'interface...")

        except Exception as e:
            print(f" Erreur ID {data.get('_id')} : {e}")

    print(f"\n Terminé ! {count} contacts transférés au bon endroit.")

if __name__ == "__main__":
    transfer_to_creme()
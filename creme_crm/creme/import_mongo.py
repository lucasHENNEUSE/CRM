import os
import sys
import django
from pymongo import MongoClient

# --- 1. CONFIGURATION DJANGO ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'creme.settings')
django.setup()

from creme.creme_core.models import CremeUser as User
from creme.persons.models import Contact, Address
from django.contrib.contenttypes.models import ContentType

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

    # --- RESET AUTOMATIQUE POUR LE DÉVELOPPEMENT ---
    # on force la réinitialisation pour être sur de tout traiter
    print ("Réinitialisation de tous les contacts à 'new' pour forcer l'import complet...")
    collection.update_many({}, {"$set": {"status": "new"}})

    # On récupère les documents 'new'
    prospects = collection.find({"status": "new"})
    
    count_created = 0
    count_updated = 0

    for data in prospects:
        try:
            # Extraction des données structurées
            info_contact = data.get('contact', {})
            info_adresse = data.get('adresse', {})
            info_entite = data.get('entite', {})
            coords = data.get('coordonnees', {})

            nom = info_contact.get('nom')
            if not nom or str(nom).strip().lower() == 'false':
                # Si pas de nom, on utilise le libellé de l'entité, l'email ou "Inconnu"
                nom = info_entite.get('libelle') or coords.get('email') or "Inconnu"

            # Conversion sécurisée pour les entiers (ex: nombre de stagiaires)
            nb_stagiaires = info_entite.get('nb_stagiaires')
            if nb_stagiaires and str(nb_stagiaires).isdigit():
                nb_stagiaires = int(nb_stagiaires)
            else:
                nb_stagiaires = None

            email = str(coords.get('email') or '').strip()

            # Conversion booléen -> OUI/NON
            is_in_taxe = 'OUI' if data.get('is_in_taxe') in [True, 1, 'True', 'true', 'OUI', 'oui'] else 'NON'
            # CORRECTION : La clé dans MongoDB est 'is_in_emailing', pas 'is_in_mailing'
            is_in_mailing = 'OUI' if data.get('is_in_emailing') in [True, 1, 'True', 'true', 'OUI', 'oui'] else 'NON'

            # Préparation des données d'adresse
            addr_kwargs = {
                'address': info_adresse.get('ligne1', ''),
                'zipcode': info_adresse.get('code_postal', ''),
                'city': info_adresse.get('ville', ''),
            }
            has_addr = any([addr_kwargs['address'], addr_kwargs['zipcode'], addr_kwargs['city']])

            # Données à sauvegarder
            contact_data = {
                'user': admin_user,
                'last_name': str(nom).strip(),
                'first_name': str(info_contact.get('prenom') or '').strip(),
                'email': email,
                # 'entity_label': info_entite.get('libelle', ''),
                'education_nb_stagiaires': nb_stagiaires,
                'education_montant_taxe': str(info_entite.get('montant_taxe', '')),
                'is_in_taxe': is_in_taxe,
                'is_in_mailing': is_in_mailing,
                'coordonnees_raw': str(coords.get('raw', '')),
                'consent_data': str(data.get('consent', '')),
                'import_status': "Importé depuis MongoDB"
            }

            # --- GESTION CRÉATION / MISE À JOUR ---
            # On cherche si le contact existe déjà par email (pour éviter les doublons et corriger l'adresse)
            existing_contact = Contact.objects.filter(email=email, is_deleted=False).first() if email else None

            if existing_contact:
                # Mise à jour des statuts (Taxe / Mailing) si le contact existe déjà
                if existing_contact.is_in_mailing != is_in_mailing or existing_contact.is_in_taxe != is_in_taxe:
                    existing_contact.is_in_mailing = is_in_mailing
                    existing_contact.is_in_taxe = is_in_taxe
                    existing_contact.save()

                # Mise à jour de l'adresse sur la fiche existante
                if existing_contact.billing_address:
                    existing_contact.billing_address.address = addr_kwargs['address']
                    existing_contact.billing_address.zipcode = addr_kwargs['zipcode']
                    existing_contact.billing_address.city = addr_kwargs['city']
                    existing_contact.billing_address.save()
                elif has_addr:
                    addr_kwargs['object'] = existing_contact
                    addr_kwargs['content_type'] = ContentType.objects.get_for_model(existing_contact)
                    existing_contact.billing_address = Address.objects.create(**addr_kwargs)
                    existing_contact.save()
                count_updated += 1
            else:
                # Création d'un nouveau contact
                contact = Contact.objects.create(**contact_data)
                
                if has_addr:
                    addr_kwargs['object'] = contact
                    addr_kwargs['content_type'] = ContentType.objects.get_for_model(contact)
                    contact.billing_address = Address.objects.create(**addr_kwargs)
                    contact.save()

                count_created += 1

            # Mise à jour MongoDB import_mongo.py
            collection.update_one(
                {"_id": data["_id"]}, 
                {"$set": {"status": "imported"}}
            )

            total = count_created + count_updated
            if total % 100 == 0:
                print(f" {total} fiches traitées ({count_created} créées, {count_updated} mises à jour)...")

        except Exception as e:
            print(f" Erreur ID {data.get('_id')} : {e}")

    print(f"\n Terminé ! {count_created} créés, {count_updated} mis à jour.")

if __name__ == "__main__":
    transfer_to_creme()
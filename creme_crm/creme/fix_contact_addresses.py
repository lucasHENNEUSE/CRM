import os
import sys
import django

# Configuration de l'environnement Django
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'creme.settings')
django.setup()

from creme.creme_core.models import CustomBrickConfigItem
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.persons.models import Contact
from creme.persons.populate import UUID_CBRICK_CONTACT_INFO

def fix_addresses_and_view():
    print("--- DÉBUT DU CORRECTIF ADRESSES ---")

    # 1. MIGRATION DES DONNÉES
    print("1. Migration des données d'adresse vers les champs standards (Adresse 1)...")
    contacts = Contact.objects.filter(is_deleted=False)
    count = 0
    for c in contacts:
        changed = False
        # On vérifie si les champs personnalisés contiennent des données
        has_custom_data = c.address_line1 or c.address_zipcode or c.address_city
        
        if has_custom_data:
            # On copie vers les champs standards (Adresse 1 / Facturation) si ceux-ci sont vides
            # Dans Creme, billing_address est utilisé pour l'adresse principale
            if c.address_line1 and not c.billing_address:
                c.billing_address = c.address_line1
                changed = True
            
            if c.address_zipcode and not c.billing_zipcode:
                c.billing_zipcode = c.address_zipcode
                changed = True
                
            if c.address_city and not c.billing_city:
                c.billing_city = c.address_city
                changed = True
            
            if changed:
                c.save()
                count += 1
    
    print(f" -> {count} contacts mis à jour (données déplacées dans 'Adresse 1').")

    # 2. NETTOYAGE DE LA VUE
    print("2. Suppression des champs doublons dans la brique 'Informations'...")
    try:
        cbci = CustomBrickConfigItem.objects.get(uuid=UUID_CBRICK_CONTACT_INFO)
        
        # Les champs à retirer de la vue
        fields_to_remove = ['address_line1', 'address_city', 'address_zipcode']
        
        # Debug : Afficher les champs actuels
        current_fields = [cell.value for cell in cbci.cells if isinstance(cell, EntityCellRegularField)]
        print(f" -> Champs actuels dans la vue : {current_fields}")

        # On reconstruit la liste des cellules en excluant celles à supprimer
        original_len = len(cbci.cells)
        new_cells = [
            cell for cell in cbci.cells 
            if not (isinstance(cell, EntityCellRegularField) and cell.value in fields_to_remove)
        ]
        
        if len(new_cells) < original_len:
            cbci.cells = new_cells
            cbci.save()
            print(f" -> {original_len - len(new_cells)} champs supprimés de la vue.")
            print(" -> Vue sauvegardée avec succès.")
        else:
            print(" -> Aucun champ à supprimer trouvé (ils sont peut-être déjà partis).")
            # On force la sauvegarde pour rafraîchir le cache de configuration
            cbci.save()
            print(" -> Sauvegarde de la configuration forcée (pour mise à jour du cache).")

    except CustomBrickConfigItem.DoesNotExist:
        print("ERREUR : La configuration de la brique est introuvable.")
    except Exception as e:
        print(f"ERREUR : {e}")

    print("--- TERMINÉ ---")

if __name__ == "__main__":
    fix_addresses_and_view()
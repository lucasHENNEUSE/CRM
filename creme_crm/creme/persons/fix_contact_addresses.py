from pathlib import Path
import sys
import os
import django


CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = next(parent for parent in CURRENT_FILE.parents if (parent / "creme_crm").exists())
CREME_ROOT = PROJECT_ROOT / "creme_crm"

sys.path.insert(0, str(CREME_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "creme.dev_settings")
django.setup()

from creme.creme_core.models import CustomBrickConfigItem
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.persons.models import Contact
from creme.persons.populate import UUID_CBRICK_CONTACT_INFO


def fix_addresses_and_view():
    print("--- DÉBUT DU CORRECTIF ADRESSES ---")

    print("1. Migration des données d'adresse vers les champs standards (Adresse 1)...")
    contacts = Contact.objects.filter(is_deleted=False)
    count = 0

    for c in contacts:
        changed = False
        has_custom_data = c.address_line1 or c.address_zipcode or c.address_city

        if has_custom_data:
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

    print("2. Suppression des champs doublons dans la brique 'Informations'...")
    try:
        cbci = CustomBrickConfigItem.objects.get(uuid=UUID_CBRICK_CONTACT_INFO)

        fields_to_remove = ["address_line1", "address_city", "address_zipcode"]

        current_fields = [cell.value for cell in cbci.cells if isinstance(cell, EntityCellRegularField)]
        print(f" -> Champs actuels dans la vue : {current_fields}")

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
            cbci.save()
            print(" -> Sauvegarde de la configuration forcée (pour mise à jour du cache).")

    except CustomBrickConfigItem.DoesNotExist:
        print("ERREUR : La configuration de la brique est introuvable.")
    except Exception as e:
        print(f"ERREUR : {e}")

    print("--- TERMINÉ ---")


if __name__ == "__main__":
    fix_addresses_and_view()

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

def update_contact_view():
    print("Mise à jour de la vue Contact...")
    try:
        # Récupération de la configuration de la brique "Informations"
        cbci = CustomBrickConfigItem.objects.get(uuid=UUID_CBRICK_CONTACT_INFO)
        
        # Liste des champs à ajouter
        new_fields = [
            'education_nb_stagiaires', 'education_montant_taxe',
            'coordonnees_raw', 'consent_data', 'import_status'
        ]
        
        # On récupère les champs déjà présents pour éviter les doublons
        existing_names = [cell.value for cell in cbci.cells if isinstance(cell, EntityCellRegularField)]
        cells_to_add = []
        
        for fname in new_fields:
            if fname not in existing_names:
                print(f" - Ajout du champ : {fname}")
                # On crée la cellule d'affichage pour le champ
                cells_to_add.append(EntityCellRegularField.build(Contact, fname))
            else:
                print(f" - Champ déjà présent : {fname}")
        
        if cells_to_add:
            # On ajoute les nouvelles cellules à la liste existante
            # (On insère avant la description qui est souvent à la fin)
            current_cells = list(cbci.cells)
            insert_pos = len(current_cells) - 3 # Juste avant description/created/modified
            if insert_pos < 0: insert_pos = len(current_cells)
            
            for cell in reversed(cells_to_add):
                current_cells.insert(insert_pos, cell)
            
            cbci.cells = current_cells
            cbci.save()
            print("\nSUCCÈS : Vue mise à jour !")
        else:
            print("\nAucun changement nécessaire.")
            
    except CustomBrickConfigItem.DoesNotExist:
        print("ERREUR : La brique 'Informations' est introuvable (UUID incorrect ?).")
    except Exception as e:
        print(f"ERREUR : {e}")

if __name__ == "__main__":
    update_contact_view()

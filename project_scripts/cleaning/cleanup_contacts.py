from pathlib import Path
import sys
import os
import django
from collections import defaultdict


CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = next(parent for parent in CURRENT_FILE.parents if (parent / "creme_crm").exists())
CREME_ROOT = PROJECT_ROOT / "creme_crm"

sys.path.insert(0, str(CREME_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "creme.dev_settings")
django.setup()

from creme.persons.models import Contact


def deep_cleanup() -> None:
    """Nettoie les contacts en double dans la base de données CRM."""
    db_path = CREME_ROOT / "db.sqlite3"
    print(f"Base de données cible : {db_path}")

    print("Récupération de tous les contacts pour analyse Python...")

    # Utilise l'ORM Django pour plus de sécurité et de flexibilité
    contacts = Contact.objects.filter(is_deleted=False).order_by("id")
    rows = list(contacts)

    print(f"{len(rows)} contacts trouvés au total. Analyse des doublons...")

    email_map = {}
    duplicates_found = 0
    deleted_count = 0

    # 1. Traitement des doublons avec email
    email_map = defaultdict(list)
    for contact in rows:
        if contact.email:
            clean_email = contact.email.strip().lower()
            email_map[clean_email].append(contact)

    # 2. Traitement des doublons sans email (basé sur nom, prénom, entité)
    no_email_map = defaultdict(list)
    for contact in rows:
        if not contact.email:
            key = (
                (contact.last_name or "").strip().lower(),
                (contact.first_name or "").strip().lower(),
                (contact.entity_label or "").strip().lower(),
            )
            # On ne traite que les clés qui ont du sens
            if any(key):
                no_email_map[key].append(contact)

    # Fusionne les deux stratégies de détection
    all_duplicate_groups = list(email_map.values()) + list(no_email_map.values())

    for group in all_duplicate_groups:
        if len(group) > 1:
            duplicates_found += 1
            # Le premier contact (le plus ancien) est conservé
            keep_contact = group[0]
            delete_contacts = group[1:]

            ids_to_delete = [c.id for c in delete_contacts]
            print(
                f"[DOUBLON] Conservation ID {keep_contact.id} ({keep_contact}), "
                f"Suppression des IDs {ids_to_delete}"
            )

            for contact_to_delete in delete_contacts:
                contact_to_delete.delete()  # Utilise la suppression sécurisée de Django
                deleted_count += 1

    print("-" * 40)
    print("TERMINÉ.")
    print(f"Groupes de doublons identifiés : {duplicates_found}")
    print(f"Fiches supprimées : {deleted_count}")
    print("-" * 40)


if __name__ == "__main__":
    deep_cleanup()

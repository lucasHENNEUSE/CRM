from pathlib import Path
import pymongo
import sqlite3


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CREME_ROOT = PROJECT_ROOT / "creme_crm"


def force_display_contacts():
    client = pymongo.MongoClient("mongodb://localhost:27018/")
    db = client["poc_aggregation"]

    db_path = CREME_ROOT / "db.sqlite3"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Chargement des emails existants dans le CRM...")
    cursor.execute("SELECT cremeentity_ptr_id, email FROM persons_contact")
    existing_contacts = {}

    for contact_id, email in cursor.fetchall():
        if email:
            existing_contacts[str(email).strip().lower()] = contact_id

    print(f"{len(existing_contacts)} emails uniques identifiés.")

    updated_count = 0
    skipped_count = 0

    def sync_collection(col_name):
        nonlocal updated_count, skipped_count

        docs = list(db[col_name].find())
        print(f"Synchronisation de {len(docs)} contacts ({col_name})...")

        for p in docs:
            email = str(p.get("coordonnees", {}).get("email", "")).strip().lower()
            if not email:
                continue

            p_taxe = p.get("is_in_taxe", "NON")
            p_mail = p.get("is_in_emailing", "NON")

            contact_id = existing_contacts.get(email)

            if contact_id is None:
                skipped_count += 1
                continue

            cursor.execute(
                """
                UPDATE persons_contact
                SET is_in_taxe = ?, is_in_mailing = ?
                WHERE cremeentity_ptr_id = ?
                """,
                (p_taxe, p_mail, contact_id),
            )

            cursor.execute(
                """
                UPDATE creme_core_cremeentity
                SET is_deleted = 0
                WHERE id = ?
                """,
                (contact_id,),
            )

            updated_count += 1

    sync_collection("prospects_taxe")
    sync_collection("prospects_emailing")

    conn.commit()
    conn.close()

    print(f"Terminé ! {updated_count} contacts mis à jour.")
    print(f"{skipped_count} contacts ignorés (absents du CRM).")


if __name__ == "__main__":
    force_display_contacts()

from pathlib import Path
import sqlite3


CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = next(parent for parent in CURRENT_FILE.parents if (parent / "creme_crm").exists())
CREME_ROOT = PROJECT_ROOT / "creme_crm"


def deep_cleanup() -> None:
    db_path = CREME_ROOT / "db.sqlite3"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    print(f"Base de données cible : {db_path}")

    print("Récupération de tous les contacts pour analyse Python...")

    cursor.execute("SELECT cremeentity_ptr_id, email FROM persons_contact")
    rows = cursor.fetchall()

    print(f"{len(rows)} contacts trouvés au total. Analyse des doublons...")

    email_map = {}
    duplicates_found = 0
    deleted_count = 0

    for pid, email in rows:
        if not email:
            continue

        clean_email = str(email).strip().lower()

        if clean_email not in email_map:
            email_map[clean_email] = []
        email_map[clean_email].append(pid)

    for email, ids in email_map.items():
        if len(ids) > 1:
            duplicates_found += 1
            ids.sort()

            keep_id = ids[0]
            delete_ids = ids[1:]

            print(
                f"[DOUBLON] {email} : Conservation ID {keep_id}, "
                f"Suppression des IDs {delete_ids}"
            )

            for did in delete_ids:
                cursor.execute(
                    "DELETE FROM persons_contact WHERE cremeentity_ptr_id = ?",
                    (did,),
                )
                cursor.execute(
                    "DELETE FROM creme_core_cremeentity WHERE id = ?",
                    (did,),
                )
                deleted_count += 1

    conn.commit()

    print("Optimisation de la base (VACUUM)...")
    cursor.execute("VACUUM")
    conn.close()

    print("-" * 40)
    print("TERMINÉ.")
    print(f"Groupes de doublons identifiés : {duplicates_found}")
    print(f"Fiches supprimées : {deleted_count}")
    print("-" * 40)


if __name__ == "__main__":
    deep_cleanup()

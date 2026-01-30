import sqlite3
import os

def deep_cleanup():
    # Chemin vers ta base active
    db_path = "/home/lucash/iadev/cremecrm/CRM/creme_crm/db.sqlite3"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(" Recherche approfondie (Espaces & Casse)...")

    # On utilise TRIM et LOWER pour détecter les vrais doublons visuels
    cursor.execute("""
        SELECT LOWER(TRIM(email)) as clean_email 
        FROM persons_contact 
        WHERE email IS NOT NULL AND email != ''
        GROUP BY clean_email HAVING COUNT(*) > 1
    """)
    duplicate_emails = [row[0] for row in cursor.fetchall()]

    if not duplicate_emails:
        print(" Toujours rien trouvé. On va lister les 5 premiers emails pour voir :")
        cursor.execute("SELECT email FROM persons_contact LIMIT 5")
        for row in cursor.fetchall():
            print(f"DEBUG: '{row[0]}'")
        return

    print(f" Nettoyage forcé de {len(duplicate_emails)} groupes de doublons...")

    for email in duplicate_emails:
        # On récupère tous les IDs pour cet email
        cursor.execute("SELECT cremeentity_ptr_id FROM persons_contact WHERE LOWER(TRIM(email)) = ?", (email,))
        ids = [row[0] for row in cursor.fetchall()]
        
        # On garde le premier, on supprime les autres
        keep_id = ids[0]
        to_delete = ids[1:]

        for old_id in to_delete:
            cursor.execute("DELETE FROM persons_contact WHERE cremeentity_ptr_id = ?", (old_id,))
            cursor.execute("DELETE FROM creme_core_cremeentity WHERE id = ?", (old_id,))

    conn.commit()
    conn.close()
    print(" TERMINÉ. Vérifie ta page Taxe maintenant !")

if __name__ == "__main__":
    deep_cleanup()
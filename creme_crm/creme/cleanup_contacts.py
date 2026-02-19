import sqlite3
import os

def deep_cleanup():
    # Chemin vers ta base active
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.abspath(os.path.join(base_dir, "..", "db.sqlite3"))
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    print(f" Base de données cible : {db_path}")

    print(" Récupération de TOUS les contacts pour analyse Python...")
    
    # On récupère ID et Email de tout le monde
    cursor.execute("SELECT cremeentity_ptr_id, email FROM persons_contact")
    rows = cursor.fetchall()
    
    print(f" {len(rows)} contacts trouvés au total. Analyse des doublons...")

    email_map = {}
    duplicates_found = 0
    deleted_count = 0

    for pid, email in rows:
        if not email:
            continue
            
        # Normalisation stricte en Python (plus fiable que SQL)
        clean_email = str(email).strip().lower()
        
        if clean_email not in email_map:
            email_map[clean_email] = []
        email_map[clean_email].append(pid)

    # Traitement des doublons
    for email, ids in email_map.items():
        if len(ids) > 1:
            duplicates_found += 1
            # On trie par ID croissant (le plus petit est le plus ancien, on le garde)
            ids.sort()
            
            keep_id = ids[0]
            delete_ids = ids[1:]
            
            print(f" [DOUBLON] {email} : Conservation ID {keep_id}, Suppression des IDs {delete_ids}")
            
            for did in delete_ids:
                # Suppression table fille
                cursor.execute("DELETE FROM persons_contact WHERE cremeentity_ptr_id = ?", (did,))
                # Suppression table mère
                cursor.execute("DELETE FROM creme_core_cremeentity WHERE id = ?", (did,))
                deleted_count += 1

    conn.commit()
    # On lance un VACUUM pour nettoyer physiquement le fichier et mettre à jour les index
    print(" Optimisation de la base (VACUUM)...")
    cursor.execute("VACUUM")
    conn.close()
    
    print("-" * 40)
    print(f" TERMINÉ.")
    print(f" Groupes de doublons identifiés : {duplicates_found}")
    print(f" Fiches supprimées : {deleted_count}")
    print("-" * 40)

if __name__ == "__main__":
    deep_cleanup()
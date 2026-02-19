import pymongo
import sqlite3
import os
import time

def force_display_contacts():
    client = pymongo.MongoClient("mongodb://localhost:27018/") 
    db = client["poc_aggregation"]
    
    # Chemin vers la base (dossier parent)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.abspath(os.path.join(base_dir, "..", "db.sqlite3"))

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # --- CHARGEMENT PRÉALABLE DES EMAILS EXISTANTS ---
    # On charge tout en mémoire pour éviter les problèmes de comparaison SQL (LOWER/TRIM)
    print(" Chargement des emails existants dans le CRM...")
    cursor.execute("SELECT email FROM persons_contact")
    existing_emails = set()
    for row in cursor.fetchall():
        if row[0]:
            existing_emails.add(str(row[0]).strip().lower())
    print(f" {len(existing_emails)} emails uniques identifiés.")

    def sync_collection(col_name):
        docs = list(db[col_name].find())
        print(f" Forçage de l'affichage pour {len(docs)} contacts ({col_name})...")
        for p in docs:
            email = str(p.get("coordonnees", {}).get("email", "")).strip().lower()
            nom = str(p.get("contact", {}).get("nom", "SANS NOM")).strip().upper()
            prenom = str(p.get("contact", {}).get("prenom", "")).strip().title()
            if not email: continue

            # On récupère les vrais statuts du document MongoDB
            p_taxe = p.get("is_in_taxe", "NON")
            p_mail = p.get("is_in_emailing", "NON")

            # 1. Vérification Python (100% fiable)
            if email in existing_emails:
                # 2. Mise à jour : on force is_deleted=0 pour la visibilité
                cursor.execute("""
                    UPDATE persons_contact 
                    SET is_in_taxe = ?, is_in_mailing = ?, is_deleted = 0 
                    WHERE LOWER(email) = ?
                """, (p_taxe, p_mail, email))
            else:
                # 3. Création complète avec ID d'entité
                new_id = int(time.time() * 1000000) % 2000000000
                try:
                    # Table mère
                    cursor.execute("""
                        INSERT INTO creme_core_cremeentity (id, user_id, created, modified, is_deleted, discr_id) 
                        VALUES (?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0, 'persons-contact')
                    """, (new_id,))
                    # Table fille
                    cursor.execute("""
                        INSERT INTO persons_contact (cremeentity_ptr_id, last_name, first_name, email, is_in_taxe, is_in_mailing, is_deleted, user_id) 
                        VALUES (?, ?, ?, ?, ?, ?, 0, 1)
                    """, (new_id, nom, prenom, email, p_taxe, p_mail))
                    
                    # On ajoute le nouvel email à la liste connue pour ne pas le recréer si on le recroise
                    existing_emails.add(email)
                except: continue

    sync_collection("prospects_taxe")
    sync_collection("prospects_emailing")

    conn.commit()
    conn.close()
    print(" TERMINÉ. Redémarre ton serveur Django !")

if __name__ == "__main__":
    force_display_contacts()
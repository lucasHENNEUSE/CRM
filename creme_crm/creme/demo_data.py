import os
import sys
import subprocess

def run_cmd(args, label):
    print(f"\n---  {label} ---")
    env = os.environ.copy()
    # On s'assure que le PYTHONPATH inclut le dossier parent pour Crème
    env["PYTHONPATH"] = f"{os.getcwd()}/..:{env.get('PYTHONPATH', '')}"
    
    result = subprocess.run(args, env=env)
    if result.returncode != 0:
        print(f" Erreur lors de l'étape : {label}")
        sys.exit(1)

def main():
    print("===  SCÉNARIO DE DÉMONSTRATION BIG DATA ===")
    
    # 1. Générer les données dans MongoDB
    run_cmd([sys.executable, "gen_mongo.py"], "GÉNÉRATION DES PROSPECTS DANS MONGODB")

    # 2. Importer ces données dans le CRM
    run_cmd([sys.executable, "test_import.py"], "IMPORTATION VERS CRÈME CRM")

    print("\n Scénario terminé ! Rafraîchissez l'interface Crème CRM pour voir les résultats.")

if __name__ == "__main__":
    main()
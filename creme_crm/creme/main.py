import os
import sys
import subprocess

def run_cmd(args):
    """Exécute une commande système et affiche la sortie."""
    print(f" Exécution : {' '.join(args)}")
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{os.getcwd()}/..:{env.get('PYTHONPATH', '')}"
    
    result = subprocess.run(args, env=env)
    if result.returncode != 0:
        print(f" Erreur sur la commande : {' '.join(args)}")
        sys.exit(1)

def main():
    # Nettoyage
    print("--- Nettoyage du cache Python ---")
    subprocess.run("find . -name '*.pyc' -delete", shell=True)

    # 1. Installation des dépendances
    if os.path.exists("requirements.txt"):
        print("---  Vérification des dépendances ---")
        run_cmd([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

    # 2. Mise à jour des modèles (IMPORTANT d'après tes logs)
    print("\n---  Génération des migrations ---")
    run_cmd([sys.executable, "manage.py", "makemigrations"])
    
    print("\n---  Migration de la base de données ---")
    run_cmd([sys.executable, "manage.py", "migrate", "--noinput"])

    # 3. Peuplement
    print("\n---  Initialisation des données Crème ---")
    run_cmd([sys.executable, "manage.py", "creme_populate"])

    # 4. Génération des médias
    print("\n---  Génération des médias ---")
    run_cmd([sys.executable, "manage.py", "generatemedia"])

    # 5. Lancement du serveur (Correction de l'argument ici)
    print("\n---  Lancement du serveur (http://127.0.0.1:8000) ---")
    run_cmd([sys.executable, "manage.py", "runserver"])

if __name__ == "__main__":
    main()
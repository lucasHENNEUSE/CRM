import os
import sys
import subprocess

def run_cmd(args):
    """Exécute une commande système et affiche la sortie."""
    print(f" Exécution : {' '.join(args)}")
    # On force le PYTHONPATH pour que les modules 'creme' soient trouvés
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{os.getcwd()}/..:{env.get('PYTHONPATH', '')}"
    
    result = subprocess.run(args, env=env)
    if result.returncode != 0:
        print(f" Erreur sur la commande : {' '.join(args)}")
        sys.exit(1)

def main():
    # 1. Installation des dépendances (si nécessaire)
    if os.path.exists("requirements.txt"):
        print("---  Vérification des dépendances ---")
        run_cmd([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

    # 2. Migration de la base de données
    print("\n---   Migration de la base de données ---")
    run_cmd([sys.executable, "manage.py", "migrate", "--noinput"])

    # 3. Peuplement (Populate)
    print("\n---  Initialisation des données Crème ---")
    run_cmd([sys.executable, "manage.py", "creme_populate"])

    # 4. Génération des médias (CSS/JS)
    print("\n---  Génération des médias ---")
    run_cmd([sys.executable, "manage.py", "generatemedia"])

    # 5. Lancement du serveur
    print("\n---  Lancement du serveur (http://127.0.0.1:8000) ---")
    run_cmd([sys.executable, "manage.py", "runserver"])

if __name__ == "__main__":
    main()
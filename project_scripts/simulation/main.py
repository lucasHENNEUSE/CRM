from pathlib import Path
import os
import sys
import subprocess


CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = next(parent for parent in CURRENT_FILE.parents if (parent / "creme_crm").exists())
CREME_ROOT = PROJECT_ROOT / "creme_crm"
CREME_APP_ROOT = CREME_ROOT / "creme"

requirements_path = CREME_APP_ROOT / "requirements.txt"
manage_py_path = CREME_APP_ROOT / "manage.py"


def run_cmd(args, cwd=None):
    print(f"Exécution : {' '.join(map(str, args))}")
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{CREME_ROOT}:{env.get('PYTHONPATH', '')}"

    result = subprocess.run(args, env=env, cwd=cwd)
    if result.returncode != 0:
        print(f"Erreur sur la commande : {' '.join(map(str, args))}")
        sys.exit(1)


def main():
    print("--- Nettoyage du cache Python ---")
    subprocess.run("find . -name '*.pyc' -delete", shell=True, cwd=PROJECT_ROOT)

    if requirements_path.exists():
        print("--- Vérification des dépendances ---")
        run_cmd([sys.executable, "-m", "pip", "install", "-r", str(requirements_path)], cwd=PROJECT_ROOT)

    print("\n--- Génération des migrations ---")
    run_cmd([sys.executable, str(manage_py_path), "makemigrations"], cwd=CREME_APP_ROOT)

    print("\n--- Migration de la base de données ---")
    run_cmd([sys.executable, str(manage_py_path), "migrate", "--noinput"], cwd=CREME_APP_ROOT)

    print("\n--- Initialisation des données Crème ---")
    run_cmd([sys.executable, str(manage_py_path), "creme_populate"], cwd=CREME_APP_ROOT)

    print("\n--- Génération des médias ---")
    run_cmd([sys.executable, str(manage_py_path), "generatemedia"], cwd=CREME_APP_ROOT)

    print("\n--- Lancement du serveur (http://127.0.0.1:8000) ---")
    run_cmd([sys.executable, str(manage_py_path), "runserver"], cwd=CREME_APP_ROOT)


if __name__ == "__main__":
    main()

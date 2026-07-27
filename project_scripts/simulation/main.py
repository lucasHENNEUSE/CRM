"""
main.py - Lanceur local sécurisé de CremeCRM POC2

Ce script sert uniquement à démarrer l'interface locale.

Il ne lance volontairement pas :
- makemigrations ;
- migrate ;
- creme_populate ;
- import MongoDB ;
- réparation automatique de la base.

Ces opérations doivent rester séparées pour éviter de mélanger :
- initialisation technique ;
- import de données ;
- interface ;
- anciens flux POC1.
"""

from pathlib import Path
import os
import subprocess
import sys


CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = next(parent for parent in CURRENT_FILE.parents if (parent / "creme_crm").exists())
CREME_ROOT = PROJECT_ROOT / "creme_crm"
CREME_APP_ROOT = CREME_ROOT / "creme"
MANAGE_PY_PATH = CREME_APP_ROOT / "manage.py"

env = os.environ.copy()
env["PYTHONPATH"] = str(CREME_ROOT)
env["DJANGO_SETTINGS_MODULE"] = "creme.dev_settings"

print("Démarrage de CremeCRM POC2")
print(f"Racine du projet : {PROJECT_ROOT}")
print("Interface : http://127.0.0.1:8000/")
print("")
print("Ce lanceur démarre uniquement le serveur local.")
print("Il ne lance ni migration, ni creme_populate, ni import de données.")
print("")

subprocess.run(
    [
        sys.executable,
        str(MANAGE_PY_PATH),
        "runserver",
        "--settings=creme.dev_settings",
    ],
    cwd=PROJECT_ROOT,
    env=env,
    check=False,
)

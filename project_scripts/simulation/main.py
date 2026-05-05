"""
main.py - Script de démarrage local de CremeCRM

Ce script sert de point d'entrée unique pour relancer l'environnement local.

Il enchaîne automatiquement les étapes suivantes :

1. nettoyage du cache Python ;
2. vérification des dépendances ;
3. génération des migrations ;
4. migration de la base ;
5. initialisation des données de base ;
6. génération des médias ;
7. lancement du serveur local.

Deux fichiers de logs sont générés automatiquement dans ./logs :
- logs_technique.log : suivi des opérations techniques ;
- logs_data.log : suivi des opérations liées aux données.

Les fichiers de logs sont gérés avec rotation automatique :
- taille maximale : 5 MB ;
- 3 archives conservées.
"""

from pathlib import Path
import getpass
import logging
from logging.handlers import RotatingFileHandler
import os
import subprocess
import sys
import time
import warnings


# On masque les avertissements de dépréciation pour garder une console lisible.
warnings.filterwarnings("ignore", category=DeprecationWarning)


CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = next(parent for parent in CURRENT_FILE.parents if (parent / "creme_crm").exists())
CREME_ROOT = PROJECT_ROOT / "creme_crm"
CREME_APP_ROOT = CREME_ROOT / "creme"
LOGS_ROOT = PROJECT_ROOT / "logs"

REQUIREMENTS_PATH = CREME_APP_ROOT / "requirements.txt"
MANAGE_PY_PATH = CREME_APP_ROOT / "manage.py"
DJANGO_SETTINGS_MODULE = "creme.dev_settings"


def setup_loggers():
    """
    Prépare les deux loggers du projet et la sortie console.

    - logs_technique.log : opérations techniques ;
    - logs_data.log      : opérations liées aux données ;
    - console            : affichage des messages importants.
    """
    LOGS_ROOT.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    tech_logger = logging.getLogger("tech_logger")
    data_logger = logging.getLogger("data_logger")

    tech_logger.setLevel(logging.DEBUG)
    data_logger.setLevel(logging.DEBUG)

    tech_logger.propagate = False
    data_logger.propagate = False

    # Évite les doublons si le script est relancé dans le même contexte Python.
    tech_logger.handlers.clear()
    data_logger.handlers.clear()

    tech_file_handler = RotatingFileHandler(
        str(LOGS_ROOT / "logs_technique.log"),
        encoding="utf-8",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
    )
    tech_file_handler.setLevel(logging.DEBUG)
    tech_file_handler.setFormatter(formatter)

    data_file_handler = RotatingFileHandler(
        str(LOGS_ROOT / "logs_data.log"),
        encoding="utf-8",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
    )
    data_file_handler.setLevel(logging.DEBUG)
    data_file_handler.setFormatter(formatter)

    tech_console_handler = logging.StreamHandler(sys.stdout)
    tech_console_handler.setLevel(logging.INFO)
    tech_console_handler.setFormatter(formatter)

    data_console_handler = logging.StreamHandler(sys.stdout)
    data_console_handler.setLevel(logging.INFO)
    data_console_handler.setFormatter(formatter)

    tech_logger.addHandler(tech_file_handler)
    tech_logger.addHandler(tech_console_handler)

    data_logger.addHandler(data_file_handler)
    data_logger.addHandler(data_console_handler)

    return tech_logger, data_logger


tech_log, data_log = setup_loggers()


def log_separator(message):
    """Ajoute une séparation lisible dans les deux fichiers de logs."""
    for logger in (tech_log, data_log):
        logger.info("=" * 60)
        logger.info(message)
        logger.info("=" * 60)


def build_env():
    """Construit l'environnement d'exécution avec le PYTHONPATH du projet."""
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{CREME_ROOT}:{env.get('PYTHONPATH', '')}"
    env["DJANGO_SETTINGS_MODULE"] = DJANGO_SETTINGS_MODULE
    return env


def run_cmd(args, logger, cwd=None, capture=True):
    """
    Lance une commande système et journalise son résultat.

    - capture=True  : la sortie est capturée puis écrite dans le log ;
    - capture=False : la sortie s'affiche en direct, utile pour runserver.
    """
    pretty_args = " ".join(map(str, args))
    logger.info(f"Exécution : {pretty_args}")

    cmd = [str(arg) for arg in args]
    env = build_env()

    if capture:
        result = subprocess.run(
            cmd,
            env=env,
            cwd=cwd,
            capture_output=True,
            text=True,
        )

        if result.stdout:
            logger.debug(f"Détails :\n{result.stdout.strip()}")

        if result.returncode != 0:
            logger.error(f"Erreur sur la commande : {pretty_args}")
            if result.stderr:
                logger.error(f"Détails d'erreur :\n{result.stderr.strip()}")
            sys.exit(1)
    else:
        result = subprocess.run(
            cmd,
            env=env,
            cwd=cwd,
            text=True,
        )

        if result.returncode != 0:
            logger.error(f"Erreur sur la commande : {pretty_args}")
            sys.exit(1)


def main():
    """
    Point d'entrée principal.

    Lance dans l'ordre :
    nettoyage, dépendances, migrations, données, médias, puis serveur.
    """
    prep_start = time.time()

    log_separator("Démarrage du script principal")

    tech_log.info(f"Lancé par : {getpass.getuser()}")
    tech_log.info(f"Racine du projet : {PROJECT_ROOT}")
    tech_log.info(f"Répertoire applicatif : {CREME_APP_ROOT}")
    tech_log.info(f"Version Python : {sys.version.split()[0]}")

    tech_log.info("--- Nettoyage du cache Python ---")
    subprocess.run("find . -name '*.pyc' -delete", shell=True, cwd=PROJECT_ROOT)

    if REQUIREMENTS_PATH.exists():
        tech_log.info("--- Vérification des dépendances ---")
        run_cmd(
            [sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS_PATH],
            tech_log,
            cwd=PROJECT_ROOT,
        )

    tech_log.info("--- Génération des migrations ---")
    run_cmd(
        [sys.executable, MANAGE_PY_PATH, "makemigrations", "--skip-checks"],
        tech_log,
        cwd=CREME_APP_ROOT,
    )

    tech_log.info("--- Migration de la base de données ---")
    run_cmd(
        [sys.executable, MANAGE_PY_PATH, "migrate", "--noinput"],
        tech_log,
        cwd=CREME_APP_ROOT,
    )

    data_log.info("--- Initialisation des données Crème ---")
    run_cmd(
        [sys.executable, MANAGE_PY_PATH, "creme_populate"],
        data_log,
        cwd=CREME_APP_ROOT,
    )
    data_log.info("Fin du peuplement des données")

    data_log.info("--- Remise en état spécifique au POC 2 ---")
    run_cmd(
        [sys.executable, MANAGE_PY_PATH, "repair_poc2_setup"],
        data_log,
        cwd=CREME_APP_ROOT,
    )
    data_log.info("Fin de la remise en état POC 2")

    tech_log.info("--- Génération des médias ---")
    run_cmd(
        [sys.executable, MANAGE_PY_PATH, "generatemedia"],
        tech_log,
        cwd=CREME_APP_ROOT,
    )

    prep_duration = time.time() - prep_start
    tech_log.info(f"Préparation terminée en {prep_duration:.2f} secondes")

    tech_log.info("--- Lancement du serveur (http://127.0.0.1:8000) ---")
    run_cmd(
        [sys.executable, MANAGE_PY_PATH, "runserver"],
        tech_log,
        cwd=CREME_APP_ROOT,
        capture=False,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        tech_log.info("Script interrompu manuellement (Ctrl+C)")
        sys.exit(0)
    except Exception as exc:
        tech_log.critical(f"Erreur inattendue : {exc}", exc_info=True)
        sys.exit(1)

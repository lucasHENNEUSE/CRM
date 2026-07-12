import os
from .settings import *

# 1. Définition du répertoire de base
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 2. Sécurité et Débogage
DEBUG = True
SECRET_KEY = 'cle-de-test-pour-poc-big-data'
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']
ALLOWED_HOSTS=['127.0.0.1', 'localhost','0.0.0.0']

# 3. Base de données SQL (Le squelette du CRM)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# 4. Connexion MongoDB POC2
# MongoDB utilise habituellement le port standard 27017.
# Ce port étant occupé dans l'environnement local du projet,
# la configuration de référence du POC2 utilise le port 27018.
# Un autre environnement peut revenir à 27017 en surchargeant MONGODB_URI.
MONGODB_URI = os.environ.get('MONGODB_URI', 'mongodb://localhost:27018/')
MONGO_URI = MONGODB_URI
MONGO_DB_NAME = os.environ.get('MONGO_DB_NAME', 'crm_poc2')

# 5. Gestion des médias et statiques (Désactivation mode production)
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
PRODUCTION_MEDIA = False
DEV_MODE = True
MEDIA_GENERATOR_CHECK_DEV_NAMES = False
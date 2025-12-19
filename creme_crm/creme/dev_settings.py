import os
from .settings import *

# 1. Définition du répertoire de base
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 2. Sécurité et Débogage
DEBUG = True
SECRET_KEY = 'cle-de-test-pour-poc-big-data'
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

# 3. Base de données SQL (Le squelette du CRM)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# 4. Connexion MongoDB (Le réservoir Big Data)
# On utilise le port 27017 pour ne pas toucher à ton projet sur le 27018
MONGO_URI = 'mongodb://localhost:27017/'
MONGO_DB_NAME = 'poc_aggregation'

# 5. Gestion des médias et statiques (Désactivation mode production)
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
PRODUCTION_MEDIA = False
DEV_MODE = True
MEDIA_GENERATOR_CHECK_DEV_NAMES = False
import os

# Définir les chemins de base
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Créer le répertoire data s'il n'existe pas
os.makedirs(DATA_DIR, exist_ok=True)

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    
    # Modifier le chemin de la base de données pour pointer vers data/
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{os.path.join(DATA_DIR, "app.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
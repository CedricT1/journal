from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Initialiser les extensions
db = SQLAlchemy()
migrate = Migrate()

def create_app(config_class=None):
    # Créer l'instance Flask
    app = Flask(__name__)

    # Configuration de base
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_secret_key_change_in_production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialiser les extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Importer et enregistrer les blueprints
    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    # Configuration du logging
    logging.basicConfig(level=logging.INFO)

    return app
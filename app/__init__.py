from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from app.config import Config

db = SQLAlchemy()
migrate = Migrate()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)

    # Créer les tables si elles n'existent pas
    with app.app_context():
        db.create_all()

    # Importer et enregistrer les blueprints
    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    # Gestionnaire d'erreurs global
    @app.errorhandler(404)
    def not_found_error(error):
        if request.is_json:
            return jsonify(error="Ressource non trouvée"), 404
        return "Page non trouvée", 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        if request.is_json:
            return jsonify(error="Une erreur interne du serveur s'est produite"), 500
        return "Erreur interne du serveur", 500

    return app
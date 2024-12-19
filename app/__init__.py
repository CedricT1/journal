from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.config import Config

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    # Importer les routes ici pour éviter les imports circulaires
    from app.routes import index, add_rss, get_rss_feeds, generate_bulletin

    # Enregistrer les routes
    app.add_url_rule('/', 'index', index)
    app.add_url_rule('/add_rss', 'add_rss', add_rss, methods=['POST'])
    app.add_url_rule('/get_rss_feeds', 'get_rss_feeds', get_rss_feeds, methods=['GET'])
    app.add_url_rule('/generate_bulletin', 'generate_bulletin', generate_bulletin, methods=['POST'])

    with app.app_context():
        db.create_all()

    return app

from app import db
from datetime import datetime

class RSSFeed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(100), nullable=False)

class LLMConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    api_url = db.Column(db.String(500), nullable=False)
    api_key = db.Column(db.String(500), nullable=False)
    selected_model = db.Column(db.String(100), nullable=False)

class WeatherConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(100), nullable=False)
    api_key = db.Column(db.String(500), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    city = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    units = db.Column(db.String(20), nullable=False, default='metric')

# Nouveau modèle pour stocker les bulletins
class Bulletin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(500), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    contenu = db.Column(db.Text, nullable=False)  # Stocke le bulletin au format JSON

    def __repr__(self):
        return f'<Bulletin {self.titre} du {self.date}>'
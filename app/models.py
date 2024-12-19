from app import db
from datetime import datetime

class RSSFeed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(200), unique=True, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<RSSFeed {self.url}>'

class LLMConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    api_url = db.Column(db.String(200), nullable=False)
    api_key = db.Column(db.String(200), nullable=False)
    selected_model = db.Column(db.String(100), nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<LLMConfig {self.api_url}>'

class WeatherConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), nullable=False)  # ex: OpenWeatherMap, WeatherAPI
    api_key = db.Column(db.String(200), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    city = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(50), nullable=False)
    units = db.Column(db.String(20), default='metric')  # metric, imperial
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<WeatherConfig {self.provider} - {self.city}>'
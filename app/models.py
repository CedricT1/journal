from app import db
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text

class RSSFeed(db.Model):
    __tablename__ = 'rss_feeds'
    id = Column(Integer, primary_key=True)
    url = Column(String(500), nullable=False)
    category = Column(String(100), nullable=False)

class LLMConfig(db.Model):
    __tablename__ = 'llm_configs'
    id = Column(Integer, primary_key=True)
    api_url = Column(String(500), nullable=False)
    api_key = Column(String(500), nullable=False)
    selected_model = Column(String(100), nullable=False)

class WeatherConfig(db.Model):
    __tablename__ = 'weather_configs'
    id = Column(Integer, primary_key=True)
    provider = Column(String(100), nullable=False)
    api_key = Column(String(500), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    city = Column(String(100), nullable=False)
    country = Column(String(100), nullable=False)
    units = Column(String(20), nullable=False, default='metric')

class Bulletin(db.Model):
    __tablename__ = 'bulletins'
    id = Column(Integer, primary_key=True)
    titre = Column(String(500), nullable=False)
    date = Column(DateTime, nullable=False, default=datetime.utcnow)
    contenu = Column(Text, nullable=False)  # Stocke le bulletin au format JSON

    def __repr__(self):
        return f'<Bulletin {self.titre} du {self.date}>'

class AudioConfig(db.Model):
    __tablename__ = 'audio_configs'
    id = Column(Integer, primary_key=True)
    engine = Column(String(20), nullable=False, default='edge-tts')  # 'edge-tts' ou 'elevenlabs'
    
    # Configuration ElevenLabs
    elevenlabs_api_key = Column(String(500))
    elevenlabs_voice_id = Column(String(100))
    elevenlabs_stability = Column(Float, default=0.5)
    elevenlabs_clarity = Column(Float, default=0.75)
    
    # Configuration Edge-TTS
    edge_voice = Column(String(100))
    edge_rate = Column(String(20), default='+0%')
    edge_volume = Column(String(20), default='+0%')
    edge_pitch = Column(String(20), default='+0Hz')
    
    # Paramètres généraux
    output_quality = Column(String(20), default='192k')  # Qualité MP3
    retention_days = Column(Integer, default=30)  # Durée de conservation des fichiers
    
    def __repr__(self):
        return f'<AudioConfig {self.id} - Engine: {self.engine}>'
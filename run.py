from app import create_app, db
from app.models import RSSFeed, LLMConfig, WeatherConfig
import logging

# Configuration du logger
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = create_app()

# Création d'un contexte d'application pour les commandes shell
@app.shell_context_processor
def make_shell_context():
    return {
        'db': db, 
        'RSSFeed': RSSFeed,
        'LLMConfig': LLMConfig,
        'WeatherConfig': WeatherConfig
    }

if __name__ == '__main__':
    logger.info("Démarrage de l'application")
    app.run(debug=True)
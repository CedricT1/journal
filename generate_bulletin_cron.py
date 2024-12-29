#!/usr/bin/env python3
from app import create_app, db
from app.models import AudioConfig
from app.routes import generate_bulletin
from app.tasks import cleanup_audio_files
import logging
import sys

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bulletin_generation.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def main():
    try:
        app = create_app()
        with app.app_context():
            logger.info("Début de la génération automatique du bulletin")
            
            # Génération du bulletin
            response, status_code = generate_bulletin()
            if status_code != 200:
                logger.error(f"Erreur lors de la génération du bulletin: {response.get_json()}")
                sys.exit(1)
                
            bulletin_data = response.get_json()
            
            # Vérification de la génération audio
            if 'audio_error' in bulletin_data:
                logger.error(f"Erreur lors de la génération audio: {bulletin_data['audio_error']}")
            elif 'audio_url' in bulletin_data:
                logger.info(f"Audio généré avec succès: {bulletin_data['audio_url']}")
            
            # Nettoyage des anciens fichiers audio
            try:
                cleanup_audio_files()
            except Exception as e:
                logger.error(f"Erreur lors du nettoyage des fichiers audio: {str(e)}")
            
            logger.info("Génération automatique terminée avec succès")
            
    except Exception as e:
        logger.error(f"Erreur lors de la génération automatique: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
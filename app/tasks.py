import os
from datetime import datetime, timedelta
import logging
from app import db
from app.models import AudioConfig
from flask import current_app

logger = logging.getLogger(__name__)

def cleanup_audio_files():
    """Nettoie les fichiers audio plus anciens que la période de rétention configurée"""
    try:
        config = AudioConfig.query.first()
        if not config:
            logger.warning("Pas de configuration audio trouvée, utilisation de la valeur par défaut de 30 jours")
            retention_days = 30
        else:
            retention_days = config.retention_days
            
        audio_dir = os.path.join(current_app.root_path, 'static', 'audio')
        if not os.path.exists(audio_dir):
            logger.info("Dossier audio non trouvé, rien à nettoyer")
            return
            
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        for filename in os.listdir(audio_dir):
            if not filename.endswith('.mp3'):
                continue
                
            file_path = os.path.join(audio_dir, filename)
            file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            
            if file_mtime < cutoff_date:
                try:
                    os.remove(file_path)
                    logger.info(f"Fichier supprimé : {filename}")
                except Exception as e:
                    logger.error(f"Erreur lors de la suppression de {filename}: {str(e)}")
                    
        logger.info("Nettoyage des fichiers audio terminé")
        
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage des fichiers audio: {str(e)}")
        raise 
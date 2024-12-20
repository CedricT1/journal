from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from app import db
from app.models import RSSFeed, LLMConfig, WeatherConfig
import feedparser
import requests
import json
import trafilatura
import logging
import openai
from datetime import datetime, timedelta
import concurrent.futures

# (Routes précédentes restent inchangées)

@bp.route('/workflow_bulletin', methods=['POST'])
def workflow_bulletin():
    """
    Workflow complet de génération de bulletin :
    1. Sélection des articles
    2. Scraping des articles
    3. Génération du bulletin
    """
    try:
        # Étape 1 : Sélection des articles
        select_response = select_articles()
        if select_response[1] != 200:
            return select_response
        
        selected_articles = select_response[0].json

        # Étape 2 : Scraping des articles
        scrape_request = requests.post(
            url_for('main.scrape_articles', _external=True), 
            json={'selected_articles': selected_articles}
        )
        
        if scrape_request.status_code != 200:
            return jsonify({"error": "Échec du scraping", "details": scrape_request.json()}), 500
        
        scraped_articles = scrape_request.json()

        # Étape 3 : Génération du bulletin
        bulletin_request = requests.post(
            url_for('main.generer_bulletin', _external=True),
            json={'scraped_articles': scraped_articles}
        )
        
        if bulletin_request.status_code != 200:
            return jsonify({"error": "Échec de génération du bulletin", "details": bulletin_request.json()}), 500
        
        bulletin = bulletin_request.json()

        # Enregistrer le bulletin généré (optionnel)
        save_bulletin(bulletin)

        return jsonify(bulletin), 200

    except Exception as e:
        logger.error(f"Erreur dans le workflow complet : {e}")
        return jsonify({"error": str(e)}), 500

def save_bulletin(bulletin):
    """
    Sauvegarde le bulletin généré dans la base de données
    """
    # Vous pouvez créer un modèle Bulletin si nécessaire
    try:
        # Exemple de sauvegarde (à adapter selon votre modèle de données)
        from app.models import Bulletin  # Vous devrez créer ce modèle

        new_bulletin = Bulletin(
            titre=bulletin.get('titre', 'Bulletin sans titre'),
            date=datetime.now(),
            contenu=json.dumps(bulletin)
        )
        
        db.session.add(new_bulletin)
        db.session.commit()
        
        logger.info("Bulletin sauvegardé avec succès")
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde du bulletin : {e}")
        db.session.rollback()

@bp.route('/bulletins_historique')
def bulletins_historique():
    """
    Récupère l'historique des bulletins générés
    """
    try:
        # Vous devrez adapter cette partie selon votre modèle de données
        from app.models import Bulletin
        
        bulletins = Bulletin.query.order_by(Bulletin.date.desc()).limit(10).all()
        
        return jsonify([
            {
                'id': bulletin.id,
                'titre': bulletin.titre,
                'date': bulletin.date.isoformat(),
                'contenu': json.loads(bulletin.contenu)
            } for bulletin in bulletins
        ]), 200
    
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'historique : {e}")
        return jsonify({"error": str(e)}), 500

# (Autres routes précédentes restent inchangées)
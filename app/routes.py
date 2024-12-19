from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from app import db
from app.models import RSSFeed, LLMConfig, WeatherConfig
import feedparser
import requests
import json
import trafilatura
import logging

# Définir le Blueprint AVANT de l'utiliser
bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)

@bp.route('/get_available_models', methods=['POST'])
def get_available_models():
    try:
        data = request.json
        api_url = data.get('api_url', '').strip()
        api_key = data.get('api_key', '').strip()

        if not api_url or not api_key:
            return jsonify({"error": "URL de l'API et clé API requises"}), 400

        # Si l'URL ne contient pas le chemin complet vers l'API des modèles
        if not api_url.endswith('/v1/models'):
            # Si l'URL se termine par un slash, on le retire
            api_url = api_url.rstrip('/')
            # On ajoute le chemin vers l'API des modèles
            if not api_url.endswith('/v1'):
                api_url += '/v1'
            api_url += '/models'

        logger.info(f"Tentative de connexion à l'API: {api_url}")

        # Faire la requête à l'API
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        response = requests.get(api_url, headers=headers)
        
        logger.info(f"Statut de la réponse: {response.status_code}")
        
        if response.status_code == 401:
            return jsonify({"error": "Clé API invalide"}), 401
        elif response.status_code == 404:
            return jsonify({"error": "URL de l'API invalide. Utilisez https://api.openai.com"}), 404
        elif response.status_code != 200:
            return jsonify({"error": f"Erreur lors de la requête: {response.status_code}"}), response.status_code

        # Récupérer uniquement les modèles de chat
        models_data = response.json().get('data', [])
        chat_models = [model for model in models_data if model['id'].startswith('gpt-')]
        
        logger.info(f"Modèles trouvés: {len(chat_models)}")

        if not chat_models:
            return jsonify({"error": "Aucun modèle GPT trouvé"}), 404

        return jsonify({"models": chat_models})

    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur lors de la requête API: {str(e)}")
        return jsonify({"error": f"Erreur de connexion à l'API: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"Erreur inattendue: {str(e)}")
        return jsonify({"error": f"Une erreur inattendue est survenue: {str(e)}"}), 500

@bp.route('/')
def index():
    feeds = RSSFeed.query.all()
    return render_template('index.html', feeds=feeds)

@bp.route('/llm_config', methods=['GET', 'POST'])
def llm_config():
    config = LLMConfig.query.first()
    if request.method == 'POST':
        if not config:
            config = LLMConfig()
        config.api_url = request.form.get('api_url')
        config.api_key = request.form.get('api_key')
        config.selected_model = request.form.get('selected_model')
        
        try:
            db.session.add(config)
            db.session.commit()
            return redirect(url_for('main.llm_config'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur lors de l'enregistrement de la configuration: {str(e)}")
            return "Erreur lors de l'enregistrement de la configuration", 500
            
    return render_template('llm_config.html', config=config)

@bp.route('/weather_config', methods=['GET', 'POST'])
def weather_config():
    config = WeatherConfig.query.first()
    if request.method == 'POST':
        if not config:
            config = WeatherConfig()
        config.provider = request.form.get('provider')
        config.api_key = request.form.get('api_key')
        config.latitude = float(request.form.get('latitude'))
        config.longitude = float(request.form.get('longitude'))
        config.city = request.form.get('city')
        config.country = request.form.get('country')
        config.units = request.form.get('units')
        db.session.add(config)
        db.session.commit()
        return redirect(url_for('main.weather_config'))
    return render_template('weather_config.html', config=config)

@bp.route('/add_rss', methods=['POST'])
def add_rss():
    data = request.json
    url = data.get('rssUrl')
    category = data.get('category')

    if not url or not category:
        return jsonify({"error": "URL et catégorie sont requis"}), 400

    # Vérifier si l'URL est valide
    feed = feedparser.parse(url)
    if feed.get('bozo_exception'):
        return jsonify({"error": "URL de flux RSS invalide"}), 400

    # Vérifier si le flux existe déjà
    existing_feed = RSSFeed.query.filter_by(url=url).first()
    if existing_feed:
        return jsonify({"error": "Ce flux RSS existe déjà"}), 400

    new_feed = RSSFeed(url=url, category=category)
    db.session.add(new_feed)
    db.session.commit()

    return jsonify({"message": "Flux RSS ajouté avec succès"}), 200

@bp.route('/get_rss_feeds')
def get_rss_feeds():
    feeds = RSSFeed.query.all()
    return jsonify([{"id": feed.id, "url": feed.url, "category": feed.category} for feed in feeds])

@bp.route('/generate_bulletin')
def generate_bulletin():
    return jsonify({"message": "Génération du bulletin en cours"}), 200

def extract_article_content(url, max_retry=3):
    """
    Extrait le contenu principal d'un article en utilisant trafilatura
    
    Args:
        url (str): URL de l'article à extraire
        max_retry (int): Nombre maximum de tentatives
    
    Returns:
        str: Contenu extrait de l'article
    """
    for _ in range(max_retry):
        try:
            # Configuration de trafilatura pour un meilleur résultat
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                # Options avancées d'extraction
                content = trafilatura.extract(
                    downloaded, 
                    include_comments=False,  # Exclure les commentaires
                    include_formatting=False,  # Texte brut
                    favor_precision=True  # Privilégier la précision
                )
                
                # Fallback si l'extraction échoue
                return content or "Contenu de l'article non disponible"
        except Exception as e:
            logger.error(f"Erreur d'extraction pour {url}: {e}")
    
    return "Contenu de l'article non disponible"
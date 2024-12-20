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

# Définir le Blueprint AVANT de l'utiliser
bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)

@bp.route('/select_articles', methods=['POST'])
def select_articles():
    """
    Sélectionne les articles pertinents à partir des flux RSS
    """
    # Récupérer la configuration du LLM
    llm_config = LLMConfig.query.first()
    if not llm_config:
        return jsonify({"error": "Configuration LLM non trouvée"}), 400

    # Configuration de l'API OpenAI
    openai.api_key = llm_config.api_key
    openai.base_url = llm_config.api_url

    # Récupérer tous les flux RSS
    feeds = RSSFeed.query.all()
    
    # Liste pour stocker tous les articles
    all_articles = []

    # Parcourir tous les flux RSS
    for feed in feeds:
        parsed_feed = feedparser.parse(feed.url)
        
        # Filtrer les articles récents (moins de 3 jours)
        three_days_ago = datetime.now() - timedelta(days=3)
        
        for entry in parsed_feed.entries:
            # Convertir la date de publication en datetime
            try:
                published_date = datetime(*entry.published_parsed[:6])
                if published_date < three_days_ago:
                    continue
            except:
                pass

            article = {
                'title': entry.title,
                'link': entry.link,
                'summary': entry.get('summary', ''),
                'category': feed.category
            }
            all_articles.append(article)

    # Préparer le prompt pour le LLM
    prompt = f"""
    Sélectionne les articles les plus pertinents et importants parmi les suivants.
    Critères de sélection :
    - Actualité récente et significative
    - Impact sociétal ou politique
    - Intérêt général
    - Diversité des catégories

    Articles disponibles ({len(all_articles)}) :
    {json.dumps(all_articles, indent=2)}

    Retourne un JSON structuré avec :
    {{
        "selected_articles": [
            {{
                "title": "Titre de l'article",
                "link": "URL de l'article",
                "category": "Catégorie"
            }}
        ]
    }}
    """

    try:
        response = openai.chat.completions.create(
            model=llm_config.selected_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "Tu es un éditeur de journal, expert dans la sélection d'articles pertinents."},
                {"role": "user", "content": prompt}
            ]
        )

        # Extraire et traiter la réponse
        result = json.loads(response.choices[0].message.content)
        selected_articles = result.get('selected_articles', [])

        return jsonify(selected_articles), 200

    except Exception as e:
        logger.error(f"Erreur lors de la sélection des articles : {e}")
        return jsonify({"error": str(e)}), 500

# Autres routes existantes restent inchangées
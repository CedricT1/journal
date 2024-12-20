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

# Définir le Blueprint AVANT de l'utiliser
bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)

# (Routes précédentes restent inchangées)

@bp.route('/generer_bulletin', methods=['POST'])
def generer_bulletin():
    """
    Génère un bulletin d'information complet à partir des articles scrappés
    """
    # Récupérer la configuration du LLM
    llm_config = LLMConfig.query.first()
    if not llm_config:
        return jsonify({"error": "Configuration LLM non trouvée"}), 400

    # Récupérer les articles scrappés depuis la requête
    scraped_articles = request.json.get('scraped_articles', [])
    
    if not scraped_articles:
        return jsonify({"error": "Aucun article scraped"}), 400

    # Récupérer la configuration météo
    weather_config = WeatherConfig.query.first()
    
    # Préparation du prompt pour la génération du bulletin
    prompt = f"""
    Tu es un journaliste professionnel chargé de rédiger un bulletin d'information complet et structuré.

    Consignes de rédaction :
    1. Structure du bulletin :
       - Titre principal du bulletin
       - Introduction générale
       - Sections par catégories (Local, National, International, Technologie)
       - Conclusion
       - Météo (si disponible)

    2. Critères de rédaction :
       - Langage clair et professionnel
       - Objectivité et neutralité
       - Mise en contexte des événements
       - Articulation logique entre les informations

    Articles disponibles :
    {json.dumps(scraped_articles, indent=2)}

    {"Informations météo : " + json.dumps({
        'provider': weather_config.provider if weather_config else 'Non disponible',
        'city': weather_config.city if weather_config else 'Non spécifié',
        'country': weather_config.country if weather_config else 'Non spécifié'
    }, indent=2) if weather_config else ""}

    Retourne ta réponse au format JSON suivant :
    {{
        "titre": "Titre du bulletin",
        "date": "Date du jour",
        "introduction": "Introduction générale",
        "sections": {{
            "Local": [
                {{
                    "titre": "Titre de l'article local",
                    "contenu": "Résumé détaillé"
                }}
            ],
            "National": [...],
            "International": [...],
            "Technologie": [...]
        }},
        "conclusion": "Conclusion du bulletin",
        "meteo": {{
            "resume": "Résumé météo",
            "details": "Détails météorologiques"
        }}
    }}
    """

    try:
        # Configuration de l'API OpenAI
        openai.api_key = llm_config.api_key
        openai.base_url = llm_config.api_url

        # Génération du bulletin
        response = openai.chat.completions.create(
            model=llm_config.selected_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "Tu es un journaliste professionnel expert en rédaction de bulletins d'information."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,  # Équilibre entre créativité et cohérence
            max_tokens=2000   # Limite la longueur de la réponse
        )

        # Extraction et traitement de la réponse
        bulletin_json = json.loads(response.choices[0].message.content)
        
        return jsonify(bulletin_json), 200

    except Exception as e:
        logger.error(f"Erreur lors de la génération du bulletin : {e}")
        return jsonify({"error": str(e)}), 500

# (Autres routes précédentes restent inchangées)
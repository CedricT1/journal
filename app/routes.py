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

# (Autres routes précédentes restent inchangées)

@bp.route('/scrape_articles', methods=['POST'])
def scrape_articles():
    """
    Scrape le contenu des articles sélectionnés
    """
    # Récupérer les articles sélectionnés depuis la requête
    selected_articles = request.json.get('selected_articles', [])
    
    if not selected_articles:
        return jsonify({"error": "Aucun article sélectionné"}), 400

    # Fonction pour scraper un article individuellement
    def scrape_single_article(article):
        try:
            # Utiliser la fonction extract_article_content existante
            content = extract_article_content(article['link'])
            
            return {
                'title': article['title'],
                'link': article['link'],
                'category': article.get('category', 'Non catégorisé'),
                'content': content
            }
        except Exception as e:
            logger.error(f"Erreur de scraping pour {article['link']}: {e}")
            return {
                'title': article['title'],
                'link': article['link'],
                'category': article.get('category', 'Non catégorisé'),
                'content': f"Erreur de scraping: {str(e)}"
            }

    # Utilisation de ThreadPoolExecutor pour scraper en parallèle
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # Soumettre chaque article au scraping
        futures = [executor.submit(scrape_single_article, article) for article in selected_articles]
        
        # Attendre et collecter les résultats
        scraped_articles = [future.result() for future in concurrent.futures.as_completed(futures)]

    return jsonify(scraped_articles), 200

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

# (Autres routes précédentes restent inchangées)
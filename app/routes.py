from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from app import db
from app.models import RSSFeed, LLMConfig, WeatherConfig, Bulletin
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

# ... autres routes ...

@bp.route('/generate_bulletin', methods=['GET', 'POST'])
def generate_bulletin():
    """
    Route pour générer un bulletin via le workflow complet
    """
    try:
        logger.info("Début de la génération du bulletin")

        # Étape 1 : Sélection des articles
        logger.info("Sélection des articles...")
        select_result = select_articles()
        if isinstance(select_result, tuple) and select_result[1] != 200:
            logger.error(f"Erreur lors de la sélection des articles: {select_result}")
            return select_result

        selected_articles = select_result.get_json()
        logger.info(f"Articles sélectionnés: {len(selected_articles)}")

        # Étape 2 : Scraping des articles
        logger.info("Scraping des articles...")
        scrape_result = scrape_articles_workflow(selected_articles)
        if isinstance(scrape_result, tuple) and scrape_result[1] != 200:
            logger.error(f"Erreur lors du scraping: {scrape_result}")
            return scrape_result

        scraped_articles = scrape_result.get_json()
        logger.info(f"Articles scrapés: {len(scraped_articles)}")

        # Étape 3 : Génération du bulletin final
        logger.info("Génération du bulletin final...")
        bulletin_result = generate_final_bulletin(scraped_articles)
        
        return bulletin_result

    except Exception as e:
        logger.error(f"Erreur dans le workflow complet : {str(e)}")
        return jsonify({"error": str(e)}), 500

def scrape_articles_workflow(selected_articles):
    """
    Fonction pour scraper les articles sélectionnés
    """
    if not selected_articles:
        return jsonify({"error": "Aucun article sélectionné"}), 400

    try:
        # Fonction pour scraper un article individuellement
        def scrape_single_article(article):
            try:
                content = extract_article_content(article['link'])
                return {
                    'title': article['title'],
                    'link': article['link'],
                    'category': article.get('category', 'Non catégorisé'),
                    'content': content
                }
            except Exception as e:
                logger.error(f"Erreur de scraping pour {article['link']}: {e}")
                return None

        # Utilisation de ThreadPoolExecutor pour scraper en parallèle
        scraped_articles = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(scrape_single_article, article) 
                      for article in selected_articles]
            
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    scraped_articles.append(result)

        if not scraped_articles:
            return jsonify({"error": "Aucun article n'a pu être scrapé"}), 500

        return jsonify(scraped_articles)

    except Exception as e:
        logger.error(f"Erreur lors du scraping des articles : {str(e)}")
        return jsonify({"error": f"Erreur de scraping : {str(e)}"}), 500

def generate_final_bulletin(scraped_articles):
    """
    Fonction pour générer le bulletin final avec le LLM
    """
    try:
        llm_config = LLMConfig.query.first()
        if not llm_config:
            return jsonify({"error": "Configuration LLM non trouvée"}), 400

        weather_config = WeatherConfig.query.first()

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
        """

        # Configuration de l'API OpenAI
        openai.api_key = llm_config.api_key
        openai.base_url = llm_config.api_url

        # Génération du bulletin
        response = openai.chat.completions.create(
            model=llm_config.selected_model,
            messages=[
                {"role": "system", "content": "Tu es un journaliste professionnel expert en rédaction de bulletins d'information."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        # Extraction et traitement de la réponse
        bulletin_content = response.choices[0].message.content
        
        # Sauvegarde du bulletin
        bulletin = Bulletin(
            titre="Bulletin du " + datetime.now().strftime("%Y-%m-%d %H:%M"),
            contenu=bulletin_content
        )
        db.session.add(bulletin)
        db.session.commit()

        return jsonify({
            "message": "Bulletin généré avec succès",
            "bulletin": bulletin_content
        }), 200

    except Exception as e:
        logger.error(f"Erreur lors de la génération du bulletin final : {str(e)}")
        return jsonify({"error": f"Erreur de génération : {str(e)}"}), 500

# ... autres routes ...
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, send_file, current_app, Response
from app import db
from app.models import RSSFeed, LLMConfig, WeatherConfig, Bulletin, AudioConfig
from app.prompts import (
    CLEAN_TEXT_SYSTEM_PROMPT, CLEAN_TEXT_USER_PROMPT,
    WEATHER_SYSTEM_PROMPT, WEATHER_USER_PROMPT,
    ARTICLE_SELECTION_SYSTEM_PROMPT, ARTICLE_SELECTION_USER_PROMPT,
    NEWS_SYSTEM_PROMPT, NEWS_USER_PROMPT,
    BULLETIN_JSON_SYSTEM_PROMPT, BULLETIN_JSON_USER_PROMPT
)
import feedparser
import requests
import json
import urllib.request
import urllib.error
import json
import trafilatura
import logging
import io
import edge_tts
import elevenlabs
import asyncio
import tempfile
from pydub import AudioSegment
import os
from datetime import datetime, timedelta
import concurrent.futures
import openai
from openai import OpenAI

bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)

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
        try:
            db.session.add(config)
            db.session.commit()
            return redirect(url_for('main.weather_config'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur lors de l'enregistrement de la configuration météo: {str(e)}")
            return "Erreur lors de l'enregistrement de la configuration", 500
    return render_template('weather_config.html', config=config)

@bp.route('/add_rss', methods=['POST'])
def add_rss():
    data = request.json
    url = data.get('rssUrl')
    category = data.get('category')
    
    if not url or not category:
        return jsonify({"error": "URL et catégorie sont requis"}), 400
    
    feed = feedparser.parse(url)
    if feed.get('bozo_exception'):
        return jsonify({"error": "URL de flux RSS invalide"}), 400
        
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

@bp.route('/delete_rss/<int:feed_id>', methods=['DELETE'])
def delete_rss(feed_id):
    feed = RSSFeed.query.get(feed_id)
    if not feed:
        return jsonify({"error": "Flux RSS non trouvé"}), 404
    
    db.session.delete(feed)
    db.session.commit()
    return jsonify({"message": "Flux RSS supprimé avec succès"}), 200
@bp.route('/get_available_models', methods=['POST'])
def get_available_models():
    try:
        data = request.json
        api_url = data.get('api_url', '').strip()
        api_key = data.get('api_key', '').strip()
        
        if not api_url or not api_key:
            return jsonify({"error": "URL de l'API et clé API requises"}), 400
            
        if not api_url.endswith('/v1/models'):
            api_url = api_url.rstrip('/')
            if not api_url.endswith('/v1'):
                api_url += '/v1'
            api_url += '/models'
            
        logger.info(f"Tentative de connexion à l'API: {api_url}")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 401:
            return jsonify({"error": "Clé API invalide"}), 401
        elif response.status_code == 404:
            return jsonify({"error": "URL de l'API invalide"}), 404
        elif response.status_code != 200:
            return jsonify({"error": f"Erreur lors de la requête: {response.status_code}"}), response.status_code
            
        models_data = response.json().get('data', [])
        chat_models = [model for model in models_data if model['id'].startswith('')]
        
        if not chat_models:
            return jsonify({"error": "Aucun modèle GPT trouvé"}), 404
            
        return jsonify({"models": chat_models})
        
    except Exception as e:
        logger.error(f"Erreur lors de la requête API: {str(e)}")
        return jsonify({"error": f"Erreur de connexion à l'API: {str(e)}"}), 500

def clean_text_for_tts(text):
    """Nettoie le texte pour la synthèse vocale"""
    try:
        llm_config = LLMConfig.query.first()
        if not llm_config:
            raise ValueError("Configuration LLM non trouvée")
            
        client = OpenAI(api_key=llm_config.api_key)
        response = client.chat.completions.create(
            model=llm_config.selected_model,
            messages=[
                {"role": "system", "content": CLEAN_TEXT_SYSTEM_PROMPT},
                {"role": "user", "content": CLEAN_TEXT_USER_PROMPT.format(text=text)}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage du texte pour TTS : {str(e)}")
        return text.replace('#', '').replace('*', '').replace('_', '').replace('`', '')

@bp.route('/generate_bulletin', methods=['GET', 'POST'])
def generate_bulletin():
    try:
        logger.info("Début de la génération du bulletin")
        
        # Récupérer la configuration LLM
        llm_config = LLMConfig.query.first()
        if not llm_config:
            return jsonify({"error": "Configuration LLM non trouvée"}), 400
            
        # Configurer le client OpenAI
        client = OpenAI(api_key=llm_config.api_key)
        
        logger.info("Sélection des articles...")
        
        select_response, status_code = select_articles()
        if status_code != 200:
            logger.error(f"Erreur lors de la sélection des articles: {select_response}")
            return select_response, status_code
            
        selected_articles = select_response.get_json()
        logger.info(f"Articles sélectionnés: {len(selected_articles)}")
        
        logger.info("Scraping des articles...")
        scrape_response, status_code = scrape_articles_workflow(selected_articles)
        if status_code != 200:
            logger.error(f"Erreur lors du scraping: {scrape_response}")
            return scrape_response, status_code
            
        scraped_articles = scrape_response.get_json()
        logger.info(f"Articles scrapés: {len(scraped_articles)}")
        
        logger.info("Génération du bulletin final...")
        bulletin_response, status_code = generate_final_bulletin(scraped_articles, client)
        if status_code != 200:
            return bulletin_response, status_code
            
        bulletin_data = bulletin_response.get_json()
        bulletin_content = bulletin_data.get('bulletin')
        
        # Génération de l'audio si la configuration existe
        audio_config = AudioConfig.query.first()
        if audio_config:
            try:
                logger.info("Préparation du texte pour la synthèse vocale...")
                tts_text = clean_text_for_tts(bulletin_content)
                
                logger.info("Génération de la version audio du bulletin...")
                audio_path = generate_audio_bulletin(tts_text, audio_config)
                bulletin_data['audio_url'] = url_for('static', filename=f'audio/{os.path.basename(audio_path)}')
                logger.info(f"Audio généré avec succès: {audio_path}")
            except Exception as e:
                logger.error(f"Erreur lors de la génération audio: {str(e)}")
                bulletin_data['audio_error'] = str(e)
        
        return jsonify(bulletin_data), 200
        
    except Exception as e:
        logger.error(f"Erreur dans le workflow complet : {str(e)}")
        return jsonify({"error": str(e)}), 500

def generate_final_bulletin(scraped_articles, client):
    try:
        llm_config = LLMConfig.query.first()
        if not llm_config:
            return jsonify({"error": "Configuration LLM non trouvée"}), 400

        weather_config = WeatherConfig.query.first()
        weather_data = get_weather_data(weather_config) if weather_config else None

        weather_text = ""
        articles_text = json.dumps(scraped_articles, indent=2)
        
        if weather_config and weather_data:
            try:
                weather_response = client.chat.completions.create(
                    model=llm_config.selected_model,
                    messages=[
                        {"role": "system", "content": WEATHER_SYSTEM_PROMPT},
                        {"role": "user", "content": WEATHER_USER_PROMPT.format(weather_data=json.dumps(weather_data, indent=2))}
                    ],
                    temperature=0.7,
                    max_tokens=500
                )
                weather_text = "\n\n### Météo ###\n" + weather_response.choices[0].message.content
            except Exception as e:
                logger.error(f"Erreur lors de la génération du bulletin météo : {str(e)}")
                weather_text = f"\n\n### Météo ###\nInformations météo : {json.dumps(weather_data, indent=2)}"

        # Générer le bulletin avec GPT
        logger.info("Génération du bulletin avec GPT...")
        news_response = client.chat.completions.create(
            model=llm_config.selected_model,
            messages=[
                {"role": "system", "content": NEWS_SYSTEM_PROMPT},
                {"role": "user", "content": NEWS_USER_PROMPT.format(articles=articles_text)}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        # Combiner le bulletin d'information et la météo
        bulletin_text = news_response.choices[0].message.content + weather_text
        
        bulletin = Bulletin(
            titre="Bulletin du " + datetime.now().strftime("%Y-%m-%d %H:%M"),
            contenu=bulletin_text
        )
        db.session.add(bulletin)
        db.session.commit()

        return jsonify({
            "message": "Bulletin généré avec succès",
            "bulletin": bulletin_text
        }), 200

    except Exception as e:
        logger.error(f"Erreur lors de la génération du bulletin final : {str(e)}")
        return jsonify({"error": f"Erreur de génération : {str(e)}"}), 500

@bp.route('/select_articles', methods=['POST'])
def select_articles():
    llm_config = LLMConfig.query.first()
    if not llm_config:
        return jsonify({"error": "Configuration LLM non trouvée"}), 400

    openai.api_key = llm_config.api_key
    openai.base_url = f"{llm_config.api_url.rstrip('/')}/"

    feeds = RSSFeed.query.all()
    all_articles = []
    
    for feed in feeds:
        try:
            parsed_feed = feedparser.parse(feed.url)
            three_days_ago = datetime.now() - timedelta(days=3)
            
            for entry in parsed_feed.entries:
                try:
                    # Vérifier si l'entrée a une date de publication
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        published_date = datetime(*entry.published_parsed[:6])
                        if published_date < three_days_ago:
                            continue
                    
                    # Vérifier et nettoyer le lien
                    link = entry.get('link', '')
                    if not link:  # Si pas de lien, passer à l'article suivant
                        logger.warning(f"Article sans lien trouvé dans le flux {feed.url}")
                        continue
                        
                    # Vérifier et nettoyer le titre
                    title = entry.get('title', 'Sans titre')
                    
                    # Construire l'article avec les champs requis
                    article = {
                        'title': title,
                        'link': link,
                        'summary': entry.get('summary', ''),
                        'category': feed.category
                    }
                    all_articles.append(article)
                    
                except Exception as e:
                    logger.error(f"Erreur lors du traitement d'une entrée du flux {feed.url}: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Erreur lors de la lecture du flux {feed.url}: {str(e)}")
            continue

    if not all_articles:
        return jsonify({"error": "Aucun article trouvé dans les flux RSS"}), 404

    try:
        response = openai.chat.completions.create(
            model=llm_config.selected_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": ARTICLE_SELECTION_SYSTEM_PROMPT},
                {"role": "user", "content": ARTICLE_SELECTION_USER_PROMPT.format(
                    article_count=len(all_articles),
                    articles=json.dumps(all_articles, indent=2)
                )}
            ]
        )
        result = json.loads(response.choices[0].message.content)
        selected_articles = result.get('selected_articles', [])
        
        # Vérifier que chaque article sélectionné a un lien valide
        validated_articles = []
        for article in selected_articles:
            if article.get('link'):
                validated_articles.append(article)
            else:
                logger.warning(f"Article sans lien ignoré: {article.get('title', 'Sans titre')}")
        
        if not validated_articles:
            return jsonify({"error": "Aucun article valide n'a été sélectionné"}), 404
            
        return jsonify(validated_articles), 200
        
    except Exception as e:
        logger.error(f"Erreur lors de la sélection des articles : {e}")
        return jsonify({"error": str(e)}), 500

def scrape_articles_workflow(selected_articles):
    if not selected_articles:
        return jsonify({"error": "Aucun article sélectionné"}), 400
        
    try:
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

        return jsonify(scraped_articles), 200
        
    except Exception as e:
        logger.error(f"Erreur lors du scraping des articles : {str(e)}")
        return jsonify({"error": f"Erreur de scraping : {str(e)}"}), 500

@bp.route('/scrape_articles', methods=['POST'])
def scrape_articles():
    selected_articles = request.json.get('selected_articles', [])
    if not selected_articles:
        return jsonify({"error": "Aucun article sélectionné"}), 400

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
            return {
                'title': article['title'],
                'link': article['link'],
                'category': article.get('category', 'Non catégorisé'),
                'content': f"Erreur de scraping: {str(e)}"
            }

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(scrape_single_article, article) 
                  for article in selected_articles]
        scraped_articles = [future.result() 
                          for future in concurrent.futures.as_completed(futures)]

    return jsonify(scraped_articles), 200
@bp.route('/generer_bulletin', methods=['POST'])
def generer_bulletin():
    try:
        llm_config = LLMConfig.query.first()
        if not llm_config:
            return jsonify({"error": "Configuration LLM non trouvée"}), 400

        scraped_articles = request.json.get('scraped_articles', [])
        if not scraped_articles:
            return jsonify({"error": "Aucun article scrappé"}), 400

        weather_config = WeatherConfig.query.first()
        weather_data = get_weather_data(weather_config) if weather_config else None

        # Construction des informations météo de manière sécurisée
        weather_info = ""
        if weather_config and weather_data:
            weather_info = f"Informations météo : {json.dumps({
                'weather_data': weather_data,
                'provider': weather_config.provider,
                'city': weather_config.city,
                'country': weather_config.country
            }, indent=2)}"

        try:
            openai.api_key = llm_config.api_key
            openai.base_url = f"{llm_config.api_url.rstrip('/')}/"
            
            response = openai.chat.completions.create(
                model=llm_config.selected_model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": BULLETIN_JSON_SYSTEM_PROMPT},
                    {"role": "user", "content": BULLETIN_JSON_USER_PROMPT.format(
                        articles=json.dumps(scraped_articles, indent=2),
                        weather_info=weather_info
                    )}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            bulletin_json = json.loads(response.choices[0].message.content)
            return jsonify(bulletin_json), 200
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération du bulletin : {e}")
            return jsonify({"error": str(e)}), 500

    except Exception as e:
        logger.error(f"Erreur lors de la génération du bulletin : {e}")
        return jsonify({"error": str(e)}), 500

@bp.route('/workflow_bulletin', methods=['POST'])
def workflow_bulletin():
    try:
        select_response, status_code = select_articles()
        if status_code != 200:
            return select_response

        selected_articles = select_response.json
        
        scrape_request = requests.post(
            url_for('main.scrape_articles', _external=True),
            json={'selected_articles': selected_articles}
        )
        
        if scrape_request.status_code != 200:
            return jsonify({
                "error": "Échec du scraping",
                "details": scrape_request.json()
            }), 500

        scraped_articles = scrape_request.json()
        
        bulletin_request = requests.post(
            url_for('main.generer_bulletin', _external=True),
            json={'scraped_articles': scraped_articles}
        )
        
        if bulletin_request.status_code != 200:
            return jsonify({
                "error": "Échec de génération du bulletin",
                "details": bulletin_request.json()
            }), 500

        bulletin = bulletin_request.json()
        save_bulletin(bulletin)
        return jsonify(bulletin), 200
        
    except Exception as e:
        logger.error(f"Erreur dans le workflow complet : {e}")
        return jsonify({"error": str(e)}), 500

def save_bulletin(bulletin):
    try:
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
    try:
        bulletins = Bulletin.query.order_by(Bulletin.date.desc()).limit(10).all()
        return jsonify([{
            'id': bulletin.id,
            'titre': bulletin.titre,
            'date': bulletin.date.isoformat(),
            'contenu': json.loads(bulletin.contenu)
        } for bulletin in bulletins]), 200
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'historique : {e}")
        return jsonify({"error": str(e)}), 500

def get_weather_data(config):
    """
    Récupère les données météorologiques en fonction de la configuration
    Args:
        config (WeatherConfig): Configuration météo
    Returns:
        dict: Données météorologiques détaillées
    """
    if not config:
        return {
            "error": "Aucune configuration météo disponible",
            "resume": "Météo non disponible",
            "details": "Veuillez configurer votre fournisseur météo"
        }

    try:
        # Utilisation de l'endpoint forecast pour les prévisions sur 5 jours
        base_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={config.latitude}&lon={config.longitude}&appid={config.api_key}&units={config.units or 'metric'}&lang=fr"
        
        req = urllib.request.Request(base_url)
        try:
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode("utf-8"))
                
                # Organiser les prévisions par jour
                daily_forecasts = {}
                for item in data['list']:
                    date = datetime.fromtimestamp(item['dt']).strftime('%Y-%m-%d')
                    if date not in daily_forecasts:
                        daily_forecasts[date] = {
                            'temperature': {
                                'min': float('inf'),
                                'max': float('-inf'),
                                'moyenne': 0
                            },
                            'description': item['weather'][0]['description'],
                            'humidite': item['main']['humidity'],
                            'vent': {
                                'vitesse': item['wind']['speed'],
                                'direction': item['wind']['deg']
                            },
                            'precipitations': item.get('rain', {}).get('3h', 0),
                            'readings': 0
                        }
                    
                    daily_forecasts[date]['temperature']['min'] = min(daily_forecasts[date]['temperature']['min'], item['main']['temp_min'])
                    daily_forecasts[date]['temperature']['max'] = max(daily_forecasts[date]['temperature']['max'], item['main']['temp_max'])
                    daily_forecasts[date]['temperature']['moyenne'] += item['main']['temp']
                    daily_forecasts[date]['readings'] += 1

                # Calculer les moyennes
                for date in daily_forecasts:
                    daily_forecasts[date]['temperature']['moyenne'] /= daily_forecasts[date]['readings']
                    del daily_forecasts[date]['readings']

                # Prendre les 5 premiers jours
                forecasts = dict(list(daily_forecasts.items())[:5])

                return {
                    "resume": f"Prévisions météo sur 5 jours pour {config.city}",
                    "details": forecasts
                }
        except urllib.error.HTTPError as e:
            logger.error(f"Erreur HTTP: {e.code} - {e.reason}")
            return {
                "error": f"Erreur API météo: {e.code}",
                "resume": "Météo temporairement indisponible",
                "details": e.reason
            }
    except Exception as e:
        logger.error(f"Erreur lors de la récupération météo: {e}")
        return {
            "error": str(e),
            "resume": "Erreur de récupération météo",
            "details": "Vérifiez votre configuration"
        }

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
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                content = trafilatura.extract(
                    downloaded,
                    include_comments=False,
                    include_formatting=False,
                    favor_precision=True
                )
                return content or "Contenu de l'article non disponible"
        except Exception as e:
            logger.error(f"Erreur d'extraction pour {url}: {e}")
    return "Contenu de l'article non disponible"

@bp.route('/audio_config', methods=['GET', 'POST'])
def audio_config():
    config = AudioConfig.query.first()
    if request.method == 'POST':
        if not config:
            config = AudioConfig()
        
        # Mise à jour de la configuration
        config.engine = request.form.get('engine')
        
        # Configuration ElevenLabs
        if config.engine == 'elevenlabs':
            config.elevenlabs_api_key = request.form.get('elevenlabs_api_key')
            config.elevenlabs_voice_id = request.form.get('elevenlabs_voice_id')
            config.elevenlabs_stability = float(request.form.get('elevenlabs_stability', 0.5))
            config.elevenlabs_clarity = float(request.form.get('elevenlabs_clarity', 0.75))
        
        # Configuration Edge-TTS
        else:
            config.edge_voice = request.form.get('edge_voice')
            config.edge_rate = request.form.get('edge_rate', '+0%')
            config.edge_volume = request.form.get('edge_volume', '+0%')
            config.edge_pitch = request.form.get('edge_pitch', '+0Hz')
        
        # Paramètres généraux
        config.output_quality = request.form.get('output_quality', '192k')
        config.retention_days = int(request.form.get('retention_days', 30))
        
        try:
            db.session.add(config)
            db.session.commit()
            return redirect(url_for('main.audio_config'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur lors de l'enregistrement de la configuration audio: {str(e)}")
            return "Erreur lors de l'enregistrement de la configuration", 500
            
    return render_template('audio_config.html', config=config)

@bp.route('/get_edge_voices')
def get_edge_voices():
    try:
        # Récupération asynchrone des voix Edge TTS
        async def get_voices():
            voices = []
            voices_list = await edge_tts.list_voices()
            for voice in voices_list:
                if voice["Locale"].startswith("fr"):  # Filtrer les voix françaises
                    voices.append({
                        "name": voice["FriendlyName"],
                        "shortName": voice["ShortName"],
                        "locale": voice["Locale"]
                    })
            return voices
        
        voices = asyncio.run(get_voices())
        return jsonify(voices)
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des voix Edge: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route('/get_elevenlabs_voices', methods=['POST'])
def get_elevenlabs_voices():
    try:
        api_key = request.json.get('api_key')
        if not api_key:
            return jsonify({"error": "Clé API requise"}), 400
            
        elevenlabs.set_api_key(api_key)
        voices_list = elevenlabs.voices()
        
        return jsonify([{
            "voice_id": voice.voice_id,
            "name": voice.name
        } for voice in voices_list])
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des voix ElevenLabs: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route('/test_voice', methods=['POST'])
def test_voice():
    try:
        engine = request.form.get('engine')
        test_text = "Ceci est un test de la synthèse vocale."
        
        if engine == 'elevenlabs':
            api_key = request.form.get('elevenlabs_api_key')
            voice_id = request.form.get('elevenlabs_voice_id')
            stability = float(request.form.get('elevenlabs_stability', 0.5))
            clarity = float(request.form.get('elevenlabs_clarity', 0.75))
            
            # Nouvelle méthode de configuration ElevenLabs
            client = elevenlabs.ElevenLabs(api_key=api_key)
            audio_stream = client.generate(
                text=test_text,
                voice=voice_id,
                model="eleven_multilingual_v2",
                voice_settings={"stability": stability, "similarity_boost": clarity}
            )
            audio_bytes = b"".join(audio_stream)
            
            return send_file(
                io.BytesIO(audio_bytes),
                mimetype='audio/mpeg',
                as_attachment=True,
                download_name='test.mp3'
            )
            
        else:  # edge-tts
            voice = request.form.get('edge_voice')
            if not voice:
                return jsonify({"error": "Voix non sélectionnée"}), 400
                
            rate = request.form.get('edge_rate', '+0%')
            volume = request.form.get('edge_volume', '+0%')
            pitch = request.form.get('edge_pitch', '+0Hz')
            
            # Création d'un fichier temporaire pour stocker l'audio
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_path = temp_file.name
            
            async def generate_speech():
                communicate = edge_tts.Communicate(
                    text=test_text,
                    voice=voice,
                    rate=rate,
                    volume=volume,
                    pitch=pitch
                )
                await communicate.save(temp_path)
            
            asyncio.run(generate_speech())
            
            return send_file(
                temp_path,
                mimetype='audio/mpeg',
                as_attachment=True,
                download_name='test.mp3'
            )
            
    except Exception as e:
        logger.error(f"Erreur lors du test de la voix: {str(e)}")
        return jsonify({"error": str(e)}), 500

def generate_audio_bulletin(bulletin_text, config=None):
    """Génère un fichier audio à partir du texte du bulletin"""
    if not config:
        config = AudioConfig.query.first()
    if not config:
        raise ValueError("Configuration audio non trouvée")
        
    # Création du dossier audio s'il n'existe pas
    audio_dir = os.path.join(current_app.root_path, 'static', 'audio')
    os.makedirs(audio_dir, exist_ok=True)
    
    # Génération du nom de fichier
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = os.path.join(audio_dir, f'bulletin_{timestamp}.mp3')
    
    try:
        if config.engine == 'elevenlabs':
            # Nouvelle méthode de configuration ElevenLabs
            client = elevenlabs.ElevenLabs(api_key=config.elevenlabs_api_key)
            audio_stream = client.generate(
                text=bulletin_text,
                voice=config.elevenlabs_voice_id,
                model="eleven_multilingual_v2",
                voice_settings={"stability": config.elevenlabs_stability, "similarity_boost": config.elevenlabs_clarity}
            )
            audio_bytes = b"".join(audio_stream)
            
            with open(output_path, 'wb') as f:
                f.write(audio_bytes)
                
        else:  # edge-tts
            if not config.edge_voice:
                raise ValueError("Voix Edge-TTS non configurée")
                
            async def generate_speech():
                communicate = edge_tts.Communicate(
                    text=bulletin_text,
                    voice=config.edge_voice,
                    rate=config.edge_rate,
                    volume=config.edge_volume,
                    pitch=config.edge_pitch
                )
                await communicate.save(output_path)
            
            asyncio.run(generate_speech())
        
        # Conversion à la qualité souhaitée si nécessaire
        audio = AudioSegment.from_mp3(output_path)
        audio.export(output_path, format='mp3', bitrate=config.output_quality)
        
        return output_path
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération audio: {str(e)}")
        if os.path.exists(output_path):
            os.remove(output_path)
        raise

@bp.route('/api/generate_bulletin', methods=['POST'])
def api_generate_bulletin():
    """
    API pour générer un nouveau bulletin.
    Ne nécessite pas de paramètres.
    Retourne le bulletin au format JSON avec le texte et le lien audio.
    """
    try:
        logger.info("API - Début de la génération du bulletin")
        
        # Vérifier la configuration LLM
        llm_config = LLMConfig.query.first()
        if not llm_config:
            return jsonify({
                "success": False,
                "error": "Configuration LLM non trouvée. Veuillez configurer l'API LLM d'abord."
            }), 400
            
        # Configurer le client OpenAI
        client = OpenAI(api_key=llm_config.api_key)
        
        # Sélection des articles
        logger.info("API - Sélection des articles...")
        select_response, status_code = select_articles()
        if status_code != 200:
            return jsonify({
                "success": False,
                "error": "Erreur lors de la sélection des articles",
                "details": select_response.get_json() if hasattr(select_response, 'get_json') else str(select_response)
            }), status_code
            
        selected_articles = select_response.get_json()
        
        # Scraping des articles
        logger.info("API - Scraping des articles...")
        scrape_response, status_code = scrape_articles_workflow(selected_articles)
        if status_code != 200:
            return jsonify({
                "success": False,
                "error": "Erreur lors du scraping des articles",
                "details": scrape_response.get_json() if hasattr(scrape_response, 'get_json') else str(scrape_response)
            }), status_code
            
        scraped_articles = scrape_response.get_json()
        
        # Génération du bulletin
        logger.info("API - Génération du bulletin...")
        bulletin_response, status_code = generate_final_bulletin(scraped_articles, client)
        if status_code != 200:
            return jsonify({
                "success": False,
                "error": "Erreur lors de la génération du bulletin",
                "details": bulletin_response.get_json() if hasattr(bulletin_response, 'get_json') else str(bulletin_response)
            }), status_code
            
        bulletin_data = bulletin_response.get_json()
        bulletin_content = bulletin_data.get('bulletin')
        
        # Préparation de la réponse
        response_data = {
            "success": True,
            "bulletin": {
                "text": bulletin_content,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "audio_url": None
            }
        }
        
        # Génération de l'audio si la configuration existe
        audio_config = AudioConfig.query.first()
        if audio_config:
            try:
                logger.info("API - Génération de l'audio...")
                tts_text = clean_text_for_tts(bulletin_content)
                audio_path = generate_audio_bulletin(tts_text, audio_config)
                response_data["bulletin"]["audio_url"] = url_for('static', 
                                                               filename=f'audio/{os.path.basename(audio_path)}',
                                                               _external=True)
            except Exception as e:
                logger.error(f"API - Erreur lors de la génération audio: {str(e)}")
                response_data["audio_error"] = str(e)
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"API - Erreur lors de la génération du bulletin: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Erreur interne du serveur",
            "details": str(e)
        }), 500

@bp.route('/podcast.xml')
def podcast_feed():
    """
    Génère un flux RSS pour les bulletins audio.
    Le flux est compatible avec les agrégateurs de podcasts.
    """
    try:
        # Récupérer les 50 derniers bulletins
        bulletins = Bulletin.query.order_by(Bulletin.date.desc()).limit(50).all()
        
        # Informations sur le podcast
        podcast_title = "Bulletin d'Information Automatisé"
        podcast_description = "Bulletins d'information générés automatiquement avec les dernières actualités, la météo et plus encore."
        podcast_author = "Journal Automatisé"
        podcast_image = url_for('static', filename='images/podcast-cover.jpg', _external=True)
        podcast_link = url_for('main.index', _external=True)
        
        # Construire le XML du flux RSS
        rss_items = []
        for bulletin in bulletins:
            # Vérifier si un fichier audio existe pour ce bulletin
            audio_filename = f"bulletin_{bulletin.date.strftime('%Y%m%d_%H%M%S')}.mp3"
            audio_path = os.path.join(current_app.root_path, 'static', 'audio', audio_filename)
            
            if os.path.exists(audio_path):
                # Obtenir la taille du fichier
                file_size = os.path.getsize(audio_path)
                
                # Construire l'élément RSS pour ce bulletin
                audio_url = url_for('static', 
                                  filename=f'audio/{audio_filename}',
                                  _external=True)
                                  
                item = f"""
                <item>
                    <title>{bulletin.titre}</title>
                    <description><![CDATA[{bulletin.contenu}]]></description>
                    <pubDate>{bulletin.date.strftime('%a, %d %b %Y %H:%M:%S GMT')}</pubDate>
                    <guid isPermaLink="false">{audio_url}</guid>
                    <enclosure url="{audio_url}" 
                             length="{file_size}"
                             type="audio/mpeg"/>
                    <link>{audio_url}</link>
                </item>"""
                rss_items.append(item)
        
        # Construire le flux RSS complet
        rss_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" 
     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:content="http://purl.org/rss/1.0/modules/content/">
    <channel>
        <title>{podcast_title}</title>
        <link>{podcast_link}</link>
        <description>{podcast_description}</description>
        <language>fr-fr</language>
        <copyright>Copyright {datetime.now().year}</copyright>
        <lastBuildDate>{datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')}</lastBuildDate>
        <itunes:author>{podcast_author}</itunes:author>
        <itunes:image href="{podcast_image}"/>
        <itunes:explicit>no</itunes:explicit>
        <itunes:category text="News"/>
        {''.join(rss_items)}
    </channel>
</rss>"""
        
        return Response(rss_xml, mimetype='application/rss+xml')
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération du flux RSS: {str(e)}")
        return jsonify({
            "error": "Erreur lors de la génération du flux RSS",
            "details": str(e)
        }), 500
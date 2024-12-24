from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from app import db
from app.models import RSSFeed, LLMConfig, WeatherConfig, Bulletin
import feedparser
import requests
import json
import urllib.request
import urllib.error
import json
import trafilatura
import logging
import openai
from datetime import datetime, timedelta
import concurrent.futures

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
        chat_models = [model for model in models_data if model['id'].startswith('gpt-')]
        
        if not chat_models:
            return jsonify({"error": "Aucun modèle GPT trouvé"}), 404
            
        return jsonify({"models": chat_models})
        
    except Exception as e:
        logger.error(f"Erreur lors de la requête API: {str(e)}")
        return jsonify({"error": f"Erreur de connexion à l'API: {str(e)}"}), 500

@bp.route('/generate_bulletin', methods=['GET', 'POST'])
def generate_bulletin():
    try:
        logger.info("Début de la génération du bulletin")
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
        bulletin_response, status_code = generate_final_bulletin(scraped_articles)
        
        return bulletin_response, status_code
        
    except Exception as e:
        logger.error(f"Erreur dans le workflow complet : {str(e)}")
        return jsonify({"error": str(e)}), 500

def generate_final_bulletin(scraped_articles):
    try:
        llm_config = LLMConfig.query.first()
        if not llm_config:
            return jsonify({"error": "Configuration LLM non trouvée"}), 400

        weather_config = WeatherConfig.query.first()
        weather_data = get_weather_data(weather_config) if weather_config else None

        # Construction des informations météo
        weather_info = ""
        if weather_config and weather_data:
            weather_info = f"Informations météo : {json.dumps({
                'weather_data': weather_data,
                'provider': weather_config.provider,
                'city': weather_config.city,
                'country': weather_config.country
            }, indent=2)}"

        prompt = f"""
        Tu es un journaliste professionnel chargé de rédiger un bulletin d'information complet et structuré.
        Consignes de rédaction :
        1. Structure du bulletin :
        - Titre principal du bulletin
        - Introduction générale
        - Sections par catégories (Local, National, International, Technologie, Religieux)
        - Conclusion
        - Météo (si disponible)
        2. Critères de rédaction :
        - Langage clair et professionnel
        - Objectivité et neutralité
        - Mise en contexte des événements
        - Articulation logique entre les informations
        
        Articles disponibles :
        {json.dumps(scraped_articles, indent=2)}
        {weather_info}
        """

        openai.api_key = llm_config.api_key
        openai.base_url = f"{llm_config.api_url.rstrip('/')}/"

        response = openai.chat.completions.create(
            model=llm_config.selected_model,
            messages=[
                {"role": "system", "content": "Tu es un journaliste professionnel expert en rédaction de bulletins d'information."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        bulletin_content = response.choices[0].message.content
        
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
        parsed_feed = feedparser.parse(feed.url)
        three_days_ago = datetime.now() - timedelta(days=3)
        
        for entry in parsed_feed.entries:
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

    prompt = f"""
    Sélectionne les articles les plus pertinents et importants parmi les suivants.
    Critères de sélection :
    - Actualité récente et significative
    - Impact sociétal ou politique
    - Intérêt général
    - Diversité des catégories
    - les intérêts: actualité local, national, religieuse et technique.
    - Dans la technique: Linux, IA, cybersécurité, python et php
    - Dans la religion: christianisme.
    - Dans l'actualité locale: les nouvelles de Delémont, Courroux et vallée de Delémont
    Tu peux mettre maximum 10 actualités par rubrique.
    
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
        result = json.loads(response.choices[0].message.content)
        selected_articles = result.get('selected_articles', [])
        return jsonify(selected_articles), 200
        
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

        prompt = f"""
        Tu es un journaliste professionnel chargé de rédiger un bulletin d'information complet et structuré.
        Consignes de rédaction :
        1. Structure du bulletin :
        - Titre principal du bulletin
        - Introduction générale
        - Sections par catégories (Local, National, International, Technologie, Religieuse.)
        - Conclusion
        - Météo (si disponible)
        2. Critères de rédaction :
        - Langage clair et professionnel
        - Objectivité avec un regard évangélique
        - Mise en contexte des événements
        - Articulation logique entre les informations
        - le texte sera lu à l'antenne par un présentateur lors du journal principal maximum 20min
        
        Articles disponibles :
        {json.dumps(scraped_articles, indent=2)}
        {weather_info}
        
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
            openai.api_key = llm_config.api_key
            openai.base_url = f"{llm_config.api_url.rstrip('/')}/"
            
            response = openai.chat.completions.create(
                model=llm_config.selected_model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "Tu es un journaliste professionnel expert en rédaction de bulletins d'information."},
                    {"role": "user", "content": prompt}
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
        base_url = f"https://api.openweathermap.org/data/2.5/weather?lat={config.latitude}&lon={config.longitude}&appid={config.api_key}&units={config.units or 'metric'}"
        
        req = urllib.request.Request(base_url)
        try:
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode("utf-8"))
                return {
                    "resume": f"Température: {data['main']['temp']}°C, {data['weather'][0]['description']}",
                    "details": {
                        "temperature": {
                            "actuelle": data["main"]["temp"],
                            "ressentie": data["main"]["feels_like"],
                            "min": data["main"]["temp_min"],
                            "max": data["main"]["temp_max"]
                        },
                        "humidite": data["main"]["humidity"],
                        "vent": {
                            "vitesse": data["wind"]["speed"],
                            "direction": data["wind"]["deg"]
                        },
                        "description": data["weather"][0]["description"]
                    }
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
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

        # Si l'URL ne contient pas le chemin complet vers l'API des modèles
        if not api_url.endswith('/v1/models'):
            api_url = api_url.rstrip('/')
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
        
        if response.status_code == 401:
            return jsonify({"error": "Clé API invalide"}), 401
        elif response.status_code == 404:
            return jsonify({"error": "URL de l'API invalide"}), 404
        elif response.status_code != 200:
            return jsonify({"error": f"Erreur lors de la requête: {response.status_code}"}), response.status_code

        # Récupérer uniquement les modèles de chat
        models_data = response.json().get('data', [])
        chat_models = [model for model in models_data if model['id'].startswith('gpt-')]

        if not chat_models:
            return jsonify({"error": "Aucun modèle GPT trouvé"}), 404

        return jsonify({"models": chat_models})

    except Exception as e:
        logger.error(f"Erreur lors de la requête API: {str(e)}")
        return jsonify({"error": f"Erreur de connexion à l'API: {str(e)}"}), 500

# Les autres routes restent identiques (select_articles, scrape_articles, workflow_bulletin, etc.)

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
    """
    Récupère l'historique des bulletins générés
    """
    try:
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
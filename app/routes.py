from flask import Blueprint, render_template, request, jsonify
from app import db
from app.models import RSSFeed, LLMConfig
import feedparser
import requests

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    feeds = RSSFeed.query.all()
    return render_template('index.html', feeds=feeds)

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

@bp.route('/get_rss_feeds', methods=['GET'])
def get_rss_feeds():
    feeds = RSSFeed.query.all()
    return jsonify([{"id": feed.id, "url": feed.url, "category": feed.category} for feed in feeds])

@bp.route('/delete_rss/<int:feed_id>', methods=['DELETE'])
def delete_rss(feed_id):
    print(f"Tentative de suppression du flux RSS avec l'ID : {feed_id}")
    feed = RSSFeed.query.get_or_404(feed_id)
    
    try:
        print(f"Suppression du flux : {feed.url}")
        db.session.delete(feed)
        db.session.commit()
        print("Suppression réussie")
        return jsonify({"message": "Flux RSS supprimé avec succès"}), 200
    except Exception as e:
        print(f"Erreur lors de la suppression : {str(e)}")
        db.session.rollback()
        return jsonify({"error": f"Erreur lors de la suppression du flux RSS: {str(e)}"}), 500

@bp.route('/llm_config', methods=['GET'])
def llm_config():
    config = LLMConfig.query.first()
    return render_template('llm_config.html', config=config)

@bp.route('/save_llm_config', methods=['POST'])
def save_llm_config():
    data = request.json
    api_url = data.get('api_url')
    api_key = data.get('api_key')
    selected_model = data.get('selected_model')

    if not all([api_url, api_key, selected_model]):
        return jsonify({"error": "Tous les champs sont requis"}), 400

    config = LLMConfig.query.first()
    if not config:
        config = LLMConfig()

    config.api_url = api_url
    config.api_key = api_key
    config.selected_model = selected_model

    try:
        db.session.add(config)
        db.session.commit()
        return jsonify({"message": "Configuration LLM sauvegardée avec succès"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Erreur lors de la sauvegarde: {str(e)}"}), 500

@bp.route('/test_llm_connection', methods=['POST'])
def test_llm_connection():
    config = LLMConfig.query.first()
    if not config:
        return jsonify({"error": "Configuration LLM non trouvée"}), 404

    try:
        response = requests.get(
            f"{config.api_url}/models",
            headers={"Authorization": f"Bearer {config.api_key}"},
            timeout=5
        )
        if response.ok:
            return jsonify({"message": "Connexion établie avec succès"}), 200
        else:
            return jsonify({"error": "Échec de la connexion à l'API"}), 400
    except requests.RequestException as e:
        return jsonify({"error": f"Erreur de connexion: {str(e)}"}), 500
from flask import Blueprint, render_template, request, jsonify
from app import db
from app.models import RSSFeed
import feedparser

# Créer un Blueprint
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

@bp.route('/get_rss_feeds', methods=['GET'])
def get_rss_feeds():
    feeds = RSSFeed.query.all()
    return jsonify([{"id": feed.id, "url": feed.url, "category": feed.category} for feed in feeds])

@bp.route('/delete_rss/<int:feed_id>', methods=['DELETE'])
def delete_rss(feed_id):
    print(f"Tentative de suppression du flux RSS avec l'ID : {feed_id}")  # Debug
    feed = RSSFeed.query.get_or_404(feed_id)
    
    try:
        print(f"Suppression du flux : {feed.url}")  # Debug
        db.session.delete(feed)
        db.session.commit()
        print("Suppression réussie")  # Debug
        return jsonify({"message": "Flux RSS supprimé avec succès"}), 200
    except Exception as e:
        print(f"Erreur lors de la suppression : {str(e)}")  # Debug
        db.session.rollback()
        return jsonify({"error": f"Erreur lors de la suppression du flux RSS: {str(e)}"}), 500

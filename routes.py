from flask import render_template, request, jsonify
from app import db
from app.models import RSSFeed
import feedparser

# Supprimez la création d'une nouvelle instance
# Les routes seront attachées à l'application via Blueprint ou directement dans create_app

def index():
    feeds = RSSFeed.query.all()
    return render_template('index.html', feeds=feeds)

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

def get_rss_feeds():
    feeds = RSSFeed.query.all()
    return jsonify([{"id": feed.id, "url": feed.url, "category": feed.category} for feed in feeds])

def generate_bulletin():
    # Cette fonction sera implémentée plus tard
    return jsonify({"message": "Génération du bulletin en cours"}), 200

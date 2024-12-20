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

# Route racine pour afficher le template index
@bp.route('/')
def index():
    # Récupérer la liste des flux RSS existants
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

@bp.route('/generate_bulletin', methods=['POST'])
def generate_bulletin():
    """
    Route pour générer un bulletin via le workflow complet
    """
    try:
        response = workflow_bulletin()
        return response
    except Exception as e:
        logger.error(f"Erreur lors de la génération du bulletin : {e}")
        return jsonify({"error": str(e)}), 500

# Les autres routes existantes restent identiques (select_articles, scrape_articles, etc.)
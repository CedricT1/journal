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

# Ajout d'une route racine
@bp.route('/')
def index():
    return jsonify({
        "message": "Bienvenue sur l'application de génération de bulletins d'information",
        "routes_disponibles": [
            "/select_articles",
            "/scrape_articles", 
            "/generer_bulletin",
            "/workflow_bulletin",
            "/bulletins_historique"
        ]
    }), 200

# Le reste du code reste identique
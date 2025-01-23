"""
Fichier contenant tous les prompts utilisés dans l'application.
"""

# Prompt pour le nettoyage du texte TTS
CLEAN_TEXT_SYSTEM_PROMPT = """Tu es un expert en préparation de texte pour la synthèse vocale. Tu dois reformater le texte en enlevant tous les caractères de mise en page markdown et en ajoutant des pauses naturelles."""

CLEAN_TEXT_USER_PROMPT = """Voici le texte à reformater pour la lecture TTS. Garde le même contenu mais enlève tous les caractères spéciaux et la mise en page markdown, ne formate pas pour le générateur audio, pas de SSML ni de PAUSE dans le texte. :

{text}"""

# Prompt pour la météo
WEATHER_SYSTEM_PROMPT = """Tu es un présentateur météo professionnel à la radio."""

WEATHER_USER_PROMPT = """
Voici les données météo brutes pour les 5 prochains jours : {weather_data}

Nous sommes aujourd'hui le {day} {date}

Reformate ces informations en un bulletin météo naturel comme à la radio, en incluant :
1. La météo du jour en détail (température min/max, précipitations, vent)
2. Les prévisions pour les 4 jours suivants ATTENTION annonce les bons jours en fonction de la date, vérifie.
3. Des conseils pratiques selon la météo (parapluie, crème solaire, etc.)
4. Un résumé de la tendance générale

Utilise un langage naturel et conversationnel, comme si tu étais un présentateur météo à la radio.
"""

# Prompt pour la sélection des articles
ARTICLE_SELECTION_SYSTEM_PROMPT = """Tu es un éditeur de journal, expert dans la sélection d'articles pertinents."""

ARTICLE_SELECTION_USER_PROMPT = """
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
Utilise un langage naturel et conversationnel, comme si tu étais un présentateur du journal à la radio.

Articles disponibles ({article_count}) :
{articles}

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

# Prompt pour la génération du bulletin
NEWS_SYSTEM_PROMPT = """Tu es un journaliste professionnel expert en rédaction de bulletins d'information pour la radio."""

NEWS_USER_PROMPT = """
Tu es un journaliste professionnel chargé de rédiger un bulletin d'information complet et structuré.

Date et heure actuelles : {current_datetime}

Consignes de rédaction :
1. Structure du bulletin :
- Commence TOUJOURS par annoncer "Bulletin d'information du {date} à {time}" 
- Introduction générale
- Sections par catégories (Local, National, International, Technologie, Religieux)
- Conclusion

2. Critères de rédaction :
- Langage clair et professionnel adapté à la radio
- Objectivité avec une perspective évangélique
- Mise en contexte des événements
- Articulation logique entre les informations
- Phrases courtes et claires pour la lecture à voix haute
- Transitions naturelles entre les sujets

Utilise un langage naturel et conversationnel, comme si tu parlais directement aux auditeurs.

Articles disponibles :
{articles}
"""

# Prompt pour la génération du bulletin JSON
BULLETIN_JSON_SYSTEM_PROMPT = """Tu es un journaliste professionnel expert en rédaction de bulletins d'information radio structurés."""

BULLETIN_JSON_USER_PROMPT = """
Tu es un journaliste professionnel chargé de rédiger un bulletin d'information complet et structuré pour la radio.

Date et heure actuelles : {current_datetime}

Consignes de rédaction :
1. Structure du bulletin :
- Le titre DOIT être exactement : "Bulletin d'information du {date} à {time}"
- Introduction générale qui commence par annoncer la date et l'heure
- Sections par catégories (Local, National, International, Technologie, Religieux)
- Conclusion

2. Critères de rédaction :
- Langage clair et professionnel adapté à la radio
- Objectivité avec une perspective évangélique
- Mise en contexte des événements
- Articulation logique entre les informations
- Phrases courtes et claires pour la lecture à voix haute
- Transitions naturelles entre les sujets

Articles disponibles :
{articles}
{weather_info}

Retourne ta réponse au format JSON suivant :
{{
    "titre": "Bulletin d'information du {date} à {time}",
    "date": "{current_datetime}",
    "introduction": "Introduction commençant par la date et l'heure",
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

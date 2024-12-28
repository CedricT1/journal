# Journal - Générateur de Bulletins d'Information Automatisé

Une application Flask qui génère automatiquement des bulletins d'information en agrégeant des sources RSS et en utilisant l'IA pour la rédaction.

## Fonctionnalités

- 📰 Agrégation de flux RSS par catégories (Local, National, International, Technologie, Religieux)
- 🤖 Génération de contenu via LLM (Large Language Model)
- ☁️ Intégration des données météorologiques
- 📊 Historique des bulletins générés
- ⚙️ Interface de configuration complète

## Configuration Requise

- Python 3.x
- Flask
- SQLAlchemy
- OpenAI API ou API compatible
- API météo (configurable)

## Installation

1. Cloner le dépôt :
```bash
git clone [URL_DU_REPO]
cd journal
```

2. Installer les dépendances :
```bash
pip install -r requirements.txt
```

3. Configurer les variables d'environnement dans `.env` :
```
FLASK_APP=run.py
FLASK_ENV=development
```

## Configuration

1. Configuration LLM :
   - URL de l'API
   - Clé API
   - Modèle à utiliser

2. Configuration Météo :
   - Fournisseur météo
   - Clé API
   - Localisation (ville, pays, coordonnées)

3. Sources RSS :
   - Ajout/suppression de flux RSS
   - Catégorisation des sources

## Utilisation

1. Lancer l'application :
```bash
flask run
```

2. Accéder à l'interface web : `http://localhost:5000`

3. Configurer les sources RSS et les paramètres

4. Générer des bulletins automatiquement ou manuellement

## Structure du Projet

- `app/` : Code principal de l'application
  - `routes.py` : Routes et logique de l'application
  - `models.py` : Modèles de données
  - `templates/` : Templates HTML
- `data/` : Données de configuration
- `requirements.txt` : Dépendances Python

## Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou un pull request.

## Licence

[À définir]

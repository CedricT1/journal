# Journal - Générateur de Bulletins d'Information Automatisé

Une application Flask qui génère automatiquement des bulletins d'information en agrégeant des sources RSS, en utilisant l'IA pour la rédaction et en produisant une version audio du bulletin.

## Fonctionnalités

### Gestion de l'Information
- 📰 Agrégation de flux RSS par catégories (Local, National, International, Technologie, Religieux)
- 🤖 Génération de contenu via LLM (Large Language Model)
- ☁️ Intégration des données météorologiques
- 📊 Historique des bulletins générés

### Synthèse Vocale
- 🎙️ Support de deux moteurs TTS :
  - ElevenLabs (voix de haute qualité)
  - Edge TTS (voix Microsoft)
- 🔊 Configuration avancée des voix :
  - Vitesse de parole
  - Tonalité
  - Volume
  - Stabilité et clarté (ElevenLabs)
- 🎵 Génération automatique de fichiers MP3
- 📁 Gestion automatique de l'archivage audio

### Interface et Configuration
- ⚙️ Interface de configuration complète
- 🎚️ Test des voix en direct
- 📱 Interface responsive
- 🔄 Génération automatique via crontab

## Configuration Requise

- Python 3.x
- Flask
- SQLAlchemy
- OpenAI API ou API compatible
- API météo (configurable)
- ElevenLabs API (optionnel)
- Edge-TTS (inclus)

## Installation

1. Cloner le dépôt :
```bash
git clone [URL_DU_REPO]
cd journal
```

2. Créer et activer un environnement virtuel :
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\\Scripts\\activate  # Windows
```

3. Installer les dépendances :
```bash
pip install -r requirements.txt
```

4. Configurer les variables d'environnement dans `.env` :
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

3. Configuration Audio :
   - Choix du moteur (ElevenLabs/Edge-TTS)
   - Paramètres de voix
   - Qualité audio et rétention

4. Sources RSS :
   - Ajout/suppression de flux RSS
   - Catégorisation des sources

## Utilisation

1. Lancer l'application :
```bash
flask run
```

2. Accéder à l'interface web : `http://localhost:5000`

3. Configurer dans l'ordre :
   - Sources RSS
   - API LLM
   - API Météo
   - Synthèse vocale

4. Générer des bulletins :
   - Manuellement via l'interface
   - Automatiquement via cron

## Structure du Projet

- `app/` : Code principal de l'application
  - `routes.py` : Routes et logique de l'application
  - `models.py` : Modèles de données
  - `tasks.py` : Tâches de maintenance
  - `templates/` : Templates HTML
- `static/` : Fichiers statiques
  - `audio/` : Fichiers audio générés
- `migrations/` : Migrations de base de données
- `requirements.txt` : Dépendances Python

## Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou un pull request.

## Licence

[À définir]

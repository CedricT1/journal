# Cahier des Charges - Phase 2

## 1. Fonctionnalités Existantes (Complétées)

### 1.1 Gestion des Sources
- ✅ Agrégation de flux RSS par catégories
- ✅ Interface de gestion des flux RSS
- ✅ Scraping automatique des contenus

### 1.2 Génération de Contenu
- ✅ Intégration LLM pour la rédaction
- ✅ Configuration flexible du LLM
- ✅ Génération de bulletins structurés

### 1.3 Météo
- ✅ Intégration des données météorologiques
- ✅ Configuration des paramètres météo
- ✅ Inclusion automatique dans les bulletins

### 1.4 Automatisation
- ✅ Exécution via crontab
- ✅ Historique des bulletins
- ✅ Interface de configuration complète

## 2. Nouvelles Fonctionnalités (Phase 2)

### 2.1 Génération Audio des Bulletins

#### 2.1.1 Support Multi-Moteurs
- Intégration d'ElevenLabs
  - Configuration de l'API
  - Sélection des voix disponibles
  - Gestion de la clé API
- Intégration d'Edge-TTS
  - Liste complète des voix françaises
  - Interface de sélection des voix
  - Configuration des paramètres vocaux

#### 2.1.2 Interface de Configuration
- Page dédiée à la configuration audio
  - Sélection du moteur (ElevenLabs/Edge-TTS)
  - Configuration spécifique par moteur
  - Test audio des voix

#### 2.1.3 Génération et Stockage
- Génération automatique des fichiers MP3
- Stockage organisé des fichiers audio
- Nommage cohérent des fichiers
- Gestion de l'historique audio

#### 2.1.4 Contrôles de Qualité
- Prévisualisation audio avant génération finale
- Contrôle de la durée des segments
- Vérification de la qualité audio

### 2.2 Améliorations Techniques

#### 2.2.1 Gestion des Ressources
- Optimisation du stockage audio
- Politique de rétention des fichiers
- Compression adaptative

#### 2.2.2 Interface Utilisateur
- Lecteur audio intégré
- Contrôles de lecture
- Téléchargement des fichiers MP3

## 3. Spécifications Techniques

### 3.1 ElevenLabs
- API Key : Stockage sécurisé
- Voice ID : Interface de sélection
- Paramètres de voix configurables
  - Stabilité
  - Clarté
  - Style de parole

### 3.2 Edge-TTS
- Liste des voix françaises disponibles
- Paramètres configurables
  - Vitesse de parole
  - Pitch
  - Volume

### 3.3 Stockage
- Format : MP3
- Qualité : 192kbps minimum
- Structure de dossiers organisée
- Système de backup

## 4. Sécurité

### 4.1 Gestion des Clés API
- Chiffrement des clés
- Rotation périodique
- Validation des accès

### 4.2 Stockage des Fichiers
- Accès contrôlé
- Sauvegarde automatique
- Nettoyage périodique

## 5. Interface Utilisateur

### 5.1 Configuration Audio
- Sélection du moteur TTS
- Configuration des paramètres
- Interface de test

### 5.2 Gestion des Fichiers
- Liste des bulletins audio
- Lecteur intégré
- Options de téléchargement

## 6. Automatisation

### 6.1 Intégration Crontab
- Génération audio automatique
- Notifications de statut
- Gestion des erreurs

### 6.2 Maintenance
- Nettoyage automatique
- Vérification d'intégrité
- Rapports de statut 
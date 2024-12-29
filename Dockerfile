FROM python:3.11-slim

# Installation des dépendances système nécessaires
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Création du répertoire de l'application
WORKDIR /app

# Copie des fichiers de dépendances
COPY requirements.txt .

# Installation des dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code de l'application
COPY . .

# Création des répertoires pour les volumes
RUN mkdir -p /app/instance /app/app/static

# Exposition du port
EXPOSE 5000

# Commande de démarrage
CMD ["flask", "run", "--host=0.0.0.0"] 
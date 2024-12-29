FROM python:3.11-slim

# Installation des dépendances système nécessaires
RUN apt-get update && apt-get install -y \
    ffmpeg \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Création du répertoire de l'application
WORKDIR /app

# Copie des fichiers de dépendances
COPY requirements.txt .

# Installation des dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Création des répertoires pour les volumes avec les bonnes permissions
RUN mkdir -p /app/instance /app/app/static && \
    chmod -R 777 /app/instance /app/app/static

# Copie du code de l'application
COPY . .

# Script d'initialisation
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Exposition du port
EXPOSE 5000

# Définition des volumes
VOLUME ["/app/instance", "/app/app/static"]

# Utilisation du script d'initialisation comme point d'entrée
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["flask", "run", "--host=0.0.0.0"]

# Copie du fichier .env
COPY .env . 
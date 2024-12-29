FROM python:3.11-slim

# Installation des dépendances système nécessaires
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Création d'un utilisateur non-root
RUN useradd -m -r -u 1000 flaskuser

# Création du répertoire de l'application
WORKDIR /app

# Copie des fichiers de dépendances
COPY requirements.txt .

# Installation des dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Création des répertoires pour les volumes avec les bonnes permissions
RUN mkdir -p /app/instance /app/app/static && \
    chown -R flaskuser:flaskuser /app && \
    chmod -R 777 /app/instance /app/app/static

# Copie du code de l'application
COPY . .
RUN chown -R flaskuser:flaskuser /app

# Script d'initialisation
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Exposition du port
EXPOSE 5000

# Changement vers l'utilisateur non-root
USER flaskuser

# Définition des volumes
VOLUME ["/app/instance", "/app/app/static"]

# Utilisation du script d'initialisation comme point d'entrée
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["flask", "run", "--host=0.0.0.0"]

# Copie du fichier .env
COPY .env . 
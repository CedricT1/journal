#!/bin/sh

# S'assurer que les répertoires existent avec les bonnes permissions
mkdir -p /app/instance
mkdir -p /app/app/static

# Donner les permissions complètes sur le dossier instance
chmod 777 /app/instance

# Créer et configurer la base de données
touch /app/instance/app.db
chmod 666 /app/instance/app.db

# Initialiser la base de données avec les migrations existantes
cd /app

if [ ! -s /app/instance/app.db ]; then
    echo "Initialisation de la base de données..."
    flask db stamp head || true
    flask db upgrade || true
fi

# Exécuter la commande passée en argument
exec "$@" 
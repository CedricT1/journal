#!/usr/bin/env python3
import os
import sys
import requests
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

def generate_bulletin():
    """
    Script pour générer un bulletin via l'API Flask
    """
    # URL de votre application Flask (à ajuster)
    BASE_URL = os.getenv('FLASK_APP_URL', 'http://localhost:5000')
    
    try:
        # Appel de la route de workflow
        response = requests.post(f'{BASE_URL}/workflow_bulletin')
        
        if response.status_code == 200:
            bulletin = response.json()
            print("Bulletin généré avec succès !")
            print(f"Titre : {bulletin.get('titre', 'Sans titre')}")
            return True
        else:
            print(f"Erreur lors de la génération du bulletin : {response.text}")
            return False
    
    except Exception as e:
        print(f"Erreur inattendue : {e}")
        return False

def main():
    result = generate_bulletin()
    sys.exit(0 if result else 1)

if __name__ == '__main__':
    main()
import random
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import logging
import trafilatura
from trafilatura.settings import use_config

logger = logging.getLogger(__name__)

class HTTPManager:
    """Gestionnaire de connexions HTTP avec mécanismes de résilience"""
    
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0'
    ]

    def __init__(self, max_retries=3, pool_connections=20, pool_maxsize=20):
        self.session = requests.Session()
        # Configuration du retry avec backoff exponentiel
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1.0,  # Augmenté pour plus d'attente entre les tentatives
            status_forcelist=[403, 429, 500, 502, 503, 504],
        )
        # Configuration des adaptateurs avec un pool de connexions plus grand
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def get(self, url, timeout=15):
        """Effectue une requête GET avec rotation des User-Agents et headers supplémentaires"""
        headers = {
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
        try:
            response = self.session.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la requête vers {url}: {str(e)}")
            raise

    def extract_article_content(self, url):
        """Extrait le contenu d'un article en utilisant trafilatura avec notre gestionnaire de connexions"""
        try:
            response = self.get(url)
            if response.status_code == 200:
                # Configuration de trafilatura
                config = use_config()
                config.set("DEFAULT", "USER_AGENTS", random.choice(self.USER_AGENTS))
                
                content = trafilatura.extract(
                    response.text,
                    config=config,
                    include_comments=False,
                    include_formatting=False,
                    favor_precision=True,
                    no_fallback=False  # Permettre les méthodes de fallback
                )
                
                if content:
                    return content.strip()
                    
            logger.warning(f"Impossible d'extraire le contenu de {url}")
            return "Contenu de l'article non disponible"
            
        except Exception as e:
            logger.error(f"Erreur d'extraction pour {url}: {e}")
            return "Contenu de l'article non disponible" 
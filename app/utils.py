import random
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import logging

logger = logging.getLogger(__name__)

class HTTPManager:
    """Gestionnaire de connexions HTTP avec mécanismes de résilience"""
    
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0',
    ]

    def __init__(self, max_retries=3, pool_connections=10, pool_maxsize=10):
        self.session = requests.Session()
        # Configuration du retry avec backoff exponentiel
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        # Configuration des adaptateurs avec un pool de connexions plus grand
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def get(self, url, timeout=10):
        """Effectue une requête GET avec rotation des User-Agents"""
        headers = {'User-Agent': random.choice(self.USER_AGENTS)}
        try:
            response = self.session.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la requête vers {url}: {str(e)}")
            raise 
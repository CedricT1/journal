import random
import requests
import time
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import logging
import trafilatura
from trafilatura.settings import use_config
from fake_useragent import UserAgent  # Ajout pour une meilleure rotation des User-Agents

logger = logging.getLogger(__name__)

class HTTPManager:
    """Gestionnaire de connexions HTTP avec mécanismes de résilience et anti-scraping"""
    
    # Liste de secours au cas où fake-useragent échoue
    FALLBACK_USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0'
    ]

    def __init__(self, max_retries=3, pool_connections=20, pool_maxsize=20):
        """Initialisation avec paramètres de résilience améliorés"""
        self.session = requests.Session()
        
        # Initialisation de fake-useragent
        try:
            self.ua = UserAgent()
        except Exception as e:
            logger.warning(f"Impossible d'initialiser fake-useragent: {e}. Utilisation de la liste de secours.")
            self.ua = None

        # Configuration du retry avec backoff exponentiel et délais aléatoires
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=2.0,  # Augmenté pour plus d'attente entre les tentatives
            status_forcelist=[403, 429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD", "OPTIONS"],  # Méthodes autorisées pour le retry
            respect_retry_after_header=True  # Respecter les headers Retry-After
        )

        # Configuration des adaptateurs avec un pool de connexions
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Dictionnaire pour stocker les timestamps des dernières requêtes par domaine
        self.last_request_time = {}

    def _get_random_delay(self, domain):
        """Calcule un délai aléatoire entre les requêtes pour un domaine"""
        # Délai minimum de 2 secondes pour les domaines connus pour bloquer
        if any(blocked in domain for blocked in ['next.ink', 'phoronix.com']):
            return random.uniform(2.0, 5.0)
        return random.uniform(0.5, 2.0)

    def _get_user_agent(self):
        """Obtient un User-Agent aléatoire"""
        if self.ua:
            try:
                return self.ua.random
            except Exception:
                pass
        return random.choice(self.FALLBACK_USER_AGENTS)

    def get(self, url, timeout=15):
        """Effectue une requête GET avec rotation des User-Agents et délais"""
        from urllib.parse import urlparse
        
        # Extraction du domaine
        domain = urlparse(url).netloc
        
        # Respect des délais entre requêtes pour le même domaine
        if domain in self.last_request_time:
            elapsed = time.time() - self.last_request_time[domain]
            delay = self._get_random_delay(domain)
            if elapsed < delay:
                time.sleep(delay - elapsed)
        
        headers = {
            'User-Agent': self._get_user_agent(),
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
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.google.com/'  # Simuler une provenance de Google
        }

        try:
            response = self.session.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            # Mise à jour du timestamp de la dernière requête
            self.last_request_time[domain] = time.time()
            
            return response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la requête vers {url}: {str(e)}")
            raise

    def extract_article_content(self, url):
        """Extrait le contenu d'un article avec gestion améliorée des erreurs"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                response = self.get(url)
                if response.status_code == 200:
                    # Configuration de trafilatura
                    config = use_config()
                    config.set("DEFAULT", "USER_AGENTS", self._get_user_agent())
                    
                    # Tentative d'extraction avec différentes méthodes
                    content = trafilatura.extract(
                        response.text,
                        config=config,
                        include_comments=False,
                        include_formatting=False,
                        favor_precision=True,
                        no_fallback=False
                    )
                    
                    if content:
                        return content.strip()
                    
                    # Si trafilatura échoue, on attend avant de réessayer
                    retry_count += 1
                    if retry_count < max_retries:
                        time.sleep(random.uniform(1.0, 3.0))
                        continue
                        
                logger.warning(f"Impossible d'extraire le contenu de {url} après {retry_count} tentatives")
                return "Contenu de l'article non disponible"
                
            except Exception as e:
                logger.error(f"Erreur d'extraction pour {url}: {e}")
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(random.uniform(1.0, 3.0))
                    continue
                return "Contenu de l'article non disponible" 
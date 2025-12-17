import logging
import random
import time
from typing import Optional, Dict, Any, List
import tls_client
import logging
import random
import time
from typing import Optional, Dict, List
import tls_client

from app.models.job import ScraperInput, JobPost, ScraperError

class ScraperError(Exception):
    pass

class BaseScraper:
    def __init__(self, site_name: str, proxies: Optional[List[str]] = None):
        self.site_name = site_name
        self.proxies = proxies
        self.session = tls_client.Session(
            client_identifier="chrome_120",
            random_tls_extension_order=True
        )
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        self.logger = logging.getLogger(f"Scraper:{site_name}")
        self.logger.setLevel(logging.DEBUG) # Default to debug for now

    def _get_proxy(self) -> Optional[str]:
        if self.proxies:
            return random.choice(self.proxies)
        return None

    def safe_get(self, url: str, params: Optional[Dict] = None, **kwargs) -> tls_client.response.Response:
        """
        Wrapper for session.get with basic error handling and random delays.
        """
        delay = random.uniform(1, 3)
        time.sleep(delay)
        
        proxy = self._get_proxy()
        if proxy:
            # tls_client format: http://user:pass@host:port
            kwargs["proxy"] = proxy

        try:
            self.logger.debug(f"Fetching {url}")
            response = self.session.get(url, params=params, **kwargs)
            if response.status_code not in range(200, 400):
                self.logger.warning(f"Request failed with status {response.status_code}")
                # We don't raise here effectively to allow scrapers to handle logic
            return response
        except Exception as e:
            self.logger.error(f"Request exception: {e}")
            raise ScraperError(f"Network error: {e}")

    def scrape(self, input_data: ScraperInput) -> List[JobPost]:
        """
        Main method to be implemented by children.
        """
        raise NotImplementedError

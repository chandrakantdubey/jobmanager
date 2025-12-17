import re
import urllib.parse
from datetime import datetime, timedelta
from typing import List, Optional

from bs4 import BeautifulSoup
import requests

from app.models.job import JobPost, ScraperInput, JobType
from app.scrapers.base import BaseScraper

class BuiltInScraper(BaseScraper):
    def __init__(self):
        super().__init__("builtin")

    def scrape(self, input_data: ScraperInput) -> List[JobPost]:
        self.logger.info(f"Scraping BuiltIn for: {input_data.search_term}")
        
        base_url = "https://builtin.com"
        search_url = f"{base_url}/jobs?q={urllib.parse.quote(input_data.search_term)}"
        
        # If remote is requested, we might want to modify the URL or filter later.
        # BuiltIn has a specific /jobs/remote endpoint, but it might separate them.
        # For now, we search all and check location text.
        # If user specifically requested ONLY remote, we might append &l=Remote if supported,
        # but the query param support is opaque.
        # We will try to rely on the general search.

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }

        try:
            response = requests.get(search_url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            job_cards = soup.find_all("div", id=re.compile(r"^job-card-\d+"))
            
            job_posts = []
            
            for card in job_cards:
                try:
                    # Title
                    title_elem = card.find("h2")
                    if not title_elem:
                        continue
                    title_link = title_elem.find("a")
                    title = title_link.get_text(strip=True) if title_link else title_elem.get_text(strip=True)
                    
                    job_path = title_link["href"] if title_link and title_link.has_attr("href") else ""
                    if job_path.startswith("/"):
                        job_url = f"{base_url}{job_path}"
                    else:
                        job_url = job_path
                        
                    # Company
                    company_elem = card.find("div", class_="left-side-tile-item-2")
                    company = company_elem.get_text(strip=True) if company_elem else "BuiltIn Community"
                    
                    # Location
                    # It's usually in the bounded-attribute-section
                    location_elem = card.find("i", class_="fa-location-dot")
                    location = "Unknown"
                    if location_elem:
                         # The parent's sibling or parent's parent text?
                         # HTML: <div class="d-flex align-items-start gap-sm"> ... <div><span>Location Text</span></div></div>
                         # location_elem is the <i>.
                         # Its parent is a div. That div's sibling is a div containing the span.
                         # Let's traverse up to the row-like container or just find the span near it.
                         
                         # Easier: The card text often contains the location.
                         # Let's look for the span details.
                         location_container = location_elem.find_parent("div", class_="gap-sm")
                         if location_container:
                             location = location_container.get_text(strip=True)
                    
                    # Date
                    date_elem = card.find("span", class_="bg-gray-01") or card.find("span", class_="text-gray-03")
                    date_text = date_elem.get_text(strip=True) if date_elem else ""
                    date_posted = self.parse_date(date_text)
                    
                    # Description (from collapsed area)
                    # ID is job-card-{id}, collapsed area is drop-data-{id}
                    card_id = card.get("id", "").replace("job-card-", "")
                    desc_div = soup.find("div", id=f"drop-data-{card_id}")
                    description = desc_div.get_text(strip=True) if desc_div else ""
                    
                    job = JobPost(
                        title=title,
                        company=company,
                        job_url=job_url,
                        location=location,
                        date_posted=date_posted,
                        description=description,
                        is_remote="remote" in location.lower(),
                        site="builtin"
                    )
                    job_posts.append(job)
                    
                except Exception as e:
                    self.logger.warning(f"Error parsing BuiltIn job card: {e}")
                    continue
            
            self.logger.info(f"Found {len(job_posts)} jobs on BuiltIn")
            return job_posts
            
        except Exception as e:
            self.logger.error(f"Error scraping BuiltIn: {e}")
            return []

    def parse_date(self, text: str) -> Optional[datetime]:
        text = text.lower()
        today = datetime.now().date()
        
        if "hour" in text or "minute" in text or "second" in text:
            return today
        if "yesterday" in text:
            return today - timedelta(days=1)
        if "days ago" in text:
            try:
                days = int(re.search(r"(\d+)", text).group(1))
                return today - timedelta(days=days)
            except:
                return today
        return today

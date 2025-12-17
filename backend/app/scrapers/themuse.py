from typing import List, Optional
import urllib.parse
from app.scrapers.base import BaseScraper
from app.models.job import ScraperInput, JobPost

class TheMuseScraper(BaseScraper):
    def __init__(self, proxies: Optional[List[str]] = None):
        super().__init__("The Muse", proxies)
        self.base_url = "https://www.themuse.com/api/public/jobs"

    def scrape(self, input_data: ScraperInput) -> List[JobPost]:
        job_posts = []
        
        params = {
            "keyword": input_data.search_term,
            "location": input_data.location,
            "page": 0,
            "per_page": min(input_data.results_wanted, 20)
        }
        
        try:
            response = self.safe_get(self.base_url, params=params)
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch The Muse jobs: {response.status_code}")
                return []
                
            data = response.json()
            jobs = data.get("results", [])
            
            for item in jobs:
                try:
                    job = JobPost(
                        title=item.get("name", "Unknown"),
                        company=item.get("company", {}).get("name", "Unknown"),
                        location=", ".join(item.get("locations", [])[0].get("name", "N/A") if item.get("locations") else ["N/A"]),
                        job_url=item.get("refs", {}).get("landing_page", ""),
                        description=item.get("contents", ""),
                        site="The Muse",
                        date_posted=item.get("publication_date", "")[:10] if item.get("publication_date") else None
                    )
                    job_posts.append(job)
                    
                except Exception as e:
                    self.logger.warning(f"Error parsing The Muse job: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"The Muse scraping error: {e}")
            
        return job_posts

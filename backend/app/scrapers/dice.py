from typing import List, Optional
import urllib.parse
from app.scrapers.base import BaseScraper
from app.models.job import ScraperInput, JobPost

class DiceScraper(BaseScraper):
    def __init__(self, proxies: Optional[List[str]] = None):
        super().__init__("Dice", proxies)
        self.base_url = "https://job-search-api.svc.dhigroupinc.com/v1/dice/jobs/search"

    def scrape(self, input_data: ScraperInput) -> List[JobPost]:
        job_posts = []
        
        # Dice API uses specific parameters
        params = {
            "q": input_data.search_term,
            "location": input_data.location,
            "page": 1,
            "pageSize": min(input_data.results_wanted, 50)
        }
        
        if input_data.is_remote:
            params["filters.workplaceTypes"] = "Remote"
        
        try:
            headers = {
                "x-api-key": "1YAt0R9wBg4WfsF9VB2778F5CHLAPMVW3WAZcKd8",  # Public API key from Dice
                "Content-Type": "application/json"
            }
            
            response = self.safe_get(self.base_url, params=params, headers=headers)
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch Dice jobs: {response.status_code}")
                return []
                
            data = response.json()
            jobs = data.get("data", [])
            
            for item in jobs:
                try:
                    job = JobPost(
                        title=item.get("title", "Unknown"),
                        company=item.get("employerName", "Unknown"),
                        location=item.get("jobLocation", {}).get("displayName", "N/A"),
                        job_url=item.get("detailsPageUrl", ""),
                        description=item.get("summary", ""),
                        site="Dice",
                        date_posted=item.get("postedDate", "")[:10] if item.get("postedDate") else None
                    )
                    job_posts.append(job)
                    
                except Exception as e:
                    self.logger.warning(f"Error parsing Dice job: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Dice scraping error: {e}")
            
        return job_posts

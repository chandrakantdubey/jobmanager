
from typing import List, Optional
import urllib.parse
from app.scrapers.base import BaseScraper
from app.models.job import ScraperInput, JobPost

class RemotiveScraper(BaseScraper):
    def __init__(self, proxies: Optional[List[str]] = None):
        super().__init__("Remotive", proxies)
        self.base_url = "https://remotive.com/api/remote-jobs"

    def scrape(self, input_data: ScraperInput) -> List[JobPost]:
        job_posts = []
        
        # Remotive has limited filtering via API: category, company_name, search, limit
        # We will use 'search' for the search term
        
        params = {
            "search": input_data.search_term,
            "limit": input_data.results_wanted
        }
        
        # Remotive doesn't support offset pagination in the strict sense for the free API (it just returns a list)
        # But we can try to fetch more if needed or just return what we have.
        # The docs say "limit" is supported.
        
        try:
            response = self.safe_get(self.base_url, params=params)
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch Remotive jobs: {response.status_code}")
                return []
                
            data = response.json()
            jobs = data.get("jobs", [])
            
            for item in jobs:
                try:
                    # Filter by location if needed (Remotive is global remote mostly, but allow checking)
                    candidate_location = item.get("candidate_required_location", "")
                    
                    # Basic client-side filtering matching input_data.location if it's specific
                    # But often users want "Remote" so we include it.
                    
                    # Salary parsing from description or tags if available (Remotive separates it sometimes)
                    # For now we skip complex salary parsing unless explicit in API.
                    
                    # Parse date
                    date_val = item.get("publication_date", None)
                    if date_val and isinstance(date_val, str) and len(date_val) >= 10:
                        date_val = date_val[:10]


                    
                    job = JobPost(
                        title=item.get("title", "Unknown"),
                        company=item.get("company_name", "Unknown"),
                        location=candidate_location if candidate_location else "Remote",
                        job_url=item.get("url", ""),
                        description=item.get("description", ""),
                        salary_min=None, 
                        salary_max=None,
                        site="Remotive",
                        date_posted=date_val
                    )
                    job_posts.append(job)
                    
                except Exception as e:
                    self.logger.warning(f"Error parsing Remotive job: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Remotive scraping error: {e}")
            
        return job_posts

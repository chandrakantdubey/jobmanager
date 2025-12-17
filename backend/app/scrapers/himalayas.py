
from typing import List, Optional
import urllib.parse
from app.scrapers.base import BaseScraper
from app.models.job import ScraperInput, JobPost

class HimalayasScraper(BaseScraper):
    def __init__(self, proxies: Optional[List[str]] = None):
        super().__init__("Himalayas", proxies)
        self.base_url = "https://himalayas.app/jobs/api"

    def scrape(self, input_data: ScraperInput) -> List[JobPost]:
        job_posts = []
        
        # Himalayas API supports limit and offset
        params = {
            "limit": input_data.results_wanted,
            "offset": input_data.offset
        }
        
        try:
            response = self.safe_get(self.base_url, params=params)
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch Himalayas jobs: {response.status_code}")
                return []
                
            data = response.json()
            jobs = data.get("jobs", [])
            
            for item in jobs:
                try:
                    # Client-side filtering for search term since API doesn't support query param?
                    # The research said "An example request would be https://himalayas.app/jobs/api?limit=20&offset=10"
                    # It didn't explicitly mention ?search=... but we can check if it exists or filter locally.
                    # We will filter locally to be safe.
                    
                    search_term = input_data.search_term.lower()
                    title = item.get("title", "Unknown")
                    description = item.get("excerpt", "") # Himalayas has 'excerpt' and 'description'
                    full_description = item.get("description", "")
                    
                    # Basic match
                    if search_term not in title.lower() and search_term not in description.lower():
                        continue

                    # Salary parsing from API fields
                    min_salary = item.get("minSalary")
                    max_salary = item.get("maxSalary")
                    
                    # Parse date
                    date_val = item.get("pubDate", None)
                    if date_val and isinstance(date_val, str) and len(date_val) >= 10:
                        date_val = date_val[:10]

                    job = JobPost(
                        title=title,
                        company=item.get("companyName", "Unknown"),
                        location="Remote", # Himalayas is remote-first
                        job_url=item.get("applicationLink", "") or item.get("guid", ""),
                        description=full_description or description,
                        salary_min=int(min_salary) if min_salary else None,
                        salary_max=int(max_salary) if max_salary else None,
                        site="Himalayas",
                        date_posted=date_val
                    )
                    job_posts.append(job)
                    
                except Exception as e:
                    self.logger.warning(f"Error parsing Himalayas job: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Himalayas scraping error: {e}")
            
        return job_posts

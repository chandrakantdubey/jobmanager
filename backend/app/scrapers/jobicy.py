
from typing import List, Optional
import urllib.parse
from app.scrapers.base import BaseScraper
from app.models.job import ScraperInput, JobPost

class JobicyScraper(BaseScraper):
    def __init__(self, proxies: Optional[List[str]] = None):
        super().__init__("Jobicy", proxies)
        self.base_url = "https://jobicy.com/api/v2/remote-jobs"

    def scrape(self, input_data: ScraperInput) -> List[JobPost]:
        job_posts = []
        
        # Jobicy API Params:
        # count: max 50 (or 100 per docs, but usually limited)
        # tag: search keywords
        # geo: region (optional)
        
        params = {
            "count": min(input_data.results_wanted, 50),
            "tag": input_data.search_term
        }
        
        if input_data.location and "remote" not in input_data.location.lower():
             params["geo"] = input_data.location
        
        try:
            response = self.safe_get(self.base_url, params=params)
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch Jobicy jobs: {response.status_code}")
                return []
                
            data = response.json()
            jobs = data.get("jobs", [])
            
            for item in jobs:
                try:
                    # Jobicy returns fields: jobTitle, companyName, jobDescription, jobSlug, pubDate, salaryMin, salaryMax
                    # Some sources say field casing might vary, we'll try standard camelCase from docs.
                    
                    title = item.get("jobTitle", "Unknown")
                    company = item.get("companyName", "Unknown")
                    url = item.get("url", "") or item.get("jobSlug", "") 
                    # If url is missing, check if jobSlug needs base url? Docs say 'url' field usually provides full link.
                    
                    description = item.get("jobDescription", "")
                    
                    min_salary = item.get("salaryMin")
                    max_salary = item.get("salaryMax")
                    
                    # Ensure numeric
                    try:
                        min_salary = int(float(min_salary)) if min_salary else None
                        max_salary = int(float(max_salary)) if max_salary else None
                    except:
                        min_salary = None
                        max_salary = None

                    # Parse date
                    date_val = item.get("pubDate", None)
                    if date_val and isinstance(date_val, str) and len(date_val) >= 10:
                        date_val = date_val[:10]

                    job = JobPost(
                        title=title,
                        company=company,
                        location="Remote", # Jobicy is remote-only
                        job_url=url,
                        description=description,
                        salary_min=min_salary,
                        salary_max=max_salary,
                        site="Jobicy",
                        date_posted=date_val
                    )
                    job_posts.append(job)
                    
                except Exception as e:
                    self.logger.warning(f"Error parsing Jobicy job: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Jobicy scraping error: {e}")
            
        return job_posts

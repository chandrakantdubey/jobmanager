
from typing import List, Optional
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper
from app.models.job import ScraperInput, JobPost

class PowerToFlyScraper(BaseScraper):
    def __init__(self):
        super().__init__("PowerToFly", None)
        self.base_url = "https://powertofly.com/jobs/"

    def scrape(self, input_data: ScraperInput) -> List[JobPost]:
        job_posts = []
        
        # params construction
        # keywords=python&location=Remote
        params = {
            "keywords": input_data.search_term,
            "location": input_data.location or "Remote"
        }
        
        # Experience mapping? 
        # The dump shows "min_experience=0&years_of_experience=0$5"
        # We can try to map but maybe just keywords/loc is enough for now.

        try:
            response = self.safe_get(self.base_url, params=params)
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch PowerToFly: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Cards are in buttons with class "job" inside .js-elem
            # But specific selector: button.job.box
            cards = soup.select("div.js-elem .job.box")
            
            self.logger.info(f"Found {len(cards)} jobs on PowerToFly")
            
            for card in cards:
                try:
                    title_tag = card.find("h5", class_="title")
                    title = title_tag.get_text(strip=True) if title_tag else "Unknown"
                    
                    company_tag = card.find("span", class_="company")
                    company = company_tag.get_text(strip=True) if company_tag else "Unknown"
                    
                    location_tag = card.find("span", class_="location")
                    location = "Remote"
                    if location_tag:
                         # There are nested spans sometimes, just get text
                         location = location_tag.get_text(" ", strip=True) # "Remote · United States"
                    
                    job_id = card.get("data-job-id")
                    if job_id:
                        job_url = f"https://powertofly.com/jobs/detail/{job_id}"
                    else:
                        # Fallback?
                        continue
                        
                    # Date is difficult in list view.
                    
                    job = JobPost(
                        title=title,
                        company=company,
                        location=location,
                        job_url=job_url,
                        description="",
                        salary_min=None,
                        salary_max=None,
                        site="PowerToFly",
                        date_posted=None
                    )
                    job_posts.append(job)
                    
                    if input_data.results_wanted and len(job_posts) >= input_data.results_wanted:
                        break
                        
                except Exception as e:
                    self.logger.warning(f"Error parsing PowerToFly card: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"PowerToFly scraping error: {e}")
            
        return job_posts

import random
import time
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

from app.scrapers.base import BaseScraper, ScraperError
from app.models.job import JobPost, ScraperInput, JobType

class BaytScraper(BaseScraper):
    def __init__(self, proxies: Optional[List[str]] = None):
        super().__init__("Bayt", proxies)
        self.base_url = "https://www.bayt.com"
        self.delay = 2
        self.band_delay = 3

    def scrape(self, input_data: ScraperInput) -> List[JobPost]:
        self.logger.info(f"Scraping Bayt for '{input_data.search_term}'")
        jobs = []
        page = 1
        results_wanted = input_data.results_wanted
        
        while len(jobs) < results_wanted:
            self.logger.debug(f"Fetching page {page}")
            try:
                # Bayt URL structure
                # https://www.bayt.com/en/international/jobs/{query}-jobs/?page={page}
                query = quote_plus(input_data.search_term).replace("+", "-")
                url = f"{self.base_url}/en/international/jobs/{query}-jobs/?page={page}"
                
                response = self.safe_get(url)
                if not response:
                    break
                
                new_jobs = self._parse_page(response.text)
                if not new_jobs:
                    self.logger.info("No jobs found on page, stopping.")
                    break
                    
                jobs.extend(new_jobs)
                
                if len(jobs) >= results_wanted:
                    break
                    
                page += 1
                time.sleep(random.uniform(self.delay, self.delay + self.band_delay))
            except ScraperError as e:
                self.logger.error(f"Page fetch failed: {e}")
                break
                
        return jobs[:results_wanted]

    def _parse_page(self, html: str) -> List[JobPost]:
        soup = BeautifulSoup(html, "html.parser")
        job_listings = soup.find_all("li", attrs={"data-js-job": ""})
        
        results = []
        for job_elem in job_listings:
            try:
                # Title
                title_tag = job_elem.find("h2")
                if not title_tag: continue
                title = title_tag.get_text(strip=True)
                
                # URL
                a_tag = title_tag.find("a")
                job_url = self.base_url + a_tag["href"].strip() if a_tag else ""
                
                # Company
                company = "Unknown"
                company_tag = job_elem.find("div", class_="t-nowrap p10l")
                if company_tag and company_tag.find("span"):
                    company = company_tag.find("span").get_text(strip=True)
                    
                # Location
                location = "Unknown"
                loc_tag = job_elem.find("div", class_="t-mute t-small")
                if loc_tag:
                    location = loc_tag.get_text(strip=True)

                if title and job_url:
                    post = JobPost(
                        title=title,
                        company=company,
                        job_url=job_url,
                        location=location,
                        site="Bayt"
                    )
                    results.append(post)
            except Exception as e:
                self.logger.warning(f"Error parsing job info: {e}")
                
        return results

import logging
import time
import random
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urlparse, urlunparse

from app.scrapers.base import BaseScraper, ScraperError
from app.models.job import JobPost, ScraperInput, JobType

class LinkedInScraper(BaseScraper):
    def __init__(self, proxies: Optional[List[str]] = None):
        super().__init__("LinkedIn", proxies)
        self.base_url = "https://www.linkedin.com"
        self.delay = 3
        self.band_delay = 4

    def scrape(self, input_data: ScraperInput) -> List[JobPost]:
        self.logger.info(f"Scraping LinkedIn for '{input_data.search_term}'")
        jobs = []
        start = 0
        results_wanted = input_data.results_wanted
        
        # Mapping job type
        f_JT = None
        if input_data.job_type:
            # Simple mapping for now, taking first one
            jt_map = {
                JobType.FULL_TIME: "F",
                JobType.PART_TIME: "P",
                JobType.CONTRACT: "C",
                JobType.TEMPORARY: "T",
                JobType.INTERNSHIP: "I",
                JobType.FREELANCE: "C"
            }
            # Assuming input_data.job_type is a list, take first
            if isinstance(input_data.job_type, list) and len(input_data.job_type) > 0:
                 f_JT = jt_map.get(input_data.job_type[0])

        while len(jobs) < results_wanted and start < 1000:
            self.logger.debug(f"Fetching start={start}")
            
            params = {
                "keywords": input_data.search_term,
                "location": input_data.location,
                "start": start,
                "f_WT": "2" if input_data.is_remote else None,
                "f_JT": f_JT
            }
            # Clean none params
            params = {k: v for k, v in params.items() if v is not None}
            
            try:
                url = f"{self.base_url}/jobs-guest/jobs/api/seeMoreJobPostings/search"
                response = self.safe_get(url, params=params)
                
                if response.status_code == 429:
                    self.logger.warning("LinkedIn: 429 Too Many Requests")
                    break
                    
                if not response.text:
                    self.logger.info("LinkedIn: Empty response, stopping.")
                    break
                    
                soup = BeautifulSoup(response.text, "html.parser")
                job_cards = soup.find_all("div", class_="base-search-card")
                
                if not job_cards:
                    self.logger.info("LinkedIn: No job cards found, stopping.")
                    break
                    
                for card in job_cards:
                    try:
                        job = self._process_card(card)
                        if job:
                            jobs.append(job)
                            if len(jobs) >= results_wanted:
                                break
                    except Exception as e:
                        self.logger.warning(f"Error processing card: {e}")
                        
                start += len(job_cards)
                time.sleep(random.uniform(self.delay, self.delay + self.band_delay))
                
            except ScraperError as e:
                self.logger.error(f"Page fetch error: {e}")
                break
                
        return jobs[:results_wanted]

    def _process_card(self, card) -> Optional[JobPost]:
        # Title
        title_tag = card.find("span", class_="sr-only")
        title = title_tag.get_text(strip=True) if title_tag else "N/A"
        
        # Company
        company_tag = card.find("h4", class_="base-search-card__subtitle")
        company = "Unknown"
        company_url = None
        if company_tag:
            a_tag = company_tag.find("a")
            if a_tag:
                company = a_tag.get_text(strip=True)
                href = a_tag.get("href")
                if href:
                    company_url = urlunparse(urlparse(href)._replace(query=""))
            else:
                company = company_tag.get_text(strip=True)

        # Location
        loc_tag = card.find("span", class_="job-search-card__location")
        location = loc_tag.get_text(strip=True) if loc_tag else "N/A"
        
        # URL & ID
        a_link = card.find("a", class_="base-card__full-link")
        if not a_link:
            return None
        job_url = a_link.get("href").split("?")[0]
        # ID is usually last part of URL path
        job_id = job_url.split("-")[-1]

        # Date Posted
        date_posted = None
        time_tag = card.find("time", class_="job-search-card__listdate")
        if time_tag and "datetime" in time_tag.attrs:
             # Basic string, could parse to date object
             # For now just keeping as is or ignoring specific date logic for simplicity
             pass

        return JobPost(
            id=f"li-{job_id}",
            title=title,
            company=company,
            job_url=job_url,
            location=location,
            site="LinkedIn",
            company_url=company_url
        )

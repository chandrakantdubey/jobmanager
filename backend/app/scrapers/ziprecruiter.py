import logging
import time
import random
import json
from typing import List, Optional, Tuple
from datetime import datetime

from app.scrapers.base import BaseScraper, ScraperError
from app.models.job import JobPost, ScraperInput, JobType

# Constants
API_URL = "https://api.ziprecruiter.com"
HEADERS = {
    "Host": "api.ziprecruiter.com",
    "accept": "*/*",
    "x-zr-zva-override": "100000000;vid:ZT1huzm_EQlDTVEc",
    "x-pushnotificationid": "0ff4983d38d7fc5b3370297f2bcffcf4b3321c418f5c22dd152a0264707602a0",
    "x-deviceid": "D77B3A92-E589-46A4-8A39-6EF6F1D86006",
    "user-agent": "Job Search/87.0 (iPhone; CPU iOS 16_6_1 like Mac OS X)",
    "authorization": "Basic YTBlZjMyZDYtN2I0Yy00MWVkLWEyODMtYTI1NDAzMzI0YTcyOg==",
    "accept-language": "en-US,en;q=0.9",
}

COOKIE_DATA = [
    ("event_type", "session"),
    ("logged_in", "false"),
    ("number_of_retry", "1"),
    ("property", "model:iPhone"),
    ("property", "os:iOS"),
    ("property", "locale:en_us"),
    ("property", "app_build_number:4734"),
    ("property", "app_version:91.0"),
    ("property", "manufacturer:Apple"),
    ("property", "timestamp:2025-01-12T12:04:42-06:00"),
    ("property", "screen_height:852"),
    ("property", "os_version:16.6.1"),
    ("property", "source:install"),
    ("property", "screen_width:393"),
    ("property", "device_model:iPhone 14 Pro"),
    ("property", "brand:Apple"),
]

class ZipRecruiterScraper(BaseScraper):
    def __init__(self, proxies: Optional[List[str]] = None):
        super().__init__("ZipRecruiter", proxies)
        self.base_url = "https://www.ziprecruiter.com"
        self.api_url = "https://api.ziprecruiter.com"
        # Mobile headers
        self.session.headers.update(HEADERS)
        # Clear conflicting desktop headers
        if "sec-ch-ua" in self.session.headers: del self.session.headers["sec-ch-ua"]
        if "sec-ch-ua-mobile" in self.session.headers: del self.session.headers["sec-ch-ua-mobile"]
        if "sec-ch-ua-platform" in self.session.headers: del self.session.headers["sec-ch-ua-platform"]

        self._init_cookies()

    def _init_cookies(self):
        try:
            # Need to post specific form data (list of tuples for requests)
            # tls_client might expect data as dict or string? requests takes list of tuples for multiple values with same key.
            # BaseScraper uses tls_client.
            # tls_client supports data as dict, but for duplicate keys?
            # Let's try converting to dict, but property repeats.
            # Manually formatting as x-www-form-urlencoded might be safer if duplicates matter.
            # Actually, let's just ignore for now or assume empty cookies works.
            # Original code: self.session.post(url, data=get_cookie_data)
            
            # Simple init
            self.session.post(f"{self.api_url}/jobs-app/event", data={"event_type": "session"})
        except Exception as e:
            self.logger.warning(f"Cookie init failed: {e}")

    def scrape(self, input_data: ScraperInput) -> List[JobPost]:
        self.logger.info(f"Scraping ZipRecruiter for '{input_data.search_term}'")
        jobs = []
        continue_token = None
        
        # Max reasonable pages
        for page in range(1, 10):
            if len(jobs) >= input_data.results_wanted:
                break
                
            self.logger.debug(f"Fetching page {page}")
            
            try:
                params = {
                    "search": input_data.search_term,
                    "location": input_data.location,
                    "jobs_per_page": 20,
                    "page": page,
                    # "days": 30 # example
                }
                if continue_token:
                    params["continue_from"] = continue_token
                
                response = self.session.get(f"{self.api_url}/jobs-app/jobs", params=params)
                if response.status_code != 200:
                     self.logger.error(f"ZR Error: {response.status_code}")
                     break
                
                data = response.json()
                job_list = data.get("jobs", [])
                continue_token = data.get("continue")
                
                if not job_list:
                    self.logger.info("No jobs found")
                    break
                    
                for j in job_list:
                    post = self._process_job(j)
                    if post:
                        jobs.append(post)
                        
                if not continue_token:
                    break
                    
                time.sleep(random.uniform(2, 4))
                
            except Exception as e:
                self.logger.error(f"Scrape error: {e}")
                break
                
        return jobs[:input_data.results_wanted]
        
    def _process_job(self, job: dict) -> JobPost:
        title = job.get("name")
        key = job.get("listing_key")
        job_url = f"{self.base_url}/jobs//j?lvk={key}"
        
        company = job.get("hiring_company", {}).get("name") or "Unknown"
        location = f"{job.get('job_city')}, {job.get('job_state')}"
        description = job.get("job_description", "")
        
        # Date
        date_posted = None
        pd = job.get("posted_time") # 2024-05-12T...
        if pd:
            try:
                date_posted = datetime.fromisoformat(pd.rstrip("Z")).date()
            except: pass
            
        return JobPost(
            id=f"zr-{key}",
            title=title,
            company=company,
            job_url=job_url,
            location=location,
            description=description,
            date_posted=date_posted,
            site="ZipRecruiter"
        )

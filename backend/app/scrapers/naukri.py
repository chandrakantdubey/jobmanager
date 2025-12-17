import logging
import json
import time
import random
from typing import List, Optional
from datetime import datetime

from app.scrapers.base import BaseScraper, ScraperError
from app.models.job import JobPost, ScraperInput, JobType

# Constants
API_URL = "https://www.naukri.com/jobapi/v3/search"
HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9",
    "appid": "109",
    "systemid": "109",
    "clientid": "d3skt0p",
    "content-type": "application/json",
    "origin": "https://www.naukri.com",
    "referer": "https://www.naukri.com/",
    "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}


class NaukriScraper(BaseScraper):
    def __init__(self, proxies: Optional[List[str]] = None):
        super().__init__("Naukri", proxies)
        self.base_url = "https://www.naukri.com"
        # Update headers
        self.session.headers.update(HEADERS)

    def scrape(self, input_data: ScraperInput) -> List[JobPost]:
        self.logger.info(f"Scraping Naukri for '{input_data.search_term}'")
        jobs = []
        
        # Max pages
        for page in range(1, 5):
            if len(jobs) >= input_data.results_wanted:
                break
                
            self.logger.debug(f"Fetching page {page}")
            
            try:
                params = {
                    "noOfResults": 20,
                    "urlType": "search_by_keyword",
                    "searchType": "adv",
                    "keyword": input_data.search_term,
                    "location": input_data.location,
                    "pageNo": page,
                    "seoKey": "job-search-api"
                }
                
                # Naukri often requires specific query params construction or standard GET
                # tls_client handle params automatically
                
                response = self.session.get(API_URL, params=params)
                
                if response.status_code != 200:
                    self.logger.error(f"Naukri Error: {response.status_code}")
                    # 429 or 403 blocks are common
                    break
                    
                data = response.json()
                
                if "jobDetails" not in data:
                    self.logger.warning("No jobDetails in response")
                    break
                    
                job_list = data["jobDetails"]
                
                if not job_list:
                    self.logger.info("No jobs found on page")
                    break
                    
                for j in job_list:
                    post = self._process_job(j)
                    if post:
                        jobs.append(post)
                
                time.sleep(random.uniform(2, 5))
                
            except Exception as e:
                self.logger.error(f"Scrape error: {e}")
                break
                
        return jobs[:input_data.results_wanted]
        
    def _process_job(self, job: dict) -> JobPost:
        try:
            title = job.get("title")
            job_id = job.get("jobId")
            company = job.get("companyName")
            
            # Location
            locs = job.get("placeholders", [])
            location = ", ".join([l.get("label") for l in locs]) if locs else "Unknown"
            
            # Description (usually short in list)
            desc = job.get("jobDescription", "")
            
            # URL
            # Usually https://www.naukri.com/job-listings-{slug}-{id}
            slug = job.get("jdURL") # actually full url often
            job_url = f"https://www.naukri.com{slug}" if slug and slug.startswith("/") else slug
            if not job_url:
                 job_url = f"https://www.naukri.com/job-listings-{job_id}"
            
            # Date
            date_posted = None
            date_str = job.get("createdDate") # millisecond timestamp sometimes?
            # Normally Naukri returns formatted date or relative time.
            # Let's keep it simple
            
            return JobPost(
                id=f"naukri-{job_id}",
                title=title,
                company=company,
                location=location,
                job_url=job_url,
                description=desc,
                site="Naukri",
                date_posted=None # Parsing timestamp logic skipped for brevity
            )
        except Exception as e:
            # self.logger.warning(f"Error parsing job: {e}")
            return None

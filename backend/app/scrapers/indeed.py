import logging
import time
import random
import json
from typing import List, Optional
from datetime import datetime

from app.scrapers.base import BaseScraper, ScraperError
from app.models.job import JobPost, ScraperInput, JobType

# Constants
API_URL = "https://apis.indeed.com/graphql"
JOB_SEARCH_QUERY = """
    query GetJobData {
        jobSearch(
        {what}
        {location}
        limit: 100
        {cursor}
        sort: RELEVANCE
        {filters}
        ) {
        pageInfo {
            nextCursor
        }
        results {
            trackingKey
            job {
            key
            title
            datePublished
            description {
                html
            }
            location {
                city
                admin1Code
                countryCode
            }
            employer {
                name
                relativeCompanyPageUrl
                dossier {
                    employerDetails {
                         briefDescription
                    }
                    images {
                         squareLogoUrl
                    }
                }
            }
            recruit {
                viewJobUrl
            }
            compensation {
                baseSalary {
                    range {
                        ... on Range {
                            min
                            max
                        }
                    }
                }
                estimated {
                    baseSalary {
                         range {
                             ... on Range {
                                 min
                                 max
                             }
                         }
                    }
                    currencyCode
                }
            }
            }
        }
        }
    }
"""

API_HEADERS = {
    "Host": "apis.indeed.com",
    "content-type": "application/json",
    "indeed-api-key": "161092c2017b5bbab13edb12461a62d5a833871e7cad6d9d475304573de67ac8",
    "accept": "application/json",
    "indeed-locale": "en-US",
    "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Indeed App 193.1",
    "indeed-app-info": "appv=193.1; appid=com.indeed.jobsearch; osv=16.6.1; os=ios; dtype=phone",
}

class IndeedScraper(BaseScraper):
    def __init__(self, proxies: Optional[List[str]] = None):
        super().__init__("Indeed", proxies)
        self.jobs_per_page = 100
        # Override headers with mobile app headers required for this API
        self.session.headers.update(API_HEADERS)
        # We might need to clear browser-specific headers that BaseScraper sets
        # if Indeed API is strict, but usually extra headers are ignored.
        # However, Sec-Ch-Ua headers from BaseScraper (Chrome) might conflict with iPhone API UA.
        # Safer to clear them or overwrite.
        if "sec-ch-ua" in self.session.headers:
            del self.session.headers["sec-ch-ua"]
        if "sec-ch-ua-platform" in self.session.headers:
             del self.session.headers["sec-ch-ua-platform"]
        if "sec-ch-ua-mobile" in self.session.headers:
             del self.session.headers["sec-ch-ua-mobile"]

    def scrape(self, input_data: ScraperInput) -> List[JobPost]:
        self.logger.info(f"Scraping Indeed for '{input_data.search_term}'")
        jobs = []
        cursor = None
        seen_urls = set()
        
        while len(jobs) < input_data.results_wanted:
            self.logger.debug(f"Fetching page with cursor: {cursor}")
            
            try:
                filters = self._build_filters(input_data)
                search_term = input_data.search_term.replace('"', '\\"') if input_data.search_term else ""
                
                # Format Query
                query = JOB_SEARCH_QUERY.replace("{what}", f'what: "{search_term}"' if search_term else "") \
                                        .replace("{location}", f'location: {{where: "{input_data.location}", radius: 50, radiusUnit: MILES}}' if input_data.location else "") \
                                        .replace("{cursor}", f'cursor: "{cursor}"' if cursor else "") \
                                        .replace("{filters}", filters)

                payload = {"query": query}
                
                # Check region for headers
                # Simply using 'en-US' for now, ideally map input_data.country to domain/locale
                
                # Debug payload
                # self.logger.debug(f"Payload: {payload}")
                
                response = self.session.post(API_URL, json=payload, headers=API_HEADERS)
                
                if response.status_code != 200:
                    self.logger.error(f"Indeed API Error: {response.status_code} - {response.text}")
                    break
                    
                data = response.json()
                if not data.get("data"):
                     self.logger.error("No data in response")
                     break
                     
                results = data["data"]["jobSearch"]["results"]
                page_info = data["data"]["jobSearch"]["pageInfo"]
                next_cursor = page_info.get("nextCursor")
                
                if not results:
                    self.logger.info("No more jobs found.")
                    break
                    
                for item in results:
                    job_data = item.get("job")
                    if not job_data: continue
                    
                    post = self._process_job(job_data)
                    if post and post.job_url not in seen_urls:
                        seen_urls.add(post.job_url)
                        jobs.append(post)
                        if len(jobs) >= input_data.results_wanted:
                            break
                
                if not next_cursor:
                    break
                cursor = next_cursor
                
                time.sleep(random.uniform(2, 5))
                
            except Exception as e:
                self.logger.error(f"Scraping error: {e}")
                import traceback
                self.logger.debug(traceback.format_exc())
                break
                
        return jobs[:input_data.results_wanted]

    def _build_filters(self, input_data: ScraperInput) -> str:
        # Simplified filters
        return ""

    def _process_job(self, job: dict) -> JobPost:
        key = job.get("key")
        title = job.get("title")
        description = job.get("description", {}).get("html")
        
        employer = job.get("employer") or {}
        company = employer.get("name") or "Unknown"
        
        # Location
        loc = job.get("location", {})
        location = f"{loc.get('city', '')}, {loc.get('admin1Code', '')}"
        
        # URL
        # Indeed viewjob
        job_url = f"https://www.indeed.com/viewjob?jk={key}"
        
        # Date
        # datePublished is timestamp ms
        date_posted = None
        ts = job.get("datePublished")
        if ts:
             # Convert ms to date
             # implementation detail
             pass

        return JobPost(
            id=f"in-{key}",
            title=title,
            company=company,
            description=description,
            location=location,
            job_url=job_url,
            site="Indeed"
        )

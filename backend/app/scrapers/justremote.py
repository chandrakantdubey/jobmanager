
import json
import re
import math
from bs4 import BeautifulSoup
from app.models.job import JobPost, ScraperInput
from app.scrapers.base import BaseScraper
from datetime import datetime

class JustRemoteScraper(BaseScraper):
    def __init__(self):
        super().__init__("JustRemote")
        self.base_url = "https://justremote.co/remote-jobs"

    def scrape(self, scraper_input: ScraperInput) -> list[JobPost]:
        self.logger.info(f"Scraping JustRemote for '{scraper_input.search_term}'...")
        job_posts = []

        try:
            response = self.safe_get(self.base_url)
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch JustRemote: {response.status_code}")
                return []
            
            # Extract JSON state
            # <script>window.__PRELOADED_STATE__ = {...}</script>
            if "window.__PRELOADED_STATE__ =" in response.text:
                part = response.text.split("window.__PRELOADED_STATE__ =", 1)[1]
                # Usually ends with </script>
                json_part = part.split("</script>", 1)[0].strip()
                # Remove trailing semicolon if present
                if json_part.endswith(";"):
                    json_part = json_part[:-1]
                
                try:
                    data = json.loads(json_part)
                except json.JSONDecodeError:
                    # Fallback: maybe it didn't end with </script> or has slightly different format
                    # Try finding the last '}'
                    last_brace = json_part.rfind("}")
                    if last_brace != -1:
                         json_part = json_part[:last_brace+1]
                         data = json.loads(json_part)
                    else:
                         self.logger.error("Could not parse JustRemote JSON")
                         return []
            else:
                self.logger.warning("Could not find __PRELOADED_STATE__ in JustRemote HTML")
                return []

            # jobsState -> entity -> all
            jobs_all = data.get("jobsState", {}).get("entity", {}).get("all", [])
            self.logger.info(f"JustRemote raw jobs found: {len(jobs_all)}")
            
            search_term_lower = scraper_input.search_term.lower() if scraper_input.search_term else None
            
            for item in jobs_all:
                title = item.get("title", "Unknown")
                company = item.get("company_name", "Unknown")
                
                # Filter by search term
                if search_term_lower:
                    text_blob = f"{title} {company} {item.get('category', '')}".lower()
                    if search_term_lower not in text_blob:
                        continue
                
                href = item.get("href")
                job_url = f"https://justremote.co/{href}" if href else ""
                
                # Location handling
                # They have 'remote_type' and 'location_restrictions'
                remote_type = item.get("remote_type", "Remote")
                loc_restrictions = item.get("location_restrictions", [])
                
                location = remote_type
                if loc_restrictions:
                    location += f" ({', '.join(loc_restrictions)})"
                
                # Clean up date? "16 Dec" -> we could parse this relative to current year/month
                # For now, just store as string or None
                date_str = item.get("date")
                
                job = JobPost(
                    title=title,
                    company=company,
                    location=location,
                    job_url=job_url,
                    description="", # Description is on detail page
                    salary_min=None,
                    salary_max=None,
                    site="JustRemote",
                    date_posted=date_str
                )
                job_posts.append(job)
                
                if scraper_input.results_wanted and len(job_posts) >= scraper_input.results_wanted:
                    break
            
            self.logger.info(f"Found {len(job_posts)} jobs from JustRemote")
            return job_posts

        except Exception as e:
            self.logger.error(f"Error scraping JustRemote: {e}")
            return []

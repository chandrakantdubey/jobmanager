import json
from datetime import datetime, date
from typing import List, Optional
import subprocess

from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper
from app.models.job import JobPost, ScraperInput, JobType

class TruelancerScraper(BaseScraper):
    def __init__(self):
        super().__init__("truelancer")

    def scrape(self, input_data: ScraperInput) -> List[JobPost]:
        self.logger.info(f"Scraping Truelancer for: {input_data.search_term}")
        
        base_url = "https://www.truelancer.com/freelance-jobs"
        if input_data.search_term:
            url = f"{base_url}?q={input_data.search_term}"
        else:
            url = base_url

        self.logger.debug(f"Fetching URL: {url}")
        
        # Use simple requests first, if blocked then subprocess curl
        # Based on previous experience, curl with specific headers works well for static scraping if user agent is right
        
        headers = [
            "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "-H", "Accept-Language: en-US,en;q=0.9",
        ]
        
        try:
            # Using curl for robustness against some TLS/header checks
            cmd = ["curl", "-s", "-L"] + headers + [url]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            html_content = result.stdout
            
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Find the Next.js data script
            script_tag = soup.find("script", {"id": "__NEXT_DATA__"})
            if not script_tag:
                self.logger.error("Could not find __NEXT_DATA__ script tag")
                # Try fallback to standard HTML parsing if JSON missing?
                # Actually if this key tag is missing, site structure probably changed or we got blocked page
                # Let's save debug
                with open("truelancer_error.html", "w") as f:
                    f.write(html_content)
                return []

            data = json.loads(script_tag.string)
            
            # Navigate nicely to the projects list
            # props -> pageProps -> data -> projects -> data (list)
            try:
                page_props = data.get("props", {}).get("pageProps", {})
                
                projects = []
                # Check for "data" -> "projects" structure (Search results)
                if "data" in page_props and "projects" in page_props["data"]:
                     projects = page_props["data"]["projects"].get("data", [])
                
                # Check for direct "projects" (Landing page sometimes)
                elif "projects" in page_props:
                    projects = page_props["projects"].get("data", [])
                    
            except AttributeError:
                projects = []
            
            job_posts = []
            for project in projects:
                try:
                    title = project.get("title")
                    link = project.get("link")
                    if not link.startswith("http"):
                        link = f"https://www.truelancer.com{link}"
                    
                    # Budget/Compensation
                    budget = project.get("budget")
                    currency = project.get("currency")
                    compensation = None
                    if budget:
                        compensation = f"{currency} {budget}"
                        job_type_name = project.get("jobTypeName", "")
                        if "Hour" in job_type_name:
                            compensation += "/hr"
                        elif "Fixed" in job_type_name:
                            compensation += " (Fixed)"

                    # Date posted
                    created_at_str = project.get("created_at") # "2025-12-16 21:56:54"
                    date_posted = None
                    if created_at_str:
                        try:
                            date_posted = datetime.strptime(created_at_str, "%Y-%m-%d %H:%M:%S").date()
                        except ValueError:
                            pass
                            
                    # Description
                    description = project.get("description", "")
                    
                    # Check hours_old filter
                    if input_data.hours_old and date_posted:
                        job_dt = datetime.combine(date_posted, datetime.min.time())
                        if (datetime.now() - job_dt).total_seconds() / 3600 > input_data.hours_old:
                            continue

                    job = JobPost(
                        title=title,
                        company="Truelancer Client", # Marketplace, no specific company usually visible in list
                        job_url=link,
                        location="Remote", # Truelancer is mostly remote/freelance
                        date_posted=date_posted,
                        compensation=compensation,
                        description=description,
                        job_type=[JobType.CONTRACT],
                        is_remote=True,
                        site="truelancer"
                    )
                    job_posts.append(job)
                except Exception as e:
                    self.logger.warning(f"Error parsing individual project: {e}")
                    continue

            self.logger.info(f"Found {len(job_posts)} jobs on Truelancer")
            return job_posts
            
        except Exception as e:
            self.logger.error(f"Error scraping Truelancer: {e}")
            return []

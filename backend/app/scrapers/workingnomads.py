
import requests
import logging
from app.models.job import JobPost, ScraperInput
from app.scrapers.base import BaseScraper

class WorkingNomadsScraper(BaseScraper):
    def __init__(self):
        super().__init__("WorkingNomads")
        self.api_url = "https://www.workingnomads.com/api/exposed_jobs/"

    def scrape(self, scraper_input: ScraperInput) -> list[JobPost]:
        self.logger.info(f"Scraping Working Nomads for '{scraper_input.search_term}'...")
        job_posts = []

        try:
            # The API returns ALL jobs (large JSON). We might need to filter client-side.
            # To be polite, we cache or just fetch once per run if possible, but for now standard fetch.
            response = self.safe_get(self.api_url)
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch WorkingNomads API: {response.status_code}")
                return []

            jobs_data = response.json()
            
            # Filter
            search_term_lower = scraper_input.search_term.lower() if scraper_input.search_term else None
            
            # The API doesn't seem to have paginated search? It dumps everything.
            # We filter locally.
            
            for item in jobs_data:
                title = item.get("title", "Unknown")
                
                # Basic filtering
                if search_term_lower and search_term_lower not in title.lower():
                    # Also check category or keywords if available
                    category = item.get("category_name", "").lower()
                    tags = item.get("tags", "")
                    if search_term_lower not in category and search_term_lower not in str(tags).lower():
                         continue

                company = item.get("company_name", "Unknown")
                location = item.get("location", "Remote") or "Remote"
                
                # They provide a direct URL usually
                link = item.get("url")
                if not link:
                     # sometimes "slug"
                     slug = item.get("slug")
                     if slug:
                         link = f"https://www.workingnomads.com/job/{slug}"
                
                pub_date = item.get("pub_date") # Timestamp or string
                if pub_date and isinstance(pub_date, str) and "T" in pub_date:
                    pub_date = pub_date.split("T")[0]
                
                description = item.get("description", "")

                job = JobPost(
                    title=title,
                    company=company,
                    location=location,
                    job_url=link,
                    description=description,
                    salary_min=None,
                    salary_max=None,
                    site="WorkingNomads",
                    date_posted=pub_date
                )
                job_posts.append(job)
                
                if scraper_input.results_wanted and len(job_posts) >= scraper_input.results_wanted:
                    break
            
            self.logger.info(f"Found {len(job_posts)} jobs from Working Nomads")
            return job_posts

        except Exception as e:
            self.logger.error(f"Error scraping Working Nomads: {e}")
            return []

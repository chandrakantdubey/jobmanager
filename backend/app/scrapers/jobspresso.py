
import urllib.parse
from typing import List, Optional
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper
from app.models.job import ScraperInput, JobPost

class JobspressoScraper(BaseScraper):
    def __init__(self, proxies: Optional[List[str]] = None):
        super().__init__("Jobspresso", proxies)
        self.base_url = "https://jobspresso.co/remote-work/"

    def scrape(self, input_data: ScraperInput) -> List[JobPost]:
        job_posts = []
        
        # HTML Scraping of browsing page
        # WP Job Manager typically uses params: ?search_keywords=...&search_location=...
        
        params = {
            "search_keywords": input_data.search_term,
            "search_location": input_data.location if input_data.location else "Remote"
        }
        
        try:
            response = self.safe_get(self.base_url, params=params)
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch Jobspresso HTML: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Selectors for WP Job Manager
            # List: ul.job_listings
            # Item: li.job_listing (but ignoring 'load_more' or similar)
            
            listings = soup.find_all("li", class_="job_listing")
            
            print(f"DEBUG: Jobspresso HTML items found: {len(listings)}")
            
            for item in listings:
                try:
                    # Title usually in h3 or an 'a' tag with class 'job_listing-clickbox' ??
                    # Actually standard structure:
                    # <div class="job_listing-about">
                    #   <div class="job_listing-position__title">...</div>
                    #   <div class="job_listing-company">...</div>
                    # </div>
                    
                    # Or simple:
                    # <a href="...">
                    #   <div class="position"><h3>Title</h3></div>
                    # </a>
                    
                    # Let's inspect generic structure
                    title_tag = item.find("h3")
                    if not title_tag: continue
                    title = title_tag.get_text(strip=True)
                    
                    link_tag = item.find("a", href=True)
                    job_url = link_tag["href"] if link_tag else ""
                    
                    company_tag = item.find("div", class_="job_listing-company")
                    # Sometimes company name is just text inside this or img alt
                    if company_tag:
                         company = company_tag.get_text(strip=True)
                    else:
                         # Try finding 'company' strong tag
                         company = "Unknown"
                         
                    location = "Remote" # It's a remote board
                    
                    # Description is generic on list page, usually hidden or just meta
                    description = ""
                    
                    # Date
                    date_tag = item.find("date")
                    date_val = None
                    if date_tag:
                        date_str = date_tag.get_text(strip=True)
                        # Parsing "Posted 2 days ago" is hard without logic, skipping for now
                    
                    job = JobPost(
                        title=title,
                        company=company,
                        location=location,
                        job_url=job_url,
                        description=description,
                        salary_min=None,
                        salary_max=None,
                        site="Jobspresso",
                        date_posted=None
                    )
                    job_posts.append(job)
                    
                except Exception as e:
                    self.logger.warning(f"Error parsing Jobspresso HTML item: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Jobspresso scraping error: {e}")
            
        return job_posts

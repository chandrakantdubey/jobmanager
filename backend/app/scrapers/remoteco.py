
import urllib.parse
from typing import List, Optional
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper
from app.models.job import ScraperInput, JobPost

class RemoteCoScraper(BaseScraper):
    def __init__(self, proxies: Optional[List[str]] = None):
        super().__init__("Remote.co", proxies)
        self.base_url = "https://remote.co/remote-jobs/search/"

    def scrape(self, input_data: ScraperInput) -> List[JobPost]:
        job_posts = []
        
        # Remote.co Search URL: https://remote.co/remote-jobs/search/?search_keywords=python
        
        params = {
            "search_keywords": input_data.search_term
        }
        
        try:
            # Handle potential 308 redirects (trailing slash or https upgrades)
            response = self.safe_get(self.base_url, params=params, allow_redirects=True)
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch Remote.co: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Next.js / Styled Components structure
            # Container has data-index attribute
            cards = soup.find_all("div", attrs={"data-index": True})
            print(f"DEBUG: Found {len(cards)} cards via data-index")
            
            for card in cards:
                try:
                    # Link & Title
                    # <a href="/job-details/..." ...>
                    link_tag = card.find("a", href=lambda h: h and "/job-details/" in h)
                    if not link_tag: continue
                    
                    href = link_tag["href"]
                    job_url = "https://remote.co" + href if href.startswith("/") else href
                    
                    # Title is in the last span inside the link usually
                    # Structure: <span>New!</span><span>Today</span><span>Title</span>
                    # But safest to get text of the span that is NOT "New!" or "Today"
                    spans = link_tag.find_all("span")
                    title = "Unknown"
                    for s in spans:
                        txt = s.get_text(strip=True)
                        if txt not in ["New!", "Today", "Yesterday"] and "New" not in txt:
                            title = txt
                            # If title is still empty or looks like a date, keep looking? 
                            # usually the title is the longest string or last one.
                    
                    # If traversal failed, just get full text and clean up
                    if title == "Unknown":
                        title = link_tag.get_text(strip=True).replace("New!", "").replace("Today", "").strip()

                    # Filter by search term if provided
                    if input_data.search_term:
                        term = input_data.search_term.lower()
                        if term not in title.lower():
                            continue

                    # Company - seems missing in list view for this new layout? 
                    # We will mark as "See Details" or "Unknown"
                    company = "Remote.co Listing"

                    # Location
                    # Look for fa-location-dot
                    # <i class="... fa-location-dot ..."></i> <span ...>Remote, US National</span>
                    location = "Remote"
                    loc_icon = card.find("i", class_=lambda c: c and "fa-location-dot" in c)
                    if loc_icon:
                        loc_span = loc_icon.find_next("span")
                        if loc_span:
                            location = loc_span.get_text(strip=True)

                    job = JobPost(
                        title=title,
                        company=company,
                        location=location,
                        job_url=job_url,
                        description="",
                        salary_min=None,
                        salary_max=None,
                        site="Remote.co",
                        date_posted=None
                    )
                    job_posts.append(job)
                    
                except Exception as e:
                    self.logger.warning(f"Error parsing Remote.co card: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Remote.co scraping error: {e}")
            
        return job_posts

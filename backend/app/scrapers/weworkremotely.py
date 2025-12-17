
from typing import List, Optional
import urllib.parse
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper
from app.models.job import ScraperInput, JobPost

class WeWorkRemotelyScraper(BaseScraper):
    def __init__(self, proxies: Optional[List[str]] = None):
        super().__init__("WeWorkRemotely", proxies)
        self.base_url = "https://weworkremotely.com/remote-jobs.rss"

    def scrape(self, input_data: ScraperInput) -> List[JobPost]:
        job_posts = []
        
        # RSS Feed doesn't support query params for search in the main feed usually.
        # WWR has category specific feeds, but we'll use the main one and filter locally
        # or just return recent jobs if the user query is generic.
        # However, we can TRY to fetch category specific feeds if we mapped them, but for now
        # the main feed is the safest "Reliable" start.
        
        try:
            response = self.safe_get(self.base_url)
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch WWR feed: {response.status_code}")
                return []
            
            # WWR RSS is XML.
            soup = BeautifulSoup(response.content, "xml")
            items = soup.find_all("item")
            
            search_term = input_data.search_term.lower()
            
            for item in items:
                try:
                    title_tag = item.find("title")
                    title = title_tag.get_text(strip=True) if title_tag else "Unknown"
                    
                    # WWR titles are often "Company: Job Title" or "Job Title"
                    # We can leave as is.
                    
                    link_tag = item.find("link")
                    link = link_tag.get_text(strip=True) if link_tag else ""
                    
                    desc_tag = item.find("description")
                    description = desc_tag.get_text(strip=True) if desc_tag else ""
                    
                    pub_date_tag = item.find("pubDate")
                    pub_date = pub_date_tag.get_text(strip=True) if pub_date_tag else None
                    
                    # Simple client-side filtering
                    if search_term not in title.lower() and search_term not in description.lower():
                        continue

                    # Parse date - usually RFC 822 e.g., "Tue, 17 Dec 2024 08:00:00 +0000"
                    # We can try to parse it or just store string if model allowed, but model wants date.
                    # We'll use a simple parser or dateutil if available. 
                    # app/models/job.py expects 'date' object or ISO string.
                    # We will try to parse with dateutil.parser if installed, otherwise leave None or try raw.
                    # Given previous steps, I'll attempt basic parsing or just use None if risky.
                    # Actually, let's try to import dateutil. If not, we skip date.
                    
                    date_obj = None
                    try:
                        from dateutil import parser
                        date_obj = parser.parse(pub_date).date()
                    except ImportError:
                        pass # Should catch this if not installed
                    except:
                        pass

                    job = JobPost(
                        title=title,
                        company="Unknown", # RSS often puts company in title "Company: Role"
                        location="Remote",
                        job_url=link,
                        description=description,
                        salary_min=None,
                        salary_max=None,
                        site="We Work Remotely",
                        date_posted=date_obj
                    )
                    
                    # Improve Company parsing: "Company Name: Job Title"
                    if ":" in title:
                        parts = title.split(":")
                        if len(parts) >= 2:
                            job.company = parts[0].strip()
                            job.title = ":".join(parts[1:]).strip()

                    job_posts.append(job)
                    
                except Exception as e:
                    self.logger.warning(f"Error parsing WWR item: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"WWR scraping error: {e}")
            
        return job_posts

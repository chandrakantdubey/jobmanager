from typing import List, Optional
import urllib.parse
from app.scrapers.base import BaseScraper
from app.models.job import ScraperInput, JobPost

class SkipTheDriveScraper(BaseScraper):
    def __init__(self, proxies: Optional[List[str]] = None):
        super().__init__("SkipTheDrive", proxies)
        self.base_url = "https://www.skipthedrive.com/jobs"

    def scrape(self, input_data: ScraperInput) -> List[JobPost]:
        job_posts = []
        
        # SkipTheDrive is a job board aggregator for remote jobs
        # Uses RSS feed approach
        rss_url = "https://www.skipthedrive.com/feed/"
        
        try:
            import feedparser
            
            feed = feedparser.parse(rss_url)
            
            for entry in feed.entries[:input_data.results_wanted]:
                try:
                    # Filter by search term in title/summary
                    if input_data.search_term.lower() in entry.title.lower() or \
                       (hasattr(entry, 'summary') and input_data.search_term.lower() in entry.summary.lower()):
                        
                        job = JobPost(
                            title=entry.title,
                            company="Various",  # SkipTheDrive aggregates, may not have specific company
                            location="Remote",
                            job_url=entry.link,
                            description=entry.summary if hasattr(entry, 'summary') else "",
                            site="SkipTheDrive",
                            date_posted=entry.published[:10] if hasattr(entry, 'published') else None
                        )
                        job_posts.append(job)
                        
                except Exception as e:
                    self.logger.warning(f"Error parsing SkipTheDrive job: {e}")
                    continue
                    
        except ImportError:
            self.logger.error("feedparser not installed. Install with: pip install feedparser")
        except Exception as e:
            self.logger.error(f"SkipTheDrive scraping error: {e}")
            
        return job_posts


import urllib.parse
from typing import List, Optional
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper
from app.models.job import ScraperInput, JobPost

class TalentScraper(BaseScraper):
    def __init__(self, proxies: Optional[List[str]] = None):
        super().__init__("Talent.com", proxies)
        self.base_url = "https://www.talent.com/jobs"

    def scrape(self, input_data: ScraperInput) -> List[JobPost]:
        job_posts = []
        
        # Talent.com pagination: likely 'p' or 'page'. Standard is often 'page' or just infinite scroll structure.
        # Research suggested 'page'.
        # We will use 'k' for keyword, 'l' for location.
        
        params = {
            "k": input_data.search_term,
            "l": input_data.location,
            "page": (input_data.offset // 10) + 1 # Assuming ~10-15 per page, map offset roughly
        }
        
        try:
            response = self.safe_get(self.base_url, params=params)
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch Talent.com: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Selector identified: section[data-testid^="jobcard-container"]
            cards = soup.find_all("section", attrs={"data-testid": lambda x: x and x.startswith("jobcard-container")})
            
            for card in cards:
                try:
                    # Title is in h2 in the card
                    title_tag = card.find("h2")
                    title = title_tag.get_text(strip=True) if title_tag else "Unknown"
                    
                    # Link
                    # There is usually a "Show more" link or the whole card might be wrapped or have a distinct link.
                    # We saw <a href="/view?id=...">Show more</a>
                    link_tag = card.find("a", href=lambda x: x and "/view?id=" in x)
                    if link_tag:
                        job_url = "https://www.talent.com" + link_tag["href"] if link_tag["href"].startswith("/") else link_tag["href"]
                    else:
                        job_url = ""
                        
                    # Company & Location
                    # They appear as spans after the h2.
                    # <div data-testid="JobCardContainer">
                    #   <h2>...</h2>
                    #   <span>Company</span>
                    #   <span>Location</span>
                    # </div>
                    
                    container = card.find("div", attrs={"data-testid": "JobCardContainer"})
                    company = "Unknown"
                    location = "Unknown"
                    
                    if container:
                        spans = container.find_all("span", recursive=False)
                        # The layout might vary but usually 1st span is Company, 2nd is Location
                        if len(spans) >= 1:
                            company = spans[0].get_text(strip=True)
                        if len(spans) >= 2:
                            location = spans[1].get_text(strip=True)
                    
                    description = ""
                    # Description snippet usually in a span before the link or separate div?
                    # The dump showed: <span class="...">...snippet... <a ...>Show more</a></span>
                    # It seems complex to pinpoint exact span without class, but we can try capturing text of card relative to title.
                    # For now, "Unknown" descriptions are acceptable if hard to parse, or we try to find the 'jiOgIp' style span if stable.
                    # Let's try to just get all text from the card that isn't title/company/loc.
                    
                    # Parsing Salary: Sometimes in a span with "$".
                    salary_min = None
                    salary_max = None
                    
                    job = JobPost(
                        title=title,
                        company=company,
                        location=location,
                        job_url=job_url,
                        description=description,
                        salary_min=salary_min,
                        salary_max=salary_max,
                        site="Talent.com",
                        date_posted=None 
                    )
                    job_posts.append(job)
                    
                except Exception as e:
                    self.logger.warning(f"Error parsing Talent.com card: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Talent.com scraping error: {e}")
            
        return job_posts

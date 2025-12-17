
import urllib.parse
from typing import List, Optional
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper
from app.models.job import ScraperInput, JobPost

class JoraScraper(BaseScraper):
    def __init__(self, proxies: Optional[List[str]] = None):
        super().__init__("Jora", proxies)
        self.base_url = "https://us.jora.com/job/search"

    def scrape(self, input_data: ScraperInput) -> List[JobPost]:
        job_posts = []
        
        # Jora Domains
        domains = {
            "australia": "https://au.jora.com",
            # "india": "https://in.jora.com", # Discontinued
            # "usa": "https://us.jora.com",   # Discontinued
            # "uk": "https://uk.jora.com",    # Discontinued
            "new zealand": "https://nz.jora.com",
            "singapore": "https://sg.jobsdb.com", # Redirects to JobsDB but theoretically Jora SG was sg.jora.com
            "hong kong": "https://hk.jora.com"
        }
        
        country = input_data.country.lower() if input_data.country else "australia"
        if country not in domains:
            self.logger.warning(f"Jora is likely unavailable or not configured for country: {country}. defaulting to skip.")
            return []
            
        base_url = domains[country] + "/j" if "jobsdb" not in domains[country] else domains[country] # Handle JobsDB edge case if needed, but for now stick to Jora domains
        
        # Jora pagination
        params = {
            "q": input_data.search_term,
            "l": input_data.location,
            "p": (input_data.offset // 10) + 1
        }
        
        try:
            response = self.safe_get(base_url, params=params, allow_redirects=True)
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch Jora: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Identify job cards
            # Usually div with class 'job-card' or 'result'
            # Let's try standard 'result' or inspect typical Jora structure
            # Typical Jora: <div class="job-card"> or <li class="result">
            
            cards = soup.find_all("div", class_="job-card")
            if not cards:
                cards = soup.find_all("li", class_="result")
            
            if not cards:
                self.logger.warning("No Jora cards found. Dumping HTML.")
                with open("jora_dump.html", "w") as f:
                    f.write(soup.prettify())
                
            for card in cards:
                try:
                    title_tag = card.find("h3", class_="job-title") or card.find("a", class_="job-link")
                    title = title_tag.get_text(strip=True) if title_tag else "Unknown"
                    
                    link_tag = card.find("a", class_="job-link")
                    if not link_tag and title_tag and title_tag.name == 'a':
                        link_tag = title_tag
                    
                    job_url = "https://us.jora.com" + link_tag["href"] if link_tag and link_tag.get("href") else ""
                    
                    company_tag = card.find("span", class_="company")
                    company = company_tag.get_text(strip=True) if company_tag else "Unknown"
                    
                    location_tag = card.find("span", class_="location")
                    location = location_tag.get_text(strip=True) if location_tag else "Unknown"
                    
                    description_tag = card.find("div", class_="summary")
                    description = description_tag.get_text(strip=True) if description_tag else ""
                    
                    date_tag = card.find("span", class_="date")
                    # Date parsing logic could be added here similar to others
                    
                    job = JobPost(
                        title=title,
                        company=company,
                        location=location,
                        job_url=job_url,
                        description=description,
                        salary_min=None,
                        salary_max=None,
                        site="Jora",
                        date_posted=None
                    )
                    job_posts.append(job)
                    
                except Exception as e:
                    self.logger.warning(f"Error parsing Jora card: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Jora scraping error: {e}")
            
        return job_posts

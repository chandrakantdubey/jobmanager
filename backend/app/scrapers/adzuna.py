
from typing import List, Optional
import urllib.parse
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper
from app.models.job import ScraperInput, JobPost

class AdzunaScraper(BaseScraper):
    def __init__(self, proxies: Optional[List[str]] = None):
        super().__init__("Adzuna", proxies)
        self.country_domains = {
            "usa": "www.adzuna.com",
            "uk": "www.adzuna.co.uk",
            "india": "www.adzuna.in",
            "canada": "www.adzuna.ca",
            "australia": "www.adzuna.com.au",
            "germany": "www.adzuna.de",
            "france": "www.adzuna.fr",
            "italy": "www.adzuna.it",
            "netherlands": "www.adzuna.nl",
            "poland": "www.adzuna.pl",
            "russia": "www.adzuna.ru",
            "brazil": "www.adzuna.com.br",
            "south_africa": "www.adzuna.co.za",
            "spain": "www.adzuna.es",
            "austria": "www.adzuna.at"
        }

    def scrape(self, input_data: ScraperInput) -> List[JobPost]:
        job_posts = []
        domain = self.country_domains.get(input_data.country.lower(), "www.adzuna.com")
        
        # Calculate start page
        # Adzuna uses page numbers 1, 2, 3...
        # We can map offset to page number approx (limit is usually 10-20 per page)
        # Using 10 results per page for safe calculation
        current_page = (input_data.offset // 20) + 1  
        
        base_url = f"https://{domain}/search"
        params = {
            "q": input_data.search_term,
            "w": input_data.location,
            "page": current_page
        }
        
        if input_data.min_experience:
             # Adzuna doesn't strictly have experience param in public url 
             # but we can try adding keywords or just rely on post-filtering if needed.
             # However, for ScraperInput compliance we accept it.
             pass

        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        
        try:
            response = self.safe_get(url)
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch {url}: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Find job cards
            cards = soup.find_all("article", attrs={"data-aid": True})
            
            for card in cards:
                try:
                    title_tag = card.find("h2").find("a")
                    title = title_tag.get_text(strip=True)
                    link = title_tag["href"]
                    
                    # Fix relative link
                    if not link.startswith("http"):
                        link = f"https://{domain}{link}"
                        
                    company_tag = card.find("div", class_="ui-company")
                    company = company_tag.get_text(strip=True) if company_tag else "Unknown"
                    
                    location_tag = card.find("div", class_="ui-location")
                    location = location_tag.get_text(strip=True) if location_tag else input_data.location
                    
                    salary_tag = card.find("div", class_="ui-salary")
                    salary = salary_tag.get_text(strip=True) if salary_tag else None
                    
                    snippet_tag = card.find("span", class_="max-snippet-height")
                    description = snippet_tag.get_text(strip=True) if snippet_tag else ""
                    
                    # Parse salary
                    salary_min = None
                    salary_max = None
                    if salary:
                        import re
                        # simple extraction of numbers
                        nums = re.findall(r'[\d,]+(?:[kK])?', salary.replace("$", "").replace("£", "").replace("€", ""))
                        clean_nums = []
                        for n in nums:
                            n = n.replace(",", "")
                            mult = 1
                            if "k" in n.lower():
                                n = n.lower().replace("k", "")
                                mult = 1000
                            try:
                                val = int(float(n) * mult)
                                clean_nums.append(val)
                            except: pass
                        
                        if clean_nums:
                            salary_min = min(clean_nums)
                            salary_max = max(clean_nums)

                    job = JobPost(
                        title=title,
                        company=company,
                        location=location,
                        job_url=link,
                        description=description,
                        salary_min=salary_min,
                        salary_max=salary_max,
                        site="Adzuna",
                        date_posted=None 
                    )
                    job_posts.append(job)
                    
                except Exception as e:
                    self.logger.warning(f"Error parsing card: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Scraping error: {e}")
            
        return job_posts

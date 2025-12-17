
from typing import List, Optional
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper
from app.models.job import ScraperInput, JobPost
from datetime import datetime, timedelta

class RemoteLeafScraper(BaseScraper):
    def __init__(self):
        super().__init__("RemoteLeaf", None)
        self.base_url = "https://remoteleaf.com/remote-jobs"

    def scrape(self, input_data: ScraperInput) -> List[JobPost]:
        job_posts = []
        
        url = self.base_url

        try:
            response = self.safe_get(url)
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch RemoteLeaf: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            cards = soup.select("ul.divide-y.divide-gray-200 > li")
            
            self.logger.info(f"Found {len(cards)} jobs on RemoteLeaf")
            
            for card in cards:
                try:
                    # Title
                    title_tag = card.select_one("p.text-indigo-600 a")
                    if not title_tag:
                        continue
                    title = title_tag.get_text(strip=True)
                    job_url = title_tag['href']
                    
                    if not job_url.startswith("http"):
                        job_url = "https://remoteleaf.com" + job_url
                        
                    # Company
                    company_tag = card.select_one("p.text-gray-500 a.underline")
                    company = company_tag.get_text(strip=True) if company_tag else "Unknown"
                    
                    # Location
                    location = "Remote"
                    paragraphs = card.select("div.sm\\:flex p.flex.items-center.text-sm.text-gray-500")
                    for p in paragraphs:
                        if "Remote" in p.get_text():
                            location = p.get_text(strip=True)
                            break
                            
                    # Date
                    date_posted = None
                    time_tag = card.find("time")
                    if time_tag and time_tag.has_attr("datetime"):
                        dt_str = time_tag["datetime"]
                        try:
                            # 2020-01-07
                            date_posted = datetime.strptime(dt_str, "%Y-%m-%d").date()
                        except ValueError:
                            pass
                    
                    # Filter by date if requested
                    if input_data.hours_old and date_posted:
                        cutoff_date = datetime.now().date() - timedelta(hours=input_data.hours_old)
                        if date_posted < cutoff_date:
                            continue

                    job = JobPost(
                        title=title,
                        company=company,
                        location=location,
                        job_url=job_url,
                        description="",
                        salary_min=None,
                        salary_max=None,
                        site="RemoteLeaf",
                        date_posted=date_posted
                    )
                    
                    # Filter by search term if provided
                    if input_data.search_term:
                        term = input_data.search_term.lower()
                        if term not in title.lower() and term not in company.lower():
                            continue

                    job_posts.append(job)
                    
                    if input_data.results_wanted and len(job_posts) >= input_data.results_wanted:
                        break
                        
                except Exception as e:
                    self.logger.warning(f"Error parsing RemoteLeaf card: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"RemoteLeaf scraping error: {e}")
            
        return job_posts

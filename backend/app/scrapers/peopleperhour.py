import asyncio
import logging
from datetime import datetime, timedelta, date
from typing import List, Optional

from bs4 import BeautifulSoup

from app.models.job import JobPost, JobType, ScraperInput
from app.scrapers.base import BaseScraper

class PeoplePerHourScraper(BaseScraper):
    """
    Scraper for PeoplePerHour.com (Freelance/Contract)
    """

    def __init__(self):
        super().__init__(site_name="PeoplePerHour")
        self.base_url = "https://www.peopleperhour.com"

    def scrape(self, input_data: ScraperInput) -> List[JobPost]:
        """
        Scrapes PeoplePerHour for freelance jobs.
        """
        self.logger.info(f"Starting scrape for {self.site_name} with term: {input_data.search_term}")
        
        job_posts = []
        
        # Construct URL
        # We can search by keywords. PPH uses /freelance-jobs/<term> or query params?
        # Let's check the dump again. The URL in dump was /freelance-jobs.
        # Searching usually works like: https://www.peopleperhour.com/freelance-jobs?q=python
        
        search_url = f"{self.base_url}/freelance-jobs"
        params = {}
        if input_data.search_term:
            params["q"] = input_data.search_term
            
        # PPH might have location filters, but for now we focus on term.
        # "remote" is often a filter.
        
        try:
            # We can't really control results_wanted easily with pagination here in one request,
            # but we will fetch the first page.
            
            response = self.safe_get(search_url, params=params)
            if not response:
                return []
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Find job cards
            # Selector strategies: using partial class matching because of hashed classes
            
            # The container seems to be an 'li' with class starting with 'list__item' 
            # or inner div with 'item__container'
            
            # Let's try to find identifying elements.
            # We can use regex for classes or just CSS selectors with substrings if supported, 
            # but BS4 supports regex in find_all(class_=re.compile(...))
            
            import re
            
            job_cards = soup.find_all("div", class_=re.compile(r"item__container"))
            
            for card in job_cards:
                try:
                    title_elem = card.find("h6", class_=re.compile(r"item__title"))
                    if not title_elem:
                        continue
                        
                    link_elem = title_elem.find("a")
                    title = link_elem.get_text(strip=True)
                    url = link_elem.get("href")
                    if url and not url.startswith("http"):
                        url = self.base_url + url
                        
                    # Company/User
                    user_elem = card.find("span", class_=re.compile(r"card__username"))
                    company = user_elem.get_text(strip=True) if user_elem else "PeoplePerHour User"
                    
                    # Price/Budget
                    price_elem = card.find("div", class_=re.compile(r"card__price"))
                    salary = price_elem.get_text(strip=True) if price_elem else None
                    
                    # Date Posted
                    # <div class="nano card__footer-left..."><span>2 hours ago</span>...</div>
                    date_posted = None
                    footer = card.find("div", class_=re.compile(r"card__footer-left"))
                    if footer:
                        time_span = footer.find("span")
                        if time_span:
                            time_text = time_span.get_text(strip=True)
                            date_posted = self._parse_relative_date(time_text)
                            
                            # Filter by hours_old if present
                            if input_data.hours_old and date_posted:
                                posted_diff = datetime.now() - date_posted
                                if posted_diff > timedelta(hours=input_data.hours_old):
                                    continue

                    # Location
                    location = "Remote" # Default for PPH often
                    # Check if there's a location icon/text
                    # <i class="fpph fpph-location"></i>Remote
                    loc_icon = card.find("i", class_=re.compile(r"fpph-location"))
                    if loc_icon and loc_icon.parent:
                        location = loc_icon.parent.get_text(strip=True)

                    job = JobPost(
                        title=title,
                        company=company,
                        location=location,
                        job_url=url,
                        site=self.site_name,
                        date_posted=date_posted,
                        description=title, # PPH list view has description snippet
                        compensation=salary
                    )
                    
                    # Description snippet
                    desc_elem = card.find("p", class_=re.compile(r"item__desc"))
                    if desc_elem:
                        job.description = desc_elem.get_text(strip=True)
                        
                    job_posts.append(job)
                    
                except Exception as e:
                    self.logger.error(f"Error parsing PPH job card: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error scraping {self.site_name}: {e}")
            
        return job_posts

    def _parse_relative_date(self, text: str) -> Optional[date]:
        try:
            now = datetime.now()
            text = text.lower()
            if "hour" in text:
                hours = int(text.split()[0])
                return (now - timedelta(hours=hours)).date()
            elif "minute" in text:
                mins = int(text.split()[0])
                return (now - timedelta(minutes=mins)).date()
            elif "day" in text:
                days = int(text.split()[0])
                return (now - timedelta(days=days)).date()
            elif "week" in text:
                weeks = int(text.split()[0])
                return (now - timedelta(weeks=weeks)).date()
            elif "month" in text:
                months = int(text.split()[0])
                return (now - timedelta(days=months*30)).date()
            return None
        except:
            return None

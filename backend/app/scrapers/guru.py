import logging
import time
from datetime import datetime, timedelta, date
from typing import List, Optional
import re

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from app.models.job import JobPost, JobType, ScraperInput
from app.scrapers.base import BaseScraper

class GuruScraper(BaseScraper):
    """
    Scraper for Guru.com using Selenium to bypass WAF.
    """

    def __init__(self):
        super().__init__(site_name="Guru")
        self.base_url = "https://www.guru.com"

    def scrape(self, input_data: ScraperInput) -> List[JobPost]:
        """
        Scrapes Guru for freelance jobs.
        """
        self.logger.info(f"Starting scrape for {self.site_name} with term: {input_data.search_term}")
        
        job_posts = []
        driver = None

        try:
            # Setup Selenium
            options = Options()
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            # Minimal user agent to look real
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            driver = webdriver.Chrome(options=options)
            
            # Construct URL
            # Using query param format which worked in test
            search_url = f"{self.base_url}/d/jobs/"
            if input_data.search_term:
                full_url = f"{search_url}?q={input_data.search_term}"
            else:
                full_url = search_url
            
            self.logger.debug(f"Navigating to {full_url}")
            driver.get(full_url)
            
            # Wait for content
            time.sleep(5) 
            
            # Parse with BS4
            soup = BeautifulSoup(driver.page_source, "html.parser")
            
            # Find job records
            job_cards = soup.find_all("div", class_="jobRecord")
            
            for card in job_cards:
                try:
                    # Title and URL
                    title_elem = card.find("h2", class_="jobRecord__title")
                    if not title_elem:
                        continue
                    
                    link_elem = title_elem.find("a")
                    if not link_elem:
                        continue
                        
                    title = link_elem.get_text(strip=True)
                    url = link_elem.get("href")
                    if url and not url.startswith("http"):
                        url = self.base_url + url
                        
                    # Company (Employer)
                    identity_elem = card.find("h3", class_="identityName")
                    company = identity_elem.get_text(strip=True) if identity_elem else "Guru Employer"
                    
                    # Location
                    location = "Remote"
                    loc_elem = card.find("p", class_="freelancerAvatar__subText")
                    if loc_elem:
                        location = loc_elem.get_text(strip=True)
                        
                    # Budget/Salary
                    budget_elem = card.find("div", class_="jobRecord__budget")
                    salary = budget_elem.get_text(strip=True) if budget_elem else None
                    
                    # Date Posted
                    date_posted = None
                    meta_elem = card.find("div", class_="jobRecord__meta")
                    if meta_elem:
                        meta_text = meta_elem.get_text(strip=True)
                        if "Posted" in meta_text:
                            date_posted = self._parse_relative_date(meta_text)
                            
                    # Filter by hours_old if present
                    if input_data.hours_old and date_posted:
                        posted_diff = datetime.now() - date_posted
                        if posted_diff > timedelta(hours=input_data.hours_old):
                            continue

                    # Description
                    desc_elem = card.find("p", class_="jobRecord__desc")
                    description = desc_elem.get_text(strip=True) if desc_elem else title

                    job = JobPost(
                        title=title,
                        company=company,
                        location=location,
                        job_url=url,
                        site=self.site_name,
                        date_posted=date_posted,
                        description=description,
                        compensation=salary
                    )
                    
                    job_posts.append(job)
                    
                except Exception as e:
                    self.logger.error(f"Error parsing Guru job card: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error scraping {self.site_name} with Selenium: {e}")
        finally:
            if driver:
                driver.quit()
            
        return job_posts

    def _parse_relative_date(self, text: str) -> Optional[date]:
        try:
            now = datetime.now()
            text = text.lower()
            match = re.search(r'(\d+)\s+(hr|hour|min|minute|day|week|month)', text)
            if match:
                value = int(match.group(1))
                unit = match.group(2)
                
                if "min" in unit:
                    return (now - timedelta(minutes=value)).date()
                elif "hr" in unit or "hour" in unit:
                    return (now - timedelta(hours=value)).date()
                elif "day" in unit:
                    return (now - timedelta(days=value)).date()
                elif "week" in unit:
                    return (now - timedelta(weeks=value)).date()
                elif "month" in unit:
                    return (now - timedelta(days=value * 30)).date()
            
            return None
        except:
            return None

import json
import re
import urllib.parse
from datetime import datetime, timedelta, date
from typing import List, Optional

from bs4 import BeautifulSoup
import requests

from app.models.job import JobPost, ScraperInput
from app.scrapers.base import BaseScraper


class ArcScraper(BaseScraper):
    """Scraper for Arc.dev - Developer-focused remote job platform."""
    
    def __init__(self):
        super().__init__("arc")

    def scrape(self, input_data: ScraperInput) -> List[JobPost]:
        self.logger.info(f"Scraping Arc.dev for: {input_data.search_term}")
        
        base_url = "https://arc.dev/remote-jobs"
        
        # Arc.dev doesn't have a simple query param, but we can filter categories
        # For now, use the main page and filter client-side
        search_url = base_url
        
        # If searching for specific skills, try category-based URLs
        if input_data.search_term:
            search_term_slug = input_data.search_term.lower().replace(' ', '-')
            # Common tech mappings
            skill_mappings = {
                'python': 'python',
                'javascript': 'javascript',
                'react': 'reactjs',
                'node': 'nodejs',
                'java': 'java',
                'typescript': 'typescript',
                'golang': 'golang',
                'go': 'golang',
                'rust': 'rust',
                'ruby': 'ruby',
                'php': 'php',
                'swift': 'swift',
                'kotlin': 'kotlin',
                'flutter': 'flutter',
                'android': 'android',
                'ios': 'ios',
                'aws': 'aws',
                'docker': 'docker',
                'kubernetes': 'kubernetes',
                'machine learning': 'machine-learning',
                'ml': 'machine-learning',
                'ai': 'ai',
                'data science': 'data-science',
            }
            if search_term_slug in skill_mappings:
                search_url = f"{base_url}/{skill_mappings[search_term_slug]}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }

        try:
            response = requests.get(search_url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Arc.dev uses __NEXT_DATA__ with job data
            script_tag = soup.find("script", {"id": "__NEXT_DATA__"})
            if not script_tag:
                self.logger.warning("No __NEXT_DATA__ found on Arc.dev")
                return []
            
            data = json.loads(script_tag.string)
            page_props = data.get("props", {}).get("pageProps", {})
            
            # Combine arcJobs (exclusive) and externalJobs
            arc_jobs = page_props.get("arcJobs", [])
            external_jobs = page_props.get("externalJobs", [])
            
            all_jobs = arc_jobs + external_jobs
            
            job_posts = []
            search_lower = input_data.search_term.lower() if input_data.search_term else ""
            
            for job in all_jobs:
                try:
                    title = job.get("title", "")
                    
                    # Filter by search term if provided
                    if search_lower:
                        categories = [cat.get("name", "").lower() for cat in job.get("categories", [])]
                        title_match = search_lower in title.lower()
                        category_match = any(search_lower in cat for cat in categories)
                        if not (title_match or category_match):
                            continue
                    
                    # Build job URL
                    random_key = job.get("randomKey", "")
                    url_string = job.get("urlString", "")
                    
                    if random_key and url_string:
                        job_url = f"https://arc.dev/remote-jobs/details/{url_string}-{random_key}"
                    elif random_key:
                        job_url = f"https://arc.dev/remote-jobs/details/{random_key}"
                    else:
                        job_url = "https://arc.dev/remote-jobs"
                    
                    # Company name
                    company_data = job.get("company", {})
                    company = company_data.get("name", "Arc Exclusive") if company_data else "Arc Exclusive"
                    
                    # Location based on requiredCountries
                    countries = job.get("requiredCountries", [])
                    if countries:
                        location = f"Remote - {', '.join(countries[:3])}"
                        if len(countries) > 3:
                            location += "..."
                    else:
                        location = "Remote Anywhere"
                    
                    # Date parsing (postedAt is Unix timestamp)
                    posted_at = job.get("postedAt")
                    date_posted = None
                    if posted_at:
                        try:
                            date_posted = datetime.fromtimestamp(posted_at).date()
                        except:
                            date_posted = date.today()
                    
                    # Job type
                    job_type = job.get("jobType", "")
                    if job_type == "contract":
                        job_type_str = "Contract/Freelance"
                    elif job_type == "permanent":
                        job_type_str = "Full-time"
                    else:
                        job_type_str = job_type.capitalize() if job_type else "Full-time"
                    
                    # Salary info
                    min_salary = job.get("minAnnualSalary")
                    max_salary = job.get("maxAnnualSalary")
                    min_hourly = job.get("minHourlyRate")
                    max_hourly = job.get("maxHourlyRate")
                    
                    compensation = None
                    if min_salary and max_salary:
                        compensation = f"${min_salary:,} - ${max_salary:,}/year"
                    elif min_hourly and max_hourly:
                        compensation = f"${min_hourly} - ${max_hourly}/hour"
                    
                    # Experience level
                    exp_level = job.get("experienceLevel", "")
                    
                    # Categories as description
                    categories = [cat.get("name", "") for cat in job.get("categories", [])]
                    description = f"Type: {job_type_str}"
                    if exp_level:
                        description += f" | Level: {exp_level.capitalize()}"
                    if categories:
                        description += f" | Skills: {', '.join(categories[:8])}"
                    
                    job_post = JobPost(
                        title=title,
                        company=company,
                        job_url=job_url,
                        location=location,
                        date_posted=date_posted,
                        description=description,
                        compensation=compensation,
                        is_remote=True,
                        site="arc"
                    )
                    job_posts.append(job_post)
                    
                except Exception as e:
                    self.logger.warning(f"Error parsing Arc job: {e}")
                    continue
            
            self.logger.info(f"Found {len(job_posts)} jobs on Arc.dev")
            return job_posts[:input_data.results_wanted]
            
        except Exception as e:
            self.logger.error(f"Error scraping Arc.dev: {e}")
            return []

import re
import json
import logging
from typing import List, Optional, Tuple
from datetime import datetime, timedelta
from urllib.parse import quote_plus

from app.scrapers.base import BaseScraper, ScraperError
from app.models.job import JobPost, ScraperInput, JobType

class GoogleScraper(BaseScraper):
    def __init__(self, proxies: Optional[List[str]] = None):
        super().__init__("Google", proxies)
        self.base_url = "https://www.google.com/search"
    
    def scrape(self, input_data: ScraperInput) -> List[JobPost]:
        self.logger.info(f"Scraping Google for '{input_data.search_term}' in '{input_data.location}'")
        
        jobs = []
        # Google Jobs "UI" is triggered by specific query format
        query = f"{input_data.search_term} jobs near {input_data.location}"
        if input_data.is_remote:
            query += " remote"
            
        params = {
            "q": query,
            "udm": "8", # "Unsorted Data Mode" 8 -> Jobs UI usually
            # "ibp": "htl;jobs", # Another trigger, sometimes needed
        }
        
        # 1. Fetch Initial Page
        try:
            response = self.safe_get(self.base_url, params=params)
        except ScraperError as e:
            self.logger.error(f"Failed to fetch initial page: {e}")
            return []

        # 2. Parse Initial Jobs & Get "Async Feature Code" (fc) for pagination
        initial_jobs, async_fc = self._parse_initial_page(response.text)
        jobs.extend(initial_jobs)
        
        # 3. Pagination
        # Limit to reasonable number if they want a lot, but Google blocks heavy pagination
        # We'll try to get 'results_wanted'
        
        next_cursor = async_fc # Used as 'fc' param
        # The logic for `next_cursor` in Google's async jobs is complex. 
        # Usually it's embedded in the `async_fc` string or a separate token.
        # JobSpy used `forward_cursor` found in the response.
        
        # Let's rely on what we found. If async_fc is present, we can try to get more.
        # Note: Google pagination is notoriously hard to reverse engineer fully and changes often.
        # We will implement a simplified version: if we found jobs, we assume we might get more if we had a cursor,
        # but the initial parser might not have extracted a cursor.
        
        # For this implementation, we'll focus on getting the initial batch correct (usually 10-20 jobs)
        # and if the user wants more, we might need to reverse engineer the 'async' endpoint better.
        # JobSpy's implementation of pagination was quite complex.
        
        return jobs[:input_data.results_wanted]

    def _parse_initial_page(self, html: str) -> Tuple[List[JobPost], Optional[str]]:
        jobs = []
        async_fc = None
        
        # Extract Async Feature Code (fc)
        # pattern_fc = r'data-async-fc="([^"]+)"'
        # fc_match = re.search(pattern_fc, html)
        # if fc_match:
        #     async_fc = fc_match.group(1)

        # Parse Job Grid
        # Google embeds job data in a specific JSON structure within script tags or hidden divs.
        # Common pattern: window.json_data = [...] or similar.
        # Or look for the specific "520084652" key JobSpy uses.
        
        pattern = r'520084652":(\[.*?\]\s*\])\s*}\s*]\s*]\s*]\s*]\s*]'
        matches = re.finditer(pattern, html)
        
        for match in matches:
            try:
                # The regex captures a JSON array string.
                # We need to be careful about matching too much or too little.
                # Using a JSON parser on the substring is safer if the regex is precise.
                # JobSpy's regex logic seems robust enough for now.
                json_str = match.group(1)
                data = json.loads(json_str)
                
                # 'data' is a list of job entries (usually)
                if isinstance(data, list):
                   extracted = self._extract_jobs_from_json_list(data)
                   jobs.extend(extracted)
                   
            except Exception as e:
                self.logger.warning(f"Failed to parse job JSON block: {e}")
                
        return jobs, async_fc

    def _extract_jobs_from_json_list(self, data: List) -> List[JobPost]:
        results = []
        # Recursive search for the job structure
        # Google's JSON is deeply nested arrays.
        # JobSpy has a recursive finder. We can simplify if we know the structure or blindly search.
        
        def recursive_find(item):
            # Heuristic: A job entry usually has a specific structure.
            # JobSpy looked for "520084652" key, but we already found that block.
            # Within that block, we have a list of jobs.
            # Each job is an array.
            # Index 0: Title, Index 1: Company, Index 2: Location? 
            # Let's inspect known mapping from JobSpy:
            # title = job_info[0]
            # company_name = job_info[1]
            # location = job_info[2]
            # description = job_info[19]
            # job_url = job_info[3][0][0]
            
            if isinstance(item, list) and len(item) > 20: 
                # Potential job array (needs to be long enough)
                # Check types
                if isinstance(item[0], str) and isinstance(item[1], str):
                    try:
                         # Validate it looks like a job
                         title = item[0]
                         company = item[1]
                         
                         # JobSpy index 28 was ID
                         if len(item) > 28:
                             job_id = item[28]
                             # Success
                             return [item]
                    except:
                        pass
            
            found = []
            if isinstance(item, list):
                for sub in item:
                    found.extend(recursive_find(sub))
            elif isinstance(item, dict):
                for sub in item.values():
                    found.extend(recursive_find(sub))
            return found

        job_arrays = recursive_find(data)
        
        for job_info in job_arrays:
            try:
                title = job_info[0]
                company = job_info[1]
                location = job_info[2]
                
                # Parse description
                description = job_info[19] if len(job_info) > 19 else ""
                
                # Parse URL
                job_url = None
                if len(job_info) > 3 and isinstance(job_info[3], list) and len(job_info[3]) > 0:
                     if isinstance(job_info[3][0], list) and len(job_info[3][0]) > 0:
                         job_url = job_info[3][0][0]

                # ID
                job_id = job_info[28] if len(job_info) > 28 else None
                
                # Date Posted
                date_posted = None
                if len(job_info) > 12:
                    date_str = job_info[12]
                    # "3 days ago"
                    if isinstance(date_str, str):
                        match = re.search(r"(\d+)", date_str)
                        if match:
                             days = int(match.group(1))
                             date_posted = datetime.now().date() - timedelta(days=days)
                
                if title and company:
                   post = JobPost(
                       id=f"google-{job_id}" if job_id else None,
                       title=title,
                       company=company,
                       location=location,
                       job_url=job_url or "https://google.com",
                       site="Google",
                       description=description,
                       date_posted=date_posted
                   )
                   results.append(post)
            except Exception as e:
                self.logger.warning(f"Error parsing job array: {e}")
                
        return results

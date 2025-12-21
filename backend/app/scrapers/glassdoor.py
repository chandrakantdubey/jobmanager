import logging
import time
import random
import json
import re
from typing import List, Optional, Tuple
from datetime import datetime, timedelta
import requests # Fallback for some requests if needed, but perfer tls_client

from app.scrapers.base import BaseScraper, ScraperError
from app.models.job import JobPost, ScraperInput, JobType

# Constants
QUERY_TEMPLATE = """
        query JobSearchResultsQuery(
            $excludeJobListingIds: [Long!], 
            $keyword: String, 
            $locationId: Int, 
            $locationType: LocationTypeEnum, 
            $numJobsToShow: Int!, 
            $pageCursor: String, 
            $pageNumber: Int, 
            $filterParams: [FilterParams], 
            $originalPageUrl: String, 
            $seoFriendlyUrlInput: String, 
            $parameterUrlInput: String, 
            $seoUrl: Boolean
        ) {
            jobListings(
                contextHolder: {
                    searchParams: {
                        excludeJobListingIds: $excludeJobListingIds, 
                        keyword: $keyword, 
                        locationId: $locationId, 
                        locationType: $locationType, 
                        numPerPage: $numJobsToShow, 
                        pageCursor: $pageCursor, 
                        pageNumber: $pageNumber, 
                        filterParams: $filterParams, 
                        originalPageUrl: $originalPageUrl, 
                        seoFriendlyUrlInput: $seoFriendlyUrlInput, 
                        parameterUrlInput: $parameterUrlInput, 
                        seoUrl: $seoUrl, 
                        searchType: SR
                    }
                }
            ) {
                jobListings {
                    jobview {
                        header {
                            employerNameFromSearch
                            jobTitleText
                            locationName
                            ageInDays
                        }
                        job {
                            listingId
                            description
                        }
                        overview {
                            squareLogoUrl
                        }
                    }
                }
                paginationCursors {
                    cursor
                    pageNumber
                }
            }
        }
"""
# Note: I simplified the query return fields slightly to match what we need.

HEADERS = {
    "authority": "www.glassdoor.com",
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "apollographql-client-name": "job-search-next",
    "apollographql-client-version": "4.65.5",
    "content-type": "application/json",
    "origin": "https://www.glassdoor.com",
    "referer": "https://www.glassdoor.com/",
}

FALLBACK_TOKEN = "Ft6oHEWlRZrxDww95Cpazw:0pGUrkb2y3TyOpAIqF2vbPmUXoXVkD3oEGDVkvfeCerceQ5-n8mBg3BovySUIjmCPHCaW0H2nQVdqzbtsYqf4Q:wcqRqeegRUa9MVLJGyujVXB7vWFPjdaS1CtrrzJq-ok"

class GlassdoorScraper(BaseScraper):
    def __init__(self, proxies: Optional[List[str]] = None):
        super().__init__("Glassdoor", proxies)
        self.base_url = "https://www.glassdoor.com"
        self.session.headers.update(HEADERS)

    def scrape(self, input_data: ScraperInput) -> List[JobPost]:
        self.logger.info(f"Scraping Glassdoor for '{input_data.search_term}'")
        jobs = []
        
        # 1. Get CSRF Token (try)
        token = self._get_csrf_token() or FALLBACK_TOKEN
        self.session.headers["gd-csrf-token"] = token
        
        # 2. Get Location ID
        loc_id, loc_type = self._get_location(input_data.location)
        if not loc_id:
             self.logger.error("Could not resolve location")
             return []
             
        cursor = None
        for page in range(1, 15): # Limit pages (supports ~400 jobs)
            if len(jobs) >= input_data.results_wanted:
                break
                
            self.logger.debug(f"Fetching page {page}")
            try:
                payload = self._build_payload(input_data, loc_id, loc_type, page, cursor)
                
                # Glassdoor seems to need standard requests sometimes or handles TLS specifically?
                # BaseScraper uses tls_client which should be better.
                # Endpoint is /graph
                
                response = self.session.post(f"{self.base_url}/graph", json=payload)
                
                if response.status_code != 200:
                    self.logger.error(f"GD Error: {response.status_code}")
                    break
                    
                data = response.json()
                if isinstance(data, list): data = data[0] # Sometimes list wrapper?
                
                if "errors" in data:
                    self.logger.error("GD API Errors")
                    break
                    
                listings = data.get("data", {}).get("jobListings", {}).get("jobListings", [])
                cursors = data.get("data", {}).get("jobListings", {}).get("paginationCursors", [])
                
                if not listings:
                    self.logger.info("No listings found")
                    break
                    
                for item in listings:
                    post = self._process_job(item)
                    if post:
                        jobs.append(post)
                
                # Find next cursor
                next_cursor = None
                for c in cursors:
                    if c["pageNumber"] == page + 1:
                        next_cursor = c["cursor"]
                        break
                
                if not next_cursor:
                    break
                cursor = next_cursor
                
                time.sleep(random.uniform(2, 5))

            except Exception as e:
                self.logger.error(f"Scrape error: {e}")
                break
                
        return jobs[:input_data.results_wanted]

    def _get_csrf_token(self):
        try:
            res = self.session.get(f"{self.base_url}/Job/computer-science-jobs.htm")
            pattern = r'"token":\s*"([^"]+)"'
            matches = re.findall(pattern, res.text)
            if matches:
                return matches[0]
        except:
            pass
        return None

    def _get_location(self, location: str) -> Tuple[Optional[int], Optional[str]]:
        if not location: return None, None
        try:
            url = f"{self.base_url}/findPopularLocationAjax.htm?maxLocationsToReturn=10&term={location}"
            res = self.session.get(url)
            items = res.json()
            if items:
                # Type mapping
                t_map = {"C": "CITY", "S": "STATE", "N": "COUNTRY"}
                l_type = items[0]["locationType"]
                return int(items[0]["locationId"]), t_map.get(l_type, "CITY")
        except Exception as e:
            self.logger.error(f"Loc fetch failed: {e}")
            
        # Fallback
        if "india" in location.lower():
            return 115, "COUNTRY"
        elif "united states" in location.lower() or "usa" in location.lower() or "us" in location.lower():
            return 1, "COUNTRY"
            
        return None, None

    def _build_payload(self, input_data, loc_id, loc_type, page, cursor):
        # Filters
        filter_params = []
        if input_data.job_type:
             jt_map = {
                JobType.FULL_TIME: "minFullTime",
                JobType.PART_TIME: "minPartTime",
                JobType.CONTRACT: "minContract",
                JobType.INTERNSHIP: "minInternship",
                JobType.TEMPORARY: "minTemporary",
                JobType.FREELANCE: "minContract"
             }
             valid = [jt_map[jt] for jt in input_data.job_type if jt in jt_map]
             if valid:
                 # Glassdoor usually takes one 'jobType'? Or multiple?
                 # Assuming simplistic "jobType" key in filterParams
                 # Actually Glassdoor filters are complex "minRating", "fromAge", etc.
                 # For jobType, it's often a specific key.
                 # Let's try simplified generic key if known, else minimal.
                 # A common key is "jobType".
                 for v in valid:
                     filter_params.append({"key": "jobType", "value": v})
                     
        if input_data.hours_old:
             days = max(1, input_data.hours_old // 24)
             filter_params.append({"key": "fromAge", "value": str(days)})

        return {
            "operationName": "JobSearchResultsQuery",
            "variables": {
                "keyword": input_data.search_term,
                "locationId": loc_id,
                "locationType": loc_type,
                "numJobsToShow": 30,
                "pageNumber": page,
                "pageCursor": cursor,
                "filterParams": filter_params
            },
            "query": QUERY_TEMPLATE
        }

    def _process_job(self, item: dict) -> Optional[JobPost]:
        try:
            view = item["jobview"]
            header = view["header"]
            job = view["job"]
            
            title = header["jobTitleText"]
            company = header["employerNameFromSearch"]
            loc = header["locationName"]
            age = header.get("ageInDays")
            
            listing_id = job["listingId"]
            desc = job.get("description", "") # Usually not full description in list view
            
            date_posted = None
            if age is not None:
                date_posted = datetime.now().date() - timedelta(days=age)
                
            job_url = f"https://www.glassdoor.com/job-listing/j?jl={listing_id}"
            
            return JobPost(
                id=f"gd-{listing_id}",
                title=title,
                company=company,
                location=loc,
                job_url=job_url,
                date_posted=date_posted,
                site="Glassdoor",
                description=desc # Usually truncated or empty in search results
            )
        except:
            return None

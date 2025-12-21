import asyncio
import argparse
import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.job import ScraperInput, JobType
from app.scrapers.linkedin import LinkedInScraper
from app.scrapers.indeed import IndeedScraper
from app.scrapers.glassdoor import GlassdoorScraper
from app.scrapers.google import GoogleScraper

async def test_scraper(site, limit, job_type_str=None):
    print(f"Testing {site} with limit {limit} and type {job_type_str}...")
    
    job_types = []
    if job_type_str:
        try:
            job_types = [JobType(jt) for jt in job_type_str.split(",")]
        except ValueError as e:
            print(f"Invalid job type: {e}")
            return

    input_data = ScraperInput(
        search_term="Python Developer",
        location="United States" if site != "naukri" else "India",
        results_wanted=limit,
        job_type=job_types if job_types else None,
        country="usa"
    )

    scraper = None
    if site.lower() == "linkedin":
        scraper = LinkedInScraper()
    elif site.lower() == "indeed":
        scraper = IndeedScraper()
    elif site.lower() == "glassdoor":
        scraper = GlassdoorScraper()
    elif site.lower() == "google":
        scraper = GoogleScraper()
    else:
        print(f"Unknown scraper: {site}")
        return

    try:
        jobs = scraper.scrape(input_data)
        print(f"✅ {site}: Found {len(jobs)} jobs")
        if jobs:
            print(f"   Sample: {jobs[0].title} at {jobs[0].company}")
            print(f"   URL: {jobs[0].job_url}")
            if job_type_str:
                print(f"   (Verified type logic was passed, but manual check of URL needed for accuracy)")
    except Exception as e:
        print(f"❌ {site}: Failed - {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", type=str, required=True)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--type", type=str, default=None, help="Comma separated types: fulltime,parttime,contract,freelance")
    
    args = parser.parse_args()
    
    asyncio.run(test_scraper(args.site, args.limit, args.type))

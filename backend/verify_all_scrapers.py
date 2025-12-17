from jobspy.bdjobs import BDJobs
from jobspy.linkedin import LinkedIn
from jobspy.indeed import Indeed
from jobspy.ziprecruiter import ZipRecruiter
from jobspy.glassdoor import Glassdoor
from jobspy.google import Google
from jobspy.bayt import BaytScraper
from jobspy.naukri import Naukri
from jobspy.model import Site

scrapers = {
    Site.BDJOBS: BDJobs,
    Site.LINKEDIN: LinkedIn,
    Site.INDEED: Indeed,
    Site.ZIP_RECRUITER: ZipRecruiter,
    Site.GLASSDOOR: Glassdoor,
    Site.GOOGLE: Google,
    Site.BAYT: BaytScraper,
    Site.NAUKRI: Naukri,
}

def verify_scrapers():
    print("Verifying Scraper Initialization with user_agent...")
    fake_ua = "Mozilla/5.0 (Test Agent)"
    
    failures = []
    
    for site, scraper_cls in scrapers.items():
        site_name = site.value
        try:
            # Try to instantiate with user_agent
            scraper = scraper_cls(user_agent=fake_ua)
            
            # Check if headers (if accessible) have the UA
            # Note: implementations vary on where they store session/headers, 
            # but they should at least NOT crash.
            print(f"[PASS] {site_name} initialized successfully.")
            
        except TypeError as e:
            print(f"[FAIL] {site_name} crashed on init: {e}")
            failures.append(site_name)
        except Exception as e:
            print(f"[FAIL] {site_name} crashed with unexpected error: {e}")
            failures.append(site_name)
            
    if failures:
        print(f"\nFailures found in: {', '.join(failures)}")
        exit(1)
    else:
        print("\nAll scrapers initialized successfully!")
        exit(0)

if __name__ == "__main__":
    verify_scrapers()

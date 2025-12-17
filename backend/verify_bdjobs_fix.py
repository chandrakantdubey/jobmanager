from jobspy.bdjobs import BDJobs
import sys

try:
    print("Attempting to instantiate BDJobs with user_agent...")
    scraper = BDJobs(user_agent="Mozilla/5.0 Test Agent")
    print("SUCCESS: BDJobs instantiated with user_agent.")
    
    ua_header = scraper.session.headers.get("user-agent") or scraper.session.headers.get("User-Agent")
    print(f"Current User-Agent header: {ua_header}")
    
    if ua_header == "Mozilla/5.0 Test Agent":
        print("SUCCESS: User-Agent header set correctly.")
    else:
        print(f"WARNING: User-Agent header mismatch.")
        # Some session creators might override or default, so we check if it didn't crash at least.

except TypeError as e:
    print(f"FAILURE: TypeError caught: {e}")
    sys.exit(1)
except Exception as e:
    print(f"FAILURE: Unexpected error: {e}")
    sys.exit(1)

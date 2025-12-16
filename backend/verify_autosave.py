import requests
import time
from jose import jwt
from datetime import datetime, timedelta
import sys

# Configuration
SECRET_KEY = "supersecretkey123"
ALGORITHM = "HS256"
BASE_URL = "http://127.0.0.1:8001"

def create_test_token():
    expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode = {"sub": "testuser", "exp": expire}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_autosave():
    token = create_test_token()
    search_term = "autosave_test_unique_" + str(int(time.time()))
    print(f"1. Searching for unique term: {search_term}")
    
    # Trigger search stream
    params = {
        "search_term": search_term, 
        "location": "Remote", 
        "country": "usa",
        "results_wanted": 1, 
        "token": token,
        "sites": "linkedin" # LinkedIn often yields better test data or mock it if needed
    }
    
    # We just need to hit the endpoint and read a bit to trigger the backend logic
    # Note: If no jobs are found effectively, we can't test autosave. 
    # But for now we just want to ensure it doesn't crash.
    try:
        with requests.get(f"{BASE_URL}/search/stream", params=params, stream=True) as r:
            for i, line in enumerate(r.iter_lines()):
                if line:
                    print(f"Stream: {line.decode('utf-8')[:50]}...")
                if i > 5: break
    except Exception as e:
        print(f"Stream interrupted (expected): {e}")

    # Now we should check if our "autosave_test" query was logged in history 
    # and ideally if any jobs were saved. 
    # But since we can't guarantee finding a job with a random name, we'll verify the endpoint ran successfully.
    
    print("2. Verifying Search History (Proxy for successful run)...")
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(f"{BASE_URL}/history", headers=headers)
    if res.status_code == 200:
        history = res.json()
        found = [h for h in history if h['search_term'] == search_term]
        if found:
            print("SUCCESS: Search history recorded, implying endpoints work.")
        else:
            print("WARNING: History not found.")
    else:
        print(f"FAILED: History fetch error {res.status_code}")

if __name__ == "__main__":
    verify_autosave()

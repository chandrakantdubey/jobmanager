import requests
import json
from datetime import datetime, timedelta
from jose import jwt
import time

# Configuration (match backend)
SECRET_KEY = "supersecretkey123"
ALGORITHM = "HS256"
BASE_URL = "http://127.0.0.1:8001"

def create_test_token():
    expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode = {"sub": "testuser", "exp": expire}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def test_history():
    token = create_test_token()
    print("1. Performing Search...")
    params = {
        "search_term": "history_test_dev",
        "location": "remote",
        "country": "usa",
        "results_wanted": 1,
        "token": token,
        "sites": "linkedin"
    }
    
    # Trigger search (consume a bit of stream)
    try:
        with requests.get(f"{BASE_URL}/search/stream", params=params, stream=True) as r:
            # Just read a few lines to ensure it started
            for i, line in enumerate(r.iter_lines()):
                if i > 2: break 
    except Exception as e:
        print(f"Search error (expected if we cut it off): {e}")

    print("2. Fetching History...")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.get(f"{BASE_URL}/history", headers=headers)
        if res.status_code == 200:
            history = res.json()
            # Find our search
            found = [h for h in history if h['search_term'] == 'history_test_dev']
            if found:
                print("SUCCESS: Search history record found!")
                print(found[0])
            else:
                print("FAILED: History record not found.")
                print("Full history:", history)
        else:
            print(f"FAILED: Status {res.status_code}, {res.text}")
    except Exception as e:
        print(f"History fetch failed: {e}")

if __name__ == "__main__":
    test_history()

import requests
import json
from datetime import datetime, timedelta
from jose import jwt

# Configuration (match backend)
SECRET_KEY = "supersecretkey123"
ALGORITHM = "HS256"
BASE_URL = "http://127.0.0.1:8001"

def create_test_token():
    expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode = {"sub": "testuser", "exp": expire}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def test_stream(country="india"):
    token = create_test_token()
    print(f"\nTesting stream with country={country}...")
    
    # Register dummy user if not exists (to pass auth check in stream endpoint)
    # Actually stream endpoint checks DB for user.
    # We might need to register a user first.
    # Let's try to register 'testuser' first.
    try:
        requests.post(f"{BASE_URL}/auth/register", json={"username": "testuser", "email": "test@example.com", "password": "password"})
    except:
        pass # Might already exist

    params = {
        "search_term": "developer",
        "location": "remote",
        "country": country,
        "results_wanted": 1,
        "token": token,
        "sites": "linkedin" # Just test one site
    }
    
    try:
        with requests.get(f"{BASE_URL}/search/stream", params=params, stream=True) as r:
            for line in r.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    # EventSource format: "data: ..."
                    if decoded.startswith("data:"): # It might just be raw if StreamResponse default?
                        # Fastapi StreamingResponse with text/event-stream usually doesn't add "data:" automatically unless using EventSourceResponse from sse-starlette
                        # But in my code I am just yielding strings.
                        # Wait, the code in main.py uses StreamingResponse(stream_generator, media_type="text/event-stream")
                        # The generator yields `json.dumps(...) + "\n"`.
                        # It doesn't strictly follow SSE format "data: ...\n\n" unless I added it.
                        # My code: yielding `json.dumps(...) + "\n"`
                        # So it's just newline delimited JSON.
                        pass
                    
                    print(f"Received: {decoded}")
                    if "Invalid country" in decoded:
                        print("SUCCESS: Caught invalid country error.")
                        return
                    if "Scraping linkedin" in decoded:
                        print("SUCCESS: Started scraping.")
                        return
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    test_stream(country="brunei") # Should fail gracefully
    test_stream(country="india")  # Should work

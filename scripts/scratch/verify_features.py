import sys
from pathlib import Path
_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))
import _repo_bootstrap  # noqa: E402
_repo_bootstrap.ensure_repo_root()

import requests
import json

BASE_URL = "http://localhost:8081/api"

def test_nso_sync():
    print("--- Testing NSO Sync ---")
    try:
        # Note: This might take a few seconds due to sleep(2) in service
        response = requests.post(f"{BASE_URL}/sync/nso")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

def test_mapping_lookup():
    print("\n--- Testing Mapping Lookup ---")
    try:
        # Testing with a dummy query
        response = requests.get(f"{BASE_URL}/lookup/mapping?query=Thủ Đức")
        print(f"Status: {response.status_code}")
        print(f"Results Count: {len(response.json())}")
        if len(response.json()) > 0:
            print(f"First Result: {json.dumps(response.json()[0], indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Ensure server is running before running this
    test_nso_sync()
    test_mapping_lookup()

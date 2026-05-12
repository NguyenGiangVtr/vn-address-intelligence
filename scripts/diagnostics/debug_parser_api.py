import requests
import json

url = "http://localhost:8081/api/parser/analyze?model=phobert"
payload = {
    "raw_address": "123 Lê Lợi, Quận 1, HCM"
}
headers = {
    "Content-Type": "application/json"
}

# Note: We need a token if it's protected, but /api/parser/analyze doesn't seem to have Depends(get_current_user)
# Let's check server.py again. 
# Line 1293: def analyze_parser_address(data: dict, model: Optional[str] = None, db: Session = Depends(get_db)):
# No Depends(get_current_user)!

try:
    response = requests.post(url, json=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    if response.status_code != 200:
        print(f"Response: {response.text}")
    else:
        print("Success!")
except Exception as e:
    print(f"Error: {e}")

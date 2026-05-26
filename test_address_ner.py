import requests
import json

url = "http://localhost:8081/api/parser/analyze?model=address_ner"
data = {"raw_address": "268 Ly Thuong Kiet, Phuong Dien Hong, Ho Chi Minh"}

print("Testing address_ner model...\n")
response = requests.post(url, json=data, timeout=30)

print(f"Status: {response.status_code}")
print(f"\nFull response:")
print(json.dumps(response.json(), indent=2, ensure_ascii=False))

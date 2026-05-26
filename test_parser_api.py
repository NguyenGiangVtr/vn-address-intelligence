import requests
import json

url = "http://localhost:8081/api/parser/analyze?model=prelabeler"
data = {"raw_address": "268 Ly Thuong Kiet, Phuong Dien Hong, Ho Chi Minh"}

try:
    print("Sending request...")
    response = requests.post(url, json=data, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Content length: {len(response.text)}")
    if response.status_code == 200:
        result = response.json()
        print(f"Keys: {list(result.keys())}")
        if 'outputs' in result:
            print(f"Outputs: {list(result['outputs'].keys())}")
            if 'prelabeler' in result['outputs']:
                prelabeler = result['outputs']['prelabeler']
                print(f"PreLabeler result: {prelabeler.get('result', [])[:3]}...")  # First 3 entities
    else:
        print(f"Error: {response.text[:500]}")
except Exception as e:
    print(f"Exception: {e}")

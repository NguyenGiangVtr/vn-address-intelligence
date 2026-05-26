import requests
import json

url = "http://localhost:8081/api/parser/analyze?model=prelabeler"
data = {"raw_address": "268 Ly Thuong Kiet, Phuong Dien Hong, Ho Chi Minh"}

print("Testing PreLabeler API...")
print(f"URL: {url}")
print(f"Data: {data}\n")

try:
    response = requests.post(url, json=data, timeout=10)
    print(f"Status: {response.status_code}\n")
    
    result = response.json()
    
    # Check structure
    print("=== Response Structure ===")
    print(f"Keys: {list(result.keys())}\n")
    
    if 'outputs' in result:
        print(f"Outputs keys: {list(result['outputs'].keys())}\n")
        
        if 'prelabeler' in result['outputs']:
            prelabeler = result['outputs']['prelabeler']
            print("=== PreLabeler Output ===")
            print(f"Mode: {prelabeler.get('mode')}")
            print(f"Entity Count: {prelabeler.get('entityCount')}")
            
            if 'result' in prelabeler and prelabeler['result']:
                print(f"\n=== Entities ({len(prelabeler['result'])}) ===")
                for i, entity in enumerate(prelabeler['result'][:5]):  # First 5
                    label = entity.get('label') or (entity.get('value', {}).get('labels', ['?'])[0])
                    text = entity.get('text') or entity.get('value', {}).get('text', '?')
                    print(f"{i+1}. {label}: {text}")
                    
                print("\n=== Full Entity Structure (first one) ===")
                print(json.dumps(prelabeler['result'][0], indent=2, ensure_ascii=False))
    
    if 'error' in result:
        print(f"\n=== Error ===")
        print(result['error'])
    
    print("\n=== Full Response (truncated) ===")
    response_str = json.dumps(result, indent=2, ensure_ascii=False)
    print(response_str[:1000] + "..." if len(response_str) > 1000 else response_str)
    
except Exception as e:
    print(f"Exception: {e}")
    import traceback
    traceback.print_exc()

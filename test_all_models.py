import requests
import json

# Test all models
url_base = "http://localhost:8081/api/parser/analyze"
data = {"raw_address": "268 Ly Thuong Kiet, Phuong Dien Hong, Ho Chi Minh"}

models = ["prelabeler", "address_ner", "phobert", "mgte", "llm"]

print("Testing parser API for all models...\n")

for model in models:
    try:
        print(f"Testing {model}...")
        response = requests.post(f"{url_base}?model={model}", json=data, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            if 'outputs' in result and model in result['outputs']:
                output = result['outputs'][model]
                if 'error' in output:
                    print(f"  [ERROR] {model}: {output['error']}")
                elif 'result' in output:
                    print(f"  [OK] {model}: {len(output['result'])} entities")
                elif 'normalizedAddress' in output:
                    print(f"  [OK] {model}: {output['normalizedAddress'][:50]}...")
                else:
                    print(f"  [OK] {model}: Response received")
            else:
                print(f"  [WARN] {model}: No output in response")
        elif response.status_code == 503:
            error = response.json()
            print(f"  [LOADING] {model}: {error.get('detail', {}).get('note', 'Loading...')}")
        else:
            print(f"  [ERROR] {model}: HTTP {response.status_code}")
            
    except requests.Timeout:
        print(f"  [TIMEOUT] {model}: Timeout (>60s)")
    except Exception as e:
        print(f"  [ERROR] {model}: {str(e)[:100]}")
    
print("\n[DONE] API test complete!")

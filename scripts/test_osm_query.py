import requests
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')

def test_query(area_name, level):
    print(f"Testing {area_name} (Level {level})...")
    query = f"""[out:json][timeout:90];
area["name"~"{area_name}"]["admin_level"="{level}"]->.searchArea;
(node["name"](area.searchArea);way["name"](area.searchArea););
out body 50;"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json'
    }
    
    try:
        r = requests.get('https://overpass-api.de/api/interpreter', params={'data': query}, headers=headers, timeout=30)
        print(f"  Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            elements = data.get("elements", [])
            print(f"  Elements found: {len(elements)}")
        else:
            print(f"  Error: {r.text[:200]}")
    except Exception as e:
        print(f"  Exception: {e}")

test_query("Ba Đình", "7")
test_query("Thanh Xuân", "7")

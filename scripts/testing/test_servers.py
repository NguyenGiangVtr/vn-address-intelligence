import requests
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')

def test_server(url):
    print(f"Testing {url}...")
    query = '[out:json];node(1);out;'
    try:
        r = requests.get(url, params={'data': query}, timeout=10)
        print(f"  Status: {r.status_code}")
    except Exception as e:
        print(f"  Exception: {e}")

test_server('https://overpass-api.de/api/interpreter')
test_server('https://lz4.overpass-api.de/api/interpreter')
test_server('https://overpass.kumi.systems/api/interpreter')
test_server('https://overpass.osm.ch/api/interpreter')

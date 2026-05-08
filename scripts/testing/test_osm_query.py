import requests
import sys
import pytest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')

@pytest.mark.parametrize(
    ("area_name", "level"),
    [("Ba Đình", "7"), ("Thanh Xuân", "7")],
)
def test_query(area_name, level):
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
        if r.status_code != 200:
            pytest.skip(f"Overpass API returned {r.status_code}")
        data = r.json()
        assert "elements" in data
    except requests.RequestException as exc:
        pytest.skip(f"Overpass API unavailable: {exc}")

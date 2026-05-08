import requests
import sys
import pytest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')

@pytest.mark.parametrize(
    "url",
    [
        "https://overpass-api.de/api/interpreter",
        "https://lz4.overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.osm.ch/api/interpreter",
    ],
)
def test_server(url):
    query = '[out:json];node(1);out;'
    try:
        r = requests.get(url, params={'data': query}, timeout=10)
        if r.status_code != 200:
            pytest.skip(f"{url} returned {r.status_code}")
    except requests.RequestException as exc:
        pytest.skip(f"Server unavailable {url}: {exc}")

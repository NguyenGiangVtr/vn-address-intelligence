"""
Tim nguon du lieu population + area_km2 cho 63 tinh
Va update vao database cho admin_version = 1 (truoc sap nhap)
"""
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import urllib.request, json

# Thu nhieu nguon khac nhau
sources = [
    ('dvhcvn main', 'https://raw.githubusercontent.com/daohoangson/dvhcvn/refs/heads/master/data/data.json'),
    ('hanhchinhvn', 'https://raw.githubusercontent.com/ThanhPhamit/hanhchinhvn/master/tinh_tp.json'),
    ('vn-hanh-chinh', 'https://raw.githubusercontent.com/madnh/hanhchinhvn/master/dist/tinh_tp.json'),
    ('vndivision', 'https://raw.githubusercontent.com/VNOpenMap/administrative-divisions-of-vietnam/master/provinces.json'),
    ('provinces2', 'https://raw.githubusercontent.com/kenzouno1/DiaGioiHanhChinhVN/master/data.json'),
]

for name, url in sources:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read()
        data = json.loads(raw)
        
        # Kiem tra co population/area khong
        sample = data[0] if isinstance(data, list) else list(data.values())[0]
        keys = list(sample.keys()) if isinstance(sample, dict) else []
        has_pop = any('pop' in k.lower() or 'dan' in k.lower() for k in keys)
        has_area = any('area' in k.lower() or 'dien' in k.lower() for k in keys)
        
        print(f'[{name}] OK, {len(data)} items, keys={keys[:8]}')
        print(f'  population={has_pop}, area={has_area}')
        if has_pop or has_area:
            print(f'  SAMPLE: {json.dumps(sample, ensure_ascii=False)[:300]}')
    except Exception as e:
        print(f'[{name}] FAIL: {e}')

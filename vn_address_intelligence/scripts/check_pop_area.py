import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from src.database import engine
from sqlalchemy import text
import pandas as pd

base = os.path.join(os.path.dirname(__file__), '..', 'data', 'seed')

print("=" * 60)
print("DB: population / area_km2 status")
print("=" * 60)

with engine.connect() as conn:
    for tbl in ['mat.province', 'mat.district', 'mat.ward']:
        total = conn.execute(text(f'SELECT COUNT(*) FROM {tbl}')).scalar()
        try:
            has_pop = conn.execute(text(f'SELECT COUNT(*) FROM {tbl} WHERE population IS NOT NULL AND population > 0')).scalar()
            has_area = conn.execute(text(f'SELECT COUNT(*) FROM {tbl} WHERE area_km2 IS NOT NULL AND area_km2 > 0')).scalar()
        except Exception as e:
            has_pop = f'ERROR: {e}'
            has_area = 'ERROR'
        print(f'{tbl}: total={total} | population filled={has_pop} | area_km2 filled={has_area}')

print()
print("=" * 60)
print("CSV: kiem tra cac file co population/area_km2 khong")
print("=" * 60)

files = [
    'province_admin_version_2.csv',
    'district_admin_version_2.csv',
    'ward_admin_version_2.csv',
    'nso-gov-province_25_04_2026.csv',
    'nso-gov-ward_25_04_2026.csv',
]

for fname in files:
    fp = os.path.join(base, fname)
    if not os.path.exists(fp):
        print(f'{fname}: NOT FOUND')
        continue
    try:
        df = pd.read_csv(fp, nrows=2)
        cols = list(df.columns)
        pop_cols = [c for c in cols if 'pop' in c.lower() or 'dan' in c.lower() or 'dan_so' in c.lower()]
        area_cols = [c for c in cols if 'area' in c.lower() or 'dien' in c.lower() or 'km' in c.lower()]
        print(f'{fname}: {len(cols)} cols | pop_related={pop_cols} | area_related={area_cols}')
        print(f'  All cols: {cols}')
    except:
        try:
            df = pd.read_csv(fp, nrows=2, encoding='latin1')
            cols = list(df.columns)
            print(f'{fname} (latin1): {cols}')
        except Exception as e:
            print(f'{fname}: ERROR - {e}')

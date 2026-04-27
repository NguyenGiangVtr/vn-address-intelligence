import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
from src.database import engine
from sqlalchemy import text

base = os.path.join(os.path.dirname(__file__), '..', 'data', 'seed')

# Province GSO
df_p = pd.read_csv(os.path.join(base, 'nso-gov-province_25_04_2026.csv'), encoding='latin1', on_bad_lines='skip')
print("Province CSV cols:", list(df_p.columns))
print("Province CSV codes (col[0]):", df_p.iloc[:5, 0].tolist())

# Ward GSO
df_w = pd.read_csv(os.path.join(base, 'nso-gov-ward_25_04_2026.csv'), encoding='latin1', on_bad_lines='skip')
print("\nWard CSV cols:", list(df_w.columns))
print("Ward CSV codes (col[0]):", df_w.iloc[:5, 0].tolist())
if len(df_w.columns) > 6:
    print("Ward CSV province codes (col[6]):", df_w.iloc[:5, 6].tolist())

# DB codes
with engine.connect() as conn:
    rows = conn.execute(text("SELECT province_id, province_no, province_no FROM mat.province WHERE admin_version=1 LIMIT 5")).fetchall()
    print("\nDB Province v1 codes:", [(r[0], r[1], r[2]) for r in rows])
    
    rows = conn.execute(text("SELECT province_id, province_no, province_no FROM mat.province WHERE admin_version=2 LIMIT 5")).fetchall()
    print("DB Province v2 codes:", [(r[0], r[1], r[2]) for r in rows])
    
    rows = conn.execute(text("SELECT ward_id, ward_no FROM mat.ward WHERE admin_version=2 LIMIT 5")).fetchall()
    print("\nDB Ward v2 codes:", [(r[0], r[1]) for r in rows])

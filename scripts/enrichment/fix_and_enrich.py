"""
Script tong hop: Fix NaN + Enrich GSO Gov data
1. Fix NaN trong province_no (34 provinces v2)
2. Chay enrichment tu file GSO Gov cho province va ward
3. Kiem tra ket qua
"""
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np
import re
from src.database import engine
from sqlalchemy import text

# ==============================
# STEP 1: Fix NaN trong 3 bang mat
# ==============================
print("=" * 60)
print("STEP 1: Fixing NaN values in mat tables")
print("=" * 60)

with engine.connect() as conn:
    # Fix province_no = 'nan' -> NULL
    result = conn.execute(text("UPDATE mat.province SET province_no = NULL WHERE province_no = 'nan'"))
    print(f"Fixed {result.rowcount} provinces with province_no='nan'")
    
    # Fix bat ky cot nao co gia tri 'nan' (string) trong province
    for col in ['served_radius', 'north_pole_lat', 'north_pole_lng', 'east_pole_lat', 'east_pole_lng', 
                'south_pole_lat', 'south_pole_lng', 'west_pole_lat', 'west_pole_lng']:
        try:
            r = conn.execute(text(f"UPDATE mat.province SET {col} = NULL WHERE {col}::text = 'NaN'"))
            if r.rowcount > 0: print(f"  Fixed {r.rowcount} rows in province.{col}")
        except: pass
    
    # Fix district
    for col in ['district_no', 'sfdc_id', 'type_name_en']:
        try:
            r = conn.execute(text(f"UPDATE mat.district SET {col} = NULL WHERE {col} = 'nan'"))
            if r.rowcount > 0: print(f"  Fixed {r.rowcount} rows in district.{col}")
        except: pass
    
    # Fix ward
    for col in ['ward_no', 'type_name_en']:
        try:
            r = conn.execute(text(f"UPDATE mat.ward SET {col} = NULL WHERE {col} = 'nan'"))
            if r.rowcount > 0: print(f"  Fixed {r.rowcount} rows in ward.{col}")
        except: pass
    
    conn.commit()
    print("STEP 1 DONE\n")

# ==============================
# STEP 2: Enrichment GSO Gov
# ==============================
print("=" * 60)
print("STEP 2: Enriching data from GSO Gov CSVs")
print("=" * 60)

def safe_read_csv(fp):
    for enc in ['utf-8', 'latin1', 'cp1252', 'utf-16']:
        try:
            return pd.read_csv(fp, encoding=enc, on_bad_lines='skip')
        except: continue
    raise Exception(f"Cannot read {fp}")

def parse_decision(txt):
    if not txt or pd.isna(txt): return None, None
    s = str(txt)
    num_m = re.search(r'(\d+/[^\s,;-]+)', s)
    dec_num = num_m.group(1) if num_m else s[:100]
    date_m = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', s)
    dec_date = None
    if date_m:
        try: dec_date = pd.to_datetime(date_m.group(1), dayfirst=True)
        except: pass
    return dec_num, dec_date

base = os.path.join(os.path.dirname(__file__), '..', 'data', 'seed')

# Enrich Provinces
prov_file = os.path.join(base, 'nso-gov-province_25_04_2026.csv')
if os.path.exists(prov_file):
    df = safe_read_csv(prov_file)
    cols = list(df.columns)
    code_col = cols[0]  # First column is Ma
    decision_col = cols[4] if len(cols) > 4 else None  # Nghi dinh
    notes_col = cols[5] if len(cols) > 5 else None  # Ghi chu
    
    with engine.connect() as conn:
        count = 0
        for _, row in df.iterrows():
            code = str(row[code_col]).strip().zfill(2)
            if code == 'nan' or code == '00' or not code.isdigit(): continue
            
            dec_num, dec_date = parse_decision(row[decision_col] if decision_col else None)
            notes = str(row[notes_col]).strip() if notes_col and pd.notna(row[notes_col]) else None
            
            r = conn.execute(text("""
                UPDATE mat.province SET decision_number = :dn, decision_date = :dd, notes = :n
                WHERE province_no = :c OR province_id::text = :c
            """), {'dn': dec_num, 'dd': dec_date, 'n': notes, 'c': code})
            count += r.rowcount
        conn.commit()
        print(f"Enriched {count} provinces")
else:
    print(f"Province file not found: {prov_file}")

# Enrich Wards
ward_file = os.path.join(base, 'nso-gov-ward_25_04_2026.csv')
if os.path.exists(ward_file):
    df = safe_read_csv(ward_file)
    cols = list(df.columns)
    code_col = cols[0]       # Ma ward
    decision_col = cols[4] if len(cols) > 4 else None
    notes_col = cols[5] if len(cols) > 5 else None
    prov_code_col = cols[6] if len(cols) > 6 else None  # Ma TP (province code)
    
    with engine.connect() as conn:
        count = 0
        for i, row in df.iterrows():
            code = str(row[code_col]).strip().zfill(5)
            if not code[:5].isdigit(): continue
            
            dec_num, dec_date = parse_decision(row[decision_col] if decision_col else None)
            notes = str(row[notes_col]).strip() if notes_col and pd.notna(row[notes_col]) else None
            
            p_code = str(row[prov_code_col]).strip().zfill(2) if prov_code_col and pd.notna(row[prov_code_col]) else None
            
            if p_code and p_code.isdigit():
                r = conn.execute(text("""
                    UPDATE mat.ward w SET decision_number = :dn, decision_date = :dd, notes = :n
                    FROM mat.district d, mat.province p
                    WHERE w.district_id = d.district_id AND d.province_id = p.province_id
                      AND (w.ward_no = :c OR w.ward_id::text = :c)
                      AND (p.province_no = :pc OR p.province_id::text = :pc)
                """), {'dn': dec_num, 'dd': dec_date, 'n': notes, 'c': code, 'pc': p_code})
            else:
                r = conn.execute(text("""
                    UPDATE mat.ward SET decision_number = :dn, decision_date = :dd, notes = :n
                    WHERE ward_no = :c OR ward_id::text = :c
                """), {'dn': dec_num, 'dd': dec_date, 'n': notes, 'c': code})
            count += r.rowcount
            
            if i > 0 and i % 1000 == 0:
                conn.commit()
                print(f"  Processed {i} wards ({count} updated)...")
        conn.commit()
        print(f"Enriched {count} wards total")
else:
    print(f"Ward file not found: {ward_file}")

# ==============================
# STEP 3: Verification
# ==============================
print("\n" + "=" * 60)
print("STEP 3: Verification")
print("=" * 60)

with engine.connect() as conn:
    checks = {
        "Provinces total": "SELECT COUNT(*) FROM mat.province",
        "Provinces v1": "SELECT COUNT(*) FROM mat.province WHERE admin_version=1 OR admin_version IS NULL",
        "Provinces v2": "SELECT COUNT(*) FROM mat.province WHERE admin_version=2",
        "Provinces enriched": "SELECT COUNT(*) FROM mat.province WHERE decision_number IS NOT NULL",
        "Provinces NaN code": "SELECT COUNT(*) FROM mat.province WHERE province_no = 'nan'",
        "Districts total": "SELECT COUNT(*) FROM mat.district",
        "Districts v2": "SELECT COUNT(*) FROM mat.district WHERE admin_version=2",
        "Wards total": "SELECT COUNT(*) FROM mat.ward",
        "Wards v2": "SELECT COUNT(*) FROM mat.ward WHERE admin_version=2",
        "Wards enriched": "SELECT COUNT(*) FROM mat.ward WHERE decision_number IS NOT NULL",
        "Ward Mappings": "SELECT COUNT(*) FROM mat.ward_mapping",
        "OSM raw_entities": "SELECT COUNT(*) FROM osm.raw_entities",
        "OSM streets": "SELECT COUNT(*) FROM osm.streets",
        "OSM buildings": "SELECT COUNT(*) FROM osm.buildings",
        "OSM pois": "SELECT COUNT(*) FROM osm.pois",
        "Training datasets": "SELECT COUNT(*) FROM ath.training_datasets",
        "Address queue": "SELECT COUNT(*) FROM prq.address_cleansing_queue",
    }
    for name, q in checks.items():
        val = conn.execute(text(q)).scalar()
        print(f"  {name:30}: {val:>10}")

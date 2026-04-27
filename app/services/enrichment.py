"""
services/enrichment.py
======================
Bổ sung thông tin hành chính từ các file dữ liệu NSO/GSO.

Ví dụ thực thi mẫu:
------------------
from app.services.enrichment import check_enrichment_stats
stats = check_enrichment_stats()
print(stats)
"""
import pandas as pd
import numpy as np
import logging
import re
from app.core.database import engine
from sqlalchemy import text as sql_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EnrichmentV2")

def safe_read_csv(file_path):
    """Thử nhiều encoding để đọc CSV an toàn."""
    for enc in ['utf-8', 'latin1', 'cp1252', 'utf-16']:
        try:
            df = pd.read_csv(file_path, encoding=enc, on_bad_lines='skip')
            logger.info(f"Successfully read {file_path} with {enc} encoding.")
            return df
        except:
            continue
    raise Exception(f"Could not read {file_path} with any common encoding.")

def parse_decision(text):
    if not text or pd.isna(text): return None, None
    num_match = re.search(r'(\d+/[^-\s,;]+)', str(text))
    decision_num = num_match.group(1) if num_match else str(text)[:100]
    date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', str(text))
    decision_date = None
    if date_match:
        try:
            decision_date = pd.to_datetime(date_match.group(1), dayfirst=True)
        except: pass
    return decision_num, decision_date

def enrich_provinces(file_path):
    logger.info(f"Enriching provinces from {file_path}...")
    df = safe_read_csv(file_path)
    
    with engine.connect() as conn:
        for _, row in df.iterrows():
            # Thử các tên cột phổ biến
            code_col = [c for c in df.columns if c.startswith('M')][0]
            code = str(row.get(code_col, '')).zfill(2)
            if not code or code == 'nan' or code == '00': continue
            
            decision_text = row.get('Ngh? ??nh') or row.get('Nghị định') or row.get('Ngh? ?nh')
            notes = row.get('Ghi cho') or row.get('Ghi chú') or row.get('Ghi ch')
            
            dec_num, dec_date = parse_decision(decision_text)
            
            query = """
                UPDATE mat.province 
                SET decision_number = :num, decision_date = :date, notes = :notes, admin_version = 2
                WHERE province_no = :code OR province_id::text = :code
            """
            conn.execute(sql_text(query), {
                'num': dec_num, 'date': dec_date, 'notes': notes, 'code': code
            })
            conn.commit()

def enrich_wards(file_path):
    logger.info(f"Enriching wards from {file_path}...")
    df = safe_read_csv(file_path)

    with engine.connect() as conn:
        for i, row in df.iterrows():
            code_col = [c for c in df.columns if 'M' in c and 'TP' not in c][0]
            p_code_col = [c for c in df.columns if 'M' in c and 'TP' in c][0]
            
            code = str(row.get(code_col, '')).zfill(5)
            province_no = str(row.get(p_code_col, '')).zfill(2)
            
            if len(code) != 5 or code == '00nan': continue
            
            decision_text = row.get('Ngh? ??nh') or row.get('Nghị định') or row.get('Ngh? ?nh')
            notes = row.get('Ghi ch') or row.get('Ghi chú') or row.get('Ghi ch')
            
            dec_num, dec_date = parse_decision(decision_text)
            
            query = """
                UPDATE mat.ward w
                SET decision_number = :num, decision_date = :date, notes = :notes, admin_version = 2
                FROM mat.district d, mat.province p
                WHERE w.district_id = d.district_id 
                  AND d.province_id = p.province_id
                  AND (w.ward_no = :code OR w.ward_id::text = :code)
                  AND (p.province_no = :p_code OR p.province_id::text = :p_code)
            """
            conn.execute(sql_text(query), {
                'num': dec_num, 'date': dec_date, 'notes': notes, 
                'code': code, 'p_code': province_no
            })
            
            if i % 500 == 0:
                conn.commit()
                logger.info(f"Processed {i} wards...")
        conn.commit()

def check_enrichment_stats():
    with engine.connect() as conn:
        p_count = conn.execute(sql_text("SELECT COUNT(*) FROM mat.province WHERE decision_number IS NOT NULL")).scalar()
        w_count = conn.execute(sql_text("SELECT COUNT(*) FROM mat.ward WHERE decision_number IS NOT NULL")).scalar()
        return {"Enriched Provinces": p_count, "Enriched Wards": w_count}

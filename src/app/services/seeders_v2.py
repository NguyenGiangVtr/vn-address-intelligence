"""
services/seeders_v2.py
======================
Nạp dữ liệu hành chính phiên bản 2 (Hỗ trợ 2025+).

Ví dụ thực thi mẫu:
------------------
from app.services.seeders_v2 import check_v2_stats
print(check_v2_stats())
"""
import pandas as pd
import numpy as np
import logging
import os
from app.core.database import engine, SessionLocal
from sqlalchemy import text as sql_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SeederV2")

def clean_dataframe(df):
    """Xử lý triệt để NaN, Inf và các kiểu dữ liệu không hợp lệ cho Postgres."""
    # Thay thế NaN, Inf bằng None (NULL trong DB)
    df = df.replace([np.nan, np.inf, -np.inf], None)
    
    # Một số trường hợp đặc biệt của Pandas/Numpy
    return df.where(pd.notnull(df), None)

def seed_admin_v2(file_path, table_name, id_col):
    """Nạp dữ liệu admin version 2 vào bảng tương ứng."""
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return

    logger.info(f"Seeding {table_name} from {file_path}...")
    df = pd.read_csv(file_path)
    df = clean_dataframe(df)
    
    with engine.connect() as conn:
        for i in range(0, len(df), 500): # Giảm chunk size để dễ debug
            chunk = df.iloc[i:i+500]
            records = chunk.to_dict(orient='records')
            
            cols = ", ".join(chunk.columns)
            placeholders = ", ".join([f":{c}" for c in chunk.columns])
            
            update_set = ", ".join([f"{c} = EXCLUDED.{c}" for c in chunk.columns if c != id_col])
            
            query = f"""
                INSERT INTO {table_name} ({cols}) 
                VALUES ({placeholders}) 
                ON CONFLICT ({id_col}) DO UPDATE SET {update_set}
            """
            try:
                conn.execute(sql_text(query), records)
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Error seeding batch at row {i} in {table_name}: {e}")
                raise e
    logger.info(f"Done seeding {table_name}.")

def seed_ward_mapping(file_path):
    """Nạp dữ liệu ánh xạ xã (ward_mapping)."""
    if not os.path.exists(file_path): return
    
    logger.info(f"Seeding mat.ward_mapping from {file_path}...")
    df = pd.read_csv(file_path)
    df = clean_dataframe(df)
    
    with engine.connect() as conn:
        for i in range(0, len(df), 1000):
            chunk = df.iloc[i:i+1000]
            cols = ", ".join(chunk.columns)
            placeholders = ", ".join([f":{c}" for c in chunk.columns])
            query = f"""
                INSERT INTO mat.ward_mapping ({cols}) VALUES ({placeholders})
                ON CONFLICT (ward_mapping_id) DO NOTHING
            """
            conn.execute(sql_text(query), chunk.to_dict(orient='records'))
            conn.commit()
    logger.info("Done seeding mat.ward_mapping.")

def check_v2_stats():
    """Kiểm tra thống kê dữ liệu sau khi nạp."""
    queries = {
        "Provinces V2": "SELECT COUNT(*) FROM mat.province WHERE admin_version = 2",
        "Districts V2": "SELECT COUNT(*) FROM mat.district WHERE admin_version = 2",
        "Wards V2": "SELECT COUNT(*) FROM mat.ward WHERE admin_version = 2",
        "Ward Mappings": "SELECT COUNT(*) FROM mat.ward_mapping"
    }
    stats = {}
    with engine.connect() as conn:
        for name, q in queries.items():
            try:
                stats[name] = conn.execute(sql_text(q)).scalar()
            except:
                stats[name] = "Error/Missing Table"
    return stats

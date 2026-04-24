import pandas as pd
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text
from .database import engine, SessionLocal, Province, District, Ward
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Seeders")

def seed_master_data(data_dir: str):
    """
    Import Master Data từ CSV/JSON vào schema 'mat'.
    Xóa dữ liệu cũ trước khi nạp mới để tránh trùng ID.
    """
    session = SessionLocal()
    data_path = Path(data_dir)
    
    try:
        # Xóa dữ liệu cũ (Theo thứ tự Ward -> District -> Province để tránh lỗi FK)
        session.execute(text("TRUNCATE TABLE mat.ward, mat.district, mat.province CASCADE"))
        session.commit()
        logger.info("🧹 Đã xóa sạch dữ liệu cũ trong mat schema.")

        # 1. Seed Provinces
        province_file = data_path / "province.csv"
        if province_file.exists():
            df = pd.read_csv(province_file)
            # Thay thế NaN bằng None để SQLAlchemy hiểu là NULL
            df = df.where(pd.notnull(df), None)
            provinces = [Province(**row) for row in df.to_dict(orient="records")]
            session.bulk_save_objects(provinces)
            logger.info(f"OK: Seeded {len(provinces)} provinces.")
        
        # 2. Seed Districts
        district_file = data_path / "district.csv"
        if district_file.exists():
            df = pd.read_csv(district_file)
            df = df.where(pd.notnull(df), None)
            districts = [District(**row) for row in df.to_dict(orient="records")]
            session.bulk_save_objects(districts)
            logger.info(f"OK: Seeded {len(districts)} districts.")
            
        # 3. Seed Wards
        ward_file = data_path / "ward.csv"
        if ward_file.exists():
            df = pd.read_csv(ward_file)
            df = df.where(pd.notnull(df), None)
            wards = [Ward(**row) for row in df.to_dict(orient="records")]
            session.bulk_save_objects(wards)
            logger.info(f"OK: Seeded {len(wards)} wards.")

        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Error seeding: {e}")
    finally:
        session.close()

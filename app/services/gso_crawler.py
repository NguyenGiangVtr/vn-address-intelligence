import pandas as pd
import logging
import requests
from app.core.database import SessionLocal, Province, District, Ward
from sqlalchemy import text as sql_text
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GSOCrawler")

class GSOCrawler:
    """
    Crawler để lấy dữ liệu hành chính từ GSO (danhmuchanhchinh.nso.gov.vn).
    Hỗ trợ admin_version = 2 (Sau sáp nhập 2025).
    """
    
    def __init__(self):
        self.url = "https://danhmuchanhchinh.nso.gov.vn/Default.aspx"
        # Định nghĩa các cột matching giữa Excel GSO và Database VNAI
        self.mapping = {
            'Mã': 'code',
            'Tên': 'name',
            'Tên Tiếng Anh': 'name_en',
            'Cấp': 'type',
            'Nghị định': 'decision_number',
            'Ghi chú': 'notes',
            'Dân số': 'population',
            'Diện tích': 'area_km2',
            'Ngày Quyết định': 'decision_date'
        }

    def import_from_excel(self, file_path, level='ward'):
        """
        Import dữ liệu từ file Excel tải về từ GSO.
        level: 'province', 'district', 'ward'
        """
        logger.info(f"Importing {level} data from {file_path}...")
        df = pd.read_excel(file_path, skiprows=2) # Thường Excel GSO có header trống ở trên
        
        session = SessionLocal()
        try:
            total = 0
            for _, row in df.iterrows():
                # Xử lý dữ liệu thô từ Excel
                data = {
                    'admin_version': 2,
                    'population': self._clean_number(row.get('Dân số')),
                    'area_km2': self._clean_number(row.get('Diện tích')),
                    'decision_number': str(row.get('Nghị định')) if pd.notna(row.get('Nghị định')) else None,
                    'notes': str(row.get('Ghi chú')) if pd.notna(row.get('Ghi chú')) else None,
                }
                
                # Logic update vào database dựa trên mã GSO
                code = str(row.get('Mã')).zfill(2 if level=='province' else 3 if level=='district' else 5)
                
                if level == 'province':
                    self._update_province(session, code, data)
                elif level == 'district':
                    self._update_district(session, code, data)
                elif level == 'ward':
                    self._update_ward(session, code, data)
                
                total += 1
                if total % 100 == 0:
                    logger.info(f"Processed {total} {level}s...")
            
            session.commit()
            logger.info(f"SUCCESS: Imported {total} {level}s.")
        except Exception as e:
            session.rollback()
            logger.error(f"Error importing GSO data: {e}")
        finally:
            session.close()

    def _clean_number(self, val):
        if pd.isna(val) or val == '': return 0
        try:
            return float(str(val).replace(',', '').replace(' ', ''))
        except:
            return 0

    def _update_province(self, session, code, data):
        # Province code trong mat.province thường là 2 chữ số (String)
        session.execute(sql_text("""
            UPDATE mat.province 
            SET admin_version = :admin_version, population = :population, area_km2 = :area_km2,
                decision_number = :decision_number, notes = :notes
            WHERE province_code = :code OR province_id::text = :code
        """), {**data, 'code': code})

    def _update_district(self, session, code, data):
        session.execute(sql_text("""
            UPDATE mat.district 
            SET admin_version = :admin_version, population = :population, area_km2 = :area_km2,
                decision_number = :decision_number, notes = :notes
            WHERE district_no = :code OR district_id::text = :code
        """), {**data, 'code': code})

    def _update_ward(self, session, code, data):
        session.execute(sql_text("""
            UPDATE mat.ward 
            SET admin_version = :admin_version, population = :population, area_km2 = :area_km2,
                decision_number = :decision_number, notes = :notes
            WHERE ward_no = :code OR ward_id::text = :code
        """), {**data, 'code': code})

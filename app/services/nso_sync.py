"""
services/nso_sync.py
====================
Đồng bộ dữ liệu hành chính từ NSO vào Database.

Ví dụ thực thi mẫu:
------------------
from app.services.nso_sync import sync_province_nso
from app.core.database import SessionLocal
db = SessionLocal()
# sync_province_nso(db, "01", "Thành phố Hà Nội")
"""
import requests
import xml.etree.ElementTree as ET
from sqlalchemy.orm import Session
from app.core.database import Province, District, Ward
from datetime import datetime
from app.services.nso_api import get_nso_provinces, get_nso_districts, get_nso_wards

# Global log store for real-time reporting
sync_logs = []

def add_log(message, level="info"):
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    log_entry = {"time": timestamp, "message": message, "level": level}
    sync_logs.append(log_entry)
    # Keep only last 100 logs
    if len(sync_logs) > 100:
        sync_logs.pop(0)

def sync_province_nso(db: Session, p_no_str: str, p_name: str):
    """Đồng bộ một tỉnh cụ thể và các huyện, xã của nó"""
    now = datetime.now()
    stats = {
        "districts_created": 0, "districts_updated": 0,
        "wards_created": 0, "wards_updated": 0
    }
    
    try:
        add_log(f"Bắt đầu đồng bộ Tỉnh: {p_name} ({p_no_str})", "info")
        
        # 1. Đảm bảo Tỉnh tồn tại trong v2
        p_no = p_no_str
        p_db = db.query(Province).filter(Province.province_no == p_no, Province.admin_version == 2).first()
        
        if not p_db:
            # Lấy thông tin loại hình từ danh sách tỉnh
            all_p = get_nso_provinces()
            this_p = next((x for x in all_p if x.get("MaTinh") == p_no_str), {})
            p_db = Province(
                province_no=p_no, 
                province_name=p_name, 
                admin_version=2, 
                type_name=this_p.get("LoaiHinh", "Tỉnh")
            )
            db.add(p_db)
            db.flush()
            add_log(f"Đã tạo Tỉnh mới: {p_name}", "success")
        else:
            # Luôn cập nhật thông tin mới nhất
            p_db.province_name = p_name
            p_db.province_no = p_no     # Update MaTinh as string (preserving leading zeros)
            p_db.updated_date = now
            add_log(f"Đã cập nhật Tỉnh: {p_name} (Mã số: {p_no})", "info")
        
        db.commit() # Lưu tỉnh trước để lấy ID cho huyện

        # 2. Đồng bộ Quận/Huyện
        add_log(f"Đang tải danh sách Huyện cho {p_name}...", "info")
        nso_districts = get_nso_districts(province_no=p_no_str, province_name=p_name)
        add_log(f"Tìm thấy {len(nso_districts)} Huyện", "info")
        
        for d_nso in nso_districts:
            d_code = d_nso.get("MaQuanHuyen")
            d_name = d_nso.get("TenQuanHuyen")
            
            d_db = db.query(District).filter(District.district_no == d_code, District.admin_version == 2).first()
            if not d_db:
                # Fallback: Match by name if code is missing/wrong
                d_db = db.query(District).filter(District.district_name == d_name, District.province_id == p_db.province_id, District.admin_version == 2).first()
                if d_db:
                    d_db.district_no = d_code # Correct the code
            if not d_db:
                d_db = District(
                    district_no=d_code, 
                    district_name=d_name, 
                    province_id=p_db.province_id, 
                    admin_version=2, 
                    type_name=d_nso.get("LoaiHinh", "")
                )
                db.add(d_db)
                db.flush()
                stats["districts_created"] += 1
            else:
                d_db.district_name = d_name
                d_db.district_no = d_code # Update MaQuanHuyen
                d_db.province_id = p_db.province_id
                d_db.type_name = d_nso.get("LoaiHinh", "")
                d_db.updated_date = now
                stats["districts_updated"] += 1
            
            # 3. Đồng bộ Phường/Xã cho Huyện này
            nso_wards = get_nso_wards(province_no=p_no_str, province_name=p_name, district_no=d_code, district_name=d_name)
            for w_nso in nso_wards:
                w_code = w_nso.get("MaPhuongXa") or w_nso.get("MaXa")
                w_name = w_nso.get("TenPhuongXa") or w_nso.get("TenXa")
                
                w_db = db.query(Ward).filter(Ward.ward_no == w_code, Ward.admin_version == 2).first()
                if not w_db:
                    # Fallback: Match by name if code is missing/wrong
                    w_db = db.query(Ward).filter(Ward.ward_name == w_name, Ward.district_id == d_db.district_id, Ward.admin_version == 2).first()
                    if w_db:
                        w_db.ward_no = w_code # Correct the code
                if not w_db:
                    w_db = Ward(
                        ward_no=w_code, 
                        ward_name=w_name, 
                        district_id=d_db.district_id, 
                        admin_version=2, 
                        type_name=w_nso.get("LoaiHinh", "")
                    )
                    db.add(w_db)
                    stats["wards_created"] += 1
                else:
                    w_db.ward_name = w_name
                    w_db.ward_no = w_code # Update MaPhuongXa/MaXa
                    w_db.district_id = d_db.district_id
                    w_db.type_name = w_nso.get("LoaiHinh", "")
                    w_db.updated_date = now
                    stats["wards_updated"] += 1
            
            add_log(f"  - Xong Huyện: {d_name} (+{len(nso_wards)} xã)", "success")
            db.commit() 

        summary = f"Hoàn thành {p_name}: Huyện ({stats['districts_created']} mới, {stats['districts_updated']} cũ), Xã ({stats['wards_created']} mới, {stats['wards_updated']} cũ)"
        add_log(summary, "success")
        return {"status": "success", "stats": stats}
        
    except Exception as e:
        db.rollback()
        add_log(f"LỖI khi đồng bộ {p_name}: {str(e)}", "error")
        return {"status": "error", "message": str(e)}

def sync_full_nso(db: Session):
    """Đồng bộ toàn bộ (Hàm cũ, giờ gọi qua từng tỉnh)"""
    sync_logs.clear()
    add_log("Bắt đầu tiến trình đồng bộ TOÀN BỘ NSO", "warning")
    nso_provinces = get_nso_provinces()
    for p in nso_provinces:
        sync_province_nso(db, p.get("MaTinh"), p.get("TenTinh"))
    return {"status": "done"}

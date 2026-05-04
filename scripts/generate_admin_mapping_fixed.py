import os
import sys
import re
from sqlalchemy import text as sql_text

# Thêm thư mục gốc vào PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal, OldSessionLocal, create_all_tables

def remove_vietnamese_marks(s, strip_prefix=True):
    if not s: return ""
    s = str(s).lower().strip()
    unicode_map = {
        'a': 'àáạảãâầấậẩẫăằắặẳẵ', 'e': 'èéẹẻẽêềếệểễ', 'i': 'ìíịỉĩỳýỵỷỹ',
        'o': 'òóọỏõôồốộổỗơờớợởỡ', 'u': 'ùúụủũưừứựửữ', 'd': 'đ',
    }
    for char, accented_chars in unicode_map.items():
        for accented_char in accented_chars: s = s.replace(accented_char, char)
    if strip_prefix:
        prefixes = ['thanh pho', 'tinh', 'quan', 'huyen', 'thi xa', 'phuong', 'xa', 'thi tran']
        for p in prefixes: s = re.sub(rf'^{p}[\.\s]+', '', s)
    s = re.sub(r'[^a-z0-9]', '', s)
    return s

PROVINCE_ALIASES = {
    "thuathienhue": ["hue", "thanhphohue"],
    "hochiminh": ["tphcm", "saigon", "hanhphohochiminh"],
    "haiphong": ["hp"],
    "bariavungtau": ["vungtau", "vt"]
}

def get_best_match(matches, target_admin_version):
    if not matches: return None
    p1 = [m for m in matches if (not getattr(m, 'is_deleted', False)) and m.admin_version == target_admin_version]
    if p1: return p1[0]
    p2 = [m for m in matches if not getattr(m, 'is_deleted', False)]
    if p2: return p2[0]
    return matches[0]

def batch_update(db, table_name, id_col, updates):
    if not updates: return
    sql = sql_text(f"UPDATE {table_name} SET old_id = :old_id WHERE {id_col} = :new_id AND admin_version = :ver")
    db.execute(sql, updates)

def generate_mapping_fixed():
    print("Updating schema...")
    create_all_tables()
    new_db = SessionLocal(); old_db = OldSessionLocal()
    try:
        print("Resetting old_id in all tables...")
        new_db.execute(sql_text("UPDATE mat.province SET old_id = NULL"))
        new_db.execute(sql_text("UPDATE mat.district SET old_id = NULL"))
        new_db.execute(sql_text("UPDATE mat.ward SET old_id = NULL"))
        new_db.commit()

        print("Loading New DB data and building Global Lookups...")
        all_new_p = new_db.execute(sql_text("SELECT province_id, province_name, province_name_en, admin_version, is_deleted FROM mat.province")).fetchall()
        all_new_d = new_db.execute(sql_text("SELECT district_id, province_id, district_name, admin_version, is_deleted FROM mat.district")).fetchall()
        all_new_w = new_db.execute(sql_text("SELECT ward_id, district_id, ward_name, admin_version, is_deleted FROM mat.ward")).fetchall()

        dist_hierarchy = {}; dist_global_full = {}; dist_global_core = {}
        for d in all_new_d:
            dist_hierarchy.setdefault(d.province_id, []).append(d)
            dist_global_full.setdefault(remove_vietnamese_marks(d.district_name, strip_prefix=False), []).append(d)
            dist_global_core.setdefault(remove_vietnamese_marks(d.district_name), []).append(d)

        ward_hierarchy = {}; ward_global_full = {}; ward_global_core = {}
        for w in all_new_w:
            ward_hierarchy.setdefault(w.district_id, []).append(w)
            ward_global_full.setdefault(remove_vietnamese_marks(w.ward_name, strip_prefix=False), []).append(w)
            ward_global_core.setdefault(remove_vietnamese_marks(w.ward_name), []).append(w)

        # 1. Provinces
        print("Mapping Provinces...")
        old_p = old_db.execute(sql_text("SELECT province_id, province_name, admin_version FROM mat.province WHERE is_deleted = false")).fetchall()
        prov_map = {}; p_updates = []
        for op in old_p:
            op_norm = remove_vietnamese_marks(op.province_name)
            matches = [np for np in all_new_p if remove_vietnamese_marks(np.province_name_en or np.province_name) == op_norm or remove_vietnamese_marks(np.province_name) == op_norm]
            if not matches:
                for ak, aliases in PROVINCE_ALIASES.items():
                    if op_norm == ak or op_norm in aliases:
                        matches = [np for np in all_new_p if remove_vietnamese_marks(np.province_name_en or np.province_name) in ([ak] + aliases)]; break
            match = get_best_match(matches, op.admin_version)
            if match:
                p_updates.append({"old_id": op.province_id, "new_id": match.province_id, "ver": match.admin_version})
                prov_map[(op.province_id, op.admin_version)] = match.province_id
        batch_update(new_db, "mat.province", "province_id", p_updates)
        print(f"Mapped {len(p_updates)} Provinces.")

        # 2. Districts
        print("Mapping Districts...")
        old_d = old_db.execute(sql_text("SELECT district_id, province_id, district_name, type_name, admin_version FROM mat.district WHERE is_deleted = false")).fetchall()
        d_updates = []
        for od in old_d:
            parent_new_id = prov_map.get((od.province_id, od.admin_version))
            full_name = f"{od.type_name} {od.district_name}" if od.type_name and od.type_name not in od.district_name else od.district_name
            f_norm = remove_vietnamese_marks(full_name, strip_prefix=False)
            c_norm = remove_vietnamese_marks(od.district_name)
            matches = []
            if parent_new_id:
                cands = dist_hierarchy.get(parent_new_id, [])
                matches = [c for c in cands if remove_vietnamese_marks(c.district_name, strip_prefix=False) == f_norm]
                if not matches: matches = [c for c in cands if remove_vietnamese_marks(c.district_name) == c_norm]
            if not matches:
                matches = dist_global_full.get(f_norm, [])
                if not matches: matches = dist_global_core.get(c_norm, [])
            match = get_best_match(matches, od.admin_version)
            if match: d_updates.append({"old_id": od.district_id, "new_id": match.district_id, "ver": match.admin_version})
        batch_update(new_db, "mat.district", "district_id", d_updates)
        print(f"Mapped {len(d_updates)} Districts.")
        new_db.commit()

        # 3. Wards
        print("Mapping Wards...")
        dist_map = {(r.old_id, r.admin_version): r.district_id for r in new_db.execute(sql_text("SELECT district_id, old_id, admin_version FROM mat.district WHERE old_id IS NOT NULL")).fetchall()}
        old_w = old_db.execute(sql_text("SELECT ward_id, district_id, ward_name, type_name, admin_version FROM mat.ward WHERE is_deleted = false")).fetchall()
        w_updates = []
        for ow in old_w:
            parent_new_id = dist_map.get((ow.district_id, ow.admin_version))
            f_norm = remove_vietnamese_marks(f"{ow.type_name} {ow.ward_name}" if ow.type_name and ow.type_name not in ow.ward_name else ow.ward_name, strip_prefix=False)
            c_norm = remove_vietnamese_marks(ow.ward_name)
            matches = []
            if parent_new_id:
                cands = ward_hierarchy.get(parent_new_id, [])
                matches = [c for c in cands if remove_vietnamese_marks(c.ward_name, strip_prefix=False) == f_norm]
                if not matches: matches = [c for c in cands if remove_vietnamese_marks(c.ward_name) == c_norm]
            if not matches:
                matches = ward_global_full.get(f_norm, [])
                if not matches: matches = ward_global_core.get(c_norm, [])
            match = get_best_match(matches, ow.admin_version)
            if match: w_updates.append({"old_id": ow.ward_id, "new_id": match.ward_id, "ver": match.admin_version})
        
        # Batch update wards in chunks to avoid large memory usage or timeout
        chunk_size = 1000
        for i in range(0, len(w_updates), chunk_size):
            batch_update(new_db, "mat.ward", "ward_id", w_updates[i:i+chunk_size])
            print(f"Updated {min(i+chunk_size, len(w_updates))}/{len(w_updates)} Wards...")
        
        new_db.commit()
        print("Mapping completed successfully!")
        
        mapped_prov = new_db.execute(sql_text('SELECT COUNT(DISTINCT old_id) FROM mat.province WHERE old_id IS NOT NULL')).scalar()
        mapped_dist = new_db.execute(sql_text('SELECT COUNT(DISTINCT old_id) FROM mat.district WHERE old_id IS NOT NULL')).scalar()
        print(f"\nFinal Report: Provinces mapped: {mapped_prov}, Districts mapped: {mapped_dist}")
    finally:
        new_db.close(); old_db.close()

if __name__ == "__main__":
    generate_mapping_fixed()

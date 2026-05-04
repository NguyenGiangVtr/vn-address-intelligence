import re
from sqlalchemy import text as sql_text
from app.core.database import SessionLocal, OldSessionLocal, create_all_tables

def remove_vietnamese_marks(s, strip_prefix=True):
    if not s: return ""
    s = str(s).lower().strip()
    
    # 1. Hợp nhất y/i
    s = s.replace('y', 'i')
    
    # 2. Xử lý số La Mã phổ biến
    roman_map = {'viii': '8', 'vii': '7', 'iii': '3', 'ii': '2', 'vi': '6', 'iv': '4', 'ix': '9', 'v': '5', 'i': '1', 'x': '10'}
    words = s.split()
    s = " ".join([roman_map[w] if w in roman_map else w for w in words])
    
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
    p1 = [m for m in matches if m.admin_version == target_admin_version and (not getattr(m, 'is_deleted', False))]
    if p1: return p1[0]
    p2 = [m for m in matches if m.admin_version == target_admin_version]
    if p2: return p2[0]
    p3 = [m for m in matches if not getattr(m, 'is_deleted', False)]
    if p3: return p3[0]
    return matches[0]

def batch_update(db, table_name, id_col, updates):
    if not updates: return
    sql = sql_text(f"UPDATE {table_name} SET old_id = :old_id WHERE {id_col} = :new_id AND admin_version = :ver")
    db.execute(sql, updates)

def run_admin_mapping():
    """Logic mapping đồng bộ ID từ DB cũ sang DB mới (Internal old_id columns)"""
    new_db = SessionLocal(); old_db = OldSessionLocal()
    try:
        print("Resetting old_id columns...")
        new_db.execute(sql_text("UPDATE mat.province SET old_id = NULL; UPDATE mat.district SET old_id = NULL; UPDATE mat.ward SET old_id = NULL;"))
        new_db.commit()

        print("Loading data and building lookups...")
        all_new_p = new_db.execute(sql_text("SELECT province_id, province_name, province_name_en, admin_version, is_deleted FROM mat.province")).fetchall()
        all_new_d = new_db.execute(sql_text("SELECT district_id, province_id, district_name, admin_version, is_deleted FROM mat.district")).fetchall()
        all_new_w = new_db.execute(sql_text("SELECT ward_id, district_id, ward_name, admin_version, is_deleted FROM mat.ward")).fetchall()

        # Build Lookups
        dist_h = {}; dist_gf = {}; dist_gc = {}
        for d in all_new_d:
            dist_h.setdefault((d.province_id, d.admin_version), []).append(d)
            dist_gf.setdefault(remove_vietnamese_marks(d.district_name, strip_prefix=False), []).append(d)
            dist_gc.setdefault(remove_vietnamese_marks(d.district_name), []).append(d)

        ward_h = {}; ward_gf = {}; ward_gc = {}
        for w in all_new_w:
            ward_h.setdefault((w.district_id, w.admin_version), []).append(w)
            ward_gf.setdefault(remove_vietnamese_marks(w.ward_name, strip_prefix=False), []).append(w)
            ward_gc.setdefault(remove_vietnamese_marks(w.ward_name), []).append(w)

        # 1. Provinces
        print("Pass 1: Provinces...")
        old_p = old_db.execute(sql_text("SELECT province_id, province_name, admin_version FROM mat.province WHERE is_deleted = false")).fetchall()
        prov_map = {}; p_updates = []
        for op in old_p:
            op_norm = remove_vietnamese_marks(op.province_name)
            matches = [np for np in all_new_p if (remove_vietnamese_marks(np.province_name_en or np.province_name) == op_norm or remove_vietnamese_marks(np.province_name) == op_norm)]
            if not matches:
                for ak, al in PROVINCE_ALIASES.items():
                    if op_norm == ak or op_norm in al:
                        matches = [np for np in all_new_p if remove_vietnamese_marks(np.province_name_en or np.province_name) in ([ak]+al)]; break
            m = get_best_match(matches, op.admin_version)
            if m:
                p_updates.append({"old_id": op.province_id, "new_id": m.province_id, "ver": m.admin_version})
                prov_map[(op.province_id, op.admin_version)] = m.province_id
        batch_update(new_db, "mat.province", "province_id", p_updates)

        # 2. Districts
        print("Pass 1: Districts...")
        old_d = old_db.execute(sql_text("SELECT district_id, province_id, district_name, type_name, admin_version FROM mat.district WHERE is_deleted = false")).fetchall()
        d_updates = []
        for od in old_d:
            p_new_id = prov_map.get((od.province_id, od.admin_version))
            f_norm = remove_vietnamese_marks(f"{od.type_name} {od.district_name}" if od.type_name and od.type_name not in od.district_name else od.district_name, strip_prefix=False)
            c_norm = remove_vietnamese_marks(od.district_name)
            matches = []
            if p_new_id:
                cands = dist_h.get((p_new_id, od.admin_version), [])
                matches = [c for c in cands if remove_vietnamese_marks(c.district_name, strip_prefix=False) == f_norm]
                if not matches: matches = [c for c in cands if remove_vietnamese_marks(c.district_name) == c_norm]
            if not matches:
                matches = dist_gf.get(f_norm, [])
                if not matches: matches = dist_gc.get(c_norm, [])
            m = get_best_match(matches, od.admin_version)
            if m: d_updates.append({"old_id": od.district_id, "new_id": m.district_id, "ver": m.admin_version})
        batch_update(new_db, "mat.district", "district_id", d_updates); new_db.commit()

        # 3. Wards
        print("Pass 1: Wards...")
        dist_map = {(r.old_id, r.admin_version): r.district_id for r in new_db.execute(sql_text("SELECT district_id, old_id, admin_version FROM mat.district WHERE old_id IS NOT NULL")).fetchall()}
        old_w = old_db.execute(sql_text("SELECT ward_id, district_id, ward_name, type_name, admin_version FROM mat.ward WHERE is_deleted = false")).fetchall()
        
        # Build OLD Ward lookup for Pass 2
        old_ward_gf = {}; old_ward_gc = {}
        for ow in old_w:
            fn = remove_vietnamese_marks(f"{ow.type_name} {ow.ward_name}" if ow.type_name and ow.type_name not in ow.ward_name else ow.ward_name, strip_prefix=False)
            cn = remove_vietnamese_marks(ow.ward_name)
            old_ward_gf.setdefault(fn, []).append(ow)
            old_ward_gc.setdefault(cn, []).append(ow)

        w_updates = []
        for ow in old_w:
            p_new_id = dist_map.get((ow.district_id, ow.admin_version))
            f_norm = remove_vietnamese_marks(f"{ow.type_name} {ow.ward_name}" if ow.type_name and ow.type_name not in ow.ward_name else ow.ward_name, strip_prefix=False)
            c_norm = remove_vietnamese_marks(ow.ward_name)
            matches = []
            if p_new_id:
                cands = ward_h.get((p_new_id, ow.admin_version), [])
                matches = [c for c in cands if remove_vietnamese_marks(c.ward_name, strip_prefix=False) == f_norm]
                if not matches: matches = [c for c in cands if remove_vietnamese_marks(c.ward_name) == c_norm]
            if not matches:
                matches = ward_gf.get(f_norm, [])
                if not matches: matches = ward_gc.get(c_norm, [])
            m = get_best_match(matches, ow.admin_version)
            if m: w_updates.append({"old_id": ow.ward_id, "new_id": m.ward_id, "ver": m.admin_version})
        
        chunk = 500
        for i in range(0, len(w_updates), chunk):
            batch_update(new_db, "mat.ward", "ward_id", w_updates[i:i+chunk]); new_db.commit()

        # Pass 2: Pull
        print("Pass 2: Pulling missing Wards...")
        still_null = new_db.execute(sql_text("SELECT ward_id, district_id, ward_name, admin_version FROM mat.ward WHERE old_id IS NULL")).fetchall()
        p2_updates = []
        for nw in still_null:
            fn = remove_vietnamese_marks(nw.ward_name, strip_prefix=False)
            cn = remove_vietnamese_marks(nw.ward_name)
            matches = old_ward_gf.get(fn, [])
            if not matches: matches = old_ward_gc.get(cn, [])
            m = get_best_match(matches, nw.admin_version)
            if m: p2_updates.append({"old_id": m.ward_id, "new_id": nw.ward_id, "ver": nw.admin_version})
        
        for i in range(0, len(p2_updates), chunk):
            batch_update(new_db, "mat.ward", "ward_id", p2_updates[i:i+chunk]); new_db.commit()

        print("\nMapping results calculated successfully.")
        
    finally:
        new_db.close(); old_db.close()

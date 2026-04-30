"""
services/seeders_v3.py
======================
Import dữ liệu hành chính từ file AdministrativeUnitConversion.csv.

Quy trình (theo thứ tự bắt buộc):
  0A. Seed Province cũ (admin_version=1) từ cột province_old  — 63 tỉnh
  0B. Seed District cũ (admin_version=1) từ cột district_old
  0C. Seed Ward cũ    (admin_version=1) từ cột ward_name_old  — ~10033 xã cũ
  0D. Mark is_deleted=True cho toàn bộ data v1 vừa seed
   1. Seed Province mới (admin_version=2)                      — 34 tỉnh
   2. Seed District mới (admin_version=2) — proxy từ district_old, province_new
   3. Seed Ward mới    (admin_version=2)                       — 3321 xã/phường
   4. Seed WardMapping v1→v2                                   — 10571 rows

Lưu ý:
  - district_id v1 == v2 (mã huyện không đổi); ON CONFLICT cập nhật admin_version
  - Ward RETAINED (cùng ward_code): v1 bị mark deleted, v2 upsert lại is_deleted=False
  - relationship_type lưu dạng String (e.g. "MERGED_FULL"), khớp schema DB String(50)

Cách chạy từ CLI:
    python -m app.main seed_v3
    python -m app.main seed_v3 --file data/seed/AdministrativeUnitConversion.csv
"""
import os
import re
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from sqlalchemy import text as sql_text
from app.core.database import engine

logger = logging.getLogger("SeederV3")

# ── Hằng số ──────────────────────────────────────────────────────────────────

EFFECTIVE_DATE = datetime(2025, 3, 1)   # Ngày hiệu lực chung các Nghị quyết 2025
NOW            = datetime.utcnow()

# ── Font decode table ────────────────────────────────────────────────────────
# File CSV xuất từ Excel với font chữ đặc biệt (không phải Unicode).
# Nhiều ký tự bị mất thành '?' (0x3f) — không thể recover.
# Các high-byte (>0x7f) còn lại có thể decode được theo bảng dưới.
# Bảng được xây dựng bằng cách đối chiếu tên tỉnh/huyện/xã chuẩn vs raw bytes.
_FONT_MAP: dict[int, str] = {
    # Confirmed from province/district name alignment:
    0x82: '\u00e9',   # é  — Nhé, Lé, Chéng
    0x83: '\u00e2',   # â  — Châu, Tây, Lâm, Xuân, Tân
    0x85: '\u00e0',   # à  — Hà, thành, toàn, Lào, Cà
    0x86: '\u1eaf',   # ắ  — Bắc, Ắc
    0x87: '\u1eb7',   # ặ  — ặc, ặt
    0x88: '\u00ea',   # ê  — Tuyên, Biên, Yên, Kiên (circumflex e)
    0x89: '\u1eb9',   # ẹ  — ẹ
    0x8a: '\u00e8',   # è  — Lèng, Lèo, Bè
    0x8b: '\u1ed3',   # ồ  — Hồ
    0x8d: '\u00ec',   # ì  — Bình, Định (Đ bị mất)
    0x8e: '\u1ee3',   # ợ  — ợ
    0x8f: '\u1edf',   # ở  — ở
    0x90: '\u1edb',   # ớ  — Ớ, Nậm Ớt
    0x93: '\u1ed3',   # ồ  — Đồng (Đ bị mất thành ?)
    0x94: '\u1ee5',   # ụ  — ụ
    0x95: '\u00f2',   # ò  — Hòa, Phòng
    0x96: '\u1eeb',   # ừ  — Thừa
    0x97: '\u1eb1',   # ằ  — Tằng, Bằng
    0x98: '\u1ef1',   # ự  — ự
    0x99: '\u01a1',   # ơ  — ơ
    0x9a: '\u1ee9',   # ứ  — ứ
    0x9b: '\u1eef',   # ử  — ử
    0x9c: '\u1ef3',   # ỳ  — ỳ
    0x9d: '\u1ef5',   # ỵ  — ỵ
    0x9e: '\u1ef7',   # ỷ  — ỷ
    0x9f: '\u1ef9',   # ỹ  — ỹ
    0xa0: '\u00e1',   # á  — Thái, Khánh, Tháp
    0xa1: '\u00ed',   # í  — Chí, Bí, Chính
    0xa2: '\u00f3',   # ó  — Hóa, Lót
    0xa3: '\u00fa',   # ú  — Phú, chú
}


def fix_font(s: object) -> str:
    """Best-effort decode chuỗi bị lỗi font từ CSV.

    Các ký tự bị mất (byte 0x3f = '?') KHÔNG thể recover.
    Các high-byte (>0x7f) được decode theo bảng _FONT_MAP.
    Trả về string với càng nhiều ký tự đúng càng tốt.
    """
    if not isinstance(s, str) or not s:
        return s
    try:
        raw = s.encode('latin-1', errors='replace')
    except Exception:
        return s
    return ''.join(_FONT_MAP.get(b, chr(b)) for b in raw)


# relationship_type string values (matches DB column type=String(50))
# Integer aliases kept for backward-compat reference only
REL_TYPE_CODE = {
    "MERGED_FULL":       1,
    "MERGED_PARTIAL":    2,
    "MERGED_AREA":       3,
    "MERGED_POPULATION": 4,
    "RETAINED":          5,
    "RENAMED":           6,
    "TYPE_CHANGED":      7,
    "SPECIAL_ZONE":      8,
    "UNKNOWN":           0,
    "OTHER":             9,
}

# Mapping note → relationship_type
def _classify_note(note: str | None) -> str:
    """Phân loại note từ Excel/CSV để xác định kiểu quan hệ giữa đơn vị cũ và mới."""
    if not note or pd.isna(note):
        return "RETAINED"
    
    n = str(note).strip().lower()
    
    # 1. Đặc khu / Sắp xếp
    if "đặc khu" in n or "đ?c khu" in n or "sắp xếp" in n or "s?p x?p" in n:
        return "SPECIAL_ZONE"
    
    # 2. Nhập toàn bộ (Full Merge)
    if "toàn bộ" in n or "toàn b?" in n:
        if "nhập" in n or "nh?p" in n:
            return "MERGED_FULL"
    
    # 3. Nhập một phần (Partial Merges)
    if "một phần" in n or "m?t ph?n" in n:
        has_area = "diện tích" in n or "di?n tích" in n or "di?n tch" in n
        has_pop  = "dân số" in n or "dân s?" in n
        
        if has_area and has_pop:
            return "MERGED_PARTIAL"
        if has_area:
            return "MERGED_AREA"
        if has_pop:
            return "MERGED_POPULATION"
        return "MERGED_PART"

    # 4. Đổi tên / Đổi loại hình
    has_rename = "đổi tên" in n or "?i tên" in n
    has_type   = "đổi loại hình" in n or "?i lo?i hình" in n or "đổi loại" in n
    
    if has_rename and has_type:
        return "RENAMED_TYPE_CHANGED"
    if has_rename:
        return "RENAMED"
    if has_type:
        return "TYPE_CHANGED"

    # 5. Giữ nguyên
    if "giữ nguyên" in n or "gi?" in n or "còn lại" in n:
        return "RETAINED"
    
    # Fallback cho các trường hợp chứa từ khóa 'nhập'
    if "nhập" in n or "nh?p" in n:
        return "MERGED_FULL"
        
    return "OTHER"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_code(s: str | None) -> int | None:
    """Trích mã số từ chuỗi dạng 'Tên đơn vị (012)' → 12."""
    if not s or pd.isna(s):
        return None
    m = re.search(r'\(0*(\d+)\)', str(s))
    return int(m.group(1)) if m else None


def _extract_name(s: str | None) -> str | None:
    """Bỏ phần '(code)' ở cuối, strip whitespace/newline."""
    if not s or pd.isna(s):
        return None
    return re.sub(r'\s*\(\d+\)\s*$', '', str(s)).strip().strip('\n')


# cp850-decoded prefix patterns (Vietnamese through cp850 codec)
_TYPE_PREFIXES = [
    ("Thành ph",  "Thành phố"),
    ("T?nh",       "Tỉnh"),
    ("Qu?n",       "Quận"),
    ("Huy?n",      "Huyện"),
    ("Th? xã",    "Thị xã"),
    ("Ph??ng",     "Phường"),
    ("X?",         "Xã"),
    ("Th? tr?n",  "Thị trấn"),
    ("??c khu",   "Đặc khu"),
]

def _extract_type(name: str | None) -> str:
    """Đoán type_name từ prefix tên đơn vị (cp850-decoded strings)."""
    if not name:
        return ""
    n = name.strip()
    for prefix, tname in _TYPE_PREFIXES:
        if n.startswith(prefix):
            return tname
    return ""


def _load_data(file_path: str) -> pd.DataFrame:
    """Detect file type and load accordingly."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.xlsx':
        return _load_excel(file_path)
    return _load_csv(file_path)


def _load_csv(csv_path: str) -> pd.DataFrame:
    """Load CSV, rename columns, clean, filter data rows."""
    # Đọc bằng latin-1 (1:1 byte) rồi decode TCVN3 thủ công
    df = pd.read_csv(csv_path, encoding='latin-1', dtype=str)
    df.columns = [
        "province_new", "ward_name_new", "ward_code_new",
        "ward_name_old", "ward_code_old", "note",
        "district_old", "province_old",
        "_x1", "_x2",
    ]
    df = df.drop(columns=["_x1", "_x2"], errors="ignore")
    return _clean_and_process_df(df, fix_encoding=True)


def _load_excel(excel_path: str) -> pd.DataFrame:
    """Load Excel, rename columns, clean, filter data rows."""
    df = pd.read_excel(excel_path)
    # Excel has 9 columns based on analysis
    df.columns = [
        "province_new", "ward_name_new", "ward_code_new",
        "ward_name_old", "ward_code_old", "note",
        "district_old", "province_old", "_x1"
    ]
    df = df.drop(columns=["_x1"], errors="ignore")
    return _clean_and_process_df(df, fix_encoding=False)


def _clean_and_process_df(df: pd.DataFrame, fix_encoding: bool) -> pd.DataFrame:
    """Common cleaning and processing logic for both formats."""
    # Bỏ các dòng header section (ward_name_new rỗng)
    df = df[df["ward_name_new"].notna()].copy()

    # Strip mọi string
    str_cols = df.select_dtypes("object").columns
    df[str_cols] = df[str_cols].apply(lambda c: c.str.strip().str.strip("\n") if hasattr(c, "str") else c)

    # Fix font nếu cần (CSV export lỗi)
    if fix_encoding:
        name_cols = ["province_new", "ward_name_new", "ward_name_old",
                     "note", "district_old", "province_old"]
        for col in name_cols:
            if col in df.columns:
                df[col] = df[col].apply(fix_font)

    # Derived columns
    df["prov_code_new"]  = df["province_new"].apply(_extract_code)
    df["prov_code_old"]  = df["province_old"].apply(_extract_code)
    df["dist_code_old"]  = df["district_old"].apply(_extract_code)
    df["prov_name_new"]  = df["province_new"].apply(_extract_name)
    df["prov_name_old"]  = df["province_old"].apply(_extract_name)
    df["dist_name_old"]  = df["district_old"].apply(_extract_name)
    df["ward_name_new"]  = df["ward_name_new"].astype(str).str.strip()
    df["ward_name_old"]  = df["ward_name_old"].astype(str).str.strip()
    df["ward_int_new"]   = pd.to_numeric(df["ward_code_new"], errors="coerce").astype("Int64")
    df["ward_int_old"]   = pd.to_numeric(df["ward_code_old"], errors="coerce").astype("Int64")
    df["rel_type"]       = df["note"].apply(_classify_note)

    logger.info("Data loaded: %d data rows", len(df))
    return df


# ── Step 0A: Seed Province/District/Ward v1 (data cũ từ CSV) ────────────────

def seed_provinces_v1(df: pd.DataFrame):
    """Insert Province cũ (admin_version=1) từ cột province_old trong CSV."""
    logger.info("Step 0A: Seeding mat.province (admin_version=1) ...")

    provinces = (
        df[["prov_code_old", "prov_name_old"]]
        .drop_duplicates("prov_code_old")
        .dropna(subset=["prov_code_old", "prov_name_old"])
        .copy()
    )

    records = [
        {
            "province_id":   int(r.prov_code_old),
            "province_no":   str(r.prov_code_old).zfill(2),
            "province_name": r.prov_name_old,
            "type_name":     _extract_type(r.prov_name_old),
            "admin_version": 1,
            "is_deleted":    False,
            "is_default":    True,
            "country_id":    0,
            "created_user":  0,
            "updated_user":  0,
            "created_date":  NOW,
            "updated_date":  NOW,
        }
        for r in provinces.itertuples()
    ]

    _upsert_batch(
        records, "mat.province", "province_id, admin_version",
        ["province_no", "province_name", "type_name",
         "is_deleted", "is_default", "country_id", "updated_user",
         "created_date", "updated_date"],
    )
    logger.info("Step 0A: %d v1 provinces inserted/updated.", len(records))


def seed_districts_v1(df: pd.DataFrame):
    """Insert District cũ (admin_version=1) từ cột district_old + province_old trong CSV."""
    logger.info("Step 0B: Seeding mat.district (admin_version=1) ...")

    districts = (
        df[["dist_code_old", "dist_name_old", "prov_code_old"]]
        .drop_duplicates("dist_code_old")
        .dropna(subset=["dist_code_old", "prov_code_old"])
        .copy()
    )

    records = [
        {
            "district_id":   int(r.dist_code_old),
            "district_no":   str(r.dist_code_old).zfill(3),
            "district_name": r.dist_name_old,
            "type_name":     _extract_type(r.dist_name_old),
            "province_id":   int(r.prov_code_old),
            "admin_version": 1,
            "is_deleted":    False,
            "is_default":    True,
            "created_user":  0,
            "updated_user":  0,
            "created_date":  NOW,
            "updated_date":  NOW,
        }
        for r in districts.itertuples()
        if r.dist_code_old and r.dist_name_old
    ]

    _upsert_batch(
        records, "mat.district", "district_id, admin_version",
        ["district_no", "district_name", "type_name", "province_id",
         "is_deleted", "is_default", "updated_user",
         "created_date", "updated_date"],
    )
    logger.info("Step 0B: %d v1 districts inserted/updated.", len(records))


def seed_wards_v1(df: pd.DataFrame):
    """Insert Ward cũ (admin_version=1) từ cột ward_name_old + ward_code_old trong CSV."""
    logger.info("Step 0C: Seeding mat.ward (admin_version=1) ...")

    # Lọc bỏ SPECIAL_ZONE (không có ward_code_old)
    ward_old = (
        df[["ward_int_old", "ward_name_old", "dist_code_old", "prov_code_old"]]
        .dropna(subset=["ward_int_old"])
        .drop_duplicates("ward_int_old")
        .copy()
    )

    records = [
        {
            "ward_id":       int(r.ward_int_old),
            "ward_no":       str(int(r.ward_int_old)).zfill(5),
            "ward_name":     r.ward_name_old,
            "type_name":     _extract_type(r.ward_name_old),
            "district_id":   int(r.dist_code_old) if r.dist_code_old and not pd.isna(r.dist_code_old) else 0,
            "province_no":   str(int(r.prov_code_old)).zfill(2) if r.prov_code_old and not pd.isna(r.prov_code_old) else None,
            "admin_version": 1,
            "is_deleted":    False,
            "is_default":    True,
            "created_user":  0,
            "updated_user":  0,
            "created_date":  NOW,
            "updated_date":  NOW,
        }
        for r in ward_old.itertuples()
    ]

    _upsert_batch(
        records, "mat.ward", "ward_id, admin_version",
        ["ward_no", "ward_name", "type_name", "district_id", "province_no",
         "is_deleted", "is_default", "updated_user",
         "created_date", "updated_date"],
    )
    logger.info("Step 0C: %d v1 wards inserted/updated.", len(records))


# ── Step 0D: Mark is_deleted cho data cũ ─────────────────────────────────────

def mark_old_data_deleted():
    """
    Đánh dấu is_deleted=True cho toàn bộ data v1 (admin_version=1)
    trong 4 bảng: province, district, ward, ward_mapping.
    Không xóa thực sự — giữ lại để phục vụ lookup lịch sử.
    """
    logger.info("Step 0: Marking old v1 data as is_deleted=True ...")
    stmts = [
        "UPDATE mat.province     SET is_deleted = TRUE WHERE admin_version = 1 OR admin_version IS NULL",
        "UPDATE mat.district     SET is_deleted = TRUE WHERE admin_version = 1 OR admin_version IS NULL",
        "UPDATE mat.ward         SET is_deleted = TRUE WHERE admin_version = 1 OR admin_version IS NULL",
        "UPDATE mat.ward_mapping SET is_deleted = TRUE",   # toàn bộ mapping cũ (nếu có)
    ]
    with engine.connect() as conn:
        for stmt in stmts:
            result = conn.execute(sql_text(stmt))
            logger.info("  %s  → %d rows affected", stmt[:60], result.rowcount)
        conn.commit()
    logger.info("Step 0: Done.")


# ── Step 1: Seed Province v2 ──────────────────────────────────────────────────

def seed_provinces_v2(df: pd.DataFrame):
    """Insert 34 Province mới (admin_version=2)."""
    logger.info("Step 1: Seeding mat.province (admin_version=2) ...")

    provinces = (
        df[["prov_code_new", "prov_name_new"]]
        .drop_duplicates("prov_code_new")
        .dropna(subset=["prov_code_new"])
        .copy()
    )
    provinces["type_name"]      = provinces["prov_name_new"].apply(_extract_type)
    provinces["admin_version"]  = 2
    provinces["is_deleted"]     = False
    provinces["is_default"]     = True
    provinces["country_id"]     = 0
    provinces["created_user"]   = 0
    provinces["updated_user"]   = 0

    records = [
        {
            "province_id":   int(r.prov_code_new),
            "province_no":   str(r.prov_code_new).zfill(2),
            "province_name": r.prov_name_new,
            "type_name":     r.type_name,
            "admin_version": 2,
            "is_deleted":    False,
            "is_default":    True,
            "country_id":    0,
            "created_user":  0,
            "updated_user":  0,
            "created_date":  NOW,
            "updated_date":  NOW,
        }
        for r in provinces.itertuples()
        if r.prov_code_new and r.prov_name_new
    ]

    _upsert_batch(
        records, "mat.province", "province_id, admin_version",
        ["province_no", "province_name", "type_name",
         "is_deleted", "is_default", "country_id", "updated_user",
         "created_date", "updated_date"],
    )
    logger.info("Step 1: %d provinces inserted/updated.", len(records))


# ── Step 2: Seed District v2 ──────────────────────────────────────────────────

def seed_districts_v2(df: pd.DataFrame):
    """
    Insert 34 District v2 — mỗi Province v2 một District cùng tên và mã.
    District v2 đại diện cho cấp hành chính tỉnh/thành phố mới (34 đơn vị).
    district_id = province_id (dùng cùng mã để dễ lookup).
    """
    logger.info("Step 2: Seeding mat.district (admin_version=2) — 34 districts ...")

    # Lấy 34 province v2 unique
    provinces = (
        df[["prov_code_new", "prov_name_new"]]
        .drop_duplicates("prov_code_new")
        .dropna(subset=["prov_code_new", "prov_name_new"])
        .copy()
    )

    records = [
        {
            "district_id":   int(r.prov_code_new),
            "district_no":   str(int(r.prov_code_new)).zfill(3),
            "district_name": r.prov_name_new,
            "type_name":     _extract_type(r.prov_name_new),
            "province_id":   int(r.prov_code_new),
            "admin_version": 2,
            "is_deleted":    False,
            "is_default":    True,
            "created_user":  0,
            "updated_user":  0,
            "created_date":  NOW,
            "updated_date":  NOW,
        }
        for r in provinces.itertuples()
        if r.prov_code_new and r.prov_name_new
    ]

    _upsert_batch(
        records, "mat.district", "district_id, admin_version",
        ["district_no", "district_name", "type_name", "province_id",
         "is_deleted", "is_default", "updated_user",
         "created_date", "updated_date"],
    )
    logger.info("Step 2: %d districts inserted/updated.", len(records))


# ── Step 3: Seed Ward v2 ──────────────────────────────────────────────────────

def seed_wards_v2(df: pd.DataFrame):
    """Insert 3321 Ward mới (admin_version=2)."""
    logger.info("Step 3: Seeding mat.ward (admin_version=2) ...")

    # Unique new wards — lấy theo ward_code_new
    # district_id: lấy từ district của old ward (theo mapping đầu tiên)
    ward_district = (
        df[["ward_int_new", "ward_name_new", "dist_code_old", "prov_code_new"]]
        .dropna(subset=["ward_int_new"])
        .drop_duplicates("ward_int_new")
        .copy()
    )

    records = [
        {
            "ward_id":       int(r.ward_int_new),
            "ward_no":       str(int(r.ward_int_new)).zfill(5),
            "ward_name":     r.ward_name_new,
            "type_name":     _extract_type(r.ward_name_new),
            "district_id":   int(r.dist_code_old) if r.dist_code_old and not pd.isna(r.dist_code_old) else 0,
            "province_no":   str(int(r.prov_code_new)).zfill(2) if r.prov_code_new and not pd.isna(r.prov_code_new) else None,
            "admin_version": 2,
            "is_deleted":    False,
            "is_default":    True,
            "created_user":  0,
            "updated_user":  0,
            "created_date":  NOW,
            "updated_date":  NOW,
        }
        for r in ward_district.itertuples()
    ]

    _upsert_batch(
        records, "mat.ward", "ward_id, admin_version",
        ["ward_no", "ward_name", "type_name", "district_id", "province_no",
         "is_deleted", "is_default", "updated_user",
         "created_date", "updated_date"],
    )
    logger.info("Step 3: %d wards inserted/updated.", len(records))


# ── Step 4: Seed Ward Mapping ─────────────────────────────────────────────────

def seed_ward_mapping_v3(df: pd.DataFrame):
    """
    Insert mat.ward_mapping — ánh xạ v1 → v2.

    ward_id_old = ward_int_old (ward_no v1, int)
                  hoặc -1 nếu SPECIAL_ZONE (cả huyện → đặc khu)
    ward_id_new = ward_int_new (ward_no v2, int)

    Dùng ward_no làm key thay vì ward_id vì:
      - ward_id trong DB được seed = ward_no (xem seed_master_data)
      - ward_code trong CSV chính là ward_no 5 chữ số
    """
    logger.info("Step 4: Seeding mat.ward_mapping ...")

    # Xóa toàn bộ ward_mapping cũ để insert sạch
    with engine.connect() as conn:
        conn.execute(sql_text("TRUNCATE TABLE mat.ward_mapping RESTART IDENTITY"))
        conn.commit()

    # Tính mapping_total: số old ward → cùng 1 new ward
    mapping_total = (
        df.groupby("ward_int_new")["ward_int_old"]
        .count()
        .rename("mapping_total")
    )
    df = df.join(mapping_total, on="ward_int_new")

    records = []
    for idx, r in enumerate(df.itertuples(), start=1):
        # SPECIAL_ZONE: cả huyện → đặc khu, không có ward_code_old → dùng -1
        if r.rel_type == "SPECIAL_ZONE" or pd.isna(r.ward_int_old):
            ward_id_old = -1
        else:
            ward_id_old = int(r.ward_int_old)

        records.append({
            "ward_mapping_id":    idx,
            "ward_id_old":        ward_id_old,
            "province_id_old":    int(r.prov_code_old) if r.prov_code_old and not pd.isna(r.prov_code_old) else None,
            "district_id_old":    int(r.dist_code_old) if r.dist_code_old and not pd.isna(r.dist_code_old) else None,
            "ward_id_new":        int(r.ward_int_new) if not pd.isna(r.ward_int_new) else None,
            "province_id_new":    int(r.prov_code_new) if r.prov_code_new and not pd.isna(r.prov_code_new) else None,
            "effective_date_from": EFFECTIVE_DATE,
            "effective_date_to":  None,
            "created_date":       NOW,
            "created_user":       3415,
            "updated_date":       NOW,
            "updated_user":       3415,
            "is_deleted":         False,
            "updated_note":       str(r.note).strip() if r.note and not pd.isna(r.note) else None,
            "relationship_type":  r.rel_type,
            "mapping_total":      int(r.mapping_total) if not pd.isna(r.mapping_total) else 1,
        })

    # Insert theo batch
    _insert_batch(records, "mat.ward_mapping", chunk_size=1000)
    logger.info("Step 4: %d ward_mapping rows inserted.", len(records))


# ── Utilities ─────────────────────────────────────────────────────────────────

def _upsert_batch(
    records: list[dict],
    table: str,
    pk_col: str,
    update_cols: list[str],
    chunk_size: int = 500,
):
    """UPSERT batch với ON CONFLICT DO UPDATE."""
    if not records:
        return
    cols         = list(records[0].keys())
    col_str      = ", ".join(cols)
    placeholder  = ", ".join(f":{c}" for c in cols)
    update_set   = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)
    stmt = sql_text(
        f"INSERT INTO {table} ({col_str}) VALUES ({placeholder}) "
        f"ON CONFLICT ({pk_col}) DO UPDATE SET {update_set}"
    )
    with engine.connect() as conn:
        for i in range(0, len(records), chunk_size):
            batch = records[i : i + chunk_size]
            try:
                conn.execute(stmt, batch)
                conn.commit()
            except Exception as exc:
                conn.rollback()
                logger.error("Upsert error at batch %d in %s: %s", i, table, exc)
                raise


def _insert_batch(records: list[dict], table: str, chunk_size: int = 1000):
    """INSERT batch, bỏ qua conflict (ward_mapping không có PK tự nhiên)."""
    if not records:
        return
    cols        = list(records[0].keys())
    col_str     = ", ".join(cols)
    placeholder = ", ".join(f":{c}" for c in cols)
    stmt = sql_text(
        f"INSERT INTO {table} ({col_str}) VALUES ({placeholder}) "
        f"ON CONFLICT DO NOTHING"
    )
    with engine.connect() as conn:
        for i in range(0, len(records), chunk_size):
            batch = records[i : i + chunk_size]
            try:
                conn.execute(stmt, batch)
                conn.commit()
            except Exception as exc:
                conn.rollback()
                logger.error("Insert error at batch %d in %s: %s", i, table, exc)
                raise


# ── Public entry point ────────────────────────────────────────────────────────

def run_seed_v3(file_path: str):
    """
    Entry point chính — gọi tuần tự 5 bước.

    Args:
        file_path: Đường dẫn tới AdministrativeUnitConversion.xlsx hoặc .csv
    """
    logger.info("=" * 60)
    logger.info("SeederV3: Starting full import from %s", file_path)
    logger.info("Quy trình: v1 (province/district/ward) → mark_deleted → v2 → ward_mapping")
    logger.info("=" * 60)

    # Load & parse
    df = _load_data(file_path)

    # Bước 1: Seed toàn bộ data v1 (admin_version=1) trước
    seed_provinces_v1(df)
    seed_districts_v1(df)
    seed_wards_v1(df)

    # Bước 2: Mark v1 là deleted (sau khi đã có data v1 trong DB)
    mark_old_data_deleted()

    # Bước 3: Seed toàn bộ data v2 (admin_version=2)
    seed_provinces_v2(df)
    seed_districts_v2(df)
    seed_wards_v2(df)

    # Bước 4: Seed ward_mapping (v1→v2)
    seed_ward_mapping_v3(df)

    logger.info("=" * 60)
    logger.info("SeederV3: DONE. Checking stats...")
    stats = check_v3_stats()
    for k, v in stats.items():
        logger.info("  %-35s: %s", k, v)
    logger.info("=" * 60)


def check_v3_stats() -> dict:
    queries = {
        "Province v1 (seeded)":       "SELECT COUNT(*) FROM mat.province WHERE admin_version = 1",
        "Province v1 (is_deleted)":   "SELECT COUNT(*) FROM mat.province WHERE admin_version = 1 AND is_deleted = TRUE",
        "Province v2 (active)":       "SELECT COUNT(*) FROM mat.province WHERE admin_version = 2 AND is_deleted = FALSE",
        "District v1 (seeded)":       "SELECT COUNT(*) FROM mat.district WHERE admin_version = 1",
        "District v1 (is_deleted)":   "SELECT COUNT(*) FROM mat.district WHERE admin_version = 1 AND is_deleted = TRUE",
        "District v2 (active)":       "SELECT COUNT(*) FROM mat.district WHERE admin_version = 2 AND is_deleted = FALSE",
        "Ward v1 (seeded)":           "SELECT COUNT(*) FROM mat.ward WHERE admin_version = 1",
        "Ward v1 (is_deleted)":       "SELECT COUNT(*) FROM mat.ward WHERE admin_version = 1 AND is_deleted = TRUE",
        "Ward v2 (active)":           "SELECT COUNT(*) FROM mat.ward WHERE admin_version = 2 AND is_deleted = FALSE",
        "WardMapping (active)":       "SELECT COUNT(*) FROM mat.ward_mapping WHERE is_deleted = FALSE",
    }
    stats = {}
    with engine.connect() as conn:
        for name, q in queries.items():
            try:
                stats[name] = conn.execute(sql_text(q)).scalar()
            except Exception as e:
                stats[name] = f"Error: {e}"
    return stats

"""
export_for_annotation.py
========================
Trích xuất dữ liệu và TỰ ĐỘNG GỢI Ý NHÃN (Pre-labeling).
Tích hợp bộ làm sạch địa chỉ.

Câu lệnh thực thi mẫu (Bash):
----------------------------
python app/ai/export_for_annotation.py --limit 1000 --config app/ai/config.yaml
"""

import json
import logging
import argparse
import sys
import re
from pathlib import Path
import yaml

# Đảm bảo import từ cùng package
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ai.db_connector import DBConnector
from app.ai.utils.address_cleaner import AddressCleaner
from app.ai.utils.config_loader import load_config_with_env

# ──────────────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("ExportAnnotation")

import datetime

import re

class PreLabeler:
    """
    Bộ gán nhãn lai (Hybrid) kết hợp String Matching (Master Data) và Regex (Heuristics).
    Tối ưu cho việc tạo Ground Truth cho mô hình NER PhoBERT.
    """
    
    # Danh sách các thành phố trực thuộc trung ương
    CENTRAL_CITIES = {"hồ chí minh", "hcm", "hà nội", "hn", "đà nẵng", "đn", "hải phòng", "hp", "cần thơ", "ct"}

    # ──────────────────────────────────────────────────────────────────────────
    # Cấu hình tiền tố và từ khóa đơn vị hành chính để làm sạch nhãn
    # ──────────────────────────────────────────────────────────────────────────
    PREFIX_PATTERNS = {
        "PCD": None,
        "BLD": r'(?i)^(Tòa\s*nhà|Chung\s*cư|CC|Khu\s*tập\s*thể|KTT|Văn\s*phòng|Khu\s*đô\s*thị|KĐT|KCN|CCN|Tầng|Phòng|Lầu|Block)\s+',
        "POI": r'(?i)^(Trường|Bệnh\s*viện|BV|Cửa\s*hàng|Tạp\s*hóa|ATM|UBND|Chợ|Siêu\s*thị|Công\s*viên|Công\s*ty|Cty|Nhà\s*thờ|Chùa|Khu công nghiệp|KCN)\s+',
        "ALY": r'(?i)^(Hẻm|Ngõ|Kiệt|Ngách)\s+',
        "NUM": r'(?i)^(Số nhà|Số|Lô|Km)\s+',
        "STR": r'(?i)^(Đường|Phố|Đ\.|QL|Quốc\s*lộ|ĐT|TL|Tỉnh\s*lộ|Đại\s*lộ|Hương\s*lộ|HL)\s+',
        "NHB": r'(?i)^(Khu\s*phố|KP|Tổ\s*dân\s*phố|Thôn|Ấp|Bản|Tổ|Sóc|Phum|Xóm|Làng|Khóm|Cụm|Buôn|Plei|KDC)\s+',
        "WDS": r'(?i)^(Phường|Xã|Thị trấn|P\.|X\.)\s+',
        "DST": r'(?i)^(Quận|Huyện|Thị xã|Q\.|H\.)\s+',
        "PRO": r'(?i)^(Thành phố|Tỉnh|TP\.|TP)\s+',
    }
    
    ADMIN_KEYWORDS = r'(?i)\s*,?\s*\b(Phường|Xã|Thị trấn|Quận|Huyện|Thị xã|Thành phố|Tỉnh|TP|P\.|Q\.|H\.|X\.)\b'

    # Quy tắc Regex cho các đơn vị vi mô (Sắp xếp theo NER_LABELS)
    MICRO_RULES = [
        ("PCD", r'(?i)(?:\b|^)([23456789CFGHJMPQRVWX]{4,8}\+[23456789CFGHJMPQRVWX]{2,3})(?:\b|$)', 0.95),
        ("BLD", r'(?i)(?:Tòa\s*nhà|Chung\s*cư|CC|Khu\s*tập\s*thể|KTT|Văn\s*phòng|Khu\s*đô\s*thị|KĐT|KCN|CCN|Tầng|Phòng|Lầu|Block)\s+[^,.\n]+', 0.75),
        ("POI", r'(?i)(?:Trường|Bệnh\s*viện|BV|Cửa\s*hàng|Tạp\s*hóa|ATM|UBND|Chợ|Siêu\s*thị|Công\s*viên|Công\s*ty|Cty|Nhà\s*thờ|Chùa|Khu công nghiệp|KCN)\s+[^,.\n]+', 0.7),
        ("ALY", r'(?i)(?:Hẻm|Ngõ|Kiệt|Ngách)\s+[^,.\n]+', 0.85),
        ("NUM", r'(?i)(?:Số nhà|Số\s+)?\d+[A-Za-z]?(?:[/\-]\d+[A-Za-z]?)*|(?:\b|^)(?:Lô|Km)\s+[\w\-]+', 0.9),
        ("STR", r'(?i)(?:Đường|Phố|Đ\.|QL|Quốc\s*lộ|ĐT|TL|Tỉnh\s*lộ|Đại\s*lộ|Hương\s*lộ|HL)\s+[^,.\n]+', 0.85),
        ("NHB", r'(?i)(?:Khu\s*phố|KP|Tổ\s*dân\s*phố|Thôn|Ấp|Bản|Tổ|Sóc|Phum|Xóm|Làng|Khóm|Cụm|Buôn|Plei|KDC)\s+[^,.\n]+', 0.8),
    ]

    @classmethod
    def predict(cls, 
                raw_address: str, 
                ward_name: str = None, 
                district_name: str = None, 
                province_name: str = None,
                known_streets: set = None) -> list:
        
        if not raw_address:
            return []

        results = []
        labeled_spans = [] # Lưu trữ (start, end) để chống quét đè nhãn

        def add_result(start: int, end: int, text: str, label: str, score: float):
            # Lấy bản gốc để tính offset nếu bị cắt tiền tố
            original_text = text
            
            # 1. Loại bỏ tiền tố (Đường, Phố, Số, ...) theo yêu cầu
            prefix_pat = cls.PREFIX_PATTERNS.get(label)
            if prefix_pat:
                m_pref = re.search(prefix_pat, text)
                if m_pref:
                    pref_len = m_pref.end()
                    remaining = text[pref_len:]
                    stripped = remaining.lstrip()
                    offset = pref_len + (len(remaining) - len(stripped))
                    
                    text = stripped
                    start += offset

            # 2. Sửa lỗi STR tham lam: Loại bỏ phần đơn vị hành chính hoặc đơn vị khác dính vào ở cuối
            if label == "STR":
                # Cắt ở cuối nếu dính đơn vị hành chính
                m_admin = re.search(cls.ADMIN_KEYWORDS, text)
                if m_admin:
                    text = text[:m_admin.start()].strip(' ,')
                
                # Cắt ở cuối nếu dính tiền tố của BLD, POI, ALY (Ví dụ: "Nguyễn Sơn Chung Cư...")
                for stop_label in ["BLD", "POI", "ALY"]:
                    stop_pat = cls.PREFIX_PATTERNS.get(stop_label)
                    if stop_pat:
                        m_stop = re.search(stop_pat, text)
                        if m_stop:
                            # Nếu dính tiền tố đơn vị khác, cắt bỏ từ đó
                            text = text[:m_stop.start()].strip(' ,')
            elif label in ["ALY", "BLD", "NHB", "POI"]:
                m_admin = re.search(cls.ADMIN_KEYWORDS, text)
                if m_admin:
                    text = text[:m_admin.start()].strip(' ,')

            if not text:
                return False
            
            end = start + len(text)

            # Kiểm tra chồng lấn (sau khi đã tinh chỉnh span)
            for s, e in labeled_spans:
                if (s <= start < e) or (s < end <= e) or (start <= s and end >= e):
                    return False
            
            results.append({
                "from_name": "label", "to_name": "text", "type": "labels", "score": score,
                "value": {"start": start, "end": end, "text": text, "labels": [label]}
            })
            labeled_spans.append((start, end))
            return True

        # Giai đoạn 1: String Matching cho các cấp Vĩ mô (Dựa trên Master Data)
        # Sắp xếp theo độ dài giảm dần để ưu tiên khớp cụm từ dài trước
        macros = [
            ("PRO", province_name),
            ("DST", district_name),
            ("WDS", ward_name)
        ]

        for label, entity_name in macros:
            if not entity_name: continue
            
            # Tạo các biến thể tìm kiếm để tăng khả năng khớp
            search_terms = [entity_name]
            # Thêm biến thể bỏ tiền tố (Ví dụ: "Quận 1" -> "1", "Phường Bến Nghé" -> "Bến Nghé")
            short_name = re.sub(r'(?i)^(Thành phố|Tỉnh|Quận|Huyện|Thị xã|Phường|Xã|Thị trấn|TP\.|Q\.|H\.|P\.|X\.)\s*', '', entity_name).strip()
            if short_name and short_name != entity_name:
                search_terms.append(short_name)
            
            for term in sorted(search_terms, key=len, reverse=True):
                # Tìm tất cả các lần xuất hiện (xử lý over-information)
                for match in re.finditer(re.escape(term), raw_address, re.I):
                    add_result(match.start(), match.end(), raw_address[match.start():match.end()], label, 1.0)

        # Giai đoạn 1.2: Heuristic nhận diện STR nằm giữa NUM và WDS (WS)
        # Theo yêu cầu: STR nằm giữa NUM và WDS và có thể nằm trong danh sách từ OSM
        num_regex = r'(?i)(?:Số\s+)?\d+[A-Za-z]?(?:[/\-]\d+[A-Za-z]?)*|(?:\b|^)(?:Lô|Km)\s+[\w\-]+'
        
        # Lấy các mốc WDS đã tìm thấy ở Giai đoạn 1
        wds_spans = [ (r['value']['start'], r['value']['end']) for r in results if 'WDS' in r['value']['labels'] ]
        
        if wds_spans:
            # Tìm tất cả các số nhà tiềm năng
            for n_match in re.finditer(num_regex, raw_address):
                n_end = n_match.end()
                # Tìm WDS gần nhất phía sau NUM này
                after_wds = [s for s in wds_spans if s[0] >= n_end]
                if after_wds:
                    w_start, _ = min(after_wds, key=lambda x: x[0])
                    # Đoạn văn bản ở giữa NUM và WDS
                    gap_text = raw_address[n_end:w_start].strip(' ,')
                    
                    # Tiền xử lý gap_text: Nếu chứa tiền tố đường, chỉ lấy từ đó (Sửa lỗi dính "Số nhà" vào STR)
                    str_pref_match = re.search(cls.PREFIX_PATTERNS["STR"], gap_text)
                    if str_pref_match:
                        gap_text = gap_text[str_pref_match.start():]
                    
                    # Nếu gap_text chứa tiền tố của các đơn vị khác (BLD, POI, ALY) -> Loại bỏ phần đó
                    for stop_label in ["BLD", "POI", "ALY"]:
                        stop_pat = cls.PREFIX_PATTERNS.get(stop_label)
                        if stop_pat:
                            m_stop = re.search(stop_pat, gap_text)
                            if m_stop:
                                gap_text = gap_text[:m_stop.start()].strip(' ,')

                    if gap_text and len(gap_text.split()) <= 6: # Tên đường thường không quá dài
                        is_match = False
                        if known_streets and gap_text.lower() in known_streets:
                            is_match = True
                        
                        # Heuristic bổ sung: Nếu bắt đầu bằng chữ hoa và không chứa dấu phẩy/chấm
                        elif re.match(r'^[A-ZĐ][^,.\n]+$', gap_text):
                            is_match = True
                            
                        if is_match:
                            # Tìm vị trí chính xác trong raw_address để add_result
                            m_gap = re.search(re.escape(gap_text), raw_address[n_end:w_start])
                            if m_gap:
                                g_start = n_end + m_gap.start()
                                g_end = g_start + len(gap_text)
                                # Ưu tiên điểm cao hơn nếu khớp trong list OSM
                                score = 0.92 if (known_streets and gap_text.lower() in known_streets) else 0.8
                                add_result(g_start, g_end, gap_text, 'STR', score)

        # Giai đoạn 1.5: Cố gắng trích xuất STR (Tên đường) khi PRO/DST/WDS đã biết
        # Chiến lược:
        # - Tạo một bản sao sạch của địa chỉ, loại bỏ các chuỗi PRO/DST/WDS và hậu tố quốc gia
        # - Tách theo dấu phẩy và tìm segment chứa số nhà + tên đường (hỗ trợ 74/26, 927/1, 11B, K814)
        # - Nếu tìm được, thêm nhãn `STR` cho phần tên đường và `NUM` cho số nhà
        clean_addr = raw_address
        # Loại bỏ hậu tố quốc gia
        clean_addr = re.sub(r',?\s*việt\s*nam.*$', '', clean_addr, flags=re.I)

        def _remove_macro_variants(text: str, name: str) -> str:
            if not name:
                return text
            # Các tiền tố thường gặp
            prefixes = r'(?:Thành phố|Tỉnh|Quận|Huyện|Thị xã|Phường|Xã|Thị trấn|TP\.|TP|Q\.|Q|H\.|P\.|P)\s*'
            # Loại bỏ cả biến thể có tiền tố và không có
            pattern = rf'(?:{prefixes})?\s*{re.escape(name)}'
            return re.sub(pattern, '', text, flags=re.I)

        clean_addr = _remove_macro_variants(clean_addr, ward_name)
        clean_addr = _remove_macro_variants(clean_addr, district_name)
        clean_addr = _remove_macro_variants(clean_addr, province_name)

        # Chuẩn hóa khoảng trắng, xóa dấu phẩy thừa
        clean_addr = re.sub(r'\s*,\s*', ',', clean_addr)
        clean_addr = re.sub(r'\s+', ' ', clean_addr).strip(' ,')

        segments = [s.strip() for s in clean_addr.split(',') if s.strip()]

        def _find_in_raw(sub: str):
            if not sub: return None
            m = re.search(re.escape(sub), raw_address, flags=re.I)
            if m:
                return m.start(), m.end(), raw_address[m.start():m.end()]
            # Fallback: try case-insensitive search by lowering
            lo = raw_address.lower().find(sub.lower())
            if lo >= 0:
                return lo, lo + len(sub), raw_address[lo:lo + len(sub)]
            return None

        # Pattern for house numbers (supports 74/26, 927/1, 11B, K814)
        num_pattern = re.compile(r'(?i)^(?P<num>(?:K\d+|\d+[A-Za-z]?)(?:[\\/\-]\d+[A-Za-z]?)*)(?:\s+)(?P<rest>.+)$')

        for i, seg in enumerate(segments[:3]):
            # Try to match number + rest
            m = num_pattern.match(seg)
            if m:
                num = m.group('num').strip()
                rest = m.group('rest').strip()
                # Attempt to isolate street name from rest by removing leading POI/building words
                rest_clean = re.sub(r'^(?:Tòa nhà|Chung cư|Khu|Khu dân cư|Block|Tầng|Phòng|Lầu|Topaz Home|Chung Cư)\b[,\s]*', '', rest, flags=re.I)

                # If rest contains additional separators (like '-') take full rest as street candidate
                street_candidate = rest_clean

                # Locate in original and add labels
                found = _find_in_raw(street_candidate)
                if found:
                    s0, e0, txt = found
                    add_result(s0, e0, txt, 'STR', 0.95)
                # also add NUM if possible
                found_num = _find_in_raw(num)
                if found_num:
                    s1, e1, txtn = found_num
                    add_result(s1, e1, txtn, 'NUM', 0.98)
                break

            # If segment doesn't start with number, but contains street words, try micro rule on segment
            for lab, pat, score in cls.MICRO_RULES:
                if lab != 'STR':
                    continue
                mm = re.search(pat, seg)
                if mm:
                    candidate = mm.group(0).strip()
                    found = _find_in_raw(candidate)
                    if found:
                        s0, e0, txt = found
                        add_result(s0, e0, txt, 'STR', max(0.85, score))
                        break

        # Giai đoạn 2: Regex Heuristics cho các cấp Vi mô
        for label, pattern, score in cls.MICRO_RULES:
            for match in re.finditer(pattern, raw_address):
                matched_text = match.group(0).strip()
                # Tính toán lại start/end sau khi strip
                start = match.start() + match.group(0).find(matched_text)
                end = start + len(matched_text)
                add_result(start, end, matched_text, label, score)

        return results

from app.ai.constants import NER_LABELS

def export_label_config(output_file: str):
    """Xuất file XML cấu hình giao diện cho Label Studio."""
    xml_content = '<View>\n  <Labels name="label" toName="text">\n'
    for l in NER_LABELS:
        attrs = f'value="{l["value"]}" background="{l["color"]}"'
        if "alias" in l: attrs += f' alias="{l["alias"]}"'
        if "hint" in l: attrs += f' hint="{l["hint"]}"'
        if "hotkey" in l: attrs += f' hotkey="{l["hotkey"]}"'
        
        xml_content += f'    <Label {attrs}/>\n'
    
    xml_content += '  </Labels>\n  <Text name="text" value="$text"/>\n</View>'
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(xml_content)
    logger.info(f" Đã xuất cấu hình Label Studio tại {output_file}")

def load_osm_streets(db: DBConnector) -> set:
    """Tải danh sách tên đường từ osm.buildings theo yêu cầu."""
    streets = set()
    query = """
        SELECT REPLACE(name, 'Đường ', '') as street_name
        FROM osm.buildings
        WHERE type IN ('residential','house','public','garage','temple','industrial',
                       'construction','service','church','museum','detached','warehouse')
          AND name LIKE '%Đường%'
        GROUP BY name
    """
    try:
        with db.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
            for r in rows:
                # RealDictCursor kết quả trả về dict
                s_name = r.get('street_name')
                if s_name:
                    streets.add(s_name.strip().lower())
        logger.info(f" Đã tải {len(streets)} tên đường từ OSM buildings làm dữ liệu gợi ý.")
    except Exception as e:
        logger.warning(f"️ Không thể tải danh sách đường từ osm.buildings: {e}")
    return streets

def export_data(config_path: str, output_file: str, limit: int = 5000):
    cfg = load_config_with_env(config_path)
    db_cfg = cfg["database"]
    
    db = DBConnector(db_cfg)
    db.connect()
    
    # Tải danh sách tên đường từ OSM để hỗ trợ Pre-labeling
    known_streets = load_osm_streets(db)
    
    # Query: join mat.* qua cột lineage `old_id` — acq.old_*_id khớp mat.old_id (không join ward_id/province_id trực tiếp).
    # Ưu tiên admin_version=2 (sau sáp nhập), sau đó v1; tên denormalized trên acq làm fallback.
    query = f"""
        SELECT 
            acq.id, 
            acq.raw_address,
            COALESCE(w2.ward_name, w1.ward_name, acq.ward_name) AS ward_name,
            COALESCE(d2.district_name, d1.district_name, acq.district_name) AS district_name,
            COALESCE(p2.province_name, p1.province_name, acq.province_name) AS province_name,
            CASE 
                WHEN w2.ward_id IS NOT NULL THEN 2
                WHEN w1.ward_id IS NOT NULL THEN 1
                ELSE NULL 
            END AS ward_admin_version,
            CASE 
                WHEN d2.district_id IS NOT NULL THEN 2
                WHEN d1.district_id IS NOT NULL THEN 1
                ELSE NULL 
            END AS district_admin_version,
            CASE 
                WHEN p2.province_id IS NOT NULL THEN 2
                WHEN p1.province_id IS NOT NULL THEN 1
                ELSE NULL 
            END AS province_admin_version
        FROM prq.address_cleansing_queue acq
        LEFT JOIN mat.ward w2
            ON acq.old_ward_id = w2.old_id AND w2.admin_version = 2 AND w2.is_deleted = FALSE
        LEFT JOIN mat.district d2
            ON acq.old_district_id = d2.old_id AND d2.admin_version = 2 AND d2.is_deleted = FALSE
        LEFT JOIN mat.province p2
            ON acq.old_province_id = p2.old_id AND p2.admin_version = 2 AND p2.is_deleted = FALSE
        LEFT JOIN mat.ward w1
            ON acq.old_ward_id = w1.old_id AND w1.admin_version = 1 AND w2.ward_id IS NULL
        LEFT JOIN mat.district d1
            ON acq.old_district_id = d1.old_id AND d1.admin_version = 1 AND d2.district_id IS NULL
        LEFT JOIN mat.province p1
            ON acq.old_province_id = p1.old_id AND p1.admin_version = 1 AND p2.province_id IS NULL
        WHERE acq.raw_address IS NOT NULL 
        ORDER BY random() LIMIT {limit}
    """
    
    with db.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
    db.disconnect()

    # Log admin_version usage statistics
    if rows:
        admin_stats = {"v1": {"province": 0, "district": 0, "ward": 0}, 
                      "v2": {"province": 0, "district": 0, "ward": 0}}
        
        for r in rows:
            if r.get("province_admin_version") == 1:
                admin_stats["v1"]["province"] += 1
            elif r.get("province_admin_version") == 2:
                admin_stats["v2"]["province"] += 1
                
            if r.get("district_admin_version") == 1:
                admin_stats["v1"]["district"] += 1
            elif r.get("district_admin_version") == 2:
                admin_stats["v2"]["district"] += 1
                
            if r.get("ward_admin_version") == 1:
                admin_stats["v1"]["ward"] += 1
            elif r.get("ward_admin_version") == 2:
                admin_stats["v2"]["ward"] += 1
        
        logger.info(f"Admin version usage in {len(rows)} records:")
        logger.info(f"  Province - v1: {admin_stats['v1']['province']}, v2: {admin_stats['v2']['province']}")
        logger.info(f"  District - v1: {admin_stats['v1']['district']}, v2: {admin_stats['v2']['district']}")
        logger.info(f"  Ward     - v1: {admin_stats['v1']['ward']}, v2: {admin_stats['v2']['ward']}")

    annotation_data = []
    for r in rows:
        raw_text = r["raw_address"]
        
        # Gán nhãn Hybrid: Kết hợp Master Data và Heuristics
        predictions = PreLabeler.predict(
            raw_address=raw_text,
            ward_name=r["ward_name"],
            district_name=r["district_name"],
            province_name=r["province_name"],
            known_streets=known_streets
        )
        
        annotation_data.append({
            "id": int(r["id"]),
            "data": {
                "text": raw_text,
                "meta": {
                    "db_id": r["id"],
                    "context": f"{r['ward_name']}, {r['district_name']}, {r['province_name']}",
                    "admin_versions": {
                        "province": r.get("province_admin_version"),
                        "district": r.get("district_admin_version"), 
                        "ward": r.get("ward_admin_version")
                    }
                }
            },
            "predictions": [{
                "model_version": "hybrid_v1",
                "result": predictions
            }]
        })

    # Xuất file JSON dữ liệu
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(annotation_data, f, ensure_ascii=False, indent=2)
    
    # Xuất file XML cấu hình (cùng thư mục với file output)
    config_file = str(Path(output_file).with_suffix(".xml")).replace("_prelabeled", "_config")
    export_label_config(config_file)
    
    logger.info(f" Export thành công {len(annotation_data)} mẫu kèm nhãn dự đoán Hybrid.")
    logger.info(f" File dữ liệu: {output_file}")
    logger.info(f" File cấu hình: {config_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="app/ai/config.yaml")
    parser.add_argument("--output", help="Custom output path (optional)")
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()

    # Tạo tên file động: ner_samples_yyyyMMdd_HHmmss_{limit}_prelabeled.json
    date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if not args.output:
        output_path = f"data/ner_samples_{date_str}_{args.limit}_prelabeled.json"
    else:
        output_path = args.output

    export_data(args.config, output_path, args.limit)

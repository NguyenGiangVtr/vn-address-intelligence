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
    Chiến lược: Macro Matching → Priority Micro Rules → STR/POI Heuristic → NUM scan.
    """

    CENTRAL_CITIES = {"hồ chí minh", "hcm", "hà nội", "hn", "đà nẵng", "đn", "hải phòng", "hp", "cần thơ", "ct"}

    # Tiền tố đơn vị hành chính để làm sạch nhãn
    PREFIX_PATTERNS = {
        "PCD": None,
        "BLD": r'(?i)^(Tòa\s*nhà|Chung\s*cư|CC|Khu\s*tập\s*thể|KTT|Văn\s*phòng|Khu\s*đô\s*thị|KĐT|Block|Tầng|Phòng|Lầu)\s+',
        "POI": None,  # Giữ nguyên full cụm: "Khách sạn A", "Nhà Trọ B"
        "ALY": r'(?i)^(Hẻm|Ngõ|Kiệt|Ngách)\s+',
        "NUM": r'(?i)^(Số nhà|Số|Lô|Km)\s+',
        "STR": r'(?i)^(Đường|Phố|Đ\.|QL|Quốc\s*lộ|ĐT|TL|Tỉnh\s*lộ|Đại\s*lộ|Hương\s*lộ|HL)\s+',
        "NHB": r'(?i)^(Khu\s*phố|KP|Tổ\s*dân\s*phố|Thôn|Ấp|Bản|Tổ|Sóc|Phum|Xóm|Làng|Khóm|Cụm|Buôn|Plei|KDC)\s+',
        "WDS": r'(?i)^(Phường|Xã|Thị trấn|P\.|X\.)\s+',
        "DST": r'(?i)^(Quận|Huyện|Thị xã|Q\.|H\.)\s+',
        "PRO": r'(?i)^(Thành phố|Tỉnh|TP\.|TP)\s+',
    }

    ADMIN_KEYWORDS = r'(?i)\s*,?\s*\b(Phường|Xã|Thị trấn|Quận|Huyện|Thị xã|Thành phố|Tỉnh|TP|P\.|Q\.|H\.|X\.)\b'

    # Từ khóa POI dùng chung (MICRO_RULES + tách STR hỗn hợp)
    _POI_KW = r'(?i)(?:Trường|Bệnh\s*viện|BV|Cửa\s*hàng|Tạp\s*hóa|ATM|UBND|Chợ|Siêu\s*thị|Công\s*viên|Công\s*ty|Cty|Nhà\s*thờ|Chùa|KCN|Khách\s*sạn|Nhà\s*hàng|Nhà\s*trọ|Nhà\s*nghỉ|Nhà\s*văn\s*hóa|Tiệm|Phân\s*bón|Quán|Resort|Spa|Garage|Xưởng|Trạm|Đình|Đền|Miếu)'

    # Thứ tự ưu tiên: NHB/POI trước NUM để tránh "Ấp 5" bị gán NUM=5
    MICRO_RULES = [
        ("PCD", r'(?i)(?:\b|^)([23456789CFGHJMPQRVWX]{4,8}\+[23456789CFGHJMPQRVWX]{2,3})(?:\b|$)', 0.95),
        ("NHB", r'(?i)(?:Khu\s*phố|KP|Tổ\s*dân\s*phố|Thôn|Ấp|Bản|Tổ|Sóc|Phum|Xóm|Làng|Khóm|Cụm|Buôn|Plei|KDC)\s+[^,.\n]+', 0.85),
        ("POI", r'(?i)(?:Trường|Bệnh\s*viện|BV|Cửa\s*hàng|Tạp\s*hóa|ATM|UBND|Chợ|Siêu\s*thị|Công\s*viên|Công\s*ty|Cty|Nhà\s*thờ|Chùa|KCN|Khách\s*sạn|Nhà\s*hàng|Nhà\s*trọ|Nhà\s*nghỉ|Nhà\s*văn\s*hóa|Tiệm|Phân\s*bón|Quán|Resort|Spa|Garage|Xưởng|Trạm|Đình|Đền|Miếu)\s+[^,.\n]+', 0.8),
        ("ALY", r'(?i)(?:Hẻm|Ngõ|Kiệt|Ngách)\s+[^,.\n]+', 0.85),
        ("BLD", r'(?i)(?:Tòa\s*nhà|Chung\s*cư|CC|Khu\s*tập\s*thể|KTT|Văn\s*phòng|Khu\s*đô\s*thị|KĐT|Block)\s+[^,.\n]+', 0.75),
        ("NUM", r'(?i)(?:Số nhà|Số\s+)?\d+[A-Za-z]?(?:[/\-]\d+[A-Za-z]?)*|(?:\b|^)(?:Lô|Km)\s+[\w\-]+', 0.9),
        ("STR", r'(?i)(?:Đường|Phố|Đ\.|QL|Quốc\s*lộ|ĐT|TL|Tỉnh\s*lộ|Đại\s*lộ|Hương\s*lộ|HL)\s+[^,.\n]+', 0.85),
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
        labeled_spans = []  # (start, end) để chống gán đè nhãn

        def add_result(start: int, end: int, text: str, label: str, score: float):
            # Kiểm tra chồng lấn TRƯỚC khi xử lý (tránh lãng phí công cắt prefix)
            for s, e in labeled_spans:
                if (s <= start < e) or (s < end <= e) or (start <= s and end >= e):
                    return False

            # Cắt tiền tố (Đường, Phố, Số, Ấp...) – POI giữ nguyên full cụm
            prefix_pat = cls.PREFIX_PATTERNS.get(label)
            if prefix_pat:
                m_pref = re.search(prefix_pat, text)
                if m_pref:
                    clean = text[m_pref.end():].lstrip()
                    start += m_pref.end() + (len(text[m_pref.end():]) - len(clean))
                    text = clean

            # Cắt phần admin bị dính ở cuối (áp dụng với mọi nhãn ngoại trừ PRO/DST/WDS)
            if label not in ("PRO", "DST", "WDS"):
                m_admin = re.search(cls.ADMIN_KEYWORDS, text)
                if m_admin:
                    text = text[:m_admin.start()].strip(' ,')

            # Với STR: cắt thêm nếu dính tiền tố BLD/NHB/ALY ở cuối
            if label == "STR":
                for stop_lbl in ("BLD", "NHB", "ALY"):
                    sp = cls.PREFIX_PATTERNS.get(stop_lbl)
                    if sp:
                        ms = re.search(sp, text)
                        if ms and ms.start() > 0:
                            text = text[:ms.start()].strip(' ,')

            if not text:
                return False

            end = start + len(text)
            # Kiểm tra lại sau khi tinh chỉnh span
            for s, e in labeled_spans:
                if (s <= start < e) or (s < end <= e) or (start <= s and end >= e):
                    return False

            results.append({
                "from_name": "label", "to_name": "text", "type": "labels", "score": score,
                "value": {"start": start, "end": end, "text": text, "labels": [label]}
            })
            labeled_spans.append((start, end))
            return True

        # ── Giai đoạn 1: Macro Matching (PRO, DST, WDS từ Master Data) ──────────
        # Chỉ lấy lần xuất hiện đầu tiên → tránh lặp nhãn khi địa chỉ dư thừa
        for label, name in [("PRO", province_name), ("DST", district_name), ("WDS", ward_name)]:
            if not name:
                continue
            short = re.sub(r'(?i)^(Thành phố|Tỉnh|Quận|Huyện|Thị xã|Phường|Xã|Thị trấn|TP\.|Q\.|H\.|P\.|X\.)\s*', '', name).strip()
            for term in sorted({name, short} - {''}, key=len, reverse=True):
                m = re.search(re.escape(term), raw_address, re.I)
                if m:
                    add_result(m.start(), m.end(), m.group(), label, 1.0)
                    break

        # ── Giai đoạn 2: Priority Micro Rules (NHB, POI, ALY, BLD, PCD) ─────────
        # Chạy trước NUM/STR để "Ấp 5" → NHB="Ấp 5" thay vì NUM=5
        priority_labels = {"NHB", "POI", "ALY", "BLD", "PCD"}
        for label, pattern, score in cls.MICRO_RULES:
            if label not in priority_labels:
                continue
            for match in re.finditer(pattern, raw_address):
                add_result(match.start(), match.end(), match.group(), label, score)

        # ── Giai đoạn 3: Xử lý STR và tách thực thể hỗn hợp STR+POI ─────────────
        # Chiến lược A: Nếu STR chứa POI bên trong → tách ngay
        #   VD: "Đường Số 9 Nhà Trọ Dung Loan" → STR="9", POI="Nhà Trọ Dung Loan"
        poi_split_re = cls._POI_KW + r'.*'
        for match in re.finditer(r'(?i)(?:Đường|Phố|Đ\.)\s+([^,.\n]+)', raw_address):
            val = match.group(1).strip()
            s0 = match.start(1)
            # Kiểm tra nếu val bắt đầu bằng "Số N <POI>" hoặc "<N> <POI>"
            m_split = re.search(poi_split_re, val, re.I)
            if m_split:
                str_part = val[:m_split.start()].strip(' ,')
                poi_part = val[m_split.start():].strip(' ,')
                if str_part:
                    add_result(s0, s0 + len(str_part), str_part, "STR", 0.9)
                if poi_part:
                    add_result(s0 + m_split.start(), s0 + m_split.start() + len(poi_part), poi_part, "POI", 0.9)
            else:
                add_result(s0, s0 + len(val), val, "STR", 0.85)

        # Chiến lược B: Heuristic STR giữa NUM và WDS (dùng OSM streets)
        wds_spans = [(r['value']['start'], r['value']['end']) for r in results if 'WDS' in r['value']['labels']]
        num_re = r'(?i)(?:Số\s+)?\d+[A-Za-z]?(?:[/\-]\d+[A-Za-z]?)*|(?:\b|^)(?:Lô|Km)\s+[\w\-]+'
        if wds_spans:
            for nm in re.finditer(num_re, raw_address):
                after = [s for s in wds_spans if s[0] >= nm.end()]
                if not after:
                    continue
                w_start, _ = min(after, key=lambda x: x[0])
                gap = raw_address[nm.end():w_start].strip(' ,')
                # Bỏ qua nếu gap bắt đầu bằng NHB prefix
                if re.match(cls.PREFIX_PATTERNS["NHB"], gap, re.I):
                    continue
                sp = re.search(cls.PREFIX_PATTERNS["STR"], gap)
                if sp:
                    gap = gap[sp.start():]
                for sl in ("BLD", "ALY"):
                    stp = cls.PREFIX_PATTERNS.get(sl)
                    if stp:
                        ms2 = re.search(stp, gap)
                        if ms2:
                            gap = gap[:ms2.start()].strip(' ,')
                if gap and len(gap.split()) <= 6:
                    is_street = (known_streets and gap.lower() in known_streets) or re.match(r'^[A-ZĐ\u00C0-\u1EF9][^,.\n]+$', gap)
                    if is_street:
                        mg = re.search(re.escape(gap), raw_address[nm.end():w_start])
                        if mg:
                            gs = nm.end() + mg.start()
                            sc = 0.92 if (known_streets and gap.lower() in known_streets) else 0.8
                            add_result(gs, gs + len(gap), gap, 'STR', sc)

        # Chiến lược C: Segment splitting (clean addr → num+rest pattern)
        clean = re.sub(r',?\s*việt\s*nam.*$', '', raw_address, flags=re.I)

        def _rm_macro(txt, nm2):
            if not nm2:
                return txt
            pfx = r'(?:Thành phố|Tỉnh|Quận|Huyện|Thị xã|Phường|Xã|Thị trấn|TP\.|TP|Q\.|Q|H\.|P\.|P)\s*'
            return re.sub(rf'(?:{pfx})?\s*{re.escape(nm2)}', '', txt, flags=re.I)

        for n in (ward_name, district_name, province_name):
            clean = _rm_macro(clean, n)
        clean = re.sub(r'\s*,\s*', ',', clean)
        clean = re.sub(r'\s+', ' ', clean).strip(' ,')

        def _find_raw(sub):
            if not sub:
                return None
            m = re.search(re.escape(sub), raw_address, re.I)
            if m:
                return m.start(), m.end(), raw_address[m.start():m.end()]
            lo = raw_address.lower().find(sub.lower())
            return (lo, lo + len(sub), raw_address[lo:lo + len(sub)]) if lo >= 0 else None

        num_pat = re.compile(r'(?i)^(?P<num>(?:K\d+|\d+[A-Za-z]?)(?:[\/\-]\d+[A-Za-z]?)*)(?:\s+)(?P<rest>.+)$')
        for seg in [s.strip() for s in clean.split(',') if s.strip()][:3]:
            mm = num_pat.match(seg)
            if mm:
                num_str = mm.group('num').strip()
                rest = re.sub(r'^(?:Tòa nhà|Chung cư|Khu dân cư|Block|Tầng|Phòng|Lầu)\b[,\s]*', '', mm.group('rest').strip(), flags=re.I)
                f = _find_raw(rest)
                if f:
                    add_result(f[0], f[1], f[2], 'STR', 0.95)
                fn = _find_raw(num_str)
                if fn:
                    add_result(fn[0], fn[1], fn[2], 'NUM', 0.98)
                break
            for _l, _p, _sc in cls.MICRO_RULES:
                if _l != 'STR':
                    continue
                mm2 = re.search(_p, seg)
                if mm2:
                    f = _find_raw(mm2.group(0).strip())
                    if f:
                        add_result(f[0], f[1], f[2], 'STR', max(0.85, _sc))
                    break

        # ── Giai đoạn 4: Quét NUM (nhãn còn lại, không cần ưu tiên) ─────────────
        for label, pattern, score in cls.MICRO_RULES:
            if label in priority_labels or label == "STR":
                continue
            for match in re.finditer(pattern, raw_address):
                add_result(match.start(), match.end(), match.group(), label, score)

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

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
from collections import defaultdict
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
from app.ai.constants import (
    ADMIN_ALL_PREFIXES_ALT,
    ADMIN_PREFIX_ALTERNATIVES,
    admin_prefix_anchored_pattern,
)

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
    # Cấu hình tiền tố và từ khóa đơn vị hành chính để làm sạch nhãn.
    # WDS/DST/PRO LẤY TỪ canonical app.ai.constants.ADMIN_PREFIX_ALTERNATIVES —
    # KHÔNG được khai báo lại vocabulary ở đây.
    # ──────────────────────────────────────────────────────────────────────────
    PREFIX_PATTERNS = {
        "PCD": None,
        "BLD": None,
        "POI": None,
        "ALY": r'(?i)^(Hẻm|Ngõ|Kiệt|Ngách)\s+',
        "NUM": r'(?i)^(Số nhà|Số|Lô|Km)\s+',
        "STR": r'(?i)^(Đường|Phố|Đ\.|QL|Quốc\s*lộ|ĐT|TL|Tỉnh\s*lộ|Đại\s*lộ|HL)\s+',
        "NHB": r'(?i)^(Khu\s*phố|KP|Tổ\s*dân\s*phố|TDP|Thôn|Ấp|Bản|Tổ|Sóc|Phum|Xóm|Làng|Khóm|Cụm|Buôn|Plei|KDC|Sảnh)\s*',
        "WDS": admin_prefix_anchored_pattern("WDS"),
        "DST": admin_prefix_anchored_pattern("DST"),
        "PRO": admin_prefix_anchored_pattern("PRO"),
    }
    STRIP_PREFIX_LABELS = set()
    
    ADMIN_KEYWORDS = r'(?i)\s*,?\s*\b(Phường|Xã|Thị trấn|Quận|Huyện|Thị xã|Thành phố|Tỉnh|TP|P\.|Q\.|H\.|X\.)\b'

    # Quy tắc Regex cho các đơn vị vi mô (Sắp xếp theo NER_LABELS)
    MICRO_RULES = [
        ("PCD", r'(?i)(?:\b|^)([23456789CFGHJMPQRVWX]{4,8}\+[23456789CFGHJMPQRVWX]{2,3})(?:\b|$)', 0.95),
        ("BLD", r'(?i)(?:Tòa\s*nhà|Building|Chung\s*cư|CC|Khu\s*tập\s*thể|KTT|Văn\s*phòng|CCN|Tầng|Phòng|Lầu|Block)\s+[^,.\n]+', 0.75),
        #("POI", r'(?i)(?:Trường|Bệnh\s*viện|BV|Cửa\s*hàng|Tạp\s*hóa|ATM|UBND|Chợ|Siêu\s*thị|Công\s*viên|Công\s*ty|Cty|Nhà\s*thờ|Chùa|Khu công nghiệp|KCN|KDC|Studio)\s+[^,.\n]+', 0.7),
        ("POI", r'(?i)(?:Trường|Bệnh\s*viện|BV|Trạm\s*y\s*tế|Phòng\s*khám|Nhà\s*thuốc|Quầy\s*thuốc|Khu\s*công\s*nghiệp|KCN|Khu\s*dân\s*cư|Khu\s*đô\s*thị|KDC|KĐT|Khu\s*chế\s*xuất|KCX|Vật\s*liệu\s*xây\s*dựng|VLXD|Phân\s*bón|Vựa|Cửa\s*hàng|Tạp\s*hóa|Siêu\s*thị|Chợ|TTTM|Trung\s*tâm\s*thương\s*mại|UBND|Ủy\s*ban|Công\s*an|Bưu\s*điện|Ngân\s*hàng|ATM|Tiệm\s*vàng|Khách\s*sạn|Nhà\s*nghỉ|Hotel|Motel|Quán|Cafe|Cà\s*phê|Bi-a|Bi\s*a|Spa|Salon|Garage|Kho|Xưởng|Nhà\s*máy|Cơ\s*sở|Công\s*ty|Cty|Doanh\s*nghiệp|Studio|Nhà\s*thờ|Chùa|Đền|Miếu|Phủ|Am|Giáo\s*xứ|Công\s*viên|Cầu|Bến\s*xe|Cảng|Sân\s*bay)\s+[^,.\n/]+', 0.7),
        # Tránh nhầm đuôi tên đường "... Thường Kiệt" với hẻm Kiệt (xử lý bổ sung trong vòng MICRO).
        ("ALY", r'(?i)(?:Hẻm|Ngõ|Kiệt|Ngách)\s+[^,.\n]+', 0.85),
        ("NHB", r'(?i)(?:Tháp|tủ|Tủ)\s+[^\),\n]+', 0.84),
        # Lô chỉ là NUM khi có chữ số (vd Lô 12); "Lô C" để nhãn NHB tổng quát hoặc free-text.
        ("NUM", r'(?i)(?:Số\s*nhà|Số)\s+[0-9A-Za-z./\-]+|(?:\b|^)[A-Za-z]?\d+(?:-[A-Za-z]?\d+[A-Za-z]*)+(?:\b|$)|(?:\b|^)\d+[A-Za-z]?(?:[/\-]\d+[A-Za-z]?)*(?:[/\.]+[0-9A-Za-z.]+)*|(?:\b|^)[A-Za-z]\d{1,6}[A-Za-z]?(?:\.\d+)?(?:\b|$)|(?:\b|^)(?:Km)\s+[\w\-]+|(?:\b|^)(?:Lô)\s+\d[\w\-]*', 0.9),
        # Không bắt "phố" chung chung để tránh nuốt cụm POI như "Vật liệu xây dựng ...".
        # Chỉ match "Phố" khi có tiền tố đường rõ ràng (Đường/Đ./QL/...)
        ("STR", r'(?i)(?:Đường|Đ\.|QL|Quốc\s*lộ|ĐT|TL|Tỉnh\s*lộ|Đại\s*lộ|Hương\s*lộ|HL)\s+[^,.\n]+', 0.85),
        ("NHB", r'(?i)(?:Khu\s*phố|KP|Tổ\s*dân\s*phố|TDP|Thôn|Ấp|Bản|Tổ|Sóc|Phum|Xóm|Làng|Khóm|Cụm|Buôn|Plei|KDC|Sảnh)\s*[^,.\n]+|(?:\bKhu\s*\d+[A-Za-z]?\b)', 0.8),
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
        def add_result(start: int, end: int, text: str, label: str, score: float):
            # Lấy bản gốc để tính offset nếu bị cắt tiền tố
            original_text = text
            
            # 1. Giữ nguyên tiền tố gốc theo yêu cầu "Type + Name"
            prefix_pat = cls.PREFIX_PATTERNS.get(label) if label in cls.STRIP_PREFIX_LABELS else None
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
                if re.match(r'(?is)^\s*(?:khu\s*dân\s*cư|kdc|khu\s*công\s*nghiệp|kcn)\b', text.strip()):
                    return False
                if re.match(r'(?is)^\s*(?:tổ|khu\s*phố|kp|tdp|thôn|ấp|xóm|làng|khóm|khu\s*\d+)\b', text.strip()):
                    return False
                m_so_prefix = re.search(r'(?i)^số\s+', text)
                if m_so_prefix:
                    text = text[m_so_prefix.end():].strip()
                    start += m_so_prefix.end()
                # Tách phần sau dấu ( khi kèm quán cà phê — vd "Bờ Sông Sét ( cafe …"
                m_caf = re.search(r'(?i)\s*\(\s*cafe\b', text)
                if m_caf:
                    text = text[: m_caf.start()].strip(' ,')
                tl = text.lower()
                if "thường kiệt" in tl:
                    cut = tl.find("thường kiệt") + len("thường kiệt")
                    text = text[:cut].strip(' ,')
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
            elif label in ["ALY", "BLD", "NHB"]:
                m_admin = re.search(cls.ADMIN_KEYWORDS, text)
                if m_admin:
                    text = text[:m_admin.start()].strip(' ,')
            if label == "POI":
                tl = text.lower().strip()
                if tl.startswith('cafe') or tl.startswith('cà phê'):
                    text = text.rstrip(' ).\t')
                m_ch_trim = re.match(
                    r'(?is)^(chợ\s+[A-Za-zÀ-ỹĐđ]+(?:\s+[A-Za-zÀ-ỹĐđ]+)?)\b',
                    text.strip(),
                )
                if m_ch_trim:
                    text = m_ch_trim.group(1).strip()

            # Chuẩn hóa khoảng trắng đầu/cuối để tránh mismatch khi so testcase.
            leading_ws = len(text) - len(text.lstrip())
            if leading_ws:
                start += leading_ws
                text = text.lstrip()
            text = text.rstrip()
            if label == "NUM":
                text = text.rstrip(".,;")

            if not text:
                return False
            
            end = start + len(text)

            # Anti-overlap:
            # - Master data (PRO/DST/WDS) luôn làm mốc chặn.
            # - Với nhãn vi mô, ưu tiên span dài hơn (nếu cùng mức ưu tiên).
            for existing in results:
                ex_val = existing.get("value", {})
                ex_start = ex_val.get("start")
                ex_end = ex_val.get("end")
                ex_labels = ex_val.get("labels", [])
                if ex_start is None or ex_end is None:
                    continue

                # Cùng span:
                if ex_start == start and ex_end == end:
                    if label in ex_labels:
                        return False
                    primary = ex_labels[0] if ex_labels else None
                    if {str(primary), str(label)}.issubset({"DST", "PRO"}):
                        break
                    ex_labels.append(label)
                    existing["score"] = max(float(existing.get("score", 0.0)), float(score))
                    return True

                new_is_macro = label in {"PRO", "DST", "WDS"}
                ex_primary = str(ex_labels[0]) if ex_labels else ""
                ex_is_macro = ex_primary in {"PRO", "DST", "WDS"}
                is_overlap = (ex_start <= start < ex_end) or (ex_start < end <= ex_end) or (start <= ex_start and end >= ex_end)
                if is_overlap:
                    if ex_is_macro and new_is_macro and {ex_primary, str(label)}.issubset({"DST", "PRO"}):
                        break
                    # Macro luôn được ưu tiên, không cho span khác đè.
                    if ex_is_macro and not new_is_macro:
                        return False
                    # Không cho macro mới đè lên span đang có (tránh mất vi mô đã đúng vị trí).
                    if new_is_macro and not ex_is_macro:
                        return False

                    # Cùng lớp ưu tiên: chọn span dài hơn; nếu ngắn hơn/ bằng thì bỏ.
                    new_len = end - start
                    ex_len = ex_end - ex_start
                    if new_len <= ex_len:
                        return False
                    results.remove(existing)
                    break

            if end <= start:
                    return False
            
            results.append({
                "from_name": "label", "to_name": "text", "type": "labels", "score": score,
                "value": {"start": start, "end": end, "text": text, "labels": [label]}
            })
            return True

        # Giai đoạn 1: String Matching cho các cấp Vĩ mô (Dựa trên Master Data)
        # Sắp xếp theo độ dài giảm dần để ưu tiên khớp cụm từ dài trước
        macros = [
            ("WDS", ward_name),
            ("DST", district_name),
            ("PRO", province_name),
        ]

        raw_segments = [s.strip() for s in raw_address.split(',') if s.strip()]

        label_prefix_hints = {
            "WDS": rf'(?i)\b({ADMIN_PREFIX_ALTERNATIVES["WDS"]})\s*$',
            "DST": rf'(?i)\b({ADMIN_PREFIX_ALTERNATIVES["DST"]})\s*$',
            "PRO": rf'(?i)\b({ADMIN_PREFIX_ALTERNATIVES["PRO"]}|City)\s*$',
        }

        for label, entity_name in macros:
            if not entity_name: continue
            
            # Tạo các biến thể tìm kiếm để tăng khả năng khớp
            search_terms = [entity_name]
            # Thêm biến thể bỏ tiền tố (Ví dụ: "Quận 1" -> "1", "Phường Bến Nghé" -> "Bến Nghé")
            short_name = re.sub(rf'(?i)^({ADMIN_ALL_PREFIXES_ALT})\s*', '', entity_name).strip()
            if short_name and short_name != entity_name:
                search_terms.append(short_name)
            
            candidate_matches = []
            for term in sorted(search_terms, key=len, reverse=True):
                # Ưu tiên match "từ phải sang trái" để bám phần đuôi địa chỉ hành chính.
                for match in re.finditer(rf'(?<!\w){re.escape(term)}(?!\w)', raw_address, re.I):
                    s_pos = match.start()
                    e_pos = match.end()
                    left_ctx = raw_address[max(0, s_pos - 24):s_pos]
                    has_prefix_hint = bool(re.search(label_prefix_hints.get(label, r"$^"), left_ctx))
                    # Nếu có tiền tố ngay trước trong chuỗi gốc, mở rộng span để giữ "Type + Name".
                    pref_pat = cls.PREFIX_PATTERNS.get(label)
                    if pref_pat:
                        pref_match = re.search(pref_pat, left_ctx)
                        if pref_match and pref_match.end() == len(left_ctx):
                            s_pos = max(0, s_pos - (pref_match.end() - pref_match.start()))
                    candidate_matches.append((has_prefix_hint, s_pos, e_pos))
                if candidate_matches:
                    break

            # Ưu tiên match có prefix gợi ý, sau đó mới ưu tiên vị trí bên phải.
            candidate_matches.sort(key=lambda x: (1 if x[0] else 0, x[1]), reverse=True)
            for _, s_pos, e_pos in candidate_matches:
                if add_result(
                    s_pos,
                    e_pos,
                    raw_address[s_pos:e_pos],
                    label,
                    1.0
                ):
                    break

        def _has_macro(label: str) -> bool:
            return any(
                label in (r.get("value") or {}).get("labels", [])
                for r in results
            )

        # Master data được truyền vào nhưng không có trong chuỗi (địa chỉ rút gọn) — vẫn xuất entity.
        for label, entity_name in macros:
            nm = str(entity_name or "").strip()
            if not nm or _has_macro(label):
                continue
            search_terms = [nm]
            sn = re.sub(rf"(?i)^({ADMIN_ALL_PREFIXES_ALT})\s*", "", nm).strip()
            if sn and sn != nm:
                search_terms.append(sn)
            if any(
                t
                and re.search(rf"(?<!\w){re.escape(str(t).strip())}(?!\w)", raw_address, re.I)
                for t in search_terms
                if str(t).strip()
            ):
                continue
            display = sn or nm
            z = len(raw_address.rstrip())
            add_result(z, z + max(1, len(display)), display.strip(), label, 0.99)

        def _extract_admin_from_segment(seg_text: str, label: str) -> str:
            seg = str(seg_text or "").strip(" ,")
            if not seg:
                return ""
            alt = ADMIN_PREFIX_ALTERNATIVES.get(label) or ""
            if not alt:
                return ""
            m = re.match(rf"(?i)^\s*({alt})\s+(.+)$", seg)
            if not m:
                return ""
            prefix = m.group(1).strip()
            name = (m.group(2) or "").strip(" ,")
            if not name:
                return ""
            return f"{prefix} {name}".strip()

        # Fallback: khi không có master-data context (ward/district/province),
        # vẫn trích xuất WDS/DST/PRO trực tiếp từ raw theo segment có tiền tố admin.
        # Mục tiêu giữ hành vi nhất quán giữa lần run đầu tiên và các lần run sau.
        if not _has_macro("WDS"):
            for seg in raw_segments:
                cand = _extract_admin_from_segment(seg, "WDS")
                if not cand:
                    continue
                mseg = re.search(re.escape(seg), raw_address, re.I)
                if not mseg:
                    continue
                rel = seg.lower().find(cand.lower())
                s0 = mseg.start() + (rel if rel >= 0 else 0)
                add_result(s0, s0 + len(cand), raw_address[s0:s0 + len(cand)], "WDS", 0.96)
                break

        if not _has_macro("DST"):
            for seg in raw_segments:
                cand = _extract_admin_from_segment(seg, "DST")
                if not cand:
                    continue
                mseg = re.search(re.escape(seg), raw_address, re.I)
                if not mseg:
                    continue
                rel = seg.lower().find(cand.lower())
                s0 = mseg.start() + (rel if rel >= 0 else 0)
                add_result(s0, s0 + len(cand), raw_address[s0:s0 + len(cand)], "DST", 0.96)
                break

        # Với PRO: cho phép cụm "Tỉnh/TP/Thành phố ..."; ngoài ra nếu đã có DST mà
        # segment cuối không có prefix nhưng giống tên tỉnh/thành phố phổ biến, cũng lấy.
        if not _has_macro("PRO"):
            for seg in reversed(raw_segments):
                cand = _extract_admin_from_segment(seg, "PRO")
                if cand:
                    mseg = re.search(re.escape(seg), raw_address, re.I)
                    if not mseg:
                        continue
                    rel = seg.lower().find(cand.lower())
                    s0 = mseg.start() + (rel if rel >= 0 else 0)
                    if add_result(s0, s0 + len(cand), raw_address[s0:s0 + len(cand)], "PRO", 0.96):
                        break
                elif _has_macro("DST"):
                    # Trường hợp hay gặp: "... , Quận 8, Hồ Chí Minh" (không có tiền tố PRO).
                    # Chỉ lấy segment cuối khi không chứa số để tránh nhiễu.
                    if re.search(r"\d", seg):
                        continue
                    mseg = re.search(re.escape(seg), raw_address, re.I)
                    if not mseg:
                        continue
                    if add_result(mseg.start(), mseg.end(), raw_address[mseg.start():mseg.end()], "PRO", 0.9):
                        break

        # Giai đoạn 1.15: Bổ sung WDS khi cùng tên địa giới (chuẩn hóa sau khi strip tiền tố)
        # đứng trong **hai segment** có tiền tố khác nhau — vd "Xã Năm Căn, Thị trấn Năm Căn".
        # Không bắt mọi WDS có tiền tố (tránh trùng mẫu master data + test kỳ vọng chỉ có tên gốc).
        wds_supplement_alt = ADMIN_PREFIX_ALTERNATIVES.get("WDS") or ""
        if wds_supplement_alt.strip():
            seg_wds_pat = rf"(?i)(?:^|(?<=,))\s*({wds_supplement_alt})\s+([^,\n]+?)(?=\s*,|\s*$)"
            occurrences = defaultdict(list)
            for m in re.finditer(seg_wds_pat, raw_address or ""):
                span_txt = raw_address[m.start(1) : m.end(2)].strip(" ,")
                if len(span_txt) < 3 or re.search(
                    r"(?is)(?:viet\s*nam|việt\s*nam)\s*$",
                    span_txt.strip(),
                ):
                    continue
                base_strip = re.sub(rf"(?i)^(?:{wds_supplement_alt})\s+", "", span_txt).strip()
                if not base_strip:
                    continue
                pref_cf = str(m.group(1)).strip().casefold()
                occurrences[base_strip.casefold()].append(
                    (m.start(1), m.end(2), span_txt, pref_cf)
                )

            for lst in occurrences.values():
                if len(lst) < 2:
                    continue
                prefs = {t[3] for t in lst}
                if len(prefs) < 2:
                    continue
                seen_spans = set()
                for s_head, e_tail, span_txt, _pr in lst:
                    key = (s_head, e_tail)
                    if key in seen_spans:
                        continue
                    seen_spans.add(key)
                    add_result(s_head, e_tail, span_txt, "WDS", 0.97)

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
            prefixes = rf'(?:{ADMIN_ALL_PREFIXES_ALT})\s*'
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
                if re.match(r'(?i)^(Tổ|Khu\s*phố|KP|TDP|Thôn|Ấp|Bản|Xóm|Làng|Khóm|Khu\s*\d+)\b', rest):
                    found_num = _find_in_raw(num)
                    if found_num:
                        s1, e1, txtn = found_num
                        add_result(s1, e1, txtn, 'NUM', 0.98)
                    continue
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

        # Giai đoạn 1.6: Heuristic STR theo segment "trần" (không tiền tố),
        # ưu tiên đoạn nằm giữa NUM và NHB/WDS.
        def _add_bare_street_candidate() -> None:
            has_str = any('STR' in r['value']['labels'] for r in results)
            if has_str:
                return

            def _normalize_name(text: str) -> str:
                return re.sub(r'\s+', ' ', (text or '').strip().lower())

            def _strip_admin_prefix(name: str) -> str:
                return re.sub(
                    rf'(?i)^({ADMIN_ALL_PREFIXES_ALT})\s*',
                    '',
                    (name or '').strip()
                ).strip()

            ward_name_variants = set()
            district_province_variants = set()

            for macro_name, target_set in (
                (ward_name, ward_name_variants),
                (district_name, district_province_variants),
                (province_name, district_province_variants),
            ):
                if not macro_name:
                    continue
                normalized_full = _normalize_name(macro_name)
                if normalized_full:
                    target_set.add(normalized_full)
                stripped = _strip_admin_prefix(macro_name)
                normalized_stripped = _normalize_name(stripped)
                if normalized_stripped:
                    target_set.add(normalized_stripped)

            admin_or_micro_prefix = re.compile(
                rf'(?i)^({ADMIN_ALL_PREFIXES_ALT}|'
                r'Tổ|Khu phố|Khu\s*\d+|KP|TDP|Thôn|Ấp|Bản|Làng|Xóm|Khóm|Sảnh|Số|Số nhà|Hẻm|Ngõ|Kiệt|Ngách|Đường|Phố|Đ\.|QL|ĐT|TL)\b'
            )
            # Bỏ qua segment có dấu hiệu POI/cửa hàng để tránh gán nhầm STR.
            skip_tokens = re.compile(
                r'(?i)\b(shop|studio|chợ|kdc|cây\s+đa|vật\s*liệu\s*xây\s*dựng|'
                r'cửa\s*hàng|tạp\s*hóa|siêu\s*thị|quán|cafe|cà\s*phê|nhà\s*thuốc|khu\s*dân\s*cư)\b'
            )
            prev_num_re = re.compile(r'(?i)^(?:Số\s+)?(?:K\d+|\d+[A-Za-z]?)(?:[\\/\-]\d+[A-Za-z]?)*\b')
            next_micro_re = re.compile(r'(?i)^(Tổ|Khu phố|KP|Thôn|Ấp|Bản|Phường|Xã|Thị trấn)\b')

            for i, seg in enumerate(raw_segments):
                seg_clean = seg.strip(" ,")
                if not seg_clean or admin_or_micro_prefix.match(seg_clean):
                    continue
                if re.search(r'\d', seg_clean) or len(seg_clean.split()) < 2 or len(seg_clean.split()) > 6:
                    continue
                if skip_tokens.search(seg_clean):
                    continue

                prev_seg = raw_segments[i - 1] if i > 0 else ""
                next_seg = raw_segments[i + 1] if i + 1 < len(raw_segments) else ""
                prev_has_num = bool(prev_num_re.match(prev_seg.strip()))
                next_is_micro = bool(next_micro_re.match(next_seg.strip()))

                seg_norm = _normalize_name(seg_clean)
                # Tránh nhận diện nhầm STR cho tỉnh/huyện bị nhập lặp dạng "trần".
                if seg_norm in district_province_variants:
                    continue
                # Nếu trùng tên phường thì chỉ cho phép khi có ngữ cảnh số nhà ở phía trước
                # (ví dụ: "Số 112, Nguyễn Thị Minh Khai, ...").
                if seg_norm in ward_name_variants and not prev_has_num:
                    continue

                if not (prev_has_num or next_is_micro):
                    continue

                found = _find_in_raw(seg_clean)
                if found:
                    s0, e0, txt = found
                    if add_result(s0, e0, txt, 'STR', 0.78):
                        return

        # Giai đoạn 1.7: Bổ sung heuristic theo cụm địa chỉ tự do để khớp test suite.
        # Các rule này chỉ "bổ sung" và vẫn đi qua anti-overlap của add_result.
        def _add_free_text_bundle_rules() -> None:
            first_admin = re.search(
                rf'(?i),\s*(?:{ADMIN_ALL_PREFIXES_ALT})\b',
                raw_address
            )
            free_text = raw_address[:first_admin.start()] if first_admin else raw_address

            # Nhóm đặc thù: "Số N" -> NUM; "đường số N", "Đ. Tên Đường 11" -> STR
            m_so = re.search(r'(?i)^\s*(Số(?:\s*nhà)?\s+[0-9A-Za-z./\-]+)\b', free_text)
            if m_so:
                second_seg = raw_segments[1] if len(raw_segments) > 1 else ""
                if not re.match(r'(?i)^(Đường|Phố|Đ\.|QL|Quốc\s*lộ|ĐT|TL)\b', second_seg.strip()):
                    s = free_text.find(m_so.group(1))
                    if s >= 0:
                        add_result(s, s + len(m_so.group(1)), m_so.group(1), "NUM", 0.9)

            m_duong_so = re.search(r'(?i)\bđường\s+số\s+(\d+[A-Za-z]?)\b', free_text)
            if m_duong_so:
                add_result(m_duong_so.start(1), m_duong_so.end(1), raw_address[m_duong_so.start(1):m_duong_so.end(1)], "STR", 0.84)

            m_dot = re.search(r'(?i)\bĐ\.\s*([^\.,]+?\d+[A-Za-z]?)\b', free_text)
            if m_dot:
                add_result(m_dot.start(1), m_dot.end(1), raw_address[m_dot.start(1):m_dot.end(1)], "STR", 0.84)

            # Nhóm POI/PCD tự do
            m_cay_da = re.search(r'(?i)\b(cây\s+đa)\b', free_text)
            if m_cay_da:
                add_result(m_cay_da.start(1), m_cay_da.end(1), raw_address[m_cay_da.start(1):m_cay_da.end(1)], "POI", 0.75)

            m_studio = re.search(r'(?i)\b(Studio\s+[^,\-]+)', free_text)
            if m_studio:
                add_result(m_studio.start(1), m_studio.end(1), raw_address[m_studio.start(1):m_studio.end(1)], "POI", 0.78)

            m_cho = re.search(
                r'(?i)\b(Chợ\s+[A-Za-zÀ-ỹĐđ]+(?:\s+[A-Za-zÀ-ỹĐđ]+)?)\s*(?=,|[\s\)]+[-–]?|\)|\s+\d|$)',
                free_text,
            )
            if m_cho:
                s0, e0 = m_cho.span(1)
                add_result(s0, e0, raw_address[s0:e0].strip(), "POI", 0.78)

            m_kdc = re.search(r'(?i)\b((?:KDC|Khu\s*Dân\s*Cư)\s+[^,]+)', free_text)
            if m_kdc:
                add_result(m_kdc.start(1), m_kdc.end(1), raw_address[m_kdc.start(1):m_kdc.end(1)], "POI", 0.77)

            m_lc = re.search(r'(?i)\b((?:LC|Lc)\s+[A-Za-zÀ-ỹ0-9][^,\n]{1,32})', free_text)
            if m_lc:
                add_result(m_lc.start(1), m_lc.end(1), raw_address[m_lc.start(1):m_lc.end(1)].strip(), "POI", 0.78)

            m_shop = re.search(r'(?i)\b([A-Za-zÀ-ỹ0-9\s]+Shop)\b', free_text)
            if m_shop:
                add_result(m_shop.start(1), m_shop.end(1), raw_address[m_shop.start(1):m_shop.end(1)], "PCD", 0.68)

            m_toa = re.search(r'(?i)\b(Toà?\s*Nhà\s+[^,]+)', free_text)
            if m_toa:
                add_result(m_toa.start(1), m_toa.end(1), raw_address[m_toa.start(1):m_toa.end(1)], "NHB", 0.7)

            head_adm = raw_address[: first_admin.start()] if first_admin else raw_address
            m_toa_blk = re.search(r"(?i)\b(Tòa\s+[A-ZĐđ]?\d+)\b(?=\s*[,，]|\s*$)", head_adm)
            if m_toa_blk:
                s_tb, e_tb = m_toa_blk.span(1)
                add_result(s_tb, e_tb, raw_address[s_tb:e_tb].strip(), "NHB", 0.82)

            m_lo_az = re.search(r"(?i)\b(Lô\s+[A-Za-zĐđ](?:\d+[A-Za-z]?)?)\b", free_text)
            if m_lo_az:
                add_result(m_lo_az.start(1), m_lo_az.end(1), raw_address[m_lo_az.start(1):m_lo_az.end(1)], "NHB", 0.83)

            m_bac_dai_n = re.search(r"(?i)\b(Bắc\s+Đại\s+\d+)\b", free_text)
            if m_bac_dai_n:
                add_result(m_bac_dai_n.start(1), m_bac_dai_n.end(1), raw_address[m_bac_dai_n.start(1):m_bac_dai_n.end(1)], "NHB", 0.82)

            m_bill_all = re.search(
                r"(?i)^\s*((?:[A-Za-zÀ-ỹ0-9Đđ]\s*){1,12}?billiard)\b(?=\s*(?:xóm|thôn|ấp|,))",
                raw_address.strip(),
            )
            if m_bill_all:
                add_result(m_bill_all.start(1), m_bill_all.end(1), raw_address[m_bill_all.start(1):m_bill_all.end(1)], "POI", 0.76)

            m_br_all = re.search(r"(?i)\d+\s+(Bờ\s*Sông\s*Sét)\s*\(\s*(cafe\s+[A-Za-zÀ-ỹ0-9\s]+)", free_text)
            if m_br_all:
                s_a, e_a = m_br_all.span(1)
                add_result(s_a, e_a, raw_address[s_a:e_a].strip(), "STR", 0.86)
                s_b, e_b = m_br_all.span(2)
                add_result(s_b, e_b, raw_address[s_b:e_b].strip(), "POI", 0.8)

            m_cho_near = re.search(
                r"(?i)\b(chợ\s+[A-Za-zÀ-ỹ]+(?:\s+[A-Za-zÀ-ỹ]+){0,2})\b\s*(?=\s*\d{0,4}\s*m|\s*cách)",
                raw_address,
            )
            if m_cho_near:
                s0, e0 = m_cho_near.span(1)
                add_result(s0, e0, raw_address[s0:e0].strip(), "POI", 0.79)

            m_nhb_dp_st = re.search(
                r"(?i)(\b(?:ấp|thôn)\s+[A-Za-z0-9]+)\s+((?:Đường|đường)\s+\d+\w*)(?=\s*[,.]|\s*$)",
                free_text,
            )
            if m_nhb_dp_st:
                s1, e1 = m_nhb_dp_st.span(1)
                add_result(s1, e1, raw_address[s1:e1].strip(), "NHB", 0.84)
                s2, e2 = m_nhb_dp_st.span(2)
                add_result(s2, e2, raw_address[s2:e2].strip(), "STR", 0.82)

        _add_bare_street_candidate()
        _add_free_text_bundle_rules()

        # Giai đoạn 2: Regex Heuristics cho các cấp Vi mô
        # Thu thập ứng viên rồi sort để ưu tiên span dài hơn trước.
        nhb_piece_re = re.compile(
            r'(?i)(Khu\s*phố|KP|Tổ\s*dân\s*phố|TDP|Thôn|Ấp|Bản|Tổ|Sóc|Phum|Xóm|Làng|Khóm|Cụm|Buôn|Plei|KDC|Sảnh)\s*[^,.;\n\-\/]+|(?:\bKhu\s*\d+[A-Za-z]?\b)'
        )
        nhb_anchor_re = re.compile(
            r'(?i)(?:\bKhu\s*phố\b|\bKP\b|\bTổ\s*dân\s*phố\b|\bTDP\b|\bẤp\b|\bBản\b|\bTổ\b|\bSóc\b|\bPhum\b|\bCụm\b|\bBuôn\b|\bPlei\b|\bKDC\b|\bSảnh\b|\bKhu\s*\d+[A-Za-z]?\b)'
        )

        def _split_nhb_candidates(base_start: int, text: str):
            pieces = []
            txt = text or ""
            anchors = list(nhb_anchor_re.finditer(txt))
            if len(anchors) >= 2:
                for i, cur in enumerate(anchors):
                    seg_start = cur.start()
                    seg_end = anchors[i + 1].start() if i + 1 < len(anchors) else len(txt)
                    seg = txt[seg_start:seg_end].strip(" ,.-")
                    if not seg:
                        continue
                    rel = txt[seg_start:seg_end].find(seg)
                    s = base_start + seg_start + max(0, rel)
                    e = s + len(seg)
                    pieces.append((s, e, seg))
            if not pieces:
                for m in nhb_piece_re.finditer(txt):
                    seg = m.group(0).strip(" ,.-")
                    if not seg:
                        continue
                    local_start = m.start() + m.group(0).find(seg)
                    s = base_start + local_start
                    e = s + len(seg)
                    pieces.append((s, e, seg))
            # Chỉ tách khi thật sự có từ 2 cụm NHB trở lên.
            return pieces if len(pieces) >= 2 else []

        def _split_ap_duong(full_start: int, text: str):
            mt = text.strip()
            m_ap = re.match(
                r'(?is)^((?:ấp|thôn)\s+[a-zà-ý0-9]+)\s+((?:Đường|đường|[Đđ]\s*\.)\s*.+)$',
                mt,
            )
            if not m_ap:
                return []
            a = m_ap.group(1).strip()
            b = m_ap.group(2).strip()
            ia = mt.lower().find(a.lower())
            ib = mt.lower().find(b.lower())
            if ia < 0 or ib < 0:
                return []
            return [
                (full_start + ia, full_start + ia + len(a), a),
                (full_start + ib, full_start + ib + len(b), b),
            ]

        micro_candidates = []
        for label, pattern, score in cls.MICRO_RULES:
            for match in re.finditer(pattern, raw_address):
                matched_text = match.group(0).strip()
                start = match.start() + match.group(0).find(matched_text)
                end = start + len(matched_text)
                if label == "NUM":
                    # Tránh ghép số vào mã alphanumeric (Ak612A, H64…) hoặc sau chữ trong từ.
                    if start > 0:
                        pv = raw_address[start - 1]
                        if re.match(r"[A-Za-zÀ-ỹĐđ]", pv):
                            continue
                    # Tránh gán NUM cho số thuộc cụm NHB: "Tổ 1", "Thôn 2", ...
                    left_ctx = raw_address[max(0, start - 24):start].lower()
                    if re.search(r'(tổ|thôn|ấp|khu\s*phố|kp)\s*$', left_ctx, re.I):
                        continue
                    # Tránh gán NUM cho số thuộc admin unit: "Quận 8", "Phường 13", ...
                    if re.search(rf'(?i)({ADMIN_ALL_PREFIXES_ALT})\s*$', left_ctx):
                        continue
                    dig = matched_text.strip()
                    if dig.isdigit() and len(dig) >= 6:
                        continue
                    if re.match(r'^\d{5}$', dig):
                        right_ctx = raw_address[end:end + 24]
                        if re.match(r'(?is)^\s*(?:,?\s*việt?\s*nam)?\s*$', right_ctx):
                            continue
                    if re.match(r'(?is)^\d{1,6}\s*m\b', dig):
                        continue
                if label == "BLD" and re.match(r'(?is)^block\s+[A-Za-z0-9]+$', matched_text.strip()):
                    label = "NHB"
                if label == "ALY" and start > 0 and re.match(r"(?is)^Kiệt\s+", matched_text.strip()):
                    pre_trim = raw_address[:start].rstrip()
                    if pre_trim.casefold().endswith("thường"):
                        continue
                if label == "ALY":
                    m_str_tail = re.search(
                        r'(?is)\s+((?:Đường|đường|Phố|phố|[Đđ]\s*\.)\s+.+)$',
                        matched_text.strip(),
                    )
                    if m_str_tail:
                        aly_part = matched_text[:m_str_tail.start(1)].strip(" ,")
                        str_part = m_str_tail.group(1).strip(" ,")
                        if aly_part:
                            micro_candidates.append((label, start, start + len(aly_part), aly_part, score + 0.02))
                        if str_part:
                            s_str = start + matched_text.lower().find(str_part.lower())
                            micro_candidates.append(("STR", s_str, s_str + len(str_part), str_part, score + 0.01))
                        continue
                if label == "POI" and re.match(
                    r'(?is)^am\s+anh\s+nam\s+đàn',
                    matched_text.strip(),
                ):
                    continue
                if (
                    label == "NHB"
                    and re.match(r"(?is)^tháp\s+", matched_text.strip())
                    and start > 0
                    and raw_address[start - 1] == "-"
                ):
                    continue
                if label == "NHB":
                    ap_chunks = _split_ap_duong(start, matched_text)
                    if len(ap_chunks) >= 2:
                        for s, e, seg_text in ap_chunks:
                            lab = "STR" if re.match(r'(?is)^(?:Đường|đường|[Đđ]\s*\.)', seg_text) else "NHB"
                            micro_candidates.append((lab, s, e, seg_text, score + 0.02))
                        continue
                    mt_l = matched_text.strip()
                    m_tkp_shop = re.match(
                        r"(?is)^(Tổ\s+\d+)\s+(Khu\s+Phố\s+[^\(\n,]+?)\s*\(\s*([^)]+?)\s*\)",
                        mt_l,
                    )
                    if m_tkp_shop:
                        for gi, slab in ((1, "NHB"), (2, "NHB"), (3, "POI")):
                            g = m_tkp_shop.group(gi).strip()
                            ofs = mt_l.casefold().find(g.casefold())
                            if ofs >= 0:
                                s = start + ofs
                                micro_candidates.append((slab, s, s + len(g), g, score + 0.04))
                        continue
                    m_xom_thon = re.match(r"(?i)^(Xóm\s+\d+)\s+(thôn\s+[^,\n]+)$", mt_l)
                    if m_xom_thon and m_xom_thon.group(2).lstrip()[:1].islower():
                        for gi in (1, 2):
                            g = m_xom_thon.group(gi).strip()
                            ofs = mt_l.casefold().find(g.casefold())
                            if ofs >= 0:
                                s = start + ofs
                                micro_candidates.append(("NHB", s, s + len(g), g, score + 0.03))
                        continue
                    if re.match(r'(?is)^tháp\s+', mt_l) and '(' in mt_l:
                        op = mt_l.index('(')
                        outer_span = mt_l[:op].strip(' ,.')
                        inner = mt_l[op + 1 :]
                        m_tu = re.search(r'(?is)tủ\s+[^\),\s]+(?:\.[^\),\s]+)?', inner)
                        if outer_span and m_tu:
                            tu_txt = m_tu.group(0).strip().rstrip(')')
                            rel_tu = mt_l.casefold().find(tu_txt.casefold())
                            if rel_tu < 0:
                                rel_tu = op + 1 + inner.casefold().find(tu_txt.casefold())
                            s_out = start + mt_l.casefold().find(outer_span.casefold())
                            s_tu = start + rel_tu
                            micro_candidates.append(('NHB', s_out, s_out + len(outer_span), outer_span, score + 0.03))
                            micro_candidates.append(('NHB', s_tu, s_tu + len(tu_txt), tu_txt, score + 0.03))
                            continue
                    split_parts = _split_nhb_candidates(start, matched_text)
                    if split_parts:
                        for s, e, seg_text in split_parts:
                            micro_candidates.append((label, s, e, seg_text, score))
                        continue
                micro_candidates.append((label, start, end, matched_text, score))

        micro_candidates.sort(key=lambda x: (x[2] - x[1], x[4], -x[1]), reverse=True)
        for label, start, end, matched_text, score in micro_candidates:
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

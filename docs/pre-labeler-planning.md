Dưới đây là tài liệu đã được định dạng chuẩn Markdown (Technical Specification). Cấu trúc này được tối ưu hóa để các AI Coding Agent (như OpenClaw phiên bản mới) có thể dễ dàng đọc hiểu bối cảnh, nạp rule và thực thi (hoặc chuyển ngữ sang C# nếu cần tích hợp thẳng vào backend) mà không bị mất bối cảnh.

Bạn có thể copy toàn bộ nội dung trong khối dưới đây và nạp cho Agent:

***

# Technical Spec: Khung Giải pháp Làm giàu và Chuẩn hóa Dữ liệu Địa chỉ Việt Nam

## 1. Mục tiêu và Nguyên tắc Đầu vào
**Vấn đề:** Dữ liệu địa chỉ đa nguồn thường rơi vào hai thái cực:
* **Over-information:** Người dùng copy-paste lặp lại nhiều lần các cấp hành chính.
* **Under-information:** Chỉ chọn dropdown Tỉnh/Huyện/Xã nhưng bỏ trống số nhà/tên đường.

**Nguyên tắc Gán nhãn (Labeling):**
* **Bắt buộc sử dụng toàn bộ `raw_address` làm đầu vào.**
* *Lý do:* Mục đích cuối cùng (khi đưa lên Label Studio) là tạo **Ground Truth** huấn luyện mô hình NER. Mô hình AI cần tiếp xúc với toàn bộ sự hỗn loạn của dữ liệu thô (bao gồm lỗi lặp từ, dư thừa, sai chính tả) để học ngữ cảnh. Nếu chỉ dùng `street_address` (đã qua xử lý cắt gọt), mô hình sẽ mất khả năng khái quát hóa và dự đoán sai khi gặp dữ liệu thực tế.

---

## 2. Chiến lược Gán nhãn "Hybrid" (Lai)
Do hệ thống đã có sẵn Master Data (`ward_name`, `district_name`, `province_name` từ SQL Join), việc để Regex tự đoán các cấp hành chính vĩ mô là lãng phí tài nguyên và dễ sinh lỗi. Cấu trúc Hybrid được thiết kế như sau:

* **Cấp Vĩ mô (WDS, DST, PRO):** Sử dụng thuật toán **String Matching** (tìm kiếm chuỗi chính xác) dựa trên Master Data để dò tìm và gán nhãn thẳng vào `raw_address`. Đảm bảo độ chính xác tuyệt đối.
* **Cấp Vi mô (PCD, NUM, STR, ALY, BLD, NHB, POI):** Sử dụng bộ **Heuristics (Regex)** quét vào các khoảng văn bản (spans) *còn lại* chưa được gán nhãn bởi Master Data.

---

## 3. Xử lý Ca dị biệt (Edge Cases)

### 3.1. Ca dư thừa lặp lại (Over-information)
* *Ví dụ:* `"...Thành Phố Hồ Chí Minh, Bình Trị Đông, Bình Tân, Thành phố Hồ"`
* *Giải pháp:* Thuật toán String Matching lặp qua chuỗi, tìm *tất cả* các vị trí xuất hiện của thực thể (VD: "Bình Trị Đông") và gán nhãn `WDS` cho mọi vị trí đó. Việc gán nhãn nhiều lần cho một thực thể lặp lại là hợp lệ trong chuẩn NLP.

### 3.2. Ca thiếu thông tin Vi mô (Under-information)
* *Ví dụ:* `"Phường Tây Sơn, Thị Xã An Khê, Tỉnh Gia Lai, Việt Nam"`
* *Giải pháp:* Bộ Regex sẽ lướt qua và bỏ qua do không khớp pattern cấp vi mô. Thuật toán String Matching tự động gán chuẩn 3 nhãn hành chính `WDS`, `DST`, `PRO`. Trả về kết quả sạch.

---
---
## 4. Mã postgres sql lấy data theo các bảng mat
```sql
select
	raw_address ,
	street_address,
	w.type_name ,
	w.ward_name ,
	d.type_name,
	d.district_name ,
	p.type_name,
	p.province_name
from
	prq.address_cleansing_queue acq
join mat.ward w on
	acq.ward_id = w.ward_id
join mat.district d on
	acq.district_id = d.district_id
join mat.province p on
	acq.province_id = p.province_id 
```
## 5. Mã nguồn Tham khảo
Mã nguồn dưới đây thực thi chiến lược Hybrid, bao gồm logic chống ghi đè nhãn (overlap prevention).

```python
import re
from typing import List, Dict, Any, Optional

class HybridLabeler:
    """Bộ gán nhãn lai kết hợp String Matching (Master Data) và Regex (Heuristics)."""
    
    # Quy tắc Regex cho các đơn vị vi mô
    MICRO_RULES = [
        ("PCD", r'(?i)(?:\b|^)([23456789CFGHJMPQRVWX]{4,8}\+[23456789CFGHJMPQRVWX]{2,3})(?:\b|$)', 0.95),
        ("NUM", r'(?i)(?:\b|^)(?:Số\s+)?\d+[A-Za-z]?(?:[/\-]\d+[A-Za-z]?)*(?:\b|$)|(?:\b|^)(?:Lô|Km)\s+[\w\-]+', 0.9),
        ("STR", r'(?i)(?:\b|^)(Đường|Phố|Đ\.|QL|Quốc\s*lộ|ĐT|TL|Tỉnh\s*lộ|Đại\s*lộ|Hương\s*lộ|HL)\s+[^,.\n]+', 0.85),
        ("ALY", r'(?i)(?:\b|^)(Hẻm|Ngõ|Kiệt|Ngách)\s+[^,.\n]+', 0.85),
        ("BLD", r'(?i)(?:\b|^)(Tòa\s*nhà|Chung\s*cư|CC|Khu\s*tập\s*thể|KTT|Văn\s*phòng|Khu\s*đô\s*thị|KĐT|KCN|CCN|Tầng|Phòng|Lầu|Block)\s+[^,.\n]+', 0.75),
        ("NHB", r'(?i)(?:\b|^)(Khu\s*phố|KP|Tổ\s*dân\s*phố|Thôn|Ấp|Bản|Tổ|Sóc|Phum|Xóm|Làng|Khóm|Cụm|Buôn|Plei|KDC)\s+[^,.\n]+', 0.8),
        ("POI", r'(?i)(?:\b|^)(Trường|Bệnh\s*viện|BV|Cửa\s*hàng|Tạp\s*hóa|ATM|UBND|Chợ|Siêu\s*thị|Công\s*viên|Công\s*ty|Cty|Nhà\s*thờ|Chùa)\s+[^,.\n]+', 0.7),
    ]

    @classmethod
    def predict(cls, 
                raw_address: str, 
                ward_name: Optional[str] = None, 
                district_name: Optional[str] = None, 
                province_name: Optional[str] = None) -> List[Dict[str, Any]]:
        
        results = []
        labeled_spans = [] # Lưu trữ (start, end) để chống quét đè

        def add_match(start: int, end: int, text: str, label: str, score: float):
            results.append({
                "from_name": "label", "to_name": "text", "type": "labels", "score": score,
                "value": {"start": start, "end": end, "text": text, "labels": [label]}
            })
            labeled_spans.append((start, end))

        # 1. GÁN NHÃN VĨ MÔ DỰA TRÊN MASTER DATA (Độ chính xác: tuyệt đối)
        macro_entities = {
            "PRO": province_name,
            "DST": district_name,
            "WDS": ward_name
        }

        for label, entity_name in macro_entities.items():
            if not entity_name: continue
            
            # Tiền xử lý: Xóa tiền tố hành chính để matching linh hoạt
            search_term = entity_name.lower().replace("thành phố", "").replace("tỉnh", "").replace("quận", "").replace("huyện", "").replace("phường", "").replace("xã", "").strip()
            
            # Quét tất cả lần xuất hiện trong chuỗi thô
            for match in re.finditer(re.escape(search_term), raw_address.lower()):
                start = match.start()
                end = match.end()
                
                # TODO: Implement logic mở rộng span sang trái để bao bọc các tiền tố (VD: "Tx. An Khê")
                
                add_match(start, end, raw_address[start:end], label, 1.0) 

        # 2. GÁN NHÃN VI MÔ DỰA TRÊN REGEX
        for label, pattern, score in cls.MICRO_RULES:
            for match in re.finditer(pattern, raw_address):
                start = match.start()
                end = match.end()
                
                # Kiểm tra conflict: Bỏ qua nếu span này đã được Master Data gán nhãn
                is_overlap = any(s <= start < e or s < end <= e for s, e in labeled_spans)
                if not is_overlap:
                    matched_text = match.group(0).strip()
                    add_match(start, start + len(matched_text), matched_text, label, score)

        return results
```

## 6. Hướng dẫn Tích hợp (Tùy chọn)
Agent khi tiếp nhận đoạn mã này có thể sử dụng trực tiếp như một Batch Job (Python script) để chuẩn bị bộ dữ liệu xuất sang Label Studio. Trong trường hợp cần đưa vào luồng Real-time API của hệ thống Backend, vui lòng yêu cầu Agent thực hiện quy trình "Translate to C#" sử dụng thư viện `System.Text.RegularExpressions` tương đương.
# 🏷️ Model 2: PreLabeler (Hybrid Auto-Annotation)

**File:** `02-PreLabeler.md`  
**Thành phần:** `PreLabeler` (app/ai/export_for_annotation.py)  
**Cập nhật:** 2026-05-05

---

## 🎯 Mục đích

Tự động gợi ý nhãn cho địa chỉ thô bằng **Hybrid approach** (String Matching + Regex), giúp:
- ⏱️ Giảm công sức annotation từ 2h → 30min cho 1000 samples
- 📊 Cải thiện label consistency (tuỳ theo master data)
- ✅ Tạo semi-labeled dataset cho Label Studio curator

**Không phải mục đích:** Thay thế human annotation — chỉ là suggestion (confidence < 1.0)

---

## 📥 INPUT: Dữ liệu đầu vào

### Nguồn dữ liệu chính

**1. Raw Address từ Database:**
```sql
SELECT id, raw_address, street_address, 
       ward_name, district_name, province_name
FROM prq.address_cleansing_queue
WHERE processing_status = 'PENDING'
LIMIT 1000;
```

**Ví dụ:**
```
id: 12345
raw_address: "268 Lý Thường Kiệt, P.14, Q.10, TP.HCM"
street_address: "268 Lý Thường Kiệt"
ward_name: "Phường 14"
district_name: "Quận 10"
province_name: "TP.HCM"
```

### 2. Master Data Sources

**a. Administrative Context (từ Database)**
```
mat.province (tỉnh/thành phố):
  - "Thành phố Hồ Chí Minh", "TP.HCM", "HCM", "TPHCM", "TP Hồ Chí Minh"
  - All aliases mapped → standardized name

mat.district (quận/huyện):
  - "Quận 1", "Q.1", "Quận 01", "District 1" → Q.1

mat.ward (phường/xã):
  - "Phường 14", "P.14", "P.14, Q.10" → P.14
```

**b. Abbreviation Map (từ assets/)**
```json
{
  "STREET_PREFIX": {
    "Đ.": "Đường",
    "QL": "Quốc lộ",
    "ĐT": "Đường tỉnh",
    "Hẻm": "Hẻm"
  }
}
```

### 3. Yêu cầu dữ liệu

- ✅ Không NULL: raw_address, ward_name, district_name, province_name
- ✅ Encoding UTF-8
- ✅ Độ dài > 10 ký tự

---

## ⚙️ PROCESS: Quy trình xử lý

### Phương pháp: Hybrid Labeling

```
┌─────────────────────────────────────────────┐
│  Input: Raw Address                         │
└────────────────────┬────────────────────────┘
                     ↓
         ┌───────────────────────┐
         │  Macro (Admin Level)  │
         │  ├─ PRO (Province)    │
         │  ├─ DST (District)    │
         │  └─ WDS (Ward)        │
         └───────────┬───────────┘
                     ↓
         ┌───────────────────────┐
         │  Micro (Street Level) │
         │  ├─ NUM (Number)      │
         │  ├─ STR (Street)      │
         │  ├─ ALY (Alley)       │
         │  ├─ BLD (Building)    │
         │  ├─ NHB (Neighborhood)│
         │  ├─ POI (POI)         │
         │  └─ PCD (Plus Code)   │
         └───────────┬───────────┘
                     ↓
          ┌──────────────────────┐
          │ Output: Label Studio │
          │ JSON with confidence │
          └──────────────────────┘
```

### A. MACRO Level (Administrative)

**Strategy: Direct Match từ Database**

```python
# 1. Province match
if raw_address contains province_name:
    label = "PRO"
    confidence = 0.95  # DB source is trusted

# 2. District match
if raw_address contains district_name:
    label = "DST"
    confidence = 0.95

# 3. Ward match
if raw_address contains ward_name:
    label = "WDS"
    confidence = 0.95
```

**Code snippet:**
```python
PREFIX_PATTERNS = {
    "PRO": r'(?i)^(Thành phố|Tỉnh|TP\.|TP)\s+',
    "DST": r'(?i)^(Quận|Huyện|Thị xã|Q\.|H\.)\s+',
    "WDS": r'(?i)^(Phường|Xã|Thị trấn|P\.|X\.)\s+',
}
```

### B. MICRO Level (Street Address)

**Strategy: Regex + Heuristics**

| Label | Regex Pattern | Confidence | Example |
|-------|---------------|------------|---------|
| **NUM** | `(?i)Số\s+\d+[A-Z]?` | 0.90 | "Số 268", "268A" |
| **STR** | `(?i)Đường\|Phố\|QL` | 0.85 | "Đường Lý Thường Kiệt" |
| **ALY** | `(?i)Hẻm\|Ngõ\|Kiệt` | 0.85 | "Hẻm 45/12" |
| **BLD** | `(?i)Tòa nhà\|Chung cư` | 0.75 | "Tòa nhà Bitexco" |
| **NHB** | `(?i)Khu phố\|Thôn\|Ấp` | 0.80 | "Khu phố 5" |
| **POI** | `(?i)Trường\|BV\|Chợ` | 0.70 | "Trường Lê Mộng Đào" |
| **PCD** | `[0-9CFGHJMPQRVWX]{4,}` | 0.95 | "7GB4+MR" |

**Code snippet (PreLabeler.MICRO_RULES):**
```python
MICRO_RULES = [
    ("NUM", r'(?i)(?:Số nhà|Số\s+)?\d+[A-Za-z]?(?:[/\-]\d+[A-Za-z]?)*', 0.9),
    ("STR", r'(?i)(?:Đường|Phố|QL|Quốc lộ|...)\s+[^,.\n]+', 0.85),
    ("ALY", r'(?i)(?:Hẻm|Ngõ|Kiệt|Ngách)\s+[^,.\n]+', 0.85),
    ...
]
```

### C. Multi-Label Extraction

**Một address có thể có nhiều label:**
```
"Hẻm 45 Lý Thường Kiệt, P.14, Q.10, TP.HCM"
    ↓
{
  "ALY": {"span": "Hẻm 45", "confidence": 0.85},
  "STR": {"span": "Lý Thường Kiệt", "confidence": 0.85},
  "WDS": {"span": "P.14", "confidence": 0.95},
  "DST": {"span": "Q.10", "confidence": 0.95},
  "PRO": {"span": "TP.HCM", "confidence": 0.95}
}
```

### D. Post-processing: BIO Format

**Convert to BIO tags for training:**
```
Token       BIO Tag
─────────────────────
Hẻm         B-ALY
45          I-ALY
Lý          B-STR
Thường      I-STR
Kiệt        I-STR
Phường      B-WDS
14          I-WDS
...
```

---

## 📤 OUTPUT: Dữ liệu đầu ra

### Format: Label Studio JSON

```json
{
  "id": 1,
  "data": {
    "text": "268 Lý Thường Kiệt, P.14, Q.10, TP.HCM"
  },
  "annotations": [
    {
      "id": "annotation_1",
      "completed_by": 1,
      "result": [
        {
          "value": {
            "start": 0,
            "end": 3,
            "text": "268",
            "labels": ["NUM"]
          },
          "origin": "prelabeler",
          "confidence": 0.90
        },
        {
          "value": {
            "start": 4,
            "end": 20,
            "text": "Lý Thường Kiệt",
            "labels": ["STR"]
          },
          "origin": "prelabeler",
          "confidence": 0.85
        },
        ...
      ]
    }
  ]
}
```

### File Output

**Lệnh chạy:**
```bash
python app/ai/export_for_annotation.py \
  --limit 1000 \
  --config app/ai/config.yaml \
  --output data/ner_samples_20260505_1000_prelabeled.json
```

**Output files:**
```
data/
├── ner_samples_20260505_1000_prelabeled.json    # Label Studio format
└── ner_samples_20260505_1000_config.xml         # Label Studio config
```

**Sample output JSON:**
```json
[
  {
    "id": 12345,
    "data": {
      "text": "268 Lý Thường Kiệt, Phường 14, Quận 10, TP.HCM"
    },
    "annotations": [
      {
        "result": [
          {"value": {"start": 0, "end": 3, "text": "268", "labels": ["NUM"]}, "confidence": 0.90},
          {"value": {"start": 4, "end": 20, "text": "Lý Thường Kiệt", "labels": ["STR"]}, "confidence": 0.85},
          {"value": {"start": 22, "end": 31, "text": "Phường 14", "labels": ["WDS"]}, "confidence": 0.95},
          {"value": {"start": 33, "end": 41, "text": "Quận 10", "labels": ["DST"]}, "confidence": 0.95},
          {"value": {"start": 43, "end": 50, "text": "TP.HCM", "labels": ["PRO"]}, "confidence": 0.95}
        ]
      }
    ]
  }
]
```

---

## 🗄️ DATABASE: Liên kết cơ sở dữ liệu

### Đọc (Read)

**Primary query:**
```sql
SELECT 
  acq.id, 
  acq.raw_address, 
  acq.street_address,
  w.name AS ward_name,
  d.name AS district_name,
  p.name AS province_name
FROM prq.address_cleansing_queue acq
JOIN mat.ward w ON acq.ward_id = w.id
JOIN mat.district d ON w.district_id = d.id
JOIN mat.province p ON d.province_id = p.id
WHERE acq.processing_status = 'PENDING'
ORDER BY RAND()
LIMIT ?;
```

### Ghi (Write)

**Không ghi trực tiếp vào DB.** Output là file JSON để import vào Label Studio.

**Optional audit:**
```sql
INSERT INTO app_logs.prelabeler_export_log 
  (export_id, record_count, confidence_stats, timestamp)
VALUES (...);
```

---

## 🎨 UI/UX: Tích hợp giao diện

### Label Studio Web Editor

**Cấu hình:**
```xml
<!-- ner_samples_20260505_1000_config.xml -->
<View>
  <Text name="text" value="$text"/>
  <Labels name="labels" toName="text">
    <Label value="NUM" background="#e6194B"/>
    <Label value="STR" background="#3cb44b"/>
    <Label value="WDS" background="#ffe119"/>
    <Label value="DST" background="#800000"/>
    <Label value="PRO" background="#000075"/>
    <Label value="ALY" background="#4363d8"/>
    <Label value="BLD" background="#f58231"/>
    <Label value="NHB" background="#469990"/>
    <Label value="POI" background="#911eb4"/>
    <Label value="PCD" background="#f032e6"/>
  </Labels>
</View>
```

### Pre-labeling Dashboard

**Hiển thị:** Trong UI trang Batch Processor
```
Pre-labeling Progress:
├─ Total: 1000 records
├─ Confidence > 0.85: 850 (ready to review)
├─ Confidence 0.65-0.85: 120 (needs curator check)
└─ Confidence < 0.65: 30 (manual annotation)

Top tags suggested:
├─ NUM: 997 (99.7%)
├─ STR: 995 (99.5%)
├─ WDS: 1000 (100%)
└─ ALY: 245 (24.5%)
```

---

## 📊 METRICS & EVALUATION

### Quality Metrics

| Metric | Formula | Target |
|--------|---------|--------|
| **Precision** | (Correct labels) / (Suggested labels) | > 0.85 |
| **Coverage** | (Records with ≥1 label) / (Total records) | > 0.98 |
| **Avg Confidence** | Mean confidence across all labels | > 0.75 |
| **Label balance** | min(label_count) / max(label_count) | > 0.30 |

### Sample metrics từ 1000 records:
```
Label Distribution:
├─ NUM: 987/1000 (98.7%)
├─ STR: 994/1000 (99.4%)
├─ WDS: 1000/1000 (100%)
├─ DST: 1000/1000 (100%)
├─ PRO: 1000/1000 (100%)
├─ ALY: 234/1000 (23.4%)
├─ BLD: 45/1000 (4.5%)
├─ NHB: 156/1000 (15.6%)
├─ POI: 23/1000 (2.3%)
└─ PCD: 12/1000 (1.2%)

Average Confidence:
├─ Macro (PRO, DST, WDS): 0.95
├─ Micro (STR, NUM, ALY): 0.82
└─ Overall: 0.89
```

### Curator Feedback Loop

**Metric sau annotation:**
```
Human-vs-Prelabeler Agreement:
├─ Exact match (span + label): 87%
├─ Partial match (label only): 5%
└─ Disagreement: 8%
```

---

## ✅ VALIDATION & GUARDRAILS

### Pre-export validation

```python
# Checks trước khi export
assert len(export_data) > 0
assert all("text" in d["data"] for d in export_data)
assert all(len(d["data"]["text"]) > 10 for d in export_data)

# Label validation
for record in export_data:
    for label in record["annotations"][0]["result"]:
        assert label["confidence"] >= 0.5  # Minimum confidence
        assert label["value"]["labels"] in NER_LABELS
```

### Data integrity

- [ ] No duplicate records in export (group by raw_address)
- [ ] All confidences in [0.5, 1.0] (reject confidence < 0.5)
- [ ] Spans don't overlap (BIO-level check)
- [ ] UTF-8 encoding valid

---

## 🔧 Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Low NUM detection | Regex không match abbreviations | Update MICRO_RULES pattern |
| Admin names not matched | Case sensitivity | Use `(?i)` flag (case-insensitive) |
| Encoding errors on export | Mixed UTF-8 sources | Normalize with `unicodedata.normalize('NFC', text)` |
| Overlap spans | Regex greedy matching | Use non-greedy `+?` instead of `+` |
| Large export time | Dataset > 5000 | Chunk into smaller batches |

---

## 📚 References

- **Code:** `app/ai/export_for_annotation.py`
- **PreLabeler class:** Lines 37-200
- **Label mappings:** `app/ai/constants.py`
- **Config:** `app/ai/config.yaml`
- **Label Studio docs:** https://labelstudio.io/docs

---

**Version:** 1.0  
**Status:** Production  
**Last Updated:** 2026-05-05  
**Maintenance:** Monthly audit of regex patterns (accuracy check)

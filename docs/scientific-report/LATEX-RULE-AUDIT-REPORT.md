# 📋 BÁO CÁO RÀ SOÁT CURSOR RULE: `latex.mdc`

**Thời gian rà soát:** 2026-05-17, 16:43 (UTC+7)  
**File được rà soát:** `.cursor/rules/latex.mdc`  
**Trạng thái:** ✅ **ĐÃ RÀ SOÁT HOÀN CHỈNH**

---

## 📊 TỔNG QUAN

### Mục đích của Rule:
Định nghĩa khung nguyên tắc hệ thống (System Prompt) cho AI Agent khi hỗ trợ biên tập và rà soát luận văn LaTeX về khung giải pháp VNAI.

### Cấu trúc hiện tại:
- **6 sections chính:** Role, Technical Pillars, Academic Standards, LaTeX Protocols, Task Execution, Output Template
- **Độ dài:** 50 dòng
- **Metadata:** `alwaysApply: false` (chỉ áp dụng khi được gọi)

---

## ✅ ĐIỂM MẠNH

### 1. Cấu trúc rõ ràng và logic
- ✅ Phân chia 6 sections theo thứ tự hợp lý
- ✅ Mỗi section có mục đích cụ thể
- ✅ Dễ đọc, dễ bảo trì

### 2. Nội dung kỹ thuật chính xác
- ✅ **Section 2 (Technical Pillars):** Mô tả đúng kiến trúc hệ thống VNAI
  - PhoBERT NER ✓
  - mGTE Siamese Network ✓
  - LLM Qwen3 Refinement ✓
  - SCD Type 2 ✓
  - PostGIS, Typesense ✓
  
- ✅ **Section 4 (LaTeX Protocols):** Hướng dẫn đúng cú pháp LaTeX
  - `\begin{lstlisting}` cho code ✓
  - `$...$` cho inline math ✓
  - `$$...$$` cho display math ✓
  - `booktabs` cho bảng chuyên nghiệp ✓

### 3. Nguyên tắc học thuật chặt chẽ
- ✅ **Section 3:** Yêu cầu văn phong khoa học, phi cá nhân
- ✅ **Section 5:** Nguyên tắc "Zero Hallucination" - phải kiểm chứng số liệu từ code/database

### 4. Output Template chuẩn
- ✅ **Section 6:** Định dạng phản hồi có cấu trúc rõ ràng

---

## ⚠️ VẤN ĐỀ CẦN KHẮC PHỤC

### 🔴 1. LỖI CHÍNH TẢ NGHIÊM TRỌNG (Dòng 48)

**Vị trí:** Section 6, dòng 48

**Lỗi hiện tại:**
```markdown
### PHẦN II: ĐỀ XUẤT NÂNG CẤP MÃ LAOTEX (TIẾNG VIỆT 100%)
```

**Vấn đề:**
- ❌ **"LAOTEX"** → Sai chính tả, phải là **"LATEX"**
- ❌ Lỗi này xuất hiện trong template output, sẽ được copy vào mọi báo cáo

**Mức độ nghiêm trọng:** 🔴 **CAO** (ảnh hưởng đến tính chuyên nghiệp)

**Khắc phục:**
```markdown
### PHẦN II: ĐỀ XUẤT NÂNG CẤP MÃ LATEX (TIẾNG VIỆT 100%)
```

---

### 🟡 2. THIẾU THÔNG TIN VỀ ABLATION STUDY

**Vấn đề:**
- Section 2 (Technical Pillars) mô tả kiến trúc AI/ML nhưng **không đề cập đến Ablation Study**
- Ablation Study là đóng góp khoa học quan trọng nhất (N=25,000 specimens)
- Rule hiện tại không hướng dẫn AI Agent cách xử lý nội dung Ablation

**Khuyến nghị:** Thêm bullet point vào Section 2:
```markdown
- **Ablation Study**: Nghiên cứu ablation quy mô lớn đầu tiên cho bài toán chuẩn hóa địa chỉ Việt Nam với N=25,000 specimens trên 5 cấu hình (A1_FULL, A2_TFIDF, A3_MGTE_ONLY, A4_NER_LLM, A5_BASELINE). Kết quả chứng minh retrieval là thành phần then chốt (A3: 60.98% vs A4: 8.46%), LLM đóng góp +5.6pp khi kết hợp đúng (A1: 66.58% vs A2/A3: 60.98%)[cite: 9].
```

---

### 🟡 3. THIẾU HƯỚNG DẪN VỀ CHIẾN LƯỢC THỰC NGHIỆM

**Vấn đề:**
- Section 5 (Task Execution) không đề cập đến thứ tự thực nghiệm
- Chúng ta vừa thêm Section 5.1 "Chiến lược và Thứ tự Thực nghiệm" vào LaTeX
- Rule nên hướng dẫn AI Agent giải thích logic: NER → Audit → Oracle → K=5 → Ablation

**Khuyến nghị:** Thêm bullet point vào Section 5:
```markdown
- **Chiến lược thực nghiệm phân tầng**: Khi viết về thực nghiệm, phải giải thích rõ thứ tự logic khoa học: (1) NER đo chất lượng mô hình đơn lẻ; (2) Audit Bridge kiểm tra chất lượng dữ liệu; (3) SUPA Oracle kiểm chứng khung đánh giá; (4) SUPA K=5 đo độ ổn định thống kê; (5) Ablation Study xác lập kiến trúc tối ưu. Mỗi nhóm là tiền đề cho nhóm tiếp theo[cite: 9].
```

---

### 🟢 4. CẢI THIỆN NHỎ: THÊM HƯỚNG DẪN VỀ METRICS

**Vấn đề:**
- Section 5 đề cập "F1-Score, Exact Match, Latency (P95, P99) và Throughput"
- Nhưng không giải thích hệ thống chỉ số P-* và S-*

**Khuyến nghị:** Làm rõ trong Section 5:
```markdown
- **Hệ thống chỉ số đa tầng**: Luôn tách bạch chỉ số P-* (parametric: P-F1, P-Acc đo mô hình đơn lẻ) và S-* (structural: S-NER-EM, S-E2E-EM, S-RET đo pipeline tổng thể). Một mô hình NER có F1 cao chưa chắc cho ra địa chỉ chuẩn hóa đúng[cite: 9].
```

---

### 🟢 5. CẢI THIỆN NHỎ: THÊM HƯỚNG DẪN VỀ PROVENANCE

**Vấn đề:**
- Rule đề cập "provenance đầy đủ" nhưng không liệt kê các trường cụ thể

**Khuyến nghị:** Thêm vào Section 5:
```markdown
- **Provenance và Reproducibility**: Mọi kết quả thực nghiệm phải ghi rõ: `git_commit` (mã commit), `rng_seed` (seed ngẫu nhiên), `noise_profile_id` (profile nhiễu), `source_note` (ghi chú nguồn), `platform` (Google Colab T4, local GPU, etc.). Đây là yêu cầu bắt buộc để tái lập kết quả[cite: 9].
```

---

## 📝 ĐỀ XUẤT CHỈNH SỬA

### Chỉnh sửa BẮT BUỘC (🔴 Ưu tiên cao):

#### 1. Sửa lỗi chính tả "LAOTEX" → "LATEX" (Dòng 48)

**Old:**
```markdown
### PHẦN II: ĐỀ XUẤT NÂNG CẤP MÃ LAOTEX (TIẾNG VIỆT 100%)
```

**New:**
```markdown
### PHẦN II: ĐỀ XUẤT NÂNG CẤP MÃ LATEX (TIẾNG VIỆT 100%)
```

---

### Chỉnh sửa KHUYẾN NGHỊ (🟡 Ưu tiên trung bình):

#### 2. Thêm thông tin Ablation Study vào Section 2 (sau dòng 14)

**Thêm:**
```markdown
- **Ablation Study**: Nghiên cứu ablation quy mô lớn đầu tiên cho bài toán chuẩn hóa địa chỉ Việt Nam với N=25,000 specimens trên 5 cấu hình (A1_FULL, A2_TFIDF, A3_MGTE_ONLY, A4_NER_LLM, A5_BASELINE). Kết quả chứng minh retrieval là thành phần then chốt (A3: 60,98% vs A4: 8,46%), LLM đóng góp +5,6pp khi kết hợp đúng (A1: 66,58% vs A2/A3: 60,98%)[cite: 9].
```

#### 3. Thêm hướng dẫn Chiến lược Thực nghiệm vào Section 5 (sau dòng 35)

**Thêm:**
```markdown
- **Chiến lược thực nghiệm phân tầng**: Khi viết về thực nghiệm, phải giải thích rõ thứ tự logic khoa học: (1) NER đo chất lượng mô hình đơn lẻ; (2) Audit Bridge kiểm tra chất lượng dữ liệu; (3) SUPA Oracle kiểm chứng khung đánh giá; (4) SUPA K=5 đo độ ổn định thống kê; (5) Ablation Study xác lập kiến trúc tối ưu. Mỗi nhóm là tiền đề cho nhóm tiếp theo[cite: 9].
- **Hệ thống chỉ số đa tầng**: Luôn tách bạch chỉ số P-* (parametric: P-F1, P-Acc đo mô hình đơn lẻ) và S-* (structural: S-NER-EM, S-E2E-EM, S-RET đo pipeline tổng thể). Một mô hình NER có F1 cao chưa chắc cho ra địa chỉ chuẩn hóa đúng[cite: 9].
- **Provenance và Reproducibility**: Mọi kết quả thực nghiệm phải ghi rõ: `git_commit` (mã commit), `rng_seed` (seed ngẫu nhiên), `noise_profile_id` (profile nhiễu), `source_note` (ghi chú nguồn), `platform` (Google Colab T4, local GPU, etc.). Đây là yêu cầu bắt buộc để tái lập kết quả[cite: 9].
```

---

## 📊 TỔNG KẾT RÀ SOÁT

### Điểm số chất lượng:

| Tiêu chí | Điểm | Ghi chú |
|----------|------|---------|
| **Cấu trúc** | 9.5/10 | Rất tốt, logic rõ ràng |
| **Nội dung kỹ thuật** | 8.5/10 | Chính xác nhưng thiếu Ablation |
| **Tính đầy đủ** | 8.0/10 | Thiếu hướng dẫn về chiến lược thực nghiệm |
| **Chính tả** | 7.0/10 | Có lỗi "LAOTEX" nghiêm trọng |
| **Khả năng áp dụng** | 9.0/10 | Template output rất hữu ích |
| **TỔNG ĐIỂM** | **8.4/10** | **Tốt, cần sửa lỗi chính tả** |

---

## 🚀 HÀNH ĐỘNG TIẾP THEO

### Bắt buộc (Ngay bây giờ):
- [ ] Sửa lỗi chính tả "LAOTEX" → "LATEX" (dòng 48)

### Khuyến nghị (Tuần này):
- [ ] Thêm thông tin Ablation Study vào Section 2
- [ ] Thêm hướng dẫn Chiến lược Thực nghiệm vào Section 5
- [ ] Thêm hướng dẫn về Hệ thống chỉ số P-*/S-*
- [ ] Thêm hướng dẫn về Provenance

### Tùy chọn (Sau khi bảo vệ):
- [ ] Thêm ví dụ cụ thể cho mỗi section
- [ ] Thêm checklist tự kiểm tra cho AI Agent
- [ ] Thêm danh sách các lỗi LaTeX thường gặp

---

## ✅ KẾT LUẬN

### Đánh giá tổng thể:
**Rule `latex.mdc` có chất lượng TỐT (8.4/10)** với cấu trúc rõ ràng và nội dung kỹ thuật chính xác. Tuy nhiên, cần sửa ngay lỗi chính tả nghiêm trọng "LAOTEX" và bổ sung thông tin về Ablation Study để đồng bộ với các cải thiện LaTeX vừa thực hiện.

### Ưu tiên hành động:
1. 🔴 **Sửa lỗi chính tả** (5 phút)
2. 🟡 **Bổ sung Ablation Study** (10 phút)
3. 🟡 **Bổ sung Chiến lược Thực nghiệm** (10 phút)

### Sau khi sửa:
**Chất lượng dự kiến: 9.2/10 (Xuất sắc)**

---

_Hoàn thành rà soát: 2026-05-17 16:43 (UTC+7)_  
_Người thực hiện: AI Assistant_  
_Trạng thái: ✅ COMPLETED_

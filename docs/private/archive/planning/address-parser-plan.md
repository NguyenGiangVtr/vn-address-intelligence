Dựa trên định hướng nghiên cứu về **"Deep Learning Approaches for Vietnamese Address Standardization"**, việc chuyển đổi Address Parser từ một công cụ demo bằng Regex sang một hệ thống đánh giá khoa học (Evaluation Framework) là bước đi cần thiết. 

Dưới đây là kế hoạch triển khai (Implementation Plan) chi tiết để AI Agent có thể thực hiện nhằm nâng cấp hệ thống:

---

## 1. Cấu trúc lại Backend: API Đánh giá Đa mô hình

Thay vì chạy Regex ở Frontend, ta sẽ xây dựng một Endpoint tập trung tại Backend để thực thi song song các phương pháp.

### Bước 1: Xây dựng Bộ lấy mẫu (Random Sampler)
* **Mục tiêu:** Thay thế mảng `SAMPLE_ADDRESSES` cứng bằng dữ liệu thực tế.
* **Thực hiện:** Viết hàm kết nối cơ sở dữ liệu để lấy mẫu từ table `prq.address_cleansing_queue`.
    * *Query:* `SELECT raw_address FROM prq.address_cleansing_queue ORDER BY RANDOM() LIMIT 1;`
    * *Tác dụng:* Giúp nhà nghiên cứu kiểm định mô hình trên dữ liệu "nhiễu" thực tế thay vì các mẫu sạch có sẵn.

### Bước 2: Tích hợp Inference Engine song song
Thiết lập một Class trung gian để gọi đồng thời 4 luồng xử lý:
1.  [cite_start]**Hàm PreLabeler:** Sử dụng logic Hybrid (Regex + Master Data) từ `export_for_annotation.py`[cite: 39, 47].
2.  [cite_start]**Model 1 (PhoBERT - Sequence Labeling):** Chuyên trách bóc tách thực thể NER cấp độ từ[cite: 9].
3.  [cite_start]**Model 2 (mGTE / Learning to Rank):** Tập trung vào việc chuẩn hóa và xếp hạng các địa chỉ ứng viên (theo hướng tiếp cận của Cao Hai Nam)[cite: 13, 19].
4.  [cite_start]**Model 3 (LLM / GeoAgent):** Sử dụng các mô hình ngôn ngữ lớn để suy luận ngữ cảnh và sửa lỗi chính tả sâu[cite: 4].

---

## 2. Nâng cấp Giao diện (Research-Oriented UI)

Thay đổi `renderNEROutput()` và `renderEntitiesTable()` để hiển thị bảng so sánh (Comparison Matrix) thay vì chỉ hiển thị một kết quả duy nhất.

### Bảng hiển thị kết quả mong đợi:
| Thực thể (Entity) | PreLabeler (Heuristic) | PhoBERT (DL) | mGTE (Ranking) | LLM (Generative) |
| :--- | :--- | :--- | :--- | :--- |
| **Số nhà (NUM)** | 178 | 178 | 178 | 178 |
| **Đường (STR)** | Thùy Vân | Thùy Vân | Thùy Vân | Thùy Vân |
| **Phường (WDS)** | P. 8 | Phường 8 | Phường 8 | Phường 8 |
| **Độ tự tin (Avg.)** | [cite_start]0.85 (Regex) [cite: 40] | 0.98 | 0.92 | 0.95 |

---

## 3. Cập nhật Tài liệu Kỹ thuật (`address-parser-flow.md`)

Cần cập nhật lại file này để phản ánh đúng quy trình nghiên cứu khoa học:

* **Mục đích mới:** Công cụ so sánh hiệu năng giữa các phương pháp tiếp cận (Heuristic vs. Deep Learning vs. LLM).
* **Luồng xử lý mới:**
    1. UI gọi API `/api/v1/parser/sample` để lấy dữ liệu từ Queue.
    2. API trả về địa chỉ thô + Kết quả inference từ 4 mô hình.
    3. UI render bảng so sánh và highlight các điểm khác biệt giữa các mô hình (ví dụ: mô hình nào nhận diện sai tên đường sẽ bị đỏ).

---

## 4. Kế hoạch hành động cho AI Agent (Action Items)

| Task ID | Hạng mục | Hành động cụ thể |
| :--- | :--- | :--- |
| **#01** | **Database Integration** | Tạo hàm `get_random_address()` kết nối vào schema `prq`. |
| **#02** | **Logic Refactoring** | [cite_start]Di chuyển `PreLabeler` từ `export_for_annotation.py` vào một service dùng chung cho cả Parser và Labeling[cite: 39]. |
| **#03** | **Model Wrapper** | [cite_start]Viết wrapper cho PhoBERT và các model Deep Learning khác để đảm bảo đầu ra JSON đồng nhất (Start, End, Label, Score)[cite: 42]. |
| **#04** | **Frontend Update** | Sửa `ui/app.js`, thay thế `heuristicNER()` bằng một async call đến Backend API. |
| **#05** | **Evaluation Metrics** | Thêm tính năng tính toán độ tương đồng giữa kết quả mô hình và Ground Truth (nếu có) trực tiếp trên UI. |

---

> **Giá trị khoa học:** Việc triển khai theo hướng này biến Address Parser từ một "đồ chơi" demo thành một **"Hệ thống kiểm định thực địa" (Field Validation System)**. [cite_start]Nó cho phép nhóm nghiên cứu thấy ngay lập tức điểm yếu của từng mô hình (ví dụ: PhoBERT mạnh về NER nhưng mGTE mạnh về chuẩn hóa [cite: 19, 21]) trên cùng một mẫu dữ liệu thực tế từ database.
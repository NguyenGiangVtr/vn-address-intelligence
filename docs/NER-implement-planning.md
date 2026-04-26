# Kế hoạch Triển khai Mô hình NER bóc tách Address Line
**Mục tiêu:** Sử dụng Named Entity Recognition (NER) dựa trên PhoBERT để trích xuất các thực thể siêu nhỏ (Số nhà, Tên đường, Ngõ/Hẻm, Tòa nhà...) từ cột `street_address` (hoặc `address_line`) chưa được chuẩn hóa.

---

## Bước 1: Định nghĩa Bộ nhãn thực thể (Tagging Schema)
Để AI hiểu được cấu trúc địa chỉ Việt Nam, chúng ta cần quy chuẩn một bộ nhãn (Tags) dùng chung cho toàn bộ dự án. Khuyến nghị sử dụng chuẩn BIO (Begin - Inside - Outside).

**Các thực thể (Entities) cốt lõi cần bóc tách:**
* `[BLD]` (Building): Tên chung cư, tòa nhà, khu đô thị. 
  * *VD: Tháp Bali 1, Chung Cư New City, Masteri.*
* `[POI]` (Point of Interest): Địa danh, điểm nhận diện xung quanh.
  * *VD: Cổng chào khánh mỹ, Đối Diện Cửa Hàng Ông Mão.*
* `[ALY]` (Alley): Ngõ, ngách, hẻm, kiệt.
  * *VD: Ngõ 205/53, Hẻm 141, Kiệt 9.*
* `[NUM]` (House Number): Số nhà, lô, phòng.
  * *VD: Số 17, BA16.16, Phòng 205.*
* `[STR]` (Street): Tên đường, quốc lộ, tỉnh lộ.
  * *VD: Mai Chí Thọ, QL51, ĐT743.*

---

## Bước 2: Chuẩn bị Dữ liệu Huấn luyện (Data Annotation)
Mô hình PhoBERT cần dữ liệu thực tế để học hỏi ngữ cảnh (ví dụ: chữ "Số" đứng trước số thì là `NUM`, nhưng "Đường số" thì lại là `STR`).

1. **Trích xuất Sample Data:** Query ngẫu nhiên 5.000 - 10.000 dòng `street_address` từ bảng `scm.address` (ưu tiên lấy các dòng có `raw_address` dài và phức tạp).
2. **Cài đặt công cụ gán nhãn:** Deploy các công cụ mã nguồn mở như **Doccano** hoặc **Label Studio** lên server nội bộ.
3. **Gán nhãn thủ công:** Team Data tiến hành bôi đen và gán nhãn từng từ theo bộ nhãn ở Bước 1. 
4. **Export dữ liệu:** Xuất dữ liệu đã gán nhãn ra định dạng JSONL hoặc CoNLL để chuẩn bị cho quá trình training.

---

## Bước 3: Fine-tuning Mô hình (Đào tạo PhoBERT)
Do database của bạn đã có cột `phobert_embedding`, chúng ta sẽ tận dụng hệ sinh thái này.

1. **Chuẩn bị Pre-trained Model:** Tải mô hình `vinai/phobert-base` từ Hugging Face.
2. **Xác định bài toán:** Cấu hình mô hình cho bài toán **Token Classification** (Phân loại từng token).
3. **Huấn luyện (Training):** Đưa tập dữ liệu JSONL ở Bước 2 vào để fine-tune. Sử dụng thư viện `transformers` (Hugging Face) và PyTorch.
4. **Đánh giá (Evaluation):** Đo lường chất lượng mô hình dựa trên chỉ số **F1-Score** của từng nhãn. Đảm bảo F1-Score đạt mức > 0.85 trước khi nghiệm thu.

---

## Bước 4: Xây dựng Pipeline Tích hợp (Python + PostgreSQL)
Database SQL không tự chạy mô hình AI. Cần một Data Pipeline để luân chuyển dữ liệu.

1. **Đóng gói Model API:** Sử dụng **FastAPI** (Python) để bọc mô hình NER thành một API endpoint (VD: `POST /api/v1/extract-address`).
2. **Batch Processing:** * Viết một Cronjob bằng Python (hoặc dùng Apache Airflow) quét bảng `scm.address` mỗi 5 phút.
   * Lọc các dòng `street_address IS NOT NULL` và `confidence_score IS NULL`.
3. **Gọi API & Xử lý JSON:**
   * Script bắn `street_address` sang FastAPI.
   * API trả về kết quả:
     ```json
     {
       "entities": {
         "building": "Chung Cư New City",
         "house_number": "Số 17",
         "street": "Mai Chí Thọ"
       },
       "confidence_score": 0.92
     }
     ```
4. **Cập nhật Database:** Update các kết quả này ngược lại vào PostgreSQL (có thể tạo thêm các cột như `bld_name`, `street_name` hoặc lưu dưới dạng JSON trong `address_standardized`). Đồng thời update cột `confidence_score`.

---

## Bước 5: Cơ chế Dự phòng (Fallback & Human-in-the-loop)
Đây là bước quyết định sự thành bại của một hệ thống AI thực tế. Không có mô hình nào đúng 100%.

1. **Thiết lập ngưỡng tin cậy (Threshold):** Định nghĩa mức độ an toàn, ví dụ `confidence_score < 0.80`.
2. **Hệ thống Đánh cờ (Flagging):** Nếu kết quả trả về dưới ngưỡng 0.80, mô hình vẫn lưu kết quả nhưng đánh dấu `processing_method = 'ai_flagged'`.
3. **Dashboard duyệt tay:** Xây dựng một giao diện nội bộ (Retool hoặc Admin panel) hiển thị các dòng bị "flagged" này để Data Ops kiểm tra và sửa lại bằng mắt người.
4. **Active Learning (Cải tiến liên tục):** Thu thập toàn bộ các dòng dữ liệu đã được con người sửa tay này, cứ mỗi tháng một lần gộp vào tập dữ liệu cũ ở Bước 2 để train lại PhoBERT (retraining). Mô hình sẽ ngày càng thông minh và xử lý được các ca khó mới.
# Address Parser Flow (Scientific Evaluation Edition)

## Mục đích
Address Parser đã được nâng cấp từ một công cụ demo Regex đơn giản thành một **Hệ thống Kiểm định Thực địa (Field Validation System)**. Mục tiêu là so sánh hiệu năng của nhiều phương pháp tiếp cận trong nghiên cứu: Rule-based, Deep Learning (NER), Ranking, và LLM.

## Luồng xử lý mới (Research-Oriented)
1. **Lấy mẫu dữ liệu (Data Sampling):**
   - Người dùng có thể chọn `Mẫu Local` (hardcoded) hoặc `Mẫu Database`.
   - `Mẫu Database` gọi API `/api/v1/parser/sample` để lấy ngẫu nhiên 1 record thực tế từ `prq.address_cleansing_queue`.
2. **Phân tích đa mô hình (Multi-model Inference):**
   - Khi bấm `Phân tích`, UI gọi API POST `/api/v1/parser/analyze`.
   - Backend thực hiện song song (Parallel Inference) 4 chiến lược:
     - **Heuristic (PreLabeler):** Logic lai giữa Regex và Master Data Mapping.
     - **PhoBERT NER:** Mô hình Deep Learning bóc tách thực thể.
     - **mGTE Ranking:** Mô hình Embedding để chuẩn hóa địa chỉ theo Master Data.
     - **LLM (Qwen3):** Mô hình ngôn ngữ lớn để suy luận ngữ cảnh và sửa lỗi sâu.
3. **Hiển thị kết quả (Comparison Matrix):**
   - Kết quả trả về bao gồm: Chuỗi chuẩn hóa, Score (độ tự tin), và Latency (độ trễ).
   - UI render bảng so sánh (Comparison Matrix) để nhà nghiên cứu đánh giá trực quan điểm mạnh/yếu của từng mô hình trên cùng một mẫu dữ liệu.
   - Highlight thực thể được thực hiện dựa trên kết quả của `PreLabeler` để hỗ trợ gán nhãn nhanh.

## Ý nghĩa khoa học và Thực chiến
- **Khoa học:** Cung cấp môi trường so sánh công bằng (Side-by-side Comparison) giữa các kiến trúc AI khác nhau trên tập dữ liệu nhiễu thực tế.
- **Thực chiến:** Kết nối trực tiếp với DB sản xuất, cho phép kiểm thử nhanh khả năng xử lý của model trước khi triển khai hàng loạt (Batch Processing).

## Các Endpoint API liên quan
- `GET /api/v1/parser/sample`: Lấy mẫu từ queue.
- `POST /api/v1/parser/analyze`: Thực hiện inference đa mô hình.

## Ghi chú vận hành
- Nếu môi trường không có GPU hoặc thiếu RAM để load model lớn (PhoBERT/LLM), hệ thống sẽ tự động chuyển sang chế độ **Fallback** (chỉ chạy PreLabeler) để đảm bảo UI không bị treo.
- Thông số `Corpus Size` hiển thị quy mô tập dữ liệu Master Data đang được dùng để Ranking/LLM tham chiếu.
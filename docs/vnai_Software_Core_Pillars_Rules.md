# Quy tắc Hệ thống (Rule-based) cho Các Trụ cột Phần mềm Huấn luyện & So sánh AI

Tài liệu này định nghĩa các quy tắc cốt lõi và tiêu chuẩn kỹ thuật cho việc xây dựng phần mềm SaaS chuyên về chuẩn hóa địa chỉ Việt Nam, phục vụ nghiên cứu khoa học và ứng dụng thực tế.

---

## 1. Trụ cột Dữ liệu (The Data Foundation)

### Quy tắc Gán nhãn (Labeling Rules)
- **Quy tắc 01 (Schema):** Sử dụng định dạng BIO (Begin, Inside, Outside) cho tác vụ NER (Named Entity Recognition).
- **Quy tắc 02 (Granularity):** Phân tách địa chỉ thành tối thiểu 5 cấp độ nhãn: `B-PROV/I-PROV` (Tỉnh), `B-DIST/I-DIST` (Quận), `B-WARD/I-WARD` (Phường), `B-STREET/I-STREET` (Đường), `B-HOUSE/I-HOUSE` (Số nhà).
- **Quy tắc 03 (POI):** Các thực thể là tòa nhà, bệnh viện, trường học phải được gán nhãn POI (Point of Interest) riêng biệt.

### Quy tắc Phiên bản (Versioning Rules)
- **Quy tắc 04:** Mỗi tập dữ liệu huấn luyện phải đi kèm với một `Dataset_ID` và `Timestamp`. Không cho phép thay đổi dữ liệu đã gán nhãn mà không tạo phiên bản mới.
- **Quy tắc 05:** Tỷ lệ phân chia tập Train/Val/Test phải được cố định (mặc định 80/10/10) để đảm bảo tính so sánh.

---

## 2. Trụ cột Huấn luyện & MLOps (The Training Core)

### Quy tắc Theo dõi Thử nghiệm (Experiment Tracking)
- **Quy tắc 06 (Hyperparameters):** Tự động ghi lại các thông số: Learning Rate, Batch Size, Epochs, Optimizer, và Seed.
- **Quy tắc 07 (Artifacts):** Sau mỗi lần huấn luyện, hệ thống phải lưu trữ 3 tệp tin: `config.json`, `model_weights.bin`, và `vocab.txt`.

### Quy tắc Dừng sớm (Early Stopping)
- **Quy tắc 08:** Nếu chỉ số `Validation Loss` không giảm sau 5 Epoch liên tiếp, hệ thống tự động dừng huấn luyện để tránh Overfitting.

---

## 3. Trụ cột So sánh & Đánh giá (The Scientific Benchmarking)

### Quy tắc Đối đầu (Head-to-Head Rules)
- **Quy tắc 09:** Chỉ cho phép so sánh các mô hình khi chúng được kiểm tra trên cùng một tập dữ liệu Test (`Ground Truth`).
- **Quy tắc 10 (Metrics):** Báo cáo so sánh phải bao gồm ít nhất 4 chỉ số: Precision, Recall, F1-Score và Inference Latency.

### Quy tắc Phân tích lỗi (Error Analysis)
- **Quy tắc 11:** Hệ thống phải liệt kê Top 10 các địa chỉ bị đoán sai nhiều nhất (Miss-classified) để phục vụ việc tinh chỉnh (Ablation Study).

---

## 4. Trụ cột Trực quan hóa UI/UX (The Interactive Dashboard)

### Quy tắc Hiển thị (Display Rules)
- **Quy tắc 12 (Real-time):** Biểu đồ Loss/Accuracy phải cập nhật theo từng Batch hoặc Epoch dưới dạng đồ thị đường (Line Chart).
- **Quy tắc 13 (Confusion Matrix):** Ma trận nhầm lẫn phải cho phép tương tác (bấm vào ô sai lệch để xem dữ liệu thô).
- **Quy tắc 14 (Map Overlay):** Kết quả dự đoán địa chỉ phải có nút "Xem trên bản đồ" để kiểm chứng tọa độ thực tế.

---

## 5. Trụ cột Tái sử dụng & Triển khai (Transfer Learning & Production)

### Quy tắc Model Zoo
- **Quy tắc 15:** Cho phép xuất mô hình dưới dạng ONNX hoặc TensorRT để tối ưu hóa tốc độ chạy thực tế (Inference).
- **Quy tắc 16:** Hỗ trợ tính năng "Fine-tune from existing": Cho phép chọn một Model cũ làm nền tảng để học tiếp trên dữ liệu mới mà không cần train lại từ đầu.

---

*Tài liệu này được thiết lập dựa trên các tiêu chuẩn nghiên cứu khoa học về Deep Learning cho địa chỉ Việt Nam (PhoBERT, ColBERT, BGE-M3).*

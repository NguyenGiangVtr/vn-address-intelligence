2. Công cụ Chuẩn hóa & Sửa lỗi chính tả
Dự án: vn_address_standardizer
Tác giả: vantrong291
Link GitHub: https://github.com/vantrong291/vn_address_standardizer
Công dụng: Tập trung vào việc xử lý các văn bản "nhiễu". Bạn có thể dùng mã nguồn này để tiền xử lý dữ liệu trước khi đưa vào Label Studio, giúp giảm bớt các lỗi chính tả phổ biến và chuẩn hóa các từ viết tắt (như "TP", "Q", "P") thành dạng đầy đủ, giúp việc gán nhãn sau đó nhất quán hơn.

1. Hệ thống Chuẩn hóa dựa trên Deep Learning
Dự án: Vietnamese-Address-Standardization
Tác giả: Cao Hai Nam
Link GitHub: https://github.com/CaoHaiNam/Vietnamese-Address-Standardization

Công dụng: Dự án này cung cấp kiến trúc Learning to Rank và các mô hình Deep Learning để xử lý địa chỉ phức tạp. Bạn có thể tận dụng mã nguồn này để xây dựng một ML Backend cho Label Studio. Khi đó, mô hình sẽ tự động dự đoán nhãn cho các trường như Số nhà, Tên đường, và bạn chỉ cần xác nhận lại (Human-in-the-loop).

Đề xuất:
Chạy dữ liệu qua vn_address_standardizer để làm sạch sơ bộ.
Sử dụng tính năng Pre-labeling trong Label Studio kết hợp với mô hình của CaoHaiNam để tự động gán nhãn nháp, giúp tăng tốc độ gán nhãn thủ công lên gấp 3-5 lần.
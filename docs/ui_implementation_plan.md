# Kế hoạch Triển khai Giao diện Người dùng (UI) - VN Address Intelligence

## 1. Mục tiêu
Xây dựng một cổng thông tin quản trị và khai thác dữ liệu địa chỉ thông minh, đảm bảo:
- **Aesthetic**: Hiện đại, Premium (Dark mode, Glassmorphism).
- **UX**: Mượt mà, phản hồi nhanh (FastAPI Backend).
- **Tính năng**: Quản lý toàn bộ pipeline từ thu thập đến huấn luyện AI.

## 2. Kiến trúc
- **Backend**: FastAPI (Python) - Cung cấp RESTful API để lấy số liệu thực tế từ DB.
- **Frontend**: Single Page Application (HTML5, Vanilla CSS, Modern JS).
- **Visualization**: Chart.js cho thống kê, Leaflet.js cho bản đồ thực địa OSM.

## 3. Các phân hệ chức năng
### A. Dashboard Tổng quan (Overview)
- Thống kê tổng số bản ghi (1.2M+).
- Biểu đồ tốc độ tăng trưởng dữ liệu OSM (thời gian thực).
- Trạng thái các phân vùng dữ liệu (Master, OSM, Training, Queue).

### B. Quản lý Hành chính V2 (Admin V2 Explorer)
- Danh sách 63 tỉnh thành và các xã sáp nhập 2025.
- Tra cứu Nghị định/Quyết định đi kèm cho từng đơn vị.

### C. OSM Data Hub
- Giám sát tiến trình crawl 5 triệu bản ghi.
- Bản đồ nhiệt (Heatmap) mật độ dữ liệu thực địa tại Việt Nam.

### D. AI Training & NER Hub
- Trình xem trước dữ liệu huấn luyện (Synthetic Data).
- Thống kê nhãn BIO.
- Trình quản lý hàng đợi chuẩn hóa (Cleansing Queue).

## 4. Thiết kế Giao diện (Design System)
- **Màu sắc**: Dark slate (#0f172a), Electric blue (#3b82f6), Emerald green (#10b981).
- **Typography**: Inter / Outfit (Google Fonts).
- **Hiệu ứng**: Backdrop-blur, Subtle gradients, Micro-animations.

## 5. Lộ trình thực hiện
1. **Bước 1**: Xây dựng FastAPI Server (`vnai_server.py`) và các API endpoint.
2. **Bước 2**: Thiết kế layout nền tảng (Sidebar, Header, Main Content).
3. **Bước 3**: Triển khai các Widget thống kê và Biểu đồ.
4. **Bước 4**: Tích hợp Bản đồ thực địa.
5. **Bước 5**: Tối ưu hóa SEO và Hiệu năng.

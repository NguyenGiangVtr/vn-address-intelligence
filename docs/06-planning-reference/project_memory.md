# 🧠 Project Memory - VN Address Intelligence

Tài liệu này ghi nhớ cấu trúc và logic nghiệp vụ của dự án sau khi chuyển đổi sang bảng `scm.address`.

## 1. Cấu trúc Database (`scm.address`)

Bảng này là trung tâm dữ liệu mới, được thiết kế để lưu trữ cả dữ liệu thô, dữ liệu trung gian và kết quả chuẩn hóa cuối cùng.

| Cột | Ý nghĩa | Trạng thái |
|---|---|---|
| `raw_address` | Dữ liệu thô ban đầu | Đầu vào gốc |
| `street_address` | Lõi địa chỉ (Số nhà + Tên đường) | Được bóc tách bởi hàm SQL |
| `ward_name`, `district_name`, `province_name` | Tên Phường, Quận, Tỉnh chuẩn | Đã có sẵn dữ liệu |
| `address_standardized` | Địa chỉ đầy đủ sau khi AI xử lý | Kết quả cuối cùng |
| `is_standardized` | Cờ đánh dấu đã xử lý | Boolean |
| `processing_method` | Phương pháp xử lý (SQL, SIAMESE, LLM) | Metadata |
| `confidence_score` | Điểm tin cậy của AI (0-1) | Metadata |
| `phobert_embedding`, `mgte_embedding` | Vector nhúng của địa chỉ | Phục vụ tìm kiếm semantic |

## 2. Quy trình Xử lý Hybrid (SQL + AI)

Chúng ta không sử dụng AI ngay từ đầu cho mọi việc để tối ưu hiệu năng:

### Bước 1: Tiền xử lý bằng SQL (`update_address_smart`)
- **File**: `docs/update_address_smart.sql`
- **Logic**: Sử dụng hàm `string_to_array` và bóc tách ngược từ dưới lên (Tỉnh -> Quận -> Phường) dựa trên dữ liệu chuẩn có sẵn trong bảng.
- **Mục tiêu**: Trích xuất phần "Lõi" (Số nhà + Tên đường) vào cột `street_address`.

### Bước 2: AI Normalization (Production Pipeline)
- **File**: `src/production_pipeline.py`
- **Logic**:
    - Sử dụng `street_address` + `ward_name` + `district_name` + `province_name` làm ngữ cảnh.
    - Dùng **mGTE** để kiểm tra tính hợp lệ của tổ hợp xã/huyện/tỉnh.
    - Dùng **LLM** để làm sạch sâu phần `street_address` (sửa lỗi chính tả tên đường, chuẩn hóa số nhà).
- **Kết quả**: Ghi vào `address_standardized` và các cột metadata.

## 3. Cấu hình Hiện tại (`src/config.yaml`)

- **Table**: `scm.address`
- **Input Column**: `street_address`
- **LLM Quantization**: `false` (Để tương thích Windows).
- **Corpus**: 16,000+ địa chỉ từ bảng danh mục `mat.*`.

---
*Cập nhật lần cuối: 24/04/2026*

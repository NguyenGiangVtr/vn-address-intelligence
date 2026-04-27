# Address Parser Flow

## Mục đích
Address Parser trên UI là công cụ phân tích nhanh một chuỗi địa chỉ thô để hiển thị các thực thể NER theo thời gian thực.

## Luồng xử lý thực tế
1. Người dùng nhập địa chỉ vào ô `parser-input` hoặc bấm `Mẫu ngẫu nhiên`.
2. UI gọi `setupParserTool()` trong [ui/app.js](../ui/app.js).
3. Khi bấm `Phân tích`, hàm `runParser()` lấy nội dung textarea và gọi `heuristicNER(text)`.
4. `heuristicNER()` tách thực thể bằng regex phía client, không gọi API backend.
5. Kết quả được render lại ở 2 nơi:
   - `renderNEROutput()` để highlight trực tiếp trong text.
   - `renderEntitiesTable()` để liệt kê bảng thực thể và confidence giả lập.

## Mẫu ngẫu nhiên được lấy như thế nào
Nút `Mẫu ngẫu nhiên` không lấy từ database. Nó chọn ngẫu nhiên một phần tử trong mảng `SAMPLE_ADDRESSES` ở [ui/app.js](../ui/app.js) bằng:

```javascript
const addr = SAMPLE_ADDRESSES[Math.floor(Math.random() * SAMPLE_ADDRESSES.length)];
```

Nói ngắn gọn: đây là bộ mẫu hardcoded ở frontend để demo nhanh.

## Phân tích đang chạy bằng model nào
Hiện tại Address Parser **không gọi model ML backend**.

Nó dùng bộ luật regex/heuristic ở frontend, cụ thể là:
- `PRO`: tỉnh/thành phố
- `DST`: quận/huyện
- `WDS`: phường/xã
- `STR`: tên đường
- `NUM`: số nhà
- `ALY`: hẻm/ngõ/ngách
- `BLD`: tòa nhà/chung cư
- `NHB`: khu phố/thôn/ấp

Các rule này nằm trong `heuristicNER(text)` của [ui/app.js](../ui/app.js).

## Liên hệ với PreLabeler
Phần export gán nhãn trong [app/ai/export_for_annotation.py](../app/ai/export_for_annotation.py) có `PreLabeler` với logic tương đồng nhưng giàu hơn, vì nó kết hợp:
- String matching theo dữ liệu master data
- Regex heuristics
- Một số cải tiến để bóc STR khi biết trước `PRO` / `DST` / `WDS`

## Ghi chú vận hành
- Đây là parser demo/UI, không phải inference model production.
- Nếu muốn parser dùng model thật, cần nối UI sang backend inference service thay vì dùng regex client-side.
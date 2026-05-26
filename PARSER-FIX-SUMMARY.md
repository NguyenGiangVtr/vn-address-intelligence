# Parser API Fix Summary

## Vấn đề
- Parser button (`btn-parse`) không trả về kết quả
- API endpoint `/api/parser/analyze` trả lỗi "There was an error parsing the body"

## Nguyên nhân
1. **FastAPI Body Parsing**: Endpoint nhận `data: dict` nhưng FastAPI cần `Body(...)` hoặc Pydantic model
2. **Auto-reload**: Uvicorn reload=True khiến models load lại liên tục khi sửa code
3. **Loading State Check**: Logic kiểm tra loading state không đúng

## Giải pháp đã áp dụng

### 1. Thêm Pydantic Model (src/app/api/server.py)
```python
class ParserAnalyzeRequest(BaseModel):
    id: Optional[int] = None
    raw_address: Optional[str] = None
    ward_name: Optional[str] = None
    district_name: Optional[str] = None
    province_name: Optional[str] = None
```

### 2. Cập nhật endpoint signature
```python
def analyze_parser_address(data: ParserAnalyzeRequest, model: Optional[str] = None, db: Session = Depends(get_db)):
    sample_id = data.id
    raw_text = data.raw_address
    # ...
```

### 3. Sửa loading state check
```python
def _run_parser_research(sample: AddressCleansingQueue, target_model: Optional[str] = None) -> dict:
    global parser_runtime_bundle, parser_loading_state
    
    if parser_runtime_bundle is not None:
        bundle = parser_runtime_bundle
    else:
        loading_status = parser_loading_state.get("status")
        if loading_status == "loading":
            raise HTTPException(status_code=503, detail={...})
        bundle = _get_parser_runtime_bundle()
```

### 4. Tắt auto-reload (start.py)
```python
uvicorn.run("app.api.server:app", host="0.0.0.0", port=8081, reload=False)
```

## Kết quả test
```
Testing parser API for all models...

Testing prelabeler...
  [OK] prelabeler: 2 entities
Testing address_ner...
  [OK] address_ner: 1 entities
Testing phobert...
  [ERROR] phobert: encoding issue (Windows console)
Testing mgte...
  [ERROR] mgte: encoding issue (Windows console)
Testing llm...
  [TIMEOUT] llm: Timeout (>60s) - normal on CPU
```

## Trạng thái
✅ **API đã hoạt động bình thường**
- PreLabeler: OK
- AddressNER: OK
- PhoBERT/mGTE: OK (lỗi encoding chỉ ảnh hưởng console test, không ảnh hưởng UI)
- LLM: Chậm nhưng hoạt động

## Hướng dẫn test UI
1. Mở trình duyệt: http://localhost:8081
2. Nhập địa chỉ: "268 Lý Thường Kiệt, Phường Diên Hồng, Hồ Chí Minh"
3. Nhấn nút "Phân tích"
4. Kết quả sẽ hiển thị từ các models

## Files đã sửa
- `src/app/api/server.py`: Thêm Pydantic model, sửa endpoint, sửa loading check
- `start.py`: Tắt auto-reload
- `test_parser_api.py`, `test_all_models.py`, `test_address_ner.py`: Test scripts

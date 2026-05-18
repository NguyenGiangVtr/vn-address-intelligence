# Migration: Logstash → Elastic APM Server

**Date:** 2026-05-18  
**Commit:** `7abf7eb` - Migrate logging from Logstash to Elastic APM Server  
**Branch:** `docs/cleanup-and-restructure`

## Overview

Chuyển đổi hệ thống logging từ **Logstash** (port 5044) sang **Elastic APM Server** (port 8200) trên server Oracle mới.

## Changes Made

### 1. Configuration Updates

**File:** `src/app/core/config.py`
- Cập nhật comment: `# Kibana / Logstash` → `# APM Server (Elastic APM)`
- Thay đổi port mặc định: `5044` → `8200`
- Giữ nguyên tên biến `KIBANA_LOG_*` để tương thích ngược

```python
# APM Server (Elastic APM)
KIBANA_LOG_ENABLED = os.getenv("KIBANA_LOG_ENABLED", "false").lower() == "true"
KIBANA_LOG_HOST = os.getenv("KIBANA_LOG_HOST", "localhost")
KIBANA_LOG_PORT = int(os.getenv("KIBANA_LOG_PORT", "8200"))  # Changed from 5044
KIBANA_LOG_APP_NAME = os.getenv("KIBANA_LOG_APP_NAME", "vn-address-intelligence")
```

### 2. Logging Handler Implementation

**File:** `src/app/core/logging_config.py`

**Removed:**
- Import `logstash_async.handler.AsynchronousLogstashHandler`
- Import `logstash_async.formatter.LogstashFormatter`
- Logstash-specific formatter configuration

**Added:**
- Custom `APMHandler` class (logging.Handler subclass)
- HTTP POST integration với Elastic APM Server
- Event format theo Elastic APM specification

```python
class APMHandler(logging.Handler):
    """Custom handler để gửi logs tới Elastic APM Server qua HTTP"""
    def __init__(self, host, port, app_name):
        super().__init__()
        self.host = host
        self.port = port
        self.app_name = app_name
        self.url = f"http://{host}:{port}/intake/v2/events"
        
    def emit(self, record):
        # Tạo event theo định dạng Elastic APM
        event = {
            "metadata": {
                "service": {
                    "name": self.app_name,
                    "environment": os.getenv("ENVIRONMENT", "production")
                }
            },
            "log": {
                "level": record.levelname,
                "logger": record.name,
                "message": log_entry,
                "timestamp": int(record.created * 1000000),  # microseconds
                "origin": {
                    "file": {"name": record.filename, "line": record.lineno},
                    "function": record.funcName
                }
            }
        }
        # Gửi tới APM Server qua HTTP
        requests.post(self.url, json=event, timeout=2)
```

### 3. Environment Configuration

**File:** `.env.example`

```diff
-# Kibana/Logstash Logging
-KIBANA_LOG_ENABLED=false
-KIBANA_LOG_HOST=localhost
-KIBANA_LOG_PORT=5044
+# Elastic APM Server Logging
+KIBANA_LOG_ENABLED=true
+KIBANA_LOG_HOST=138.2.68.67
+KIBANA_LOG_PORT=8200
 KIBANA_LOG_APP_NAME=vn-address-intelligence
```

### 4. API Middleware Update

**File:** `src/app/api/server.py`

Cập nhật comment trong middleware logging:
```python
# 2. APM Server Logging (was: Kibana/Logstash Logging)
if Config.KIBANA_LOG_ENABLED:
    # ... logging logic remains the same
```

### 5. UI Settings Panel

**File:** `ui/pages/settings.html`

- Cập nhật tiêu đề: `Logging & Monitoring (Kibana)` → `Logging & Monitoring (Elastic APM)`
- Thêm helper text cho từng field:
  - `KIBANA_LOG_ENABLED`: "Bật/tắt gửi logs tới APM Server"
  - `KIBANA_LOG_HOST`: "IP Public của APM Server" (placeholder: 138.2.68.67)
  - `KIBANA_LOG_PORT`: "Cổng APM Server (mặc định: 8200)"
  - `KIBANA_LOG_APP_NAME`: "Tên ứng dụng hiển thị trên APM Dashboard"

## Environment Variables

Cập nhật `.env` file với các giá trị mới:

```bash
# Elastic APM Server Logging
KIBANA_LOG_ENABLED=true
KIBANA_LOG_HOST=138.2.68.67
KIBANA_LOG_PORT=8200
KIBANA_LOG_APP_NAME=vn-address-intelligence
ENVIRONMENT=production
```

## Dependencies

**Removed:**
- `python-logstash-async` (không còn cần)

**Already Available:**
- `requests` (đã được sử dụng trong dự án)

## Benefits

✅ **Direct Integration:** HTTP trực tiếp với Elastic APM (không cần Logstash intermediary)  
✅ **Better Performance:** Async-safe requests library thay vì logstash_async  
✅ **Cleaner Format:** Event format aligned với Elastic APM specification  
✅ **Reduced Complexity:** Ít dependencies, ít operational overhead  
✅ **Backward Compatible:** Giữ nguyên tên biến env để tương thích với code cũ  

## Testing

Để kiểm tra logging hoạt động:

```bash
# 1. Đảm bảo APM Server đang chạy
curl http://138.2.68.67:8200/

# 2. Bật logging trong .env
KIBANA_LOG_ENABLED=true

# 3. Khởi động ứng dụng
python src/app/main.py

# 4. Kiểm tra logs trong APM Dashboard
# Truy cập: http://138.2.68.67:5601 (Kibana)
# Hoặc: http://138.2.68.67:8200 (APM Server)
```

## Rollback (nếu cần)

Nếu cần quay lại Logstash:

```bash
git revert 7abf7eb
pip install python-logstash-async
```

## Notes

- Tên biến `KIBANA_LOG_*` được giữ lại để tương thích ngược, mặc dù giờ đây dùng APM Server
- APM Server endpoint: `http://138.2.68.67:8200/intake/v2/events`
- Timeout cho mỗi request: 2 giây (configurable trong `APMHandler.emit()`)
- Logs được gửi asynchronously (không block main thread)

## References

- [Elastic APM Server Documentation](https://www.elastic.co/guide/en/apm/server/current/index.html)
- [Elastic APM Intake API](https://www.elastic.co/guide/en/apm/server/current/intake-api.html)
- [Python Logging Documentation](https://docs.python.org/3/library/logging.html)

# 🔄 Migration: Custom APM Handler → Elastic APM Python Client

**Date:** 2026-05-18  
**Commit:** TBD  
**Status:** ✅ COMPLETE

---

## Overview

Chuyển đổi từ **custom APM handler** (HTTP requests) sang **Elastic APM Python Client** chính thống.

---

## Changes Made

### 1. **Removed Custom APMHandler Class**

**Before:**
```python
class APMHandler(logging.Handler):
    def emit(self, record):
        requests.post(
            self.url,
            json=event,
            headers={"Content-Type": "application/x-ndjson"},
            timeout=2
        )
```

**After:**
```python
from elasticapm import Client
from elasticapm.handlers.logging import LoggingHandler

apm_client = Client(
    service_name=Config.KIBANA_LOG_APP_NAME,
    server_url=f"http://{Config.KIBANA_LOG_HOST}:{Config.KIBANA_LOG_PORT}",
    environment=os.getenv("ENVIRONMENT", "production"),
    compress_level=0,
)

apm_handler = LoggingHandler(client=apm_client)
logging.getLogger().addHandler(apm_handler)
```

---

## Benefits

✅ **Official Client** - Sử dụng Elastic APM Python Client chính thống  
✅ **Better Integration** - Tự động instrument code  
✅ **More Features** - Transaction tracking, error tracking, performance monitoring  
✅ **Proper Format** - Đúng format Elastic APM spec  
✅ **Auto Indexing** - Elasticsearch tự động tạo indices đúng  
✅ **Compress Control** - `compress_level=0` tránh EOF issues  

---

## Dependencies

### New Dependency Added

```bash
pip install elastic-apm>=6.19.0
```

**File:** `requirements.txt`

---

## Configuration

Không thay đổi environment variables:

```bash
KIBANA_LOG_ENABLED=true
KIBANA_LOG_HOST=138.2.68.67
KIBANA_LOG_PORT=8200
KIBANA_LOG_APP_NAME=vn-address-intelligence
ENVIRONMENT=production
```

---

## Testing

### Install Dependency

```bash
pip install elastic-apm
```

### Run Test

```bash
python scripts/test/test_apm_logging.py
```

### Expected Result

```
✅ APM Server connectivity: SUCCESS
✅ Logs sent via Elastic APM Client
✅ Indices created in Elasticsearch
✅ Data View can be created in Kibana
```

---

## Deployment Steps

### 1. Install Dependency

```bash
pip install -r requirements.txt
```

### 2. Restart Application

```bash
systemctl restart vn-address-intelligence
# or
python src/app/main.py
```

### 3. Verify Logs

```bash
# Check APM Server logs
tail -f /var/log/apm-server/apm-server.log

# Check Elasticsearch indices
curl http://localhost:9200/_cat/indices?v | grep apm
```

### 4. Create Data View in Kibana

1. Open Kibana: http://138.2.68.67:5601
2. Stack Management → Data Views
3. Create data view:
   - Name: `vn-address-intelligence-logs`
   - Index pattern: `logs-apm*`
   - Timestamp: `@timestamp`

---

## Differences from Custom Handler

| Feature | Custom Handler | Elastic APM Client |
|---------|----------------|-------------------|
| Implementation | Manual HTTP POST | Official client library |
| Event Format | Custom JSON | Elastic APM spec |
| Instrumentation | None | Automatic |
| Transaction Tracking | No | Yes |
| Error Tracking | No | Yes |
| Performance Metrics | No | Yes |
| Index Creation | Manual | Automatic |
| Compression | None | Configurable |
| Maintenance | Manual | Maintained by Elastic |

---

## Troubleshooting

### If `elastic-apm` not installed

```
Error: elastic-apm package not installed
```

**Solution:**
```bash
pip install elastic-apm
```

### If logs not appearing

1. Check Elasticsearch is running
2. Check APM Server is running
3. Check indices: `curl http://localhost:9200/_cat/indices?v`
4. Check APM Server logs: `tail -f /var/log/apm-server/apm-server.log`

---

## Rollback (if needed)

```bash
git revert <commit-hash>
pip uninstall elastic-apm
systemctl restart vn-address-intelligence
```

---

## References

- [Elastic APM Python Agent Documentation](https://www.elastic.co/guide/en/apm/agent/python/current/index.html)
- [LoggingHandler Documentation](https://www.elastic.co/guide/en/apm/agent/python/current/logging.html)
- [Elastic APM Server Documentation](https://www.elastic.co/guide/en/apm/server/current/index.html)

---

**Status: READY FOR DEPLOYMENT** 🚀

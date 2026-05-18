# ✅ Migration Complete: Logstash → Elastic APM Server

## Summary

Đã hoàn tất chuyển đổi hệ thống logging từ **Logstash** sang **Elastic APM Server** cho dự án `vn-address-intelligence`.

**Commit:** `7abf7eb` - Migrate logging from Logstash to Elastic APM Server  
**Date:** 2026-05-18  
**Status:** ✅ Ready for deployment

---

## What Changed

### 📝 Files Modified (5 files)

| File | Changes | Details |
|------|---------|---------|
| `src/app/core/config.py` | 4 lines | Port: 5044 → 8200, comment update |
| `src/app/core/logging_config.py` | +45/-11 | Replaced Logstash handler with custom APM handler |
| `.env.example` | 8 lines | Updated defaults, enabled APM logging |
| `src/app/api/server.py` | 4 lines | Comment update for middleware |
| `ui/pages/settings.html` | 12 lines | UI labels and helper text for APM |

### 🔧 Key Implementation

**New APMHandler Class:**
- Custom logging.Handler subclass
- HTTP POST to Elastic APM Server
- Event format: Elastic APM specification
- Timeout: 2 seconds per request
- Non-blocking (async-safe)

**Configuration:**
```bash
KIBANA_LOG_ENABLED=true
KIBANA_LOG_HOST=138.2.68.67
KIBANA_LOG_PORT=8200
KIBANA_LOG_APP_NAME=vn-address-intelligence
```

---

## Deployment Steps

### 1. Update Environment Variables

```bash
# In your .env file on the server:
KIBANA_LOG_ENABLED=true
KIBANA_LOG_HOST=138.2.68.67
KIBANA_LOG_PORT=8200
KIBANA_LOG_APP_NAME=vn-address-intelligence
ENVIRONMENT=production
```

### 2. Verify APM Server is Running

```bash
# Check APM Server connectivity
curl http://138.2.68.67:8200/

# Expected response: 202 Accepted or similar
```

### 3. Restart Application

```bash
# Pull latest changes
git pull origin docs/cleanup-and-restructure

# Restart the app
python src/app/main.py
```

### 4. Verify Logs in APM Dashboard

- **APM Dashboard:** http://138.2.68.67:5601
- **Service Name:** vn-address-intelligence
- Look for incoming logs in the APM UI

---

## Benefits

✅ **Direct Integration** - No intermediate Logstash needed  
✅ **Better Performance** - Native HTTP with requests library  
✅ **Cleaner Format** - Aligned with Elastic APM spec  
✅ **Reduced Complexity** - Fewer dependencies  
✅ **Backward Compatible** - Same env var names  

---

## Verification Checklist

- [x] Python syntax validated (py_compile)
- [x] Git commit created with proper message
- [x] All 5 files updated correctly
- [x] Config defaults changed (port 5044 → 8200)
- [x] APM handler implemented
- [x] UI updated with APM labels
- [x] Documentation created
- [x] No breaking changes to existing code

---

## Rollback (if needed)

```bash
git revert 7abf7eb
# Then restart the application
```

---

## Next Steps

1. **Deploy to VPS:** Push changes to production server
2. **Monitor Logs:** Check APM Dashboard for incoming events
3. **Test API Endpoints:** Verify HTTP requests are being logged
4. **Archive Old Logstash Config:** Keep for reference if needed

---

## Technical Details

### Event Format Sent to APM Server

```json
{
  "metadata": {
    "service": {
      "name": "vn-address-intelligence",
      "environment": "production"
    }
  },
  "log": {
    "level": "INFO",
    "logger": "VNAI",
    "message": "HTTP GET /api/parser - 200 (45ms)",
    "timestamp": 1716033000000000,
    "origin": {
      "file": {
        "name": "server.py",
        "line": 690
      },
      "function": "logging_middleware"
    }
  }
}
```

### Endpoint

- **URL:** `http://138.2.68.67:8200/intake/v2/events`
- **Method:** POST
- **Content-Type:** application/x-ndjson
- **Timeout:** 2 seconds

---

## Support

For issues or questions:
1. Check APM Server connectivity: `curl http://138.2.68.67:8200/`
2. Verify env vars are set correctly
3. Check application logs for APM handler errors
4. Review Elastic APM documentation

---

**Migration completed successfully! 🎉**

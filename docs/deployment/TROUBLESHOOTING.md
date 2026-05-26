# Troubleshooting — VN Address Intelligence

## Lỗi: `ModuleNotFoundError: No module named '_lzma'`

### Triệu chứng

```
File "/usr/local/lib/python3.11/lzma.py", line 27, in <module>
    from _lzma import *
ModuleNotFoundError: No module named '_lzma'
```

Xảy ra khi:
- Batch processing (`/api/batch/trigger`)
- Import `sentence-transformers` hoặc `datasets`
- Chạy `production_pipeline.py`

### Nguyên nhân

Python 3.11 được cài từ `apt` hoặc `deadsnakes PPA` **thiếu module `_lzma`** vì:
1. Hệ thống thiếu `liblzma-dev` khi build Python
2. Package `python3.11` từ PPA không include `_lzma` built-in

**Chi tiết:** Xem [BATCH-PROCESSING-LZMA-FIX.md](./BATCH-PROCESSING-LZMA-FIX.md)

### Giải pháp nhanh

```bash
# Trên VPS
cd /opt/vnai
wget https://raw.githubusercontent.com/your-org/vn-address-intelligence/main/scripts/deployment/hotfix-lzma.sh
sudo bash hotfix-lzma.sh
sudo supervisorctl restart vnai-api
```

### Giải pháp thủ công

```bash
# 1. Cài system libraries
sudo apt-get update
sudo apt-get install -y liblzma-dev libbz2-dev libffi-dev libssl-dev zlib1g-dev

# 2. Reinstall Python 3.11
sudo apt-get install --reinstall python3.11 python3.11-dev

# 3. Test _lzma
python3.11 -c "import _lzma; print('OK')"

# 4. Rebuild venv packages
cd /opt/vnai
source .venv/bin/activate
pip uninstall -y datasets sentence-transformers
pip install --no-cache-dir datasets sentence-transformers

# 5. Restart API
sudo supervisorctl restart vnai-api
```

Nếu reinstall thất bại, xem hướng dẫn build Python từ source trong [BATCH-PROCESSING-LZMA-FIX.md](./BATCH-PROCESSING-LZMA-FIX.md).

---

## Lỗi khác

### PostgreSQL connection refused

**Triệu chứng:** `psycopg2.OperationalError: could not connect to server`

**Giải pháp:**
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Check port
sudo netstat -tulpn | grep 5432

# Check .env
cat /opt/vnai/.env | grep DB_

# Test connection
psql -h 157.66.81.69 -U vnai_admin -d vn_address_intelligence_db
```

### Nginx 502 Bad Gateway

**Triệu chứng:** API không phản hồi, Nginx trả 502

**Giải pháp:**
```bash
# Check API process
sudo supervisorctl status vnai-api

# Check logs
tail -f /var/log/vnai/api-error.log

# Restart
sudo supervisorctl restart vnai-api
```

### Model loading timeout

**Triệu chứng:** API start chậm, timeout khi load model

**Giải pháp:**
```bash
# Tăng timeout trong supervisor
sudo nano /etc/supervisor/conf.d/vnai.conf
# Thêm: startsecs=60

# Hoặc giảm corpus size trong .env
echo "PARSER_CORPUS_MAX_ADDRESSES=5000" >> /opt/vnai/.env

sudo supervisorctl restart vnai-api
```

---

## Logs & Monitoring

```bash
# API logs
tail -f /var/log/vnai/api-error.log
tail -f /var/log/vnai/api-access.log

# Nginx logs
tail -f /var/log/nginx/error.log
tail -f /var/log/nginx/access.log

# Supervisor logs
sudo supervisorctl tail -f vnai-api

# System resources
htop
df -h
free -h
```

---

## Contact

Nếu gặp lỗi không có trong tài liệu này, tạo issue tại GitHub hoặc liên hệ team DevOps.

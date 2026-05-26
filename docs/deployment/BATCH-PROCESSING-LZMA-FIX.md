# Sửa lỗi Batch Processing: ModuleNotFoundError: No module named '_lzma'

## Tóm tắt

**Lỗi:** Batch processing (`/api/batch/trigger`) thất bại với lỗi `ModuleNotFoundError: No module named '_lzma'`

**Nguyên nhân:** Python 3.11 trên VPS thiếu module `_lzma` (C built-in) do:
1. Hệ thống thiếu `liblzma-dev` khi cài Python
2. Package `python3.11` từ `deadsnakes PPA` không bao gồm `_lzma`

**Luồng lỗi:**
```
UI (batch.html) 
  → POST /api/batch/trigger 
    → run_batch_job() (job_runners.py:66)
      → subprocess: python -m app.ai.production_pipeline
        → import models (production_pipeline.py:21)
          → from .phobert_model import PhoBERTSiamese
            → from sentence_transformers import ...
              → from datasets import Dataset
                → import lzma
                  → from _lzma import *  ❌ ModuleNotFoundError
```

**Ảnh hưởng:**
- ❌ Batch processing UI không hoạt động
- ❌ Không thể chạy `production_pipeline.py` trực tiếp
- ✅ Các endpoint khác (parse, lookup, admin) vẫn hoạt động bình thường

---

## Giải pháp nhanh (Hotfix cho VPS đang chạy)

### Bước 1: SSH vào VPS

```bash
ssh root@157.66.81.69
```

### Bước 2: Chạy hotfix script

```bash
cd /opt/vnai
wget https://raw.githubusercontent.com/your-org/vn-address-intelligence/main/scripts/deployment/hotfix-lzma.sh
sudo bash hotfix-lzma.sh
```

Script sẽ:
1. Cài `liblzma-dev` + các system libs cần thiết
2. Reinstall Python 3.11 (hoặc hướng dẫn build từ source nếu thất bại)
3. Rebuild `datasets` + `sentence-transformers` trong venv
4. Test import `_lzma`

### Bước 3: Restart API

```bash
sudo supervisorctl restart vnai-api
```

### Bước 4: Kiểm tra

```bash
# Test import trực tiếp
cd /opt/vnai
source .venv/bin/activate
python -c "import _lzma; from datasets import Dataset; print('✓ OK')"

# Test batch processing từ UI
# Truy cập: https://vnai.nod.io.vn/batch
# Click "Xử lý" → Kiểm tra log console
```

---

## Giải pháp thủ công (nếu script thất bại)

### Option A: Reinstall Python 3.11 (khuyến nghị)

```bash
# 1. Cài system libraries
sudo apt-get update
sudo apt-get install -y liblzma-dev libbz2-dev libffi-dev libssl-dev zlib1g-dev

# 2. Reinstall Python 3.11
sudo apt-get install --reinstall python3.11 python3.11-dev

# 3. Verify _lzma
python3.11 -c "import _lzma; print('OK')"

# 4. Rebuild venv packages
cd /opt/vnai
source .venv/bin/activate
pip uninstall -y datasets sentence-transformers
pip install --no-cache-dir datasets sentence-transformers

# 5. Test
python -c "from datasets import Dataset; print('OK')"

# 6. Restart
sudo supervisorctl restart vnai-api
```

### Option B: Build Python 3.11 từ source (nếu Option A thất bại)

```bash
# 1. Cài build dependencies
sudo apt-get install -y build-essential liblzma-dev libbz2-dev libffi-dev \
    libssl-dev zlib1g-dev libreadline-dev libsqlite3-dev wget curl

# 2. Download Python 3.11.9
cd /tmp
wget https://www.python.org/ftp/python/3.11.9/Python-3.11.9.tgz
tar -xzf Python-3.11.9.tgz
cd Python-3.11.9

# 3. Configure + build (5-10 phút)
./configure --enable-optimizations --with-lto
make -j$(nproc)
sudo make altinstall

# 4. Verify
/usr/local/bin/python3.11 -c "import _lzma; print('OK')"

# 5. Recreate venv
cd /opt/vnai
rm -rf .venv
/usr/local/bin/python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 6. Update supervisor config
sudo nano /etc/supervisor/conf.d/vnai.conf
# Đổi dòng command thành:
# command=/opt/vnai/.venv/bin/gunicorn app.api.server:app ...
# (venv sẽ tự dùng /usr/local/bin/python3.11)

sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl restart vnai-api
```

---

## Phòng tránh cho VPS mới

Setup script mới (`vnai-vps-setup.sh` v2.1) đã bổ sung system libs:

```bash
apt-get install -y -qq \
    liblzma-dev \
    libbz2-dev \
    libffi-dev \
    libssl-dev \
    zlib1g-dev
```

Khi setup VPS mới, dùng script v2.1+ để tránh lỗi này.

---

## Kiểm tra sau khi sửa

### 1. Test import Python

```bash
cd /opt/vnai
source .venv/bin/activate
python -c "
import _lzma
from datasets import Dataset
from sentence_transformers import SentenceTransformer
print('✓ All imports OK')
"
```

### 2. Test production_pipeline trực tiếp

```bash
cd /opt/vnai
source .venv/bin/activate
python -m app.ai.production_pipeline --limit 10
```

Kết quả mong đợi:
```
[HH:MM:SS] Loading models...
[HH:MM:SS] Processing 10 rows...
[HH:MM:SS] Progress: 10/10
[HH:MM:SS] Done. Processed 10 addresses.
```

### 3. Test batch processing từ UI

1. Truy cập: https://vnai.nod.io.vn/batch
2. Chọn "Số lượng địa chỉ mỗi lô": 100
3. Click "Xử lý"
4. Kiểm tra log console → Không có lỗi `ModuleNotFoundError`

### 4. Test API endpoint

```bash
curl -X POST https://vnai.nod.io.vn/api/batch/trigger \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"batch_size": 50, "method": "hybrid"}'
```

Kết quả mong đợi:
```json
{
  "status": "accepted",
  "message": "Batch processing job started",
  "job": {
    "jobId": "...",
    "status": "running",
    "totalCount": 50,
    ...
  }
}
```

---

## Logs & Debugging

### API logs

```bash
tail -f /var/log/vnai/api-error.log
```

### Supervisor logs

```bash
sudo supervisorctl tail -f vnai-api
```

### Test _lzma availability

```bash
python3.11 -c "import _lzma; print(_lzma.__file__)"
```

Kết quả mong đợi:
```
/usr/lib/python3.11/lib-dynload/_lzma.cpython-311-x86_64-linux-gnu.so
```

Nếu lỗi → Python thiếu `_lzma` built-in → Cần reinstall hoặc build từ source.

---

## Tài liệu liên quan

- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - Tổng hợp các lỗi deployment
- [vnai-vps-setup.sh](../../scripts/deployment/vnai-vps-setup.sh) - Setup script v2.1+
- [hotfix-lzma.sh](../../scripts/deployment/hotfix-lzma.sh) - Hotfix script tự động

---

## Changelog

### 2026-05-18
- Documented root cause: `_lzma` missing in Python 3.11 from deadsnakes PPA
- Added hotfix script + manual fix options
- Updated setup script to include `liblzma-dev` by default

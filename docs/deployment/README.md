# Deployment Documentation

Tài liệu triển khai VN Address Intelligence lên VPS production.

## Mục lục

### Setup & Configuration

- **[vnai-vps-setup.sh](../../scripts/deployment/vnai-vps-setup.sh)** - Script tự động setup VPS (Ubuntu 20.04+, Python 3.11, Nginx, Supervisor)
- **[.env.example](../../.env.example)** - Template cấu hình môi trường production

### Troubleshooting

- **[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)** - Tổng hợp các lỗi thường gặp và cách sửa
- **[BATCH-PROCESSING-LZMA-FIX.md](./BATCH-PROCESSING-LZMA-FIX.md)** - Chi tiết sửa lỗi `ModuleNotFoundError: No module named '_lzma'` trong batch processing

### Hotfix Scripts

- **[hotfix-lzma.sh](../../scripts/deployment/hotfix-lzma.sh)** - Sửa lỗi `_lzma` module missing

## Quick Start

### 1. Setup VPS mới

```bash
# Trên máy local
scp scripts/deployment/vnai-vps-setup.sh root@YOUR_VPS_IP:/tmp/

# SSH vào VPS
ssh root@YOUR_VPS_IP
sudo bash /tmp/vnai-vps-setup.sh
```

### 2. Deploy code

```bash
# Trên máy local
rsync -avz --exclude='.git' --exclude='__pycache__' --exclude='.venv' \
  ./ root@YOUR_VPS_IP:/opt/vnai/

# SSH vào VPS
ssh root@YOUR_VPS_IP
cd /opt/vnai

# Tạo .env
cp .env.example .env
nano .env  # Điền thông tin DB, API keys, etc.

# Cài dependencies
source .venv/bin/activate
pip install -r requirements.txt

# Start API
sudo supervisorctl start vnai-api
```

### 3. Kiểm tra

```bash
# Check API status
curl http://localhost:8081/api/stats

# Check logs
tail -f /var/log/vnai/api-error.log

# Check Nginx
curl https://vnai.nod.io.vn/api/stats
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Nginx (Port 80/443)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Frontend   │  │   API Proxy  │  │   Reports    │  │
│  │  /ui/*.html  │  │  /api/* →    │  │  /reports/*  │  │
│  │              │  │  :8081       │  │              │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│              Supervisor (Process Manager)               │
│  ┌──────────────────────────────────────────────────┐   │
│  │  vnai-api (Gunicorn + Uvicorn Workers)          │   │
│  │  Port: 8081 (internal)                          │   │
│  │  Workers: 4                                      │   │
│  │  User: vnai                                      │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                  FastAPI Application                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  AI Models   │  │  Database    │  │  External    │  │
│  │  - PhoBERT   │  │  PostgreSQL  │  │  - Typesense │  │
│  │  - NER       │  │  - PostGIS   │  │  - Label     │  │
│  │  - MGTE      │  │              │  │    Studio    │  │
│  │  - LLM       │  │              │  │  - Kibana    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Directory Structure

```
/opt/vnai/
├── app/              ← Python source code
│   ├── ai/           ← AI models & training
│   ├── api/          ← FastAPI server
│   ├── core/         ← Database & config
│   └── services/     ← Business logic
├── ui/               ← Static frontend (Nginx)
├── data/             ← Datasets
├── models/           ← Saved AI models
├── reports/          ← Experiment reports
├── logs/             ← App logs
├── .env              ← Secrets
├── .venv/            ← Python virtual environment
└── requirements.txt  ← Python dependencies

/var/log/vnai/
├── api-error.log     ← API error logs
└── api-access.log    ← API access logs

/etc/nginx/sites-available/
└── vnai              ← Nginx config

/etc/supervisor/conf.d/
└── vnai.conf         ← Supervisor config
```

## Common Tasks

### Update code

```bash
# Trên máy local
rsync -avz --exclude='.git' --exclude='__pycache__' --exclude='.venv' \
  ./ root@YOUR_VPS_IP:/opt/vnai/

# SSH vào VPS
ssh root@YOUR_VPS_IP
cd /opt/vnai
source .venv/bin/activate
pip install -r requirements.txt  # Nếu có dependencies mới
sudo supervisorctl restart vnai-api
```

### Update dependencies

```bash
cd /opt/vnai
source .venv/bin/activate
pip install --upgrade -r requirements.txt
sudo supervisorctl restart vnai-api
```

### Database migration

```bash
cd /opt/vnai
source .venv/bin/activate
alembic upgrade head
sudo supervisorctl restart vnai-api
```

### View logs

```bash
# API logs
tail -f /var/log/vnai/api-error.log
tail -f /var/log/vnai/api-access.log

# Supervisor logs
sudo supervisorctl tail -f vnai-api

# Nginx logs
tail -f /var/log/nginx/error.log
tail -f /var/log/nginx/access.log
```

### Restart services

```bash
# Restart API
sudo supervisorctl restart vnai-api

# Restart Nginx
sudo systemctl restart nginx

# Restart PostgreSQL
sudo systemctl restart postgresql
```

## Environment Variables

Xem [.env.example](../../.env.example) để biết danh sách đầy đủ.

**Quan trọng:**
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASS`, `DB_NAME` - PostgreSQL connection
- `HF_TOKEN` - Hugging Face token (để tải models)
- `NER_MODEL_ID` - NER model path hoặc Hugging Face model ID
- `PARSER_CORPUS_MAX_ADDRESSES` - Giới hạn corpus size (giảm nếu RAM thấp)
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` - JWT token expiration

## Security Checklist

- [ ] Đổi mật khẩu PostgreSQL mặc định
- [ ] Cấu hình firewall (ufw) chỉ mở port 80, 443, 22
- [ ] Cấu hình SSL/TLS với Certbot
- [ ] Giới hạn rate limiting trong Nginx
- [ ] Backup database định kỳ
- [ ] Rotate logs định kỳ
- [ ] Không commit `.env` vào git

## Performance Tuning

### Giảm memory usage

```bash
# Trong .env
PARSER_CORPUS_MAX_ADDRESSES=5000  # Giảm từ 10000

# Trong supervisor config
# Giảm số workers từ 4 xuống 2
command=/opt/vnai/.venv/bin/gunicorn app.api.server:app -w 2 ...
```

### Tăng timeout

```bash
# Trong supervisor config
command=/opt/vnai/.venv/bin/gunicorn app.api.server:app ... --timeout 600

# Trong Nginx config
proxy_read_timeout 600s;
proxy_connect_timeout 120s;
```

### Enable Redis cache

```bash
# Trong .env
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_CACHE_TTL=3600

# Cài Redis
sudo apt-get install redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

## Monitoring

### Health check endpoints

```bash
# API status
curl https://vnai.nod.io.vn/api/stats

# Parser status
curl https://vnai.nod.io.vn/api/parser/status

# Database connection
curl https://vnai.nod.io.vn/api/provinces?limit=1
```

### System resources

```bash
# CPU & Memory
htop

# Disk usage
df -h

# Network
netstat -tulpn | grep LISTEN
```

### Kibana APM (nếu enabled)

```bash
# Trong .env
KIBANA_LOG_ENABLED=true
KIBANA_LOG_HOST=138.2.68.67
KIBANA_LOG_PORT=8200
KIBANA_LOG_APP_NAME=vn-address-intelligence
ENVIRONMENT=production
```

Truy cập Kibana dashboard để xem logs, traces, metrics.

## Backup & Recovery

### Database backup

```bash
# Backup
pg_dump -h 157.66.81.69 -U vnai_admin -d vn_address_intelligence_db > backup.sql

# Restore
psql -h 157.66.81.69 -U vnai_admin -d vn_address_intelligence_db < backup.sql
```

### Code backup

```bash
# Backup
tar -czf vnai-backup-$(date +%Y%m%d).tar.gz /opt/vnai

# Restore
tar -xzf vnai-backup-20260518.tar.gz -C /
```

## Support

Nếu gặp vấn đề:

1. Kiểm tra [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
2. Xem logs: `/var/log/vnai/api-error.log`
3. Tạo issue trên GitHub
4. Liên hệ team DevOps

---

**Last updated:** 2026-05-18

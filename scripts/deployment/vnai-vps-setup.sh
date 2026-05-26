#!/bin/bash
# ══════════════════════════════════════════════════════════════
# VPS Setup — VN Address Intelligence
# Target: Ubuntu 20.04+ | PostgreSQL 12+ (đã có) | Nginx (đã có)
# Python: 3.11 — script sẽ cài qua apt / deadsnakes nếu thiếu
# Chạy: sudo bash /tmp/vnai-vps-setup.sh
# ══════════════════════════════════════════════════════════════

set -e

APP_USER="vnai"
APP_DIR="/opt/vnai"
API_PORT=8081   # 8080 đã bị Docker chiếm

ensure_python311() {
    if command -v python3.11 >/dev/null 2>&1 && python3.11 -c "import sys; assert sys.version_info >= (3, 11)" 2>/dev/null; then
        echo "  Python 3.11 đã có: $(python3.11 --version)"
        return 0
    fi
    echo "  Đang cài Python 3.11..."
    apt-get install -y -qq software-properties-common
    # shellcheck source=/dev/null
    . /etc/os-release
    case "${VERSION_ID:-}" in
        20.04|18.04)
            add-apt-repository -y ppa:deadsnakes/ppa
            apt-get update -qq
            apt-get install -y -qq python3.11 python3.11-venv python3.11-dev
            ;;
        *)
            apt-get update -qq
            apt-get install -y -qq python3.11 python3.11-venv python3.11-dev || {
                add-apt-repository -y ppa:deadsnakes/ppa
                apt-get update -qq
                apt-get install -y -qq python3.11 python3.11-venv python3.11-dev
            }
            ;;
    esac
    echo "  Đã cài: $(python3.11 --version)"
}

echo "══════════════════════════════════════════════"
echo "  VN Address Intelligence — VPS Setup"
echo "  Ubuntu 20.04+ · PostgreSQL (giữ nguyên)"
echo "  Python 3.11 (tự cài nếu thiếu)"
echo "══════════════════════════════════════════════"

# ── 0. Xóa repo PostgreSQL bị lỗi 404 ──
echo "[0/7] Cleaning broken apt repos..."
if ls /etc/apt/sources.list.d/pgdg* 2>/dev/null; then
    echo "  Removing broken pgdg repos..."
    rm -f /etc/apt/sources.list.d/pgdg*
    rm -f /etc/apt/sources.list.d/postgresql*
fi
# Xóa dòng apt.postgresql.org nếu bị nhúng trong sources.list
sed -i '/apt\.postgresql\.org/d' /etc/apt/sources.list 2>/dev/null || true

# ── 1. Python 3.11 + system packages ──
echo "[1/7] Ensuring Python 3.11 and system packages..."
apt-get update -qq
ensure_python311

apt-get install -y -qq \
    build-essential \
    git curl wget unzip \
    supervisor \
    rsync \
    liblzma-dev \
    libbz2-dev \
    libffi-dev \
    libssl-dev \
    zlib1g-dev

# PostGIS (bổ sung cho PostgreSQL 12 đã có)
echo "  Checking PostGIS..."
if ! dpkg -l | grep -q postgresql-12-postgis; then
    echo "  Installing PostGIS for PostgreSQL 12..."
    apt-get install -y -qq postgresql-12-postgis-3 2>/dev/null || echo "  PostGIS not available, skipping."
else
    echo "  PostGIS already installed. ✓"
fi

echo "  PostgreSQL: $(psql --version 2>/dev/null || echo 'N/A')"
echo "  Python:     $(python3.11 --version 2>/dev/null || echo 'N/A')"

# ── 2. Create app user ──
echo "[2/7] Creating app user: $APP_USER"
if ! id "$APP_USER" &>/dev/null; then
    useradd -m -s /bin/bash "$APP_USER"
    echo "  User '$APP_USER' created."
else
    echo "  User '$APP_USER' already exists. ✓"
fi

# ── 3. Create directory structure ──
echo "[3/7] Creating directory structure..."
mkdir -p "$APP_DIR"/{app,ui,data,models,reports,logs,scripts}
mkdir -p "$APP_DIR"/app/{ai,api,core,services}
mkdir -p "$APP_DIR"/data/seed
mkdir -p /var/log/vnai

cat << 'EOF'

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
  └── start.py          ← Entry point

EOF

# ── 4. Python venv ──
echo "[4/7] Setting up Python 3.11 virtual environment..."
cd "$APP_DIR"
if [ ! -d ".venv" ]; then
    python3.11 -m venv .venv
    echo "  venv created."
else
    echo "  venv already exists. ✓"
fi
source .venv/bin/activate
pip install --upgrade pip -q
echo "  pip: $(pip --version)"

# ── 5. Nginx config (thêm site, KHÔNG xóa default) ──
echo "[5/7] Configuring Nginx (site: vnai, port: $API_PORT)..."
cat > /etc/nginx/sites-available/vnai << NGINX
server {
    listen 80;
    server_name vnai.nod.io.vn;

    # ── Frontend (SaaS UI) ──
    location / {
        root /opt/vnai/ui;
        index index.html;
        try_files \$uri \$uri/ /index.html;
    }

    # ── API Backend (port $API_PORT, tránh 8080 Docker) ──
    location /api/ {
        proxy_pass http://127.0.0.1:$API_PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # ── Static reports ──
    location /reports/ {
        alias /opt/vnai/reports/;
        autoindex on;
    }

    # ── Security headers ──
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # ── Gzip ──
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml;
    gzip_min_length 256;
}
NGINX

ln -sf /etc/nginx/sites-available/vnai /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
echo "  Nginx configured: vnai.nod.io.vn ✓"

# ── SSL với Certbot ──
echo "  Installing SSL certificate..."
apt-get install -y -qq certbot python3-certbot-nginx 2>/dev/null || true
certbot --nginx -d vnai.nod.io.vn --non-interactive --agree-tos --email admin@nod.io.vn --redirect 2>/dev/null || echo "  ⚠ Certbot failed — run manually: sudo certbot --nginx -d vnai.nod.io.vn"

# ── 6. Supervisor ──
echo "[6/7] Configuring Supervisor..."
cat > /etc/supervisor/conf.d/vnai.conf << SUPERVISOR
[program:vnai-api]
command=/opt/vnai/.venv/bin/gunicorn app.api.server:app -w 4 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:$API_PORT --timeout 300
directory=/opt/vnai
user=$APP_USER
autostart=true
autorestart=true
stderr_logfile=/var/log/vnai/api-error.log
stdout_logfile=/var/log/vnai/api-access.log
; Repo dùng package app dưới src/app — PYTHONPATH bắt buộc để trùng với start.py / máy dev
environment=PYTHONPATH="/opt/vnai/src",PATH="/opt/vnai/.venv/bin:%(ENV_PATH)s"
SUPERVISOR

supervisorctl reread 2>/dev/null || true
supervisorctl update 2>/dev/null || true
echo "  Supervisor configured. ✓"

# ── 7. Permissions ──
echo "[7/7] Setting permissions..."
chown -R "$APP_USER":"$APP_USER" "$APP_DIR"
chown -R "$APP_USER":"$APP_USER" /var/log/vnai

echo ""
echo "══════════════════════════════════════════════"
echo "  ✅ SETUP COMPLETE"
echo "══════════════════════════════════════════════"
echo ""
echo "  URLs:"
echo "    UI:         https://vnai.nod.io.vn"
echo "    API:        https://vnai.nod.io.vn/api/"
echo "    API Local:  http://127.0.0.1:$API_PORT (internal)"
echo "    PostgreSQL: 5432 (giữ nguyên)"
echo ""
echo "  Next steps:"
echo "    1. Tạo .env:    nano $APP_DIR/.env"
echo "    2. Deploy code:  rsync từ máy local"
echo "    3. Cài deps:     source $APP_DIR/.venv/bin/activate && pip install -r requirements.txt"
echo "    4. Start API:    sudo supervisorctl start vnai-api"
echo "    5. Kiểm tra:     curl http://localhost:$API_PORT/api/stats"
echo ""

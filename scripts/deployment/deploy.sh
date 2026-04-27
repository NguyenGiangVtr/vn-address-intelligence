#!/bin/bash
# ══════════════════════════════════════════════════════════════
# Deploy Script — Chạy từ máy local (Windows/Git Bash/WSL)
# Usage: bash scripts/deployment/deploy.sh [user@host]
# Example: bash scripts/deployment/deploy.sh root@157.66.81.69
# ══════════════════════════════════════════════════════════════

set -e

# ── Load config from .env if exists ──
if [ -f .env ]; then
    # Filter out comments and empty lines, then export
    export $(grep -v '^#' .env | xargs)
fi

# ── Config ──
# Use environment variables if set, otherwise fallback to defaults
REMOTE_USER="${VPS_USER:-root}"
REMOTE_HOST="${VPS_IP:-157.66.81.69}"
REMOTE="${1:-$REMOTE_USER@$REMOTE_HOST}"

APP_DIR="/opt/vnai"
BRANCH="main"

echo "══════════════════════════════════════════════"
echo "  Deploying VN Address Intelligence"
echo "  Target: $REMOTE:$APP_DIR"
echo "══════════════════════════════════════════════"

# ── 1. Pre-flight checks ──
echo "[1/5] Pre-flight checks..."
if ! command -v rsync &>/dev/null; then
    echo "  rsync not found. Install: apt install rsync / choco install rsync"
    exit 1
fi

# ── 2. Sync files via rsync ──
echo "[2/5] Syncing files to VPS..."
rsync -avz --progress \
    --exclude='.git' \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='logs/' \
    --exclude='evidence/' \
    --exclude='models/' \
    --exclude='data/*.json' \
    --exclude='data/seed/' \
    --exclude='data/db_stats_history.json' \
    --exclude='docs/private/' \
    --exclude='scratch/' \
    --exclude='ls_env/' \
    --exclude='node_modules/' \
    ./ "$REMOTE:$APP_DIR/"

# ── 3. Remote: install deps + restart ──
echo "[3/5] Installing dependencies on VPS..."
ssh "$REMOTE" << 'REMOTE_CMD'
    cd /opt/vnai
    source .venv/bin/activate
    pip install -r requirements.txt -q
    pip install uvicorn gunicorn seqeval -q 2>/dev/null
REMOTE_CMD

# ── 4. Restart services ──
echo "[4/5] Restarting services..."
ssh "$REMOTE" << 'REMOTE_CMD'
    sudo supervisorctl restart vnai-api
    sudo nginx -t && sudo systemctl reload nginx
    echo "  Services restarted."
REMOTE_CMD

# ── 5. Health check ──
echo "[5/5] Health check..."
ssh "$REMOTE" << 'REMOTE_CMD'
    sleep 2
    STATUS=$(sudo supervisorctl status vnai-api | awk '{print $2}')
    echo "  vnai-api: $STATUS"
    if [ "$STATUS" = "RUNNING" ]; then
        echo "  ✅ Deploy successful!"
    else
        echo "  ❌ Service not running. Check: sudo tail -50 /var/log/vnai/api-error.log"
        exit 1
    fi
REMOTE_CMD

echo ""
echo "══════════════════════════════════════════════"
echo "  ✅ DEPLOY COMPLETE"
echo "══════════════════════════════════════════════"

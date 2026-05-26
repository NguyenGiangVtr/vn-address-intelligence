#!/bin/bash
# ══════════════════════════════════════════════════════════════
# Hotfix: ModuleNotFoundError: No module named '_lzma'
# Nguyên nhân: Python thiếu liblzma-dev khi build
# Giải pháp: Cài system libs + rebuild Python hoặc reinstall packages
# ══════════════════════════════════════════════════════════════

set -e

APP_DIR="/opt/vnai"

echo "══════════════════════════════════════════════"
echo "  Hotfix: _lzma module missing"
echo "══════════════════════════════════════════════"

# ── 1. Cài đặt system libraries ──
echo "[1/3] Installing system libraries..."
apt-get update -qq
apt-get install -y -qq \
    liblzma-dev \
    libbz2-dev \
    libffi-dev \
    libssl-dev \
    zlib1g-dev

echo "  ✓ System libraries installed"

# ── 2. Kiểm tra Python có _lzma built-in không ──
echo "[2/3] Checking Python 3.11 _lzma module..."
if python3.11 -c "import _lzma" 2>/dev/null; then
    echo "  ✓ Python 3.11 has _lzma built-in"
    NEED_REBUILD=false
else
    echo "  ✗ Python 3.11 missing _lzma — cần rebuild hoặc reinstall"
    NEED_REBUILD=true
fi

# ── 3. Giải pháp ──
if [ "$NEED_REBUILD" = true ]; then
    echo ""
    echo "  Python 3.11 được cài từ apt/deadsnakes KHÔNG có _lzma."
    echo "  Có 2 cách sửa:"
    echo ""
    echo "  A. Reinstall Python 3.11 từ deadsnakes (khuyến nghị):"
    echo "     sudo apt-get install --reinstall python3.11 python3.11-dev"
    echo ""
    echo "  B. Build Python 3.11 từ source (mất 5-10 phút):"
    echo "     cd /tmp"
    echo "     wget https://www.python.org/ftp/python/3.11.9/Python-3.11.9.tgz"
    echo "     tar -xzf Python-3.11.9.tgz"
    echo "     cd Python-3.11.9"
    echo "     ./configure --enable-optimizations"
    echo "     make -j\$(nproc)"
    echo "     sudo make altinstall"
    echo ""
    echo "  Chọn A (reinstall) trước. Nếu vẫn lỗi, dùng B (build source)."
    echo ""
    read -p "  Reinstall Python 3.11 ngay? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "  Reinstalling Python 3.11..."
        apt-get install --reinstall -y python3.11 python3.11-dev
        
        if python3.11 -c "import _lzma" 2>/dev/null; then
            echo "  ✓ _lzma module now available!"
        else
            echo "  ✗ Reinstall failed. Cần build từ source (option B)."
            exit 1
        fi
    else
        echo "  Skipped. Chạy lại script hoặc làm thủ công."
        exit 0
    fi
fi

# ── 4. Rebuild venv packages ──
echo "[3/3] Rebuilding venv packages..."
cd "$APP_DIR"
if [ -d ".venv" ]; then
    source .venv/bin/activate
    
    echo "  Reinstalling datasets + sentence-transformers..."
    pip uninstall -y datasets sentence-transformers 2>/dev/null || true
    pip install --no-cache-dir datasets sentence-transformers
    
    echo "  ✓ Packages reinstalled"
    
    # Test import
    echo "  Testing import..."
    python -c "import _lzma; from datasets import Dataset; print('✓ _lzma + datasets OK')"
else
    echo "  ✗ venv not found at $APP_DIR/.venv"
    exit 1
fi

echo ""
echo "══════════════════════════════════════════════"
echo "  ✅ HOTFIX COMPLETE"
echo "══════════════════════════════════════════════"
echo ""
echo "  Restart API:"
echo "    sudo supervisorctl restart vnai-api"
echo ""
echo "  Test batch processing:"
echo "    curl -X POST https://vnai.nod.io.vn/api/batch/process \\"
echo "         -H 'Content-Type: application/json' \\"
echo "         -d '{\"addresses\": [\"123 Lê Lợi, Q1, HCM\"]}'"
echo ""

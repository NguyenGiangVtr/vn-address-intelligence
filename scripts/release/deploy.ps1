# --------------------------------------------------------------
# Automated Deploy Script for VN Address Intelligence
# Builds, uploads, and deploys to VPS in one command
# Usage: .\scripts\release\deploy.ps1 [-VpsIp IP] [-VpsUser USER]
# --------------------------------------------------------------

param(
    [string]$VpsIp = "157.66.81.69",
    [string]$VpsUser = "root",
    [switch]$SkipBuild,
    [switch]$RestartOnly
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "==============================================================================================" -ForegroundColor Cyan
Write-Host "  🚀 VN Address Intelligence - Automated Deploy"
Write-Host "  Target: $VpsUser@$VpsIp"
Write-Host "==============================================================================================" -ForegroundColor Cyan

# 1. Build publish folder (unless skipped)
if (-not $SkipBuild -and -not $RestartOnly) {
    Write-Host ""
    Write-Host "📦 [Step 1/4] Building publish folder..." -ForegroundColor Yellow
    & "$PSScriptRoot\publish.ps1"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "❌ Build failed!"
        exit 1
    }
}

# 2. Upload to VPS (unless restart only)
if (-not $RestartOnly) {
    Write-Host ""
    Write-Host "📤 [Step 2/4] Uploading to VPS..." -ForegroundColor Yellow
    
    # Check if rsync is available
    $rsyncCmd = Get-Command rsync -ErrorAction SilentlyContinue
    if ($rsyncCmd) {
        Write-Host "  Using rsync for fast sync..."
        rsync -avz --delete --progress publish/ "${VpsUser}@${VpsIp}:/opt/vnai/"
    } else {
        Write-Host "  Rsync not found. Using scp..."
        scp -r publish/* "${VpsUser}@${VpsIp}:/opt/vnai/"
    }
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "❌ Upload failed! Check VPS connection."
        exit 1
    }
}

# 3. Install dependencies and setup on VPS
Write-Host ""
Write-Host "⚙️  [Step 3/4] Installing dependencies on VPS..." -ForegroundColor Yellow

$RemoteScript = @'
cd /opt/vnai
echo "📍 Current directory: $(pwd)"

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    echo "🐍 Activating Python virtual environment..."
    source .venv/bin/activate
else
    echo "❌ Virtual environment not found at /opt/vnai/.venv"
    exit 1
fi

# Install/update dependencies
if [ -f "requirements.txt" ]; then
    echo "📦 Installing Python dependencies..."
    pip install -r requirements.txt -q --no-cache-dir
else
    echo "⚠️  requirements.txt not found"
fi

# Set proper permissions
echo "🔒 Setting file permissions..."
chown -R vnai:vnai /opt/vnai
chmod 600 /opt/vnai/.env 2>/dev/null || true
chmod +x /opt/vnai/scripts/* 2>/dev/null || true

echo "✅ Dependencies installed successfully"
'@

ssh "${VpsUser}@${VpsIp}" "$RemoteScript"
if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ Remote setup failed!"
    exit 1
}

# 4. Restart services
Write-Host ""
Write-Host "🔄 [Step 4/4] Restarting services..." -ForegroundColor Yellow

$RestartScript = @'
# Restart API service
echo "🔄 Restarting vnai-api service..."
supervisorctl restart vnai-api

# Wait a bit for startup
sleep 3

# Check service status
echo "📊 Service status:"
supervisorctl status vnai-api

# Test API health
echo "🏥 Testing API health..."
if curl -s http://localhost:8081/api/stats > /dev/null; then
    echo "✅ API is responding"
else
    echo "⚠️  API health check failed - check logs"
fi

# Reload nginx (if needed)
echo "🌐 Reloading nginx..."
nginx -t && systemctl reload nginx || echo "⚠️  Nginx reload failed"

echo "✅ Services restarted successfully"
'@

ssh "${VpsUser}@${VpsIp}" "$RestartScript"
if ($LASTEXITCODE -ne 0) {
    Write-Warning "⚠️  Service restart had issues - check manually"
}

# 5. Cleanup local files for security
if (-not $SkipBuild -and -not $RestartOnly) {
    Write-Host ""
    Write-Host "🧹 Cleaning up local publish folder..." -ForegroundColor Yellow
    Remove-Item -Path "publish" -Recurse -Force -ErrorAction SilentlyContinue
}

# 6. Success message
Write-Host ""
Write-Host "==============================================================================================" -ForegroundColor Green
Write-Host "  ✅ DEPLOY COMPLETED SUCCESSFULLY!"
Write-Host ""
Write-Host "  🌐 Application URLs:"
Write-Host "    • Frontend: https://vnai.nod.io.vn"
Write-Host "    • API:      https://vnai.nod.io.vn/api/"
Write-Host "    • Health:   https://vnai.nod.io.vn/api/stats"
Write-Host ""
Write-Host "  📊 Quick Commands:"
Write-Host "    • Check logs: ssh $VpsUser@$VpsIp 'tail -f /var/log/vnai/api-access.log'"
Write-Host "    • Restart only: .\scripts\release\deploy.ps1 -RestartOnly"
Write-Host "    • Check status: ssh $VpsUser@$VpsIp 'supervisorctl status'"
Write-Host "==============================================================================================" -ForegroundColor Green
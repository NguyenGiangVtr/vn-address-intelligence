# ══════════════════════════════════════════════════════════════
# Deploy Script for Windows (PowerShell)
# Usage: .\scripts\deploy.ps1
# ══════════════════════════════════════════════════════════════

$ErrorActionPreference = "Stop"

# ── 1. Load config from .env ──
if (Test-Path ".env") {
    Get-Content .env | Where-Object { $_ -match "=" -and $_ -notmatch "^#" } | ForEach-Object {
        $name, $value = $_.Split('=', 2)
        Set-Variable -Name "ENV_$($name.Trim())" -Value $value.Trim() -Scope Script
    }
}

$REMOTE_USER = if ($null -ne $ENV_VPS_USER) { $ENV_VPS_USER } else { "root" }
$REMOTE_HOST = if ($null -ne $ENV_VPS_IP) { $ENV_VPS_IP } else { "157.66.81.69" }
$REMOTE = "$REMOTE_USER@$REMOTE_HOST"
$APP_DIR = "/opt/vnai"

Write-Host "══════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Deploying VN Address Intelligence (Windows)"
Write-Host "  Target: ${REMOTE}:${APP_DIR}"
Write-Host "══════════════════════════════════════════════" -ForegroundColor Cyan

# ── 2. Check for rsync ──
if (-not (Get-Command rsync -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Error: rsync not found! Please install Git for Windows or use MobaXterm's rsync." -ForegroundColor Red
    exit 1
}

# ── 3. Sync files via rsync ──
Write-Host "[1/3] Syncing files to VPS..." -ForegroundColor Yellow
rsync -avz --progress `
    --exclude='.git' `
    --exclude='.venv' `
    --exclude='__pycache__' `
    --exclude='*.pyc' `
    --exclude='.env' `
    --exclude='logs/' `
    --exclude='evidence/' `
    --exclude='models/' `
    --exclude='data/*.json' `
    --exclude='data/seed/' `
    --exclude='data/db_stats_history.json' `
    --exclude='docs/private/' `
    --exclude='scratch/' `
    --exclude='ls_env/' `
    --exclude='node_modules/' `
    ./ "${REMOTE}:${APP_DIR}/"

# ── 4. Remote: install deps + restart ──
Write-Host "[2/3] Updating dependencies and restarting services..." -ForegroundColor Yellow
ssh $REMOTE "cd $APP_DIR && source .venv/bin/activate && pip install -r requirements.txt -q && sudo supervisorctl restart vnai-api && sudo nginx -t && sudo systemctl reload nginx"

# ── 5. Health check ──
Write-Host "[3/3] Health check..." -ForegroundColor Yellow
Start-Sleep -Seconds 2
ssh $REMOTE "sudo supervisorctl status vnai-api"

Write-Host "══════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  ✅ DEPLOY COMPLETE!"
Write-Host "  Access UI at: https://vnai.nod.io.vn"
Write-Host "══════════════════════════════════════════════" -ForegroundColor Green

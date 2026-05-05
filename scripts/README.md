# VN Address Intelligence - Deploy Scripts

## Quick Start

### 🚀 One-Command Deploy (Recommended)
```powershell
# Deploy everything to VPS
.\scripts\deploy.ps1

# Deploy to custom VPS
.\scripts\deploy.ps1 -VpsIp "1.2.3.4" -VpsUser "ubuntu"

# Just restart services (no build/upload)
.\scripts\deploy.ps1 -RestartOnly
```

### 📦 Build Only
```powershell
# Build publish folder (includes .env file)
.\scripts\publish.ps1

# Build with auto-cleanup after 30 seconds
.\scripts\publish.ps1 -CleanupAfter
```

## What's Changed

### ✅ Environment Variables Fixed
- **Before**: Only copied `.env.example`, needed manual setup on VPS
- **After**: Automatically copies actual `.env` file with real credentials
- **Security**: Local publish folder auto-cleaned after deploy

### ✅ Automated Deploy Process
1. **Build** - Creates clean publish folder
2. **Upload** - Uses rsync (fast) or scp (fallback) 
3. **Setup** - Installs dependencies on VPS
4. **Restart** - Restarts API service and nginx
5. **Test** - Verifies API health
6. **Cleanup** - Removes local files for security

## File Structure

```
scripts/
├── deploy.ps1          # Wrapper → release/deploy.ps1
├── publish.ps1         # Wrapper → release/publish.ps1
└── release/
    ├── deploy.ps1      # Full automated deploy
    └── publish.ps1     # Build publish folder only
```

## Security Notes

- ✅ `.env` is gitignored (won't be committed)
- ✅ Local publish folder auto-cleaned after deploy
- ✅ VPS `.env` file gets 600 permissions (owner-only read)
- ⚠️ Ensure your local `.env` has production values before deploy

## Troubleshooting

### SSH Issues
```powershell
# Test SSH connection
ssh root@157.66.81.69 'echo "Connection OK"'

# Check VPS service status
ssh root@157.66.81.69 'supervisorctl status'
```

### API Issues
```powershell
# Check API logs
ssh root@157.66.81.69 'tail -f /var/log/vnai/api-access.log'

# Manual restart
ssh root@157.66.81.69 'supervisorctl restart vnai-api'
```

### Build Issues
```powershell
# Check if .env exists
Test-Path .env

# Manual build without auto-cleanup
.\scripts\publish.ps1
```
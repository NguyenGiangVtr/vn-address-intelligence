Write-Host ">>> Starting Full Migration Pipeline: Administrative Data..." -ForegroundColor Cyan

# 1. Seed V3
Write-Host "`n[1/3] Running seed_v3 - Master data v1 and v2..." -ForegroundColor Yellow
python -m app.main seed_v3
if ($LASTEXITCODE -ne 0) { Write-Error "Seed V3 failed!"; exit $LASTEXITCODE }

# 2. Refresh Old ID
Write-Host "`n[2/3] Running refresh_mat_old_id.py - Mapping legacy IDs..." -ForegroundColor Yellow
python scripts/migration/refresh_mat_old_id.py
if ($LASTEXITCODE -ne 0) { Write-Error "Refresh Old ID failed!"; exit $LASTEXITCODE }

# 3. Migrate Data
Write-Host "`n[3/3] Running migrate_acq_to_admin_v2.py - Migrating business data..." -ForegroundColor Yellow
python scripts/migration/migrate_acq_to_admin_v2.py --migrate
if ($LASTEXITCODE -ne 0) { Write-Error "Migration failed!"; exit $LASTEXITCODE }

Write-Host "`n>>> [SUCCESS] All systems updated to Administrative Admin V2!" -ForegroundColor Green

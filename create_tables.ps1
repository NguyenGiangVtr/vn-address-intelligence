Write-Host "🚀 Setting up database tables..." -ForegroundColor Cyan
$env:PYTHONPATH = "."
python scripts/create_tables.py
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Database initialization successful!" -ForegroundColor Green
} else {
    Write-Host "❌ Database initialization failed!" -ForegroundColor Red
}

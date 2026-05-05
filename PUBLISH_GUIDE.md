# 📦 VN Address Intelligence - Publish Guide

## ✅ Hệ thống Publish + Versioning đã setup hoàn tất!

### 🚀 Cách sử dụng nhanh

#### 1. Publish đầy đủ (Recommended)
```powershell
.\publish.ps1
```
**Kết quả:**
- ✅ Tự động update version cho tất cả CSS/JS files  
- ✅ Tạo thư mục `publish/` với code clean
- ✅ Sẵn sàng upload lên VPS

#### 2. Publish với auto-cleanup (Bảo mật)
```powershell
.\publish.ps1 -CleanupAfter
```
**Kết quả:** 
- Giống như trên + tự xóa folder `publish/` sau 30 giây

#### 3. Chỉ update version (Không tạo publish folder)
```powershell
.\publish.ps1 -VersionOnly
```

### 📋 NPM Scripts (Alternative)

```bash
npm run publish        # Chạy full publish
npm run version-only   # Chỉ update versions  
npm run build         # Chỉ chạy versioning (không copy files)
npm run version-check  # Xem version hiện tại
```

## 🔧 Cơ chế hoạt động

1. **Auto Versioning**: Tự động tạo version từ timestamp `YYYYMMDDHHMM`
2. **Cache Busting**: Update tất cả HTML files với:
   ```html
   <link rel="stylesheet" href="style.css?v=202605051714">
   <script src="app.js?v=202605051714"></script>
   ```
3. **Clean Publish**: Copy chỉ files cần thiết vào `publish/`
4. **Version Tracking**: Lưu thông tin build trong `version-info.json`

## 📁 Publish Folder Structure

```
publish/
├── app/              # Python backend
├── ui/               # Frontend (với versioned assets)
│   ├── index.html    # Updated với version mới
│   ├── style.css     # CSS files
│   ├── app.js        # JS files  
│   └── pages/        # All HTML pages updated
├── data/seed/        # Database seed
├── scripts/          # Deploy scripts
├── .env              # Production config
├── requirements.txt  # Python deps
├── start.py          # App entry
└── version-info.json # Build info
```

## 🌐 Deployment to VPS

### Option 1: Zip & Upload
```powershell
# Sau khi chạy .\publish.ps1
Compress-Archive -Path "publish\*" -DestinationPath "vnai-deploy.zip"
# Upload vnai-deploy.zip lên VPS
```

### Option 2: MobaXterm Drag & Drop  
1. Chạy `.\publish.ps1`
2. Mở MobaXterm
3. Kéo nội dung folder `publish/` vào `/opt/vnai/` trên VPS

### Option 3: rsync (Linux/WSL)
```bash
rsync -avz publish/ user@vps:/opt/vnai/
```

## ✨ Benefits

- ✅ **Zero manual version management** - Tự động update mọi thứ
- ✅ **Instant cache refresh** - Browser luôn load code mới nhất  
- ✅ **Clean deployment** - Chỉ files cần thiết được copy
- ✅ **Version tracking** - Biết chính xác version nào đang deploy
- ✅ **Production ready** - .env, requirements.txt được copy đúng

## 🐛 Troubleshooting

**PowerShell execution policy:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Node.js not found:**
- Install Node.js >= 14.0.0

**Encoding issues:**
- Scripts tự động handle UTF-8

## 📊 Version Format

- **Version**: `YYYYMMDDHHMM` (ví dụ: `202605051714`)
- **Timestamp**: ISO format trong `version-info.json`
- **Files updated**: 21 HTML files across the project

---

**🎉 Ready to deploy! Chạy `.\publish.ps1` và upload lên VPS!**
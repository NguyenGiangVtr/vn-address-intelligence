# 🚀 VN Address Intelligence - Build & Versioning System

## Tổng quan

System tự động cập nhật version numbers cho CSS và JS files để đảm bảo browser cache được refresh khi có update mới.

## Cách sử dụng

### 1. Chạy build script (Recommended)
```bash
npm run build
```

### 2. Chạy PowerShell script (Windows)
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\release\build_ui_assets.ps1
```

### 3. Build + publish
```bash
npm run publish
```

## Cơ chế hoạt động

1. **Version Generation**: Sử dụng timestamp format `YYYYMMDDHHMM`
2. **File Updates**: Tự động tìm và update tất cả `.html` files trong thư mục `ui/`
3. **Cache Busting**: Thêm `?v=YYYYMMDDHHMM` vào CSS và JS files
4. **Tracking**: Lưu thông tin version vào `version-info.json`

## File structure

```
├── build-version.js      # Node.js build script
├── scripts/release/build_ui_assets.ps1  # PowerShell cache-bust (tương đương)
├── package.json         # NPM scripts
├── version-info.json    # Version tracking (auto-generated)
└── ui/
    ├── index.html       # Main app (được update)
    ├── style.css        # CSS file
    ├── app.js          # JS file  
    └── pages/          # HTML pages (được update)
```

## Examples

### Before build:
```html
<link rel="stylesheet" href="style.css?v=20260505">
<script src="app.js?v=20260505"></script>
```

### After build (ví dụ lúc 14:30):
```html
<link rel="stylesheet" href="style.css?v=202605051430">
<script src="app.js?v=202605051430"></script>
```

## Lợi ích

✅ **Tự động cache busting** - Browser luôn load version mới nhất  
✅ **Zero manual work** - Không cần update version thủ công  
✅ **Cross-platform** - Hỗ trợ cả Node.js và PowerShell  
✅ **Version tracking** - Lưu lịch sử builds  
✅ **Safe updates** - Chỉ update local files, không touch external CDN  

## Tích hợp với CI/CD

Thêm vào build pipeline:

```yaml
# GitHub Actions example
- name: Build with versioning
  run: npm run build
  
- name: Deploy
  run: # your deployment commands
```

## Troubleshooting

- **Node.js not found**: Cài đặt Node.js >= 14.0.0
- **Permission denied**: Chạy `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
- **File encoding issues**: Script tự động sử dụng UTF-8

---

*Được tạo bởi VN Address Intelligence Team*
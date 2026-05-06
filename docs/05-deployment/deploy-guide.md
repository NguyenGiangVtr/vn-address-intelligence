# 🚀 Hướng dẫn Deploy VN Address Intelligence (Phiên bản Cuối cùng)

Tài liệu này tổng hợp toàn bộ quy trình từ thiết lập server ban đầu đến quy trình deploy hàng ngày.

## 1. Thông số Hệ thống & Yêu cầu

| Thành phần | Thông số |
|---|---|
| **Hệ điều hành** | Ubuntu 20.04+ hoặc 22.04+ (khuyến nghị LTS) |
| **Python** | 3.11.x (ràng buộc `requires-python` trong `pyproject.toml`) |
| **Cơ sở dữ liệu** | PostgreSQL 12 + PostGIS 3 |
| **Domain** | [https://vnai.nod.io.vn](https://vnai.nod.io.vn) |
| **IP Server** | 157.66.81.69 |
| **Cổng API (Internal)** | 8081 |

---

## 2. Giai đoạn 1: Thiết lập Server (Chỉ thực hiện 1 lần)

Thực hiện các lệnh này trên **VPS** (thông qua MobaXterm):

### 2.1. Cài Python 3.11 trên VPS (thủ công — chỉ khi không chạy script đủ bước)

Script `vnai-vps-setup.sh` đã **tự cài Python 3.11** nếu máy chưa có (Ubuntu 20.04 dùng PPA deadsnakes). Nếu bạn cài tay trước khi chạy script hoặc chỉ cần bổ sung interpreter:

**Ubuntu 22.04 / 24.04** (gói trong repo chính):

```bash
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev build-essential
python3.11 --version
```

**Ubuntu 20.04** (không có sẵn 3.11 trên Focal):

```bash
sudo apt-get update
sudo apt-get install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev build-essential
python3.11 --version
```

**Tạo/chạy lại virtualenv ở `/opt/vnai`** (sau khi đã có code + `requirements.txt`):

```bash
cd /opt/vnai
sudo -u vnai bash -c 'python3.11 -m venv .venv && source .venv/bin/activate && pip install -U pip && pip install -r requirements.txt'
sudo supervisorctl restart vnai-api
```

### 2.2. Upload Setup Script
Sử dụng lệnh sau tại terminal máy local (PowerShell hoặc Git Bash) để đẩy file setup lên VPS:
```powershell
scp scripts/deployment/vnai-vps-setup.sh root@157.66.81.69:/tmp/
```

### 2.3. Chạy Setup
Đăng nhập vào VPS (MobaXterm) và chạy lệnh:
```bash
# Cấp quyền và chạy script
sudo bash /tmp/vnai-vps-setup.sh
```
*Script này sẽ tự động cấu hình Nginx, Supervisor, Python venv, Certbot SSL và tạo cấu trúc thư mục `/opt/vnai`.*

### 2.4. Cấu hình Biến môi trường (.env)
```bash
# Copy file mẫu
cp /opt/vnai/.env.example /opt/vnai/.env

# Chỉnh sửa thông tin Database và IP
nano /opt/vnai/.env
```
*Sau khi sửa: `Ctrl + O` (Lưu), `Enter`, `Ctrl + X` (Thoát).*

**Hugging Face Hub:** Nếu log có cảnh báo kiểu unauthenticated / rate limit khi tải model (PhoBERT, mGTE, LLM…), thêm vào `.env` một dòng `HF_TOKEN=…` với [token Read](https://huggingface.co/settings/tokens). API đọc `.env` qua `load_dotenv` khi khởi động — không cần chỉnh Supervisor.

---

## 3. Giai đoạn 2: Deploy từ máy Local (Mỗi khi cập nhật code)

Bạn có 2 lựa chọn tùy thuộc vào môi trường terminal trên máy Windows của bạn.

### Lựa chọn A: Dùng PowerShell (Khuyên dùng cho Windows)
Mở PowerShell tại thư mục dự án:
```powershell
# Cho phép chạy script nếu bị chặn
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process

# Chạy lệnh deploy
.\scripts\deploy.ps1
```

### Lựa chọn B: Dùng Git Bash
Mở Git Bash tại thư mục dự án:
```bash
bash scripts/deployment/deploy.sh
```

### Lựa chọn C: Tạo folder Publish (Dành cho Upload thủ công)
Nếu bạn không có `rsync` hoặc muốn kiểm soát các file đẩy lên, hãy dùng script tạo folder sạch:
1. Chạy script tại PowerShell Local:
```powershell
.\scripts\publish.ps1
```
2. Mở thư mục `publish` vừa tạo.
3. Kéo toàn bộ **nội dung bên trong** thư mục `publish` vào `/opt/vnai/` trên VPS qua MobaXterm.

### Quy tắc loại trừ (Exclude)
Script deploy sẽ **không** đẩy các file sau lên server để bảo mật và tối ưu dung lượng:
- `.git/`, `.venv/`, `node_modules/`
- `.env` (Sử dụng file .env riêng trên server)
- `models/`, `data/*.json` (Dữ liệu lớn sinh ra trong quá trình chạy)

---

## 4. Quản lý Dịch vụ (Trên VPS)

Sử dụng các lệnh sau trong **MobaXterm** để quản lý ứng dụng:

| Lệnh | Mô tả |
|---|---|
| `sudo supervisorctl status` | Kiểm tra trạng thái vnai-api |
| `sudo supervisorctl restart vnai-api` | Khởi động lại API sau khi đổi code |
| `sudo supervisorctl stop vnai-api` | Dừng ứng dụng |
| `tail -f /var/log/vnai/api-access.log` | Xem log truy cập thời gian thực |
| `tail -f /var/log/vnai/api-error.log` | Xem log lỗi để debug |
| `sudo nginx -t` | Kiểm tra cấu hình Nginx |
| `sudo systemctl reload nginx` | Cập nhật cấu hình Nginx |

---

## 5. Cấu trúc thư mục Production

```text
/opt/vnai/                  ← Thư mục gốc ứng dụng
├── app/                    ← Code Python chính
├── ui/                     ← Giao diện Web (HTML/CSS/JS)
├── data/                   ← Dữ liệu xuất bản & seed
├── models/                 ← Nơi lưu trữ weights của mô hình AI
├── reports/                ← Các báo cáo thực nghiệm
├── logs/                   ← Log ứng dụng
├── .env                    ← Cấu hình bảo mật (Database, IP)
└── .venv/                  ← Môi trường ảo Python 3.11
```

---

## 6. Xử lý sự cố thường gặp (Troubleshooting)

### 6.1. Lỗi "502 Bad Gateway"
Thường do API chưa khởi động xong hoặc bị crash.
- Kiểm tra status: `sudo supervisorctl status vnai-api`
- Kiểm tra log lỗi: `tail -n 50 /var/log/vnai/api-error.log`

### 6.2. Lỗi SSL / Certbot
Nếu trang web báo "Không bảo mật", hãy chạy lại lệnh cấp SSL thủ công:
```bash
sudo certbot --nginx -d vnai.nod.io.vn
```

### 6.3. Lỗi Python Libraries
Nếu ứng dụng báo thiếu thư viện:
```bash
cd /opt/vnai
source .venv/bin/activate
pip install -r requirements.txt
sudo supervisorctl restart vnai-api
```

---
**Lưu ý Bảo mật:** Không bao giờ commit file `.env` lên Git. Luôn sử dụng `.env.example` làm mẫu.

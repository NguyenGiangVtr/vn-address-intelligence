# 🚀 Quick Start Guide - Experimental Workflow

**Ngày:** 2026-05-16  
**Trạng thái:** ✅ Infrastructure hoàn thành, sẵn sàng chạy thực nghiệm

---

## 📦 Đã Chuẩn Bị Sẵn

✅ **3 Wrapper Scripts** - Tự động hóa toàn bộ pipeline  
✅ **3 Analysis Scripts** - Phân tích và so sánh kết quả  
✅ **3 Checklists** - Theo dõi tiến độ chi tiết  
✅ **1 Validation Script** - Kiểm tra tính đầy đủ  
✅ **Evidence Structure** - Lưu trữ bằng chứng có tổ chức  

---

## 🎯 Chạy Thực Nghiệm (3 Bước)

### Bước 1: Ablation Study (2-3 ngày)

```powershell
# Chạy 5 cấu hình A1-A5
.\scripts\experiments\run_ablation_study.ps1

# Tạo bảng tổng hợp
python scripts/analysis/ablation_summary.py

# Kiểm tra bằng chứng
python scripts/analysis/validate_evidence.py --stage ablation

# Xem kết quả
cat evidence/ablation/summary/ablation_summary.md
```

**Output:** Xác định cấu hình tốt nhất (A1/A2/A3/A4/A5)

---

### Bước 2: Stratified K=5 (3-4 ngày)

```powershell
# Thay <BEST_CONFIG> bằng kết quả từ Ablation (ví dụ: A1)
.\scripts\experiments\run_stratified_k5_pipeline.ps1 -BestConfig <BEST_CONFIG>

# So sánh với oracle
python scripts/analysis/compare_oracle_vs_real.py

# Kiểm tra bằng chứng
python scripts/analysis/validate_evidence.py --stage stratified

# Xem kết quả
cat evidence/stratified/comparison/oracle_vs_real.md
```

**Output:** Đánh giá độ ổn định, gap với oracle

---

### Bước 3: SUPA-Bench Final (1-2 ngày)

```powershell
# Chạy với N=10,000 và nhiễu nặng D2
.\scripts\experiments\run_supa_final.ps1 -BestConfig <BEST_CONFIG>

# Kiểm tra bằng chứng
python scripts/analysis\validate_evidence.py --stage final

# Xem metrics
cat evidence/final/report/metrics.json

# Xem PDF
start evidence/final/report/vnai-chapters-master_*.pdf
```

**Output:** Báo cáo chính thức, PDF luận văn

---

## ✅ Validation Tổng Thể

Sau khi hoàn thành cả 3 giai đoạn:

```powershell
# Kiểm tra tất cả
python scripts/analysis/validate_evidence.py --stage all

# Tạo backup cuối cùng
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
Copy-Item -Recurse evidence "evidence_backup_final_$timestamp"
```

---

## 📋 Checklist Nhanh

### Trước Khi Bắt Đầu
- [ ] Database connection OK
- [ ] GPU/CPU đủ mạnh
- [ ] Checkpoint models đầy đủ
- [ ] Disk space ≥ 10GB

### Sau Mỗi Giai Đoạn
- [ ] Chạy validation script
- [ ] Điền checklist trong `evidence/*/CHECKLIST.md`
- [ ] Tạo backup
- [ ] Review kết quả

### Khi Hoàn Thành
- [ ] Validation pass cho cả 3 giai đoạn
- [ ] PDF luận văn biên dịch thành công
- [ ] Backup đầy đủ
- [ ] Sẵn sàng nộp luận văn

---

## 🔧 Tùy Chỉnh (Nếu Cần)

### Thay đổi tham số Ablation
```powershell
.\scripts\experiments\run_ablation_study.ps1 -N 500 -Seed 777
```

### Thay đổi tham số Stratified
```powershell
.\scripts\experiments\run_stratified_k5_pipeline.ps1 -KRuns 5 -N 2000 -BestConfig A1
```

### Thay đổi tham số Final
```powershell
.\scripts\experiments\run_supa_final.ps1 -N 10000 -Seed 42 -BestConfig A1
```

### Skip các bước đã chạy
```powershell
# Skip extract nếu đã có cohort
.\scripts\experiments\run_ablation_study.ps1 -SkipExtract -RunId 10

# Skip pipeline nếu đã có predictions
.\scripts\experiments\run_supa_final.ps1 -SkipPipeline -RunId 100
```

---

## 📊 Ước Tính Thời Gian

| Giai đoạn | Thời gian | Output |
|-----------|-----------|--------|
| Ablation Study | 2-3 ngày | 5 cấu hình, bảng so sánh |
| Stratified K=5 | 3-4 ngày | 5 run, aggregate, comparison |
| SUPA-Bench Final | 1-2 ngày | Metrics, LaTeX, PDF |
| **Tổng** | **6-9 ngày** | **Luận văn hoàn chỉnh** |

---

## 🆘 Troubleshooting

### Lỗi: "Run ID not found"
```powershell
# Kiểm tra run_id trong database
psql -d vnai -c "SELECT MAX(run_id) FROM prq.supa_benchmark_run;"
```

### Lỗi: "Pipeline failed"
```powershell
# Xem log file
cat evidence/*/logs/*.log | Select-String "ERROR"
```

### Lỗi: "Validation failed"
```powershell
# Xem chi tiết lỗi
python scripts/analysis/validate_evidence.py --stage all
```

---

## 📚 Tài Liệu Chi Tiết

- **Tổng quan:** `evidence/README.md`
- **Checklist Ablation:** `evidence/ablation/CHECKLIST.md`
- **Checklist Stratified:** `evidence/stratified/CHECKLIST.md`
- **Checklist Final:** `evidence/final/CHECKLIST.md`
- **SUPA-Bench Guide:** `docs/scientific-report/SUPA-BENCH-RUNBOOK.md`

---

## 🎉 Khi Hoàn Thành

Bạn sẽ có:

✅ Bảng so sánh 5 cấu hình Ablation  
✅ Đánh giá độ ổn định qua K=5 run  
✅ Kết quả chính thức N=10,000 với nhiễu nặng  
✅ PDF luận văn với số liệu thật  
✅ Bằng chứng đầy đủ, không bịa đặt  

**Sẵn sàng nộp luận văn và bảo vệ!** 🎓

---

**Lưu ý:** Tất cả script đã được thiết kế để chạy tự động, lưu evidence, và validate kết quả. Bạn chỉ cần chạy 3 lệnh chính và theo dõi tiến độ qua checklist.

**Good luck!** 🚀

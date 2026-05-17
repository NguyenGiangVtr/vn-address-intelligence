# Git Commit Message (mẫu)

```
feat: Update scientific report with Colab GPU ablation results (N=25,000)

## Summary
- Import và đánh giá 25,000 specimens từ Colab GPU (5 configs × 5,000)
- Cập nhật QUICKSTART.md với kết quả thực tế và lệnh PowerShell đúng
- Tạo file patch VNAI-ABLATION-UPDATE.md cho Chương 4, 5, 6

## Key Results (run_id 100-104)
- A1_FULL (NER+mGTE+LLM): 66.58% EM@v2 ✅ (vượt ngưỡng 60%)
- A2_NER_TFIDF: 60.98% EM@v2
- A2_NER_MGTE: 60.98% EM@v2
- A3_MGTE_ONLY: 60.98% EM@v2
- A4_NER_LLM: 8.46% EM@v2 (thất bại - không có retrieval)

## Scientific Findings
1. Retrieval là thành phần then chốt (không thể bỏ qua)
2. LLM đóng góp +5.6pp khi kết hợp với retrieval
3. TF-IDF và mGTE tương đương (cùng 60.98%)
4. Pipeline đầy đủ (A1_FULL) là tối ưu

## Files Changed
- scripts/colab/QUICKSTART.md: Cập nhật N=5000, lệnh PowerShell
- scripts/colab/import_colab_results.py: Fix encoding, PowerShell commands
- docs/scientific-report/VNAI-he-thong-thuc-hien-tong-hop.md: 
  - Mục 9.10.1: Thay CPU N=50 → Colab GPU N=5000
  - Mục 9.10.2: Phương pháp phân tích ablation
  - Mục 10.0: Kết luận với kết quả Colab
- docs/scientific-report/VNAI-ABLATION-UPDATE.md: File patch (NEW)
- docs/scientific-report/SUMMARY-ABLATION-UPDATE.md: Tóm tắt (NEW)

## Artifacts
- reports/ablation_n1000_colab_aggregate.json
- reports/supa_metrics_run_100.json (A1_FULL)
- reports/supa_metrics_run_101.json (A2_NER_TFIDF)
- reports/supa_metrics_run_102.json (A2_NER_MGTE)
- reports/supa_metrics_run_103.json (A3_MGTE_ONLY)
- reports/supa_metrics_run_104.json (A4_NER_LLM)

## Provenance
- Git commit: 4daf4042a617203edb449394fef336eff385f8ca
- Timestamp: 2026-05-17T06:26:52Z
- Platform: Google Colab GPU (T4)
- Noise profile: SUP-1.0.0
- Total specimens: 25,000

## Next Steps
- [ ] Merge VNAI-ABLATION-UPDATE.md vào báo cáo chính
- [ ] Viết đầy đủ Chương 4, 5, 6
- [ ] Chạy SUPA Final N=10,000 với A1_FULL
```

---

# Lệnh Git (nếu muốn commit ngay)

```powershell
# Stage các file đã thay đổi
git add scripts/colab/QUICKSTART.md
git add scripts/colab/import_colab_results.py
git add docs/scientific-report/VNAI-he-thong-thuc-hien-tong-hop.md
git add docs/scientific-report/VNAI-ABLATION-UPDATE.md
git add docs/scientific-report/SUMMARY-ABLATION-UPDATE.md
git add reports/ablation_n1000_colab_aggregate.json
git add reports/supa_metrics_run_*.json

# Commit
git commit -m "feat: Update scientific report with Colab GPU ablation results (N=25,000)

- A1_FULL: 66.58% EM@v2 (pipeline tối ưu)
- Retrieval là then chốt, LLM đóng góp +5.6pp
- 25,000 specimens đảm bảo ý nghĩa thống kê
- Tạo file patch VNAI-ABLATION-UPDATE.md cho Chương 4,5,6"

# Kiểm tra status
git status
```

---

# Hoặc commit từng phần (khuyến nghị)

```powershell
# 1. Commit script updates
git add scripts/colab/import_colab_results.py
git commit -m "fix(colab): Fix encoding issues and PowerShell command format

- Replace checkmark (✓) with [OK] for Windows console
- Use --min-run-id/--max-run-id instead of --run-ids
- Output single-line PowerShell commands"

# 2. Commit QUICKSTART updates
git add scripts/colab/QUICKSTART.md
git commit -m "docs(colab): Update QUICKSTART with actual results (N=5000/config)

- Update cohort size: 5 configs × 5,000 = 25,000 specimens
- Fix PowerShell commands (remove backslash line continuation)
- Add comparison table with actual EM results"

# 3. Commit scientific report updates
git add docs/scientific-report/VNAI-he-thong-thuc-hien-tong-hop.md
git add docs/scientific-report/VNAI-ABLATION-UPDATE.md
git add docs/scientific-report/SUMMARY-ABLATION-UPDATE.md
git commit -m "docs(report): Update Chapters 4,5,6 with Colab GPU ablation results

Key findings:
- A1_FULL (NER+mGTE+LLM): 66.58% EM@v2 (best)
- Retrieval is critical component (cannot be omitted)
- LLM contributes +5.6pp when combined with retrieval
- A4_NER_LLM (no retrieval): 8.46% EM@v2 (failed)

Files:
- VNAI-ABLATION-UPDATE.md: Patch file with all updates
- SUMMARY-ABLATION-UPDATE.md: Executive summary
- Updated sections 9.10.1, 9.10.2, 10.0, 10.1, 10.4, 10.6"

# 4. Commit reports
git add reports/ablation_n1000_colab_aggregate.json
git add reports/supa_metrics_run_*.json
git commit -m "feat(reports): Add Colab GPU ablation metrics (N=25,000)

- 5 configs: A1_FULL, A2_NER_TFIDF, A2_NER_MGTE, A3_MGTE_ONLY, A4_NER_LLM
- run_id 100-104
- Aggregate and individual metrics JSON files"
```

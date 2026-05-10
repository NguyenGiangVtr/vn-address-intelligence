# `scripts/ops` — vận hành corpus, vector, tối ưu

Mã **đầy đủ** nằm đây. Ở thư mục gốc repo vẫn có file cùng tên (shim) để lệnh `python compute_embeddings.py` và `from optimize_parser_performance import …` hoạt động như trước.

| File | Mục đích |
|------|-----------|
| `compute_embeddings.py` | Tính & ghi embedding mGTE/PhoBERT cho corpus |
| `setup_vector_indexes.py` | Tạo index pgvector (HNSW/IVFFlat) |
| `optimize_parser_performance.py` | Pool, index queue/corpus, batch demo |
| `optimize_training_pipeline.py` | Pipeline huấn luyện / tối ưu liên quan |
| `quick_corpus_setup.py` | Nạp corpus nhanh từ queue hoặc nguồn định sẵn |
| `update_corpus_advanced.py` | Cập nhật corpus nâng cao |
| `check_raw_join.py` | Kiểm tra join thô |
| `debug_parser_status.py`, `fix_parser_503.py` | Debug parser / API |
| `fix_corpus_names.py` | Sửa tên corpus |
| `test_api_corpus.py`, `test_corpus_simple.py` | Smoke test corpus/API |
| `temp_debug_lookup.py`, `temp_fix_llm.py` | Script tạm (cân nhắc xóa sau khi xong) |

**Chạy trực tiếp (không qua shim):**

```bash
python scripts/ops/compute_embeddings.py
```

Bootstrap đầu file thêm repo root vào `sys.path` + thư mục `ops` để `import _repo_bootstrap` ổn định khi load qua `importlib`.

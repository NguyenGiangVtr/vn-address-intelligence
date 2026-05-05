# AI Training Workflow Summary (Code-Truth)

## 1. Mục tiêu tài liệu
Tài liệu này là **TÀI LIỆU CỔ** - dùng cho tham khảo.

**VUI LÒNG THAM KHẢO PHIÊN BẢN MỚI:**
- **[00-TRAINING-PIPELINE-OVERVIEW.md](00-TRAINING-PIPELINE-OVERVIEW.md)** - Tổng hợp toàn bộ quy trình (IPO, thứ tự, kiểm chứng)
- **[01-NER_Entities.md](01-NER_Entities.md)** - PhoBERT NER (Input, Process, Output, DB, UI/UX, Metrics, Validation)
- **[02-PreLabeler.md](02-PreLabeler.md)** - Hybrid auto-labeling
- **[03-PhoBERT_Siamese.md](03-PhoBERT_Siamese.md)** - Dense retriever (Vietnamese)
- **[04-mGTE_Siamese.md](04-mGTE_Siamese.md)** - Multilingual baseline
- **[05-Qwen_LLM.md](05-Qwen_LLM.md)** - LLM normalization

## 2. End-to-end workflow (thuc te)

### Phase A - Tao du lieu gan nhan (pre-labeling)
- Script: app/ai/export_for_annotation.py
- Entry point: export_data(config_path, output_file, limit)
- Quy trinh:
  1. Doc config va ket noi DB qua DBConnector
  2. Query ngau nhien du lieu tu prq.address_cleansing_queue, join mat.ward, mat.district, mat.province de lay context hanh chinh
  3. Dung PreLabeler.predict(...) de tao predictions theo 2 lop:
     - Macro labels: PRO, DST, WDS tu string matching theo master context
     - Micro labels: NUM, STR, ALY, BLD, NHB, POI, PCD tu regex rules
  4. Xuat JSON theo format Label Studio + xuat XML cau hinh labels
- Dau vao:
  - DB: prq.address_cleansing_queue + mat.*
  - Config: app/ai/config.yaml
- Dau ra:
  - data/ner_samples_<timestamp>_<limit>_prelabeled.json
  - data/ner_samples_<timestamp>_<limit>_config.xml

### Phase B - Fine-tune NER PhoBERT
- Script: app/ai/train_ner.py
- Entry point: train_model(...)
- CLI:
  - python app/ai/train_ner.py --data <label_studio_json> [--output ... --epochs ... --batch-size ... --lr ... --eval-split ...]
  - python app/ai/train_ner.py --data <label_studio_json> --validate-only
- Quy trinh:
  1. Load Label Studio JSON
  2. Lay nhan BIO tu constants.get_ner_label_list()
  3. Chuyen doi Label Studio -> BIO token-level bang convert_labelstudio_to_bio(...)
  4. Validate mapping bang validate_conversion(...)
  5. Split train/eval theo seed (mac dinh 42)
  6. Fine-tune AutoModelForTokenClassification(vinai/phobert-base) bang HuggingFace Trainer
  7. Tinh metrics (f1/precision/recall) qua seqeval
  8. Luu model + tokenizer + training_log.json
- Dau vao:
  - JSON Label Studio da gan nhan
  - Label set tai app/ai/constants.py
- Dau ra:
  - models/phobert-ner-vn/
  - models/phobert-ner-vn/training_log.json

### Phase C - Chay experiment so sanh mo hinh
- Script: app/ai/experiment_runner.py
- Entry point: main(config_path, skip_llm=False)
- CLI:
  - python app/ai/experiment_runner.py --config app/ai/config.yaml
  - python app/ai/experiment_runner.py --config app/ai/config.yaml --no-llm
- Quy trinh:
  1. Load config va ket noi DB
  2. Load queries tu table cau hinh (input_column)
  3. Load corpus tu standard_addresses_table/column
  4. Chay PhoBERT Siamese (models/phobert_model.py)
  5. Chay mGTE Siamese (models/siamese_mgte.py)
  6. Chay LLM Qwen3 (models/llm_model.py), su dung mGTE retriever lay top-5 candidates
  7. Luu ket qua moi model vao cot ket qua tuong ung trong DB
  8. Neu co ground truth thi tinh metrics qua metrics.compute_metrics(...)
  9. Tao bao cao HTML + CSV qua report_generator
- Dau vao:
  - Config app/ai/config.yaml
  - DB table: database.table_name + experiment.standard_addresses_table
- Dau ra:
  - DB columns: normalized_phobert, normalized_mgte, normalized_llm (theo config)
  - reports/experiment_report.html
  - reports/experiment_results.csv

### Phase D - Production hybrid pipeline
- Script: app/ai/production_pipeline.py
- Entry point: run_pipeline(config_path, limit)
- CLI:
  - python app/ai/production_pipeline.py --config app/ai/config.yaml [--limit N]
- Quy trinh:
  1. Load config, ket noi DB
  2. Load abbreviation map (assets/abbreviation_map.json)
  3. Khoi tao retriever SiameseMGTE + NER + LLM
  4. Query cac dong can xu ly trong prq.address_cleansing_queue (street_address co gia tri, address_standardized chua co)
  5. NER extract tung row, chuan hoa tien to duong bang dictionary
  6. Tao context_addr va goi LLM normalize
  7. Ghi ket qua vao DB: is_standardized, confidence_score, processing_method, address_standardized
- Dau vao:
  - DB queue prq.address_cleansing_queue
  - assets/abbreviation_map.json
- Dau ra:
  - Cap nhat ket qua chuan hoa tren queue table

## 3. Thanh phan model va vai tro
- app/ai/models/ner_model.py:
  - AddressNER
  - Neu load duoc fine-tuned model thi dung HF NER pipeline
  - Neu khong load duoc thi fallback regex
- app/ai/models/phobert_model.py:
  - PhoBERTSiamese
  - encode_corpus() + normalize()
- app/ai/models/siamese_mgte.py:
  - SiameseMGTE
  - encode_corpus() + normalize()
- app/ai/models/llm_model.py:
  - LLMQwen3
  - normalize() de sinh dia chi chuan cuoi cung

## 4. Metrics va bao cao
- app/ai/metrics.py:
  - Exact match
  - Fuzzy match (SequenceMatcher >= 0.85)
  - Levenshtein ratio mean
  - Component accuracy: phuong, quan, tinh
  - Latency mean/p95/p99 + throughput qps
- app/ai/report_generator.py:
  - Tao bang so sanh metrics
  - Winner box theo weighted composite
  - Xuat HTML report + CSV chi tiet

## 5. Lenh chay nhanh de tai lap
1. Tao du lieu pre-label:
   - python app/ai/export_for_annotation.py --config app/ai/config.yaml --limit 1000
2. Train NER:
   - python app/ai/train_ner.py --data data/ner_samples_<timestamp>_1000_prelabeled.json
3. Chay benchmark models:
   - python app/ai/experiment_runner.py --config app/ai/config.yaml
4. Chay production hybrid pipeline:
   - python app/ai/production_pipeline.py --config app/ai/config.yaml --limit 1000

## 6. Luu y quan trong (thuc te code)
- Nguon nhan NER su that nam tai app/ai/constants.py; khong sua mapping o nhieu noi.
- production_pipeline.py dang truy van truc tiep prq.address_cleansing_queue cho xu ly production.
- production_pipeline.py dang hardcode duong dan assets/abbreviation_map.json.
- Neu khong co model fine-tuned, NER se fallback regex (chat luong thap hon).
- Config app/ai/config.yaml da dat schema/table theo phu hop queue prq.

## 7. Scope va gioi han tai lieu
- Tai lieu nay mo ta workflow dang co trong code hien tai.
- Cac de xuat mo rong (active learning, retrain scheduler, model registry) chua duoc trien khai thanh code trong app/ai.

# VN Address Intelligence - Codebase Context

**Cấu trúc thư mục & quy ước (chuẩn hóa):** [`docs/00-ENGINEERING/SOURCE-LAYOUT.md`](docs/00-ENGINEERING/SOURCE-LAYOUT.md) · [`scripts/README.md`](scripts/README.md)

## 🎯 Project Overview
**Vietnamese Address Intelligence System**: AI-powered platform for address normalization, geospatial enrichment, and administrative boundary management. Handles VN admin hierarchy (63 provinces → districts → wards), OSM data integration, NER training, and real-time parsing research.

**Tech Stack**:
- **Backend**: FastAPI (app/api/server.py)
- **Frontend**: Static HTML/JS/CSS (ui/)
- **DB**: PostgreSQL (schemas: `mat`, `osm`, `ath`, `prq`)
- **AI/ML**: PhoBERT, mGTE (Siamese), Qwen LLM for address normalization
- **CLI**: Click (app/main.py)
- **Data Sources**: NSO API, OSM Overpass, GSO crawlers, synthetic data

## 🏗️ Architecture & Data Flow
```
CLI (app/main.py) → Data Ingestion → DB → FastAPI API/UI → AI Models → Normalized Addresses
                    ↓
              OSM/NSO/GSO → Enrichment → Training Data → NER Models
```

1. **Data Ingestion** (CLI):
   - `init_db()`: Create schemas/tables
   - `seed_master()`: Import Province/District/Ward CSV
   - `seed_v2()`: Admin v2 + WardMapping
   - `fetch_osm`: OSM streets/buildings/POIs
   - `seed_queue`: Raw addresses → prq.address_cleansing_queue

2. **API Server** (app/api/server.py):
   - Serves UI static files (/ui, /pages)
   - Endpoints: /api/provinces, /api/lookup/mapping, /api/parser/analyze, /api/benchmark
   - Background jobs: OSM fetch, AI benchmarks
   - Auth: JWT (admin/vnai@2026)

3. **AI Pipeline** (app/ai/*):
   - **Models**: PhoBERTSiamese, SiameseMGTE, LLMQwen3
   - **Research**: /api/parser/analyze compares models on samples
   - **Training**: app/ai/train_ner.py, export_for_annotation.py
   - **Docs UI**: `GET /api/repo-docs/list|raw/*` reads `docs/*.md`; sidebar **Trung tâm tài liệu** (`#/documentation`)
   - **Queue**: prq.address_cleansing_queue stores raw → standardized (runbook: `docs/01-ai-training/11-OPERATING-PHASES-ABCD.md`). **Join master HC v1**: `old_*` on queue = `mat.*.old_id` with `admin_version = 1` (see `.cursor/rules/address-queue-mat-lineage.mdc`, `app/domain/acq_mat_lineage.py`).

4. **Key DB Schemas**:
   | Schema | Purpose | Key Tables |
   |--------|---------|------------|
   | `mat` | Admin hierarchy | Province, District, Ward, WardMapping |
   | `osm` | Geospatial | OSMStreet, OSMBuilding, OSMPoi, OSMRawEntity |
   | `prq` | Processing | AddressCleansingQueue (raw → AI normalized) |
   | `ath` | AI Hub | TrainingDataset, TrainingHistory, BenchmarkModelBaseline |

## 🚀 Key Files & Entry Points
```
├── app/main.py              # Click CLI: init_db, seed_*, fetch_osm
├── app/api/server.py        # FastAPI app + all endpoints
├── app/core/database.py     # SQLAlchemy models + create_all_tables()
├── app/core/config.py       # DB URL, env vars
├── ui/                      # Static frontend (app.js orchestrates pages)
├── app/ai/models/*.py       # PhoBERT, mGTE, Qwen LLM
├── app/services/osm_fetcher.py # OSM Overpass API client
├── scripts/ops/             # Embeddings, vector indexes, corpus ops (root-level *.py shims)
└── docs/*.md                # Architecture plans
```

## 📊 Core Data Models
- **AddressCleansingQueue** (prq): `{raw_address, province_name, ..., phobert_parsed_components, address_standardized, selected_ai_model}`
- **WardMapping** (mat): Admin changes (sáp nhập/đổi tên): `{ward_id_old → ward_id_new, effective_date_from/to}`

## 🔧 Usage Flow
1. `python -m app.main init_db`
2. `python -m app.main seed_master data/seed`
3. `python -m app.main seed_v2`
4. `python -m app.main fetch_osm --limit 5 --target 100000`
5. `uvicorn app.api.server:app --port 8081`
6. UI: http://localhost:8081 → Parser/Explorer/Benchmark pages

## 🎛️ Key API Endpoints
- `GET /api/provinces|districts|wards`
- `POST /api/parser/analyze` (PhoBERT/mGTE/LLM comparison)
- `POST /api/benchmark/trigger` (run app.ai.experiment_runner)
- `GET /api/benchmark/realtime` (F1/throughput from DB)
- `GET /explorer/queue` (raw address samples)

## 🤖 AI Models Performance (Seed Baselines)
| Model | F1 | Throughput (addr/s) | Cost/1M addr |
|-------|----|-------------------|--------------|
| PhoBERT | 84.2 | 27.8 | $42 |
| mGTE | 81.3 | 31.6 | $28 |
| Qwen LLM | 86.8 | 9.4 | $260 |

**Updated**: $(date)

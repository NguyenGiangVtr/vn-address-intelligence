-- ============================================================================
-- Migration: ACS Score + Epoch Columns + Area Polygon + Benchmark Tables
-- Áp dụng cho: G2 (ACS), G5 (Epoch), G3 (Spatial), G8 (Benchmark)
-- Ngày tạo: 2026-05-04
-- ============================================================================

-- ────────────────────────────────────────────────────────────────────────────
-- G2: Address Confidence Score — prq.address_cleansing_queue
-- ────────────────────────────────────────────────────────────────────────────

ALTER TABLE prq.address_cleansing_queue
    ADD COLUMN IF NOT EXISTS acs_score    NUMERIC(5,4),
    ADD COLUMN IF NOT EXISTS acs_decision VARCHAR(20),
    ADD COLUMN IF NOT EXISTS s_text       NUMERIC(5,4),
    ADD COLUMN IF NOT EXISTS s_sem        NUMERIC(5,4),
    ADD COLUMN IF NOT EXISTS v_hierarchy  NUMERIC(5,4),
    ADD COLUMN IF NOT EXISTS v_temporal   NUMERIC(5,4);

COMMENT ON COLUMN prq.address_cleansing_queue.acs_score    IS 'Address Confidence Score tổng hợp [0..1]';
COMMENT ON COLUMN prq.address_cleansing_queue.acs_decision IS 'AUTO_ACCEPT | AUTO_CONVERT | SUGGEST | REJECT';
COMMENT ON COLUMN prq.address_cleansing_queue.s_text       IS 'Thành phần text similarity [0..1]';
COMMENT ON COLUMN prq.address_cleansing_queue.s_sem        IS 'Thành phần semantic similarity [0..1]';
COMMENT ON COLUMN prq.address_cleansing_queue.v_hierarchy  IS 'Thành phần hierarchy validity [0..1]';
COMMENT ON COLUMN prq.address_cleansing_queue.v_temporal   IS 'Thành phần temporal weight [0..1]';

-- Index để filter theo acs_decision
CREATE INDEX IF NOT EXISTS idx_acq_acs_decision
    ON prq.address_cleansing_queue (acs_decision);

CREATE INDEX IF NOT EXISTS idx_acq_acs_score
    ON prq.address_cleansing_queue (acs_score);

-- ────────────────────────────────────────────────────────────────────────────
-- G5: Dual-Epoch Recognition — prq.address_cleansing_queue
-- ────────────────────────────────────────────────────────────────────────────

ALTER TABLE prq.address_cleansing_queue
    ADD COLUMN IF NOT EXISTS address_epoch VARCHAR(20);

COMMENT ON COLUMN prq.address_cleansing_queue.address_epoch IS 'PRE_2025 | POST_2025 | AMBIGUOUS';

CREATE INDEX IF NOT EXISTS idx_acq_address_epoch
    ON prq.address_cleansing_queue (address_epoch);

-- ────────────────────────────────────────────────────────────────────────────
-- G3: Spatial — mat.area_polygon (GeoJSON polygon storage)
-- Ghi chú: Để dùng ST_* functions, cần cài PostGIS:
--   CREATE EXTENSION IF NOT EXISTS postgis;
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS mat.area_polygon (
    id            SERIAL PRIMARY KEY,
    unit_level    VARCHAR(20)  NOT NULL,    -- 'province' | 'district' | 'ward'
    unit_id       INTEGER      NOT NULL,
    unit_name     VARCHAR(200),
    geojson       JSONB,                    -- GeoJSON geometry object
    source        VARCHAR(50)  DEFAULT 'OSM',  -- 'OSM' | 'GSO' | 'MANUAL' | 'CONCAVE_HULL'
    admin_version INTEGER      DEFAULT 2,
    created_at    TIMESTAMPTZ  DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_area_polygon_unit
    ON mat.area_polygon (unit_level, unit_id);

COMMENT ON TABLE mat.area_polygon IS 'Ranh giới polygon đơn vị hành chính (GeoJSON). Dùng với PostGIS cho Point-in-Polygon.';

-- ────────────────────────────────────────────────────────────────────────────
-- G8: Benchmark Datasets D1-D5 — ath.benchmark_dataset
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS ath.benchmark_dataset (
    id                   SERIAL PRIMARY KEY,
    dataset_code         VARCHAR(10)  NOT NULL,   -- D1, D2, D3, D4, D5
    raw_address          TEXT         NOT NULL,
    expected_ward_id     INTEGER,
    expected_district_id INTEGER,
    expected_province_id INTEGER,
    noise_type           VARCHAR(50),             -- typo | no_diacritic | abbreviation | pre_2025 | rural | boundary
    admin_version        INTEGER      DEFAULT 2,
    notes                TEXT,
    created_at           TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_benchmark_dataset_code
    ON ath.benchmark_dataset (dataset_code);

COMMENT ON TABLE ath.benchmark_dataset IS 'Dataset chuẩn D1-D5 cho thực nghiệm benchmark (Chương 4.1)';

-- ────────────────────────────────────────────────────────────────────────────
-- G8: Benchmark Run Results — ath.benchmark_run_result
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS ath.benchmark_run_result (
    id                    SERIAL PRIMARY KEY,
    run_id                VARCHAR(50)  NOT NULL,     -- UUID lần chạy
    dataset_code          VARCHAR(10)  NOT NULL,
    model_key             VARCHAR(32)  NOT NULL,
    sample_id             INTEGER      REFERENCES ath.benchmark_dataset(id),
    predicted_ward_id     INTEGER,
    predicted_district_id INTEGER,
    predicted_province_id INTEGER,
    acs_score             NUMERIC(5,4),
    acs_decision          VARCHAR(20),
    address_epoch         VARCHAR(20),
    latency_ms            FLOAT,
    is_correct            BOOLEAN,
    created_at            TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_benchmark_run_id
    ON ath.benchmark_run_result (run_id);

CREATE INDEX IF NOT EXISTS idx_benchmark_run_model
    ON ath.benchmark_run_result (model_key, dataset_code);

COMMENT ON TABLE ath.benchmark_run_result IS 'Kết quả từng lần chạy benchmark theo run_id và model (G8)';

-- ────────────────────────────────────────────────────────────────────────────
-- Verify
-- ────────────────────────────────────────────────────────────────────────────

-- SELECT column_name, data_type FROM information_schema.columns
-- WHERE table_schema = 'prq' AND table_name = 'address_cleansing_queue'
-- AND column_name IN ('acs_score','acs_decision','s_text','s_sem','v_hierarchy','v_temporal','address_epoch');

-- SELECT COUNT(*) FROM mat.area_polygon;
-- SELECT COUNT(*) FROM ath.benchmark_dataset;

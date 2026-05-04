-- =============================================================================
-- SCD Type 2 Migration — G1: GOV-SYNC NÂNG CẤP
-- Ngày: 04/05/2026
-- Mô tả: Thêm cột SCD Type 2 vào mat.province, mat.district, mat.ward
--        và tạo bảng mat.unit_edge, ath.sync_log
-- =============================================================================

-- Đảm bảo schema tồn tại
CREATE SCHEMA IF NOT EXISTS mat;
CREATE SCHEMA IF NOT EXISTS ath;

-- =============================================================================
-- 1. Thêm cột SCD Type 2 vào mat.province
-- =============================================================================
ALTER TABLE mat.province
  ADD COLUMN IF NOT EXISTS valid_from    TIMESTAMPTZ DEFAULT NOW(),
  ADD COLUMN IF NOT EXISTS valid_to      TIMESTAMPTZ DEFAULT '9999-12-31 00:00:00+00',
  ADD COLUMN IF NOT EXISTS is_current    BOOLEAN     DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS version_id    INTEGER     DEFAULT 1,
  ADD COLUMN IF NOT EXISTS predecessor_id INTEGER    REFERENCES mat.province(row_id) ON DELETE SET NULL;

-- Khởi tạo dữ liệu hiện có: đánh dấu tất cả là bản ghi hiện tại
UPDATE mat.province
SET
  valid_from  = COALESCE(created_date, NOW()),
  valid_to    = '9999-12-31 00:00:00+00',
  is_current  = TRUE,
  version_id  = 1
WHERE valid_from IS NULL OR is_current IS NULL;

-- Index để tăng tốc query SCD
CREATE INDEX IF NOT EXISTS idx_province_scd
  ON mat.province (province_id, is_current, valid_from, valid_to);

-- =============================================================================
-- 2. Thêm cột SCD Type 2 vào mat.district
-- =============================================================================
ALTER TABLE mat.district
  ADD COLUMN IF NOT EXISTS valid_from     TIMESTAMPTZ DEFAULT NOW(),
  ADD COLUMN IF NOT EXISTS valid_to       TIMESTAMPTZ DEFAULT '9999-12-31 00:00:00+00',
  ADD COLUMN IF NOT EXISTS is_current     BOOLEAN     DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS version_id     INTEGER     DEFAULT 1,
  ADD COLUMN IF NOT EXISTS predecessor_id INTEGER     REFERENCES mat.district(row_id) ON DELETE SET NULL;

UPDATE mat.district
SET
  valid_from  = COALESCE(created_date, NOW()),
  valid_to    = '9999-12-31 00:00:00+00',
  is_current  = TRUE,
  version_id  = 1
WHERE valid_from IS NULL OR is_current IS NULL;

CREATE INDEX IF NOT EXISTS idx_district_scd
  ON mat.district (district_id, is_current, valid_from, valid_to);

-- =============================================================================
-- 3. Thêm cột SCD Type 2 vào mat.ward
-- =============================================================================
ALTER TABLE mat.ward
  ADD COLUMN IF NOT EXISTS valid_from     TIMESTAMPTZ DEFAULT NOW(),
  ADD COLUMN IF NOT EXISTS valid_to       TIMESTAMPTZ DEFAULT '9999-12-31 00:00:00+00',
  ADD COLUMN IF NOT EXISTS is_current     BOOLEAN     DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS version_id     INTEGER     DEFAULT 1,
  ADD COLUMN IF NOT EXISTS predecessor_id INTEGER     REFERENCES mat.ward(row_id) ON DELETE SET NULL;

UPDATE mat.ward
SET
  valid_from  = COALESCE(created_date, NOW()),
  valid_to    = '9999-12-31 00:00:00+00',
  is_current  = TRUE,
  version_id  = 1
WHERE valid_from IS NULL OR is_current IS NULL;

CREATE INDEX IF NOT EXISTS idx_ward_scd
  ON mat.ward (ward_id, is_current, valid_from, valid_to);

-- =============================================================================
-- 4. Tạo bảng mat.unit_edge — Đồ thị quan hệ hành chính
-- =============================================================================
CREATE TABLE IF NOT EXISTS mat.unit_edge (
  id                SERIAL PRIMARY KEY,
  from_unit_id      INTEGER      NOT NULL,
  from_level        VARCHAR(20)  NOT NULL,  -- 'province', 'district', 'ward'
  to_unit_id        INTEGER      NOT NULL,
  to_level          VARCHAR(20)  NOT NULL,
  relationship_type VARCHAR(50)  NOT NULL,  -- MERGES_INTO, SPLIT_FROM, RENAMES_TO, BOUNDARY_ADJUSTED
  effective_date    TIMESTAMPTZ  NOT NULL,
  resolution_ref    VARCHAR(200),           -- Số nghị quyết, VD: "1228/NQ-UBTVQH15"
  notes             TEXT,
  created_at        TIMESTAMPTZ  DEFAULT NOW()
);

COMMENT ON TABLE mat.unit_edge IS
  'Đồ thị quan hệ thay đổi hành chính: sáp nhập, tách, đổi tên, điều chỉnh ranh giới.';

CREATE INDEX IF NOT EXISTS idx_unit_edge_from
  ON mat.unit_edge (from_unit_id, from_level);
CREATE INDEX IF NOT EXISTS idx_unit_edge_to
  ON mat.unit_edge (to_unit_id, to_level);
CREATE INDEX IF NOT EXISTS idx_unit_edge_date
  ON mat.unit_edge (effective_date);

-- =============================================================================
-- 5. Tạo bảng ath.sync_log — Nhật ký đồng bộ hành chính (persist)
-- =============================================================================
CREATE TABLE IF NOT EXISTS ath.sync_log (
  id               SERIAL PRIMARY KEY,
  sync_source      VARCHAR(50),   -- 'NSO_API', 'N8N_WORKFLOW', 'MANUAL'
  level            VARCHAR(20),   -- 'province', 'district', 'ward'
  unit_id          INTEGER,
  change_type      VARCHAR(30),   -- 'CREATE', 'UPDATE', 'MERGE', 'RENAME', 'NO_CHANGE', 'SYNC_COMPLETE'
  old_value        JSONB,
  new_value        JSONB,
  synced_at        TIMESTAMPTZ    DEFAULT NOW(),
  records_affected INTEGER        DEFAULT 0,
  run_id           VARCHAR(50)    -- UUID để nhóm các log cùng một lần chạy
);

COMMENT ON TABLE ath.sync_log IS
  'Nhật ký đồng bộ dữ liệu hành chính từ NSO/n8n. Mỗi lần chạy workflow có cùng run_id.';

CREATE INDEX IF NOT EXISTS idx_sync_log_run_id
  ON ath.sync_log (run_id);
CREATE INDEX IF NOT EXISTS idx_sync_log_synced_at
  ON ath.sync_log (synced_at DESC);
CREATE INDEX IF NOT EXISTS idx_sync_log_level_unit
  ON ath.sync_log (level, unit_id);

-- =============================================================================
-- 6. View tiện ích: Trạng thái hiện tại (tương đương trước migration)
-- =============================================================================
CREATE OR REPLACE VIEW mat.province_current AS
  SELECT * FROM mat.province WHERE is_current = TRUE;

CREATE OR REPLACE VIEW mat.district_current AS
  SELECT * FROM mat.district WHERE is_current = TRUE;

CREATE OR REPLACE VIEW mat.ward_current AS
  SELECT * FROM mat.ward WHERE is_current = TRUE;

-- =============================================================================
-- Kiểm tra kết quả
-- =============================================================================
-- SELECT 'province SCD columns' as check, COUNT(*) FROM information_schema.columns
--   WHERE table_schema = 'mat' AND table_name = 'province'
--     AND column_name IN ('valid_from','valid_to','is_current','version_id','predecessor_id');
-- SELECT 'unit_edge rows' as check, COUNT(*) FROM mat.unit_edge;
-- SELECT 'sync_log rows' as check, COUNT(*) FROM ath.sync_log;

-- =============================================================================
-- mat.* : thêm is_active cho province, đồng bộ từ is_current, bỏ is_current
-- Ngày: 2026-05-12
-- Chạy: psql hoặc SQL client (một transaction).
-- Sau file này: chạy kiểm tra trùng + 20260512_mat_unique_business_ids_apply.py
-- =============================================================================

BEGIN;

-- 1) Province: thêm is_active nếu chưa có
ALTER TABLE mat.province
  ADD COLUMN IF NOT EXISTS is_active BOOLEAN;

DO $sync_province_active$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'mat' AND table_name = 'province' AND column_name = 'is_current'
  ) THEN
    EXECUTE 'UPDATE mat.province SET is_active = COALESCE(is_active, is_current, TRUE)';
  ELSE
    EXECUTE 'UPDATE mat.province SET is_active = COALESCE(is_active, TRUE)';
  END IF;
END
$sync_province_active$;

UPDATE mat.province
SET is_active = TRUE
WHERE is_active IS NULL;

ALTER TABLE mat.province
  ALTER COLUMN is_active SET DEFAULT TRUE;

ALTER TABLE mat.province
  ALTER COLUMN is_active SET NOT NULL;

-- 2) District / Ward: đồng bộ is_active từ is_current (nếu cột còn tồn tại)
DO $sync_district_active$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'mat' AND table_name = 'district' AND column_name = 'is_current'
  ) THEN
    EXECUTE 'UPDATE mat.district SET is_active = COALESCE(is_active, is_current, TRUE)';
  ELSE
    EXECUTE 'UPDATE mat.district SET is_active = COALESCE(is_active, TRUE)';
  END IF;
END
$sync_district_active$;

UPDATE mat.district
SET is_active = TRUE
WHERE is_active IS NULL;

ALTER TABLE mat.district
  ALTER COLUMN is_active SET DEFAULT TRUE;

ALTER TABLE mat.district
  ALTER COLUMN is_active SET NOT NULL;

DO $sync_ward_active$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'mat' AND table_name = 'ward' AND column_name = 'is_current'
  ) THEN
    EXECUTE 'UPDATE mat.ward SET is_active = COALESCE(is_active, is_current, TRUE)';
  ELSE
    EXECUTE 'UPDATE mat.ward SET is_active = COALESCE(is_active, TRUE)';
  END IF;
END
$sync_ward_active$;

UPDATE mat.ward
SET is_active = TRUE
WHERE is_active IS NULL;

ALTER TABLE mat.ward
  ALTER COLUMN is_active SET DEFAULT TRUE;

ALTER TABLE mat.ward
  ALTER COLUMN is_active SET NOT NULL;

-- 3) Bỏ index SCD cũ (có is_current)
DROP INDEX IF EXISTS mat.idx_province_scd;
DROP INDEX IF EXISTS mat.idx_district_scd;
DROP INDEX IF EXISTS mat.idx_ward_scd;

-- 4) Index thay thế (không unique): tra cứu theo mã nghiệp vụ + trạng thái
CREATE INDEX IF NOT EXISTS idx_mat_province_bid_active
  ON mat.province (province_id)
  WHERE is_deleted = FALSE AND is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_mat_district_bid_active
  ON mat.district (district_id)
  WHERE is_deleted = FALSE AND is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_mat_ward_bid_active
  ON mat.ward (ward_id)
  WHERE is_deleted = FALSE AND is_active = TRUE;

-- 5) Bỏ cột is_current
ALTER TABLE mat.province DROP COLUMN IF EXISTS is_current;
ALTER TABLE mat.district DROP COLUMN IF EXISTS is_current;
ALTER TABLE mat.ward DROP COLUMN IF EXISTS is_current;

COMMIT;

-- -----------------------------------------------------------------------------
-- After this migration:
-- 1) If duplicate business ids remain: run
--    scripts/migration/20260512_mat_remap_duplicate_business_ids.sql
--    (remap *_id — does not set is_deleted / does not delete rows).
-- 2) python scripts/migration/mat_unique_business_ids_apply.py --check-only
-- 3) python scripts/migration/mat_unique_business_ids_apply.py --apply
-- -----------------------------------------------------------------------------

-- =============================================================================
-- Data migration: NO soft-delete — keep every mat row; fix duplicate business ids
-- by assigning NEW province_id / district_id / ward_id to non-canonical rows.
--
-- Canonical row per duplicate group (same *_id, is_deleted = false):
--   ORDER BY admin_version DESC NULLS LAST,
--            CASE WHEN is_active THEN 1 ELSE 0 END DESC,
--            row_id DESC
--   → rn = 1 keeps the existing *_id; rn > 1 gets max(*)+offset (globally unique).
--
-- Child updates (same admin_version as the remapped parent row):
--   - mat.district.province_id when province business id changes
--   - mat.ward.district_id when district business id changes
--   - mat.area_polygon.unit_id for unit_level province|district|ward + admin_version
--
-- Persists remap audit tables (survive COMMIT) for downstream SQL:
--   mat.migration_remap_province
--   mat.migration_remap_district
--   mat.migration_remap_ward
--
-- Run AFTER: 20260512_mat_is_active_drop_is_current.sql
-- Then run:  20260512_mat_remap_downstream_business_ids.sql
-- Then:      mat_unique_business_ids_apply.py --check-only / --apply
-- =============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS mat.migration_remap_province (
  loser_row_id      INTEGER PRIMARY KEY,
  old_province_id   INTEGER NOT NULL,
  new_province_id   INTEGER NOT NULL,
  admin_version     INTEGER
);

CREATE TABLE IF NOT EXISTS mat.migration_remap_district (
  loser_row_id       INTEGER PRIMARY KEY,
  old_district_id    INTEGER NOT NULL,
  new_district_id    INTEGER NOT NULL,
  admin_version      INTEGER,
  snapshot_province_id INTEGER
);

CREATE TABLE IF NOT EXISTS mat.migration_remap_ward (
  loser_row_id        INTEGER PRIMARY KEY,
  old_ward_id         INTEGER NOT NULL,
  new_ward_id         INTEGER NOT NULL,
  admin_version       INTEGER,
  snapshot_district_id  INTEGER,
  snapshot_province_id  INTEGER
);

TRUNCATE mat.migration_remap_province;
TRUNCATE mat.migration_remap_district;
TRUNCATE mat.migration_remap_ward;

-- Preflight
DO $chk$
BEGIN
  IF EXISTS (
    SELECT 1 FROM mat.province WHERE is_deleted = FALSE
    GROUP BY province_id, admin_version HAVING COUNT(*) > 1
  ) THEN
    RAISE EXCEPTION 'mat.province: duplicate (province_id, admin_version) with is_deleted=false';
  END IF;
  IF EXISTS (
    SELECT 1 FROM mat.district WHERE is_deleted = FALSE
    GROUP BY district_id, admin_version HAVING COUNT(*) > 1
  ) THEN
    RAISE EXCEPTION 'mat.district: duplicate (district_id, admin_version) with is_deleted=false';
  END IF;
  IF EXISTS (
    SELECT 1 FROM mat.ward WHERE is_deleted = FALSE
    GROUP BY ward_id, admin_version HAVING COUNT(*) > 1
  ) THEN
    RAISE EXCEPTION 'mat.ward: duplicate (ward_id, admin_version) with is_deleted=false';
  END IF;
END
$chk$;

-- --------------------------------------------------------------------------- 1) Province
CREATE TEMP TABLE _prov_remap (
  row_id              INTEGER NOT NULL PRIMARY KEY,
  old_province_id     INTEGER NOT NULL,
  new_province_id     INTEGER NOT NULL,
  admin_version       INTEGER NOT NULL
) ON COMMIT DROP;

WITH dups AS (
  SELECT province_id
  FROM mat.province
  WHERE is_deleted = FALSE
  GROUP BY province_id
  HAVING COUNT(*) > 1
),
ranked AS (
  SELECT
    p.row_id,
    p.province_id AS old_pid,
    p.admin_version,
    ROW_NUMBER() OVER (
      PARTITION BY p.province_id
      ORDER BY
        p.admin_version DESC NULLS LAST,
        CASE WHEN p.is_active THEN 1 ELSE 0 END DESC,
        p.row_id DESC
    ) AS rn
  FROM mat.province p
  INNER JOIN dups d ON d.province_id = p.province_id
  WHERE p.is_deleted = FALSE
),
losers AS (
  SELECT row_id, old_pid, admin_version,
         ROW_NUMBER() OVER (ORDER BY row_id) AS seq
  FROM ranked
  WHERE rn > 1
),
mx AS (SELECT COALESCE(MAX(province_id), 0) AS m FROM mat.province)
INSERT INTO _prov_remap (row_id, old_province_id, new_province_id, admin_version)
SELECT l.row_id, l.old_pid, mx.m + l.seq::INTEGER, l.admin_version
FROM losers l CROSS JOIN mx;

INSERT INTO mat.migration_remap_province (loser_row_id, old_province_id, new_province_id, admin_version)
SELECT row_id, old_province_id, new_province_id, admin_version FROM _prov_remap;

UPDATE mat.province p
SET
  province_id = r.new_province_id,
  updated_date = NOW()
FROM _prov_remap r
WHERE p.row_id = r.row_id;

UPDATE mat.district d
SET
  province_id = r.new_province_id,
  updated_date = NOW()
FROM _prov_remap r
WHERE d.province_id = r.old_province_id
  AND d.admin_version IS NOT DISTINCT FROM r.admin_version
  AND d.is_deleted = FALSE;

UPDATE mat.area_polygon ap
SET
  unit_id = r.new_province_id,
  updated_at = NOW()
FROM _prov_remap r
WHERE ap.unit_level = 'province'
  AND ap.unit_id = r.old_province_id
  AND ap.admin_version IS NOT DISTINCT FROM r.admin_version;

-- --------------------------------------------------------------------------- 2) District
CREATE TEMP TABLE _dist_remap (
  row_id                 INTEGER NOT NULL PRIMARY KEY,
  old_district_id        INTEGER NOT NULL,
  new_district_id        INTEGER NOT NULL,
  admin_version          INTEGER NOT NULL,
  snapshot_province_id   INTEGER
) ON COMMIT DROP;

WITH dups AS (
  SELECT district_id
  FROM mat.district
  WHERE is_deleted = FALSE
  GROUP BY district_id
  HAVING COUNT(*) > 1
),
ranked AS (
  SELECT
    d.row_id,
    d.district_id AS old_did,
    d.admin_version,
    d.province_id AS snap_pid,
    ROW_NUMBER() OVER (
      PARTITION BY d.district_id
      ORDER BY
        d.admin_version DESC NULLS LAST,
        CASE WHEN d.is_active THEN 1 ELSE 0 END DESC,
        d.row_id DESC
    ) AS rn
  FROM mat.district d
  INNER JOIN dups x ON x.district_id = d.district_id
  WHERE d.is_deleted = FALSE
),
losers AS (
  SELECT row_id, old_did, admin_version, snap_pid,
         ROW_NUMBER() OVER (ORDER BY row_id) AS seq
  FROM ranked
  WHERE rn > 1
),
mx AS (SELECT COALESCE(MAX(district_id), 0) AS m FROM mat.district)
INSERT INTO _dist_remap (row_id, old_district_id, new_district_id, admin_version, snapshot_province_id)
SELECT l.row_id, l.old_did, mx.m + l.seq::INTEGER, l.admin_version, l.snap_pid
FROM losers l CROSS JOIN mx;

INSERT INTO mat.migration_remap_district (loser_row_id, old_district_id, new_district_id, admin_version, snapshot_province_id)
SELECT row_id, old_district_id, new_district_id, admin_version, snapshot_province_id FROM _dist_remap;

UPDATE mat.district d
SET
  district_id = r.new_district_id,
  updated_date = NOW()
FROM _dist_remap r
WHERE d.row_id = r.row_id;

UPDATE mat.ward w
SET
  district_id = r.new_district_id,
  updated_date = NOW()
FROM _dist_remap r
WHERE w.district_id = r.old_district_id
  AND w.admin_version IS NOT DISTINCT FROM r.admin_version
  AND w.is_deleted = FALSE;

UPDATE mat.area_polygon ap
SET
  unit_id = r.new_district_id,
  updated_at = NOW()
FROM _dist_remap r
WHERE ap.unit_level = 'district'
  AND ap.unit_id = r.old_district_id
  AND ap.admin_version IS NOT DISTINCT FROM r.admin_version;

-- --------------------------------------------------------------------------- 3) Ward
CREATE TEMP TABLE _ward_remap (
  row_id                  INTEGER NOT NULL PRIMARY KEY,
  old_ward_id             INTEGER NOT NULL,
  new_ward_id             INTEGER NOT NULL,
  admin_version           INTEGER NOT NULL,
  snapshot_district_id    INTEGER,
  snapshot_province_id    INTEGER
) ON COMMIT DROP;

WITH dups AS (
  SELECT ward_id
  FROM mat.ward
  WHERE is_deleted = FALSE
  GROUP BY ward_id
  HAVING COUNT(*) > 1
),
ranked AS (
  SELECT
    w.row_id,
    w.ward_id AS old_wid,
    w.admin_version,
    w.district_id AS snap_did,
    d.province_id AS snap_pid,
    ROW_NUMBER() OVER (
      PARTITION BY w.ward_id
      ORDER BY
        w.admin_version DESC NULLS LAST,
        CASE WHEN w.is_active THEN 1 ELSE 0 END DESC,
        w.row_id DESC
    ) AS rn
  FROM mat.ward w
  INNER JOIN dups x ON x.ward_id = w.ward_id
  LEFT JOIN mat.district d
    ON d.district_id = w.district_id
   AND d.admin_version IS NOT DISTINCT FROM w.admin_version
   AND d.is_deleted = FALSE
  WHERE w.is_deleted = FALSE
),
losers AS (
  SELECT row_id, old_wid, admin_version, snap_did, snap_pid,
         ROW_NUMBER() OVER (ORDER BY row_id) AS seq
  FROM ranked
  WHERE rn > 1
),
mx AS (SELECT COALESCE(MAX(ward_id), 0) AS m FROM mat.ward)
INSERT INTO _ward_remap (row_id, old_ward_id, new_ward_id, admin_version, snapshot_district_id, snapshot_province_id)
SELECT l.row_id, l.old_wid, mx.m + l.seq::INTEGER, l.admin_version, l.snap_did, l.snap_pid
FROM losers l CROSS JOIN mx;

INSERT INTO mat.migration_remap_ward (loser_row_id, old_ward_id, new_ward_id, admin_version, snapshot_district_id, snapshot_province_id)
SELECT row_id, old_ward_id, new_ward_id, admin_version, snapshot_district_id, snapshot_province_id FROM _ward_remap;

UPDATE mat.ward w
SET
  ward_id = r.new_ward_id,
  updated_date = NOW()
FROM _ward_remap r
WHERE w.row_id = r.row_id;

UPDATE mat.area_polygon ap
SET
  unit_id = r.new_ward_id,
  updated_at = NOW()
FROM _ward_remap r
WHERE ap.unit_level = 'ward'
  AND ap.unit_id = r.old_ward_id
  AND ap.admin_version IS NOT DISTINCT FROM r.admin_version;

COMMIT;

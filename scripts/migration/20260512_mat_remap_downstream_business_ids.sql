-- =============================================================================
-- Downstream remap: apply mat.migration_remap_* to other tables.
--
-- Each block uses its own BEGIN/COMMIT (or standalone DO) so one failure does
-- not leave the session in 25P02 "transaction aborted" for the rest.
--
-- Optional objects use EXECUTE (dynamic SQL) so missing tables/columns are not
-- parsed at plan time when skipped.
--
-- Prerequisites: mat.migration_remap_* populated by
--   20260512_mat_remap_duplicate_business_ids.sql
--
-- If you see 25P02 from a *previous* run in the same session: run ROLLBACK; then
-- re-execute from the failed section onward.
--
-- "0 row updated" usually means: (1) mat.migration_remap_* is empty — re-run
-- 20260512_mat_remap_duplicate_business_ids.sql while duplicates still exist;
-- or (2) queue lineage columns old_* do not match mat.*.old_id on loser rows —
-- run scripts/migration/mat_remap_downstream_diagnostics.sql
-- =============================================================================

DO $pre$
DECLARE
  np INTEGER;
  nd INTEGER;
  nw INTEGER;
BEGIN
  IF to_regclass('mat.migration_remap_province') IS NULL THEN
    RAISE WARNING 'mat.migration_remap_province missing — run remap SQL first';
    RETURN;
  END IF;
  SELECT COUNT(*)::int INTO np FROM mat.migration_remap_province;
  SELECT COUNT(*)::int INTO nd FROM mat.migration_remap_district;
  SELECT COUNT(*)::int INTO nw FROM mat.migration_remap_ward;
  RAISE NOTICE 'mat.migration_remap rows: province=%, district=%, ward=%', np, nd, nw;
  IF np = 0 AND nd = 0 AND nw = 0 THEN
    RAISE WARNING 'All remap tables empty — downstream updates will affect 0 rows.';
  END IF;
END
$pre$;

-- --------------------------------------------------------------------------- 1) prq.address_cleansing_queue
BEGIN;

UPDATE prq.address_cleansing_queue q
SET
  province_id = m.new_province_id,
  updated_at = NOW()
FROM mat.migration_remap_province m
JOIN mat.province pl ON pl.row_id = m.loser_row_id
WHERE q.province_id IS NOT DISTINCT FROM m.old_province_id
  AND (
    q.old_province_id IS NOT DISTINCT FROM pl.old_id
    OR (q.old_province_id IS NULL AND pl.old_id IS NULL)
  );

UPDATE prq.address_cleansing_queue q
SET
  district_id = m.new_district_id,
  updated_at = NOW()
FROM mat.migration_remap_district m
JOIN mat.district dl ON dl.row_id = m.loser_row_id
WHERE q.district_id IS NOT DISTINCT FROM m.old_district_id
  AND (
    q.old_district_id IS NOT DISTINCT FROM dl.old_id
    OR (q.old_district_id IS NULL AND dl.old_id IS NULL)
  );

UPDATE prq.address_cleansing_queue q
SET
  ward_id = m.new_ward_id,
  updated_at = NOW()
FROM mat.migration_remap_ward m
JOIN mat.ward wl ON wl.row_id = m.loser_row_id
WHERE q.ward_id IS NOT DISTINCT FROM m.old_ward_id
  AND (
    q.old_ward_id IS NOT DISTINCT FROM wl.old_id
    OR (q.old_ward_id IS NULL AND wl.old_id IS NULL)
  );

COMMIT;

-- --------------------------------------------------------------------------- 2) prq.address_clean_corpus (skip if table or admin_version missing)
DO $corpus$
BEGIN
  IF to_regclass('prq.address_clean_corpus') IS NULL THEN
    RAISE NOTICE 'Skip: prq.address_clean_corpus does not exist';
    RETURN;
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'prq' AND table_name = 'address_clean_corpus' AND column_name = 'admin_version'
  ) THEN
    RAISE NOTICE 'Skip: prq.address_clean_corpus has no admin_version column';
    RETURN;
  END IF;

  EXECUTE $sql$
    UPDATE prq.address_clean_corpus c
    SET province_id = m.new_province_id
    FROM mat.migration_remap_province m
    WHERE c.province_id IS NOT DISTINCT FROM m.old_province_id
      AND c.admin_version IS NOT DISTINCT FROM m.admin_version
  $sql$;

  EXECUTE $sql$
    UPDATE prq.address_clean_corpus c
    SET district_id = m.new_district_id
    FROM mat.migration_remap_district m
    WHERE c.district_id IS NOT DISTINCT FROM m.old_district_id
      AND c.admin_version IS NOT DISTINCT FROM m.admin_version
  $sql$;

  EXECUTE $sql$
    UPDATE prq.address_clean_corpus c
    SET ward_id = m.new_ward_id
    FROM mat.migration_remap_ward m
    WHERE c.ward_id IS NOT DISTINCT FROM m.old_ward_id
      AND c.admin_version IS NOT DISTINCT FROM m.admin_version
  $sql$;
END
$corpus$;

-- --------------------------------------------------------------------------- 3) mat.admin_unit_mapping (optional table)
DO $admin_map$
BEGIN
  IF to_regclass('mat.admin_unit_mapping') IS NULL THEN
    RAISE NOTICE 'Skip: mat.admin_unit_mapping does not exist';
    RETURN;
  END IF;

  EXECUTE $sql$
    UPDATE mat.admin_unit_mapping a
    SET new_id = m.new_province_id, updated_at = NOW()
    FROM mat.migration_remap_province m
    WHERE a.level = 1
      AND a.new_id = m.old_province_id
      AND a.admin_version IS NOT DISTINCT FROM m.admin_version
  $sql$;

  EXECUTE $sql$
    UPDATE mat.admin_unit_mapping a
    SET new_id = m.new_district_id, updated_at = NOW()
    FROM mat.migration_remap_district m
    WHERE a.level = 2
      AND a.new_id = m.old_district_id
      AND a.admin_version IS NOT DISTINCT FROM m.admin_version
  $sql$;

  EXECUTE $sql$
    UPDATE mat.admin_unit_mapping a
    SET new_id = m.new_ward_id, updated_at = NOW()
    FROM mat.migration_remap_ward m
    WHERE a.level = 3
      AND a.new_id = m.old_ward_id
      AND a.admin_version IS NOT DISTINCT FROM m.admin_version
  $sql$;
END
$admin_map$;

-- --------------------------------------------------------------------------- 4) mat.ward_mapping
DO $wm$
BEGIN
  IF to_regclass('mat.ward_mapping') IS NULL THEN
    RAISE NOTICE 'Skip: mat.ward_mapping does not exist';
    RETURN;
  END IF;

  EXECUTE $sql$
    UPDATE mat.ward_mapping wm
    SET ward_id_old = rw.new_ward_id, updated_date = NOW()
    FROM mat.migration_remap_ward rw
    WHERE wm.ward_id_old = rw.old_ward_id
      AND wm.district_id_old IS NOT DISTINCT FROM rw.snapshot_district_id
      AND wm.province_id_old IS NOT DISTINCT FROM rw.snapshot_province_id
  $sql$;

  EXECUTE $sql$
    UPDATE mat.ward_mapping wm
    SET district_id_old = rd.new_district_id, updated_date = NOW()
    FROM mat.migration_remap_district rd
    WHERE wm.district_id_old = rd.old_district_id
      AND wm.province_id_old IS NOT DISTINCT FROM rd.snapshot_province_id
  $sql$;
END
$wm$;

-- --------------------------------------------------------------------------- 5) ath.benchmark_dataset
DO $bd$
BEGIN
  IF to_regclass('ath.benchmark_dataset') IS NULL THEN
    RAISE NOTICE 'Skip: ath.benchmark_dataset does not exist';
    RETURN;
  END IF;

  EXECUTE $sql$
    UPDATE ath.benchmark_dataset bd
    SET expected_province_id = m.new_province_id
    FROM mat.migration_remap_province m
    WHERE bd.expected_province_id IS NOT DISTINCT FROM m.old_province_id
      AND bd.admin_version IS NOT DISTINCT FROM m.admin_version
  $sql$;

  EXECUTE $sql$
    UPDATE ath.benchmark_dataset bd
    SET expected_district_id = m.new_district_id
    FROM mat.migration_remap_district m
    WHERE bd.expected_district_id IS NOT DISTINCT FROM m.old_district_id
      AND bd.admin_version IS NOT DISTINCT FROM m.admin_version
  $sql$;

  EXECUTE $sql$
    UPDATE ath.benchmark_dataset bd
    SET expected_ward_id = m.new_ward_id
    FROM mat.migration_remap_ward m
    WHERE bd.expected_ward_id IS NOT DISTINCT FROM m.old_ward_id
      AND bd.admin_version IS NOT DISTINCT FROM m.admin_version
  $sql$;
END
$bd$;

-- --------------------------------------------------------------------------- 6) ath.benchmark_run_result
DO $br$
BEGIN
  IF to_regclass('ath.benchmark_run_result') IS NULL THEN
    RAISE NOTICE 'Skip: ath.benchmark_run_result does not exist';
    RETURN;
  END IF;
  IF to_regclass('ath.benchmark_dataset') IS NULL THEN
    RAISE NOTICE 'Skip: ath.benchmark_run_result needs ath.benchmark_dataset (missing)';
    RETURN;
  END IF;

  EXECUTE $sql$
    UPDATE ath.benchmark_run_result br
    SET predicted_province_id = m.new_province_id
    FROM mat.migration_remap_province m, ath.benchmark_dataset bd
    WHERE bd.id = br.sample_id
      AND br.predicted_province_id IS NOT DISTINCT FROM m.old_province_id
      AND bd.admin_version IS NOT DISTINCT FROM m.admin_version
  $sql$;

  EXECUTE $sql$
    UPDATE ath.benchmark_run_result br
    SET predicted_district_id = m.new_district_id
    FROM mat.migration_remap_district m, ath.benchmark_dataset bd
    WHERE bd.id = br.sample_id
      AND br.predicted_district_id IS NOT DISTINCT FROM m.old_district_id
      AND bd.admin_version IS NOT DISTINCT FROM m.admin_version
  $sql$;

  EXECUTE $sql$
    UPDATE ath.benchmark_run_result br
    SET predicted_ward_id = m.new_ward_id
    FROM mat.migration_remap_ward m, ath.benchmark_dataset bd
    WHERE bd.id = br.sample_id
      AND br.predicted_ward_id IS NOT DISTINCT FROM m.old_ward_id
      AND bd.admin_version IS NOT DISTINCT FROM m.admin_version
  $sql$;
END
$br$;

-- OPTIONAL (review before uncomment): OSM narrow join by province_name
-- UPDATE osm.streets s ...

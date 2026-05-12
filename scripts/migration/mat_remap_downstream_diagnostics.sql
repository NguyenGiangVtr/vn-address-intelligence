-- =============================================================================
-- Diagnostics: why 20260512_mat_remap_downstream_business_ids.sql may update
-- 0 rows on prq.address_cleansing_queue.
--
-- Run in psql or any SQL client against the same DB.
--
-- Reading results
-- ---------------
-- If section (1) remap counts are all 0, then queries (2)–(5) are **expected**
-- to be 0 as well (no remap.old to join). Use section (0) baseline:
--   - queue_rows = 0           → no queue data (or wrong schema).
--   - remap_* = 0, mat_dup_* = 0 → no duplicate business ids left in mat;
--       downstream 0 rows is normal (nothing to remap / already applied).
--   - remap_* = 0, mat_dup_* > 0 → duplicates still in mat but remap log empty;
--       run 20260512_mat_remap_duplicate_business_ids.sql (must insert before
--       duplicates are removed), or restore DB snapshot from before dedupe.
--   - remap_* > 0, queue overlap = 0 → queue never references old_* ids from
--       remap (already updated, or different IDs than mat).
-- =============================================================================

-- 0) Baseline — still meaningful when remap tables are empty
SELECT
  '0_baseline' AS section,
  (SELECT COUNT(*)::bigint FROM prq.address_cleansing_queue) AS queue_rows,
  (SELECT COUNT(*)::bigint FROM mat.migration_remap_province) AS remap_province_rows,
  (SELECT COUNT(*)::bigint FROM mat.migration_remap_district) AS remap_district_rows,
  (SELECT COUNT(*)::bigint FROM mat.migration_remap_ward) AS remap_ward_rows,
  (
    SELECT COUNT(*)::bigint
    FROM (
      SELECT province_id
      FROM mat.province
      WHERE is_deleted = FALSE
      GROUP BY province_id
      HAVING COUNT(*) > 1
    ) s
  ) AS mat_dup_province_id_groups,
  (
    SELECT COUNT(*)::bigint
    FROM (
      SELECT district_id
      FROM mat.district
      WHERE is_deleted = FALSE
      GROUP BY district_id
      HAVING COUNT(*) > 1
    ) s
  ) AS mat_dup_district_id_groups,
  (
    SELECT COUNT(*)::bigint
    FROM (
      SELECT ward_id
      FROM mat.ward
      WHERE is_deleted = FALSE
      GROUP BY ward_id
      HAVING COUNT(*) > 1
    ) s
  ) AS mat_dup_ward_id_groups;

-- 1) Remap log population (empty => downstream queue updates stay 0 by design)
SELECT '1_remap_log' AS section, 'mat.migration_remap_province' AS tbl, COUNT(*)::bigint AS n
FROM mat.migration_remap_province
UNION ALL
SELECT '1_remap_log', 'mat.migration_remap_district', COUNT(*) FROM mat.migration_remap_district
UNION ALL
SELECT '1_remap_log', 'mat.migration_remap_ward', COUNT(*) FROM mat.migration_remap_ward;

-- 2) Queue rows whose denorm id still equals some remap "old" (needs non-empty remap)
SELECT
  '2_queue_denorm_in_remap_old' AS section,
  'province' AS level,
  COUNT(*)::bigint AS n
FROM prq.address_cleansing_queue q
WHERE EXISTS (
  SELECT 1 FROM mat.migration_remap_province m
  WHERE q.province_id IS NOT DISTINCT FROM m.old_province_id
)
UNION ALL
SELECT '2_queue_denorm_in_remap_old', 'district', COUNT(*)
FROM prq.address_cleansing_queue q
WHERE EXISTS (
  SELECT 1 FROM mat.migration_remap_district m
  WHERE q.district_id IS NOT DISTINCT FROM m.old_district_id
)
UNION ALL
SELECT '2_queue_denorm_in_remap_old', 'ward', COUNT(*)
FROM prq.address_cleansing_queue q
WHERE EXISTS (
  SELECT 1 FROM mat.migration_remap_ward m
  WHERE q.ward_id IS NOT DISTINCT FROM m.old_ward_id
);

-- 3) Rows that match the full downstream JOIN (should equal updated count)
SELECT
  '3_queue_province_full_join' AS section,
  COUNT(*)::bigint AS n
FROM prq.address_cleansing_queue q
JOIN mat.migration_remap_province m
  ON q.province_id IS NOT DISTINCT FROM m.old_province_id
JOIN mat.province pl ON pl.row_id = m.loser_row_id
WHERE q.old_province_id IS NOT DISTINCT FROM pl.old_id
   OR (q.old_province_id IS NULL AND pl.old_id IS NULL);

-- 4) Mismatch: denorm matches remap.old but lineage does not match loser old_id
SELECT
  '4_queue_province_lineage_mismatch' AS section,
  COUNT(*)::bigint AS n
FROM prq.address_cleansing_queue q
JOIN mat.migration_remap_province m
  ON q.province_id IS NOT DISTINCT FROM m.old_province_id
JOIN mat.province pl ON pl.row_id = m.loser_row_id
WHERE NOT (
  q.old_province_id IS NOT DISTINCT FROM pl.old_id
  OR (q.old_province_id IS NULL AND pl.old_id IS NULL)
);

-- 5) Sample mismatches (inspect old_province_id vs mat.province.old_id on loser)
SELECT
  '5_sample_lineage_mismatch' AS section,
  q.id AS queue_id,
  q.province_id,
  q.old_province_id,
  m.old_province_id AS remap_old,
  m.new_province_id AS remap_new,
  pl.old_id AS loser_mat_old_id
FROM prq.address_cleansing_queue q
JOIN mat.migration_remap_province m
  ON q.province_id IS NOT DISTINCT FROM m.old_province_id
JOIN mat.province pl ON pl.row_id = m.loser_row_id
WHERE NOT (
  q.old_province_id IS NOT DISTINCT FROM pl.old_id
  OR (q.old_province_id IS NULL AND pl.old_id IS NULL)
)
LIMIT 25;

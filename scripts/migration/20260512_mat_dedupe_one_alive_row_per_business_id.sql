-- =============================================================================
-- DEPRECATED — do not run.
--
-- This script soft-deleted duplicate mat rows (is_deleted = true). That violates
-- the rule: all rows remain valid per admin_version; duplicates are resolved by
-- remapping business ids, not deletion.
--
-- Use instead:
--   scripts/migration/20260512_mat_remap_duplicate_business_ids.sql
-- =============================================================================

SELECT 1 AS deprecated_do_not_run;

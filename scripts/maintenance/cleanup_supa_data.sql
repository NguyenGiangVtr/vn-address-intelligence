-- Cleanup SUPA benchmark data for fresh re-run
-- Run: python scripts/sql/apply_sql_file.py scripts/maintenance/cleanup_supa_data.sql

BEGIN;

-- Delete all stratified eval summary records
DELETE FROM ath.supa_stratified_eval_summary;

-- Delete all benchmark runs (CASCADE will delete specimens)
DELETE FROM prq.supa_benchmark_run;

COMMIT;

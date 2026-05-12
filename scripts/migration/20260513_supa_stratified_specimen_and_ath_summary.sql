-- SUPA stratified bench: specimen provenance + latency column; aggregate summary in ath.
-- Apply: python scripts/sql/apply_sql_file.py scripts/migration/20260513_supa_stratified_specimen_and_ath_summary.sql

BEGIN;

ALTER TABLE prq.supa_benchmark_specimen
    ADD COLUMN IF NOT EXISTS stratum_code TEXT;

ALTER TABLE prq.supa_benchmark_specimen
    ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION;

ALTER TABLE prq.supa_benchmark_specimen
    ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;

ALTER TABLE prq.supa_benchmark_specimen
    ADD COLUMN IF NOT EXISTS latency_ms DOUBLE PRECISION;

COMMENT ON COLUMN prq.supa_benchmark_specimen.stratum_code IS
    'Stratum for stratified SUPA: D1 urban-complex, D2 high-noise (profile SUP-D2), D3 temporal admin delta, D4 GPS-boundary proxy or PostGIS.';
COMMENT ON COLUMN prq.supa_benchmark_specimen.latitude IS
    'Copied from prq.ground_truth at extract (optional; used for D4 / reporting).';
COMMENT ON COLUMN prq.supa_benchmark_specimen.longitude IS
    'Copied from prq.ground_truth at extract (optional; used for D4 / reporting).';
COMMENT ON COLUMN prq.supa_benchmark_specimen.latency_ms IS
    'Per-specimen latency from normalization pipeline (optional; import-preds CSV column latency_ms).';

CREATE TABLE IF NOT EXISTS ath.supa_stratified_eval_summary (
    id                   BIGSERIAL PRIMARY KEY,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    methodology_version  TEXT NOT NULL,
    k_runs               INTEGER NOT NULL,
    n_per_run            INTEGER NOT NULL,
    run_id_min           BIGINT,
    run_id_max           BIGINT,
    metrics_json         JSONB NOT NULL,
    notes                TEXT,
    git_commit           TEXT
);

CREATE INDEX IF NOT EXISTS idx_supa_strat_eval_summary_created
    ON ath.supa_stratified_eval_summary (created_at DESC);

COMMENT ON TABLE ath.supa_stratified_eval_summary IS
    'One row per aggregate of stratified SUPA runs (K independent cohorts, eval_metrics_json rolled up).';

COMMIT;

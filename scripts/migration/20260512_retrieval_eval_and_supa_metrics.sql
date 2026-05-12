-- Retrieval eval history + SUPA per-run metrics (JSONB).
-- Apply: python scripts/sql/apply_sql_file.py scripts/migration/20260512_retrieval_eval_and_supa_metrics.sql

BEGIN;

CREATE SCHEMA IF NOT EXISTS ath;

CREATE TABLE IF NOT EXISTS ath.retrieval_eval_run (
    id              BIGSERIAL PRIMARY KEY,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    model_name      TEXT NOT NULL,
    limit_pairs     INTEGER NOT NULL,
    top_k_max       INTEGER NOT NULL,
    metrics_json    JSONB NOT NULL,
    notes           TEXT,
    git_commit      TEXT
);

COMMENT ON TABLE ath.retrieval_eval_run IS
    'One row per Siamese/mGTE retrieval evaluation run (R@k, MRR, NDCG, provenance in metrics_json).';

CREATE INDEX IF NOT EXISTS idx_retrieval_eval_run_created
    ON ath.retrieval_eval_run (created_at DESC);

ALTER TABLE prq.supa_benchmark_run
    ADD COLUMN IF NOT EXISTS eval_metrics_json JSONB;

COMMENT ON COLUMN prq.supa_benchmark_run.eval_metrics_json IS
    'Last SUPA eval metrics for this run (same payload as reports/supa_metrics_run_{id}.json).';

COMMIT;

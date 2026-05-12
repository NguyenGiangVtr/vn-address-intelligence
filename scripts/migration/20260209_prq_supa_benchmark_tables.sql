-- SUPA-Bench: Synthetic User-style Perturbation benchmark tables.
-- Rule: NEVER modify prq.ground_truth — only SELECT from it into these tables.
-- Apply on DB after standard schema prq exists.

BEGIN;

CREATE TABLE IF NOT EXISTS prq.supa_benchmark_run (
    id              BIGSERIAL PRIMARY KEY,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    n_requested     INTEGER NOT NULL,
    n_realized      INTEGER NOT NULL,
    rng_seed        BIGINT NOT NULL,
    noise_profile_id TEXT NOT NULL,
    source_schema   TEXT NOT NULL DEFAULT 'prq',
    source_table    TEXT NOT NULL DEFAULT 'ground_truth',
    git_commit      TEXT,
    notes           TEXT
);

COMMENT ON TABLE prq.supa_benchmark_run IS
    'SUPA-Bench run metadata: reproducible cohort from prq.ground_truth (read-only extract).';

CREATE TABLE IF NOT EXISTS prq.supa_benchmark_specimen (
    id                   BIGSERIAL PRIMARY KEY,
    run_id               BIGINT NOT NULL REFERENCES prq.supa_benchmark_run (id) ON DELETE CASCADE,
    local_idx            INTEGER NOT NULL,
    ground_truth_id      BIGINT NOT NULL,
    ref_address_v2       TEXT NOT NULL,
    ref_address_v1       TEXT NOT NULL,
    noisy_raw_address    TEXT,
    pred_standardized    TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_supa_specimen_run_idx UNIQUE (run_id, local_idx),
    CONSTRAINT uq_supa_specimen_run_gt UNIQUE (run_id, ground_truth_id)
);

COMMENT ON TABLE prq.supa_benchmark_specimen IS
    'One row per benchmark specimen: frozen refs from ground_truth, noisy input, optional pipeline output.';

CREATE INDEX IF NOT EXISTS idx_supa_specimen_run ON prq.supa_benchmark_specimen (run_id);

COMMIT;

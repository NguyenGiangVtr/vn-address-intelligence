-- =============================================================================
-- add_prelabeler_random_predict_norm_indexes.sql
-- Optimize /api/prelabeler-cases/random-predict anti-join by precomputing
-- normalized raw address and indexing both sides.
-- Idempotent for PostgreSQL 12+.
-- =============================================================================

BEGIN;

-- Queue side: normalized raw address (for probe side of anti-join).
ALTER TABLE prq.address_cleansing_queue
    ADD COLUMN IF NOT EXISTS raw_address_norm text
    GENERATED ALWAYS AS (NULLIF(LOWER(BTRIM(raw_address)), '')) STORED;

-- Testcase side: normalized input raw address (supports both legacy string input
-- and object input {"raw_address": "..."}).
ALTER TABLE ai.prelabeler_testcases
    ADD COLUMN IF NOT EXISTS input_raw_address_norm text
    GENERATED ALWAYS AS (
        NULLIF(
            LOWER(
                BTRIM(
                    CASE
                        WHEN input IS NULL THEN ''
                        WHEN jsonb_typeof(input) = 'string' THEN BTRIM(input::text, '"')
                        WHEN jsonb_typeof(input) = 'object' THEN COALESCE(input->>'raw_address', '')
                        ELSE ''
                    END
                )
            ),
            ''
        )
    ) STORED;

CREATE INDEX IF NOT EXISTS idx_acq_raw_address_norm
    ON prq.address_cleansing_queue (raw_address_norm);

CREATE INDEX IF NOT EXISTS idx_prelabeler_testcases_input_raw_address_norm
    ON ai.prelabeler_testcases (input_raw_address_norm);

COMMIT;


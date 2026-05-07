-- =============================================================================
-- add_queue_acs_address_epoch_columns.sql
-- Adds columns required by app/ai/production_pipeline.py when writing ACS and
-- epoch outputs (ORM documents these; DB may lag until this migration runs).
-- Idempotent: uses IF NOT EXISTS (PostgreSQL 11+).
-- =============================================================================

BEGIN;

ALTER TABLE prq.address_cleansing_queue
    ADD COLUMN IF NOT EXISTS acs_score numeric(5, 4),
    ADD COLUMN IF NOT EXISTS acs_decision varchar(20),
    ADD COLUMN IF NOT EXISTS s_text numeric(5, 4),
    ADD COLUMN IF NOT EXISTS s_sem numeric(5, 4),
    ADD COLUMN IF NOT EXISTS v_hierarchy numeric(5, 4),
    ADD COLUMN IF NOT EXISTS v_temporal numeric(5, 4),
    ADD COLUMN IF NOT EXISTS address_epoch varchar(20);

COMMIT;

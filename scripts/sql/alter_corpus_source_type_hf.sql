-- =============================================================================
-- alter_corpus_source_type_hf.sql
-- Phase 1.1 — Extend prq.address_clean_corpus.source_type CHECK constraint
-- to allow 'HF_NER_DERIVED' so we can ingest unique (street, ward) pairs
-- extracted from the Hugging Face NER corpus.
--
-- Idempotent: safe to run multiple times. Only modifies the CHECK constraint;
-- no data is affected.
-- =============================================================================

BEGIN;

ALTER TABLE prq.address_clean_corpus
    DROP CONSTRAINT IF EXISTS check_source_type;

ALTER TABLE prq.address_clean_corpus
    ADD CONSTRAINT check_source_type
    CHECK (source_type IN (
        'ADMINISTRATIVE',
        'QUEUE_STANDARDIZED',
        'MANUAL_CURATED',
        'HF_NER_DERIVED'
    ));

COMMIT;

-- Verify
-- SELECT conname, pg_get_constraintdef(oid)
-- FROM pg_constraint
-- WHERE conrelid = 'prq.address_clean_corpus'::regclass
--   AND conname = 'check_source_type';

-- Remove duplicated corpus records by unique key contract.
-- Keep the latest updated row for each (standardized_address, admin_epoch, source_type).

WITH ranked AS (
    SELECT
        id,
        ROW_NUMBER() OVER (
            PARTITION BY standardized_address, admin_epoch, source_type
            ORDER BY updated_at DESC NULLS LAST, created_at DESC NULLS LAST, id DESC
        ) AS rn
    FROM prq.address_clean_corpus
)
DELETE FROM prq.address_clean_corpus c
USING ranked r
WHERE c.id = r.id
  AND r.rn > 1;

ALTER TABLE prq.address_clean_corpus
    DROP CONSTRAINT IF EXISTS unique_standardized_address_epoch;

ALTER TABLE prq.address_clean_corpus
    ADD CONSTRAINT unique_standardized_address_epoch
    UNIQUE (standardized_address, admin_epoch, source_type);

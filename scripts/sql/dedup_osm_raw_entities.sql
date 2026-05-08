-- Deduplicate historical data in osm.raw_entities by semantic content.
-- Keep the earliest row (created_at, then id) for each duplicate group.
-- Duplicate key definition:
--   (osm_type, province_id, province_name(normalized), tags::jsonb)

BEGIN;

WITH ranked AS (
    SELECT
        id,
        ROW_NUMBER() OVER (
            PARTITION BY
                osm_type,
                province_id,
                lower(trim(coalesce(province_name, ''))),
                (tags::jsonb)
            ORDER BY
                created_at ASC NULLS FIRST,
                id ASC
        ) AS rn
    FROM osm.raw_entities
),
to_delete AS (
    SELECT id
    FROM ranked
    WHERE rn > 1
)
DELETE FROM osm.raw_entities r
USING to_delete d
WHERE r.id = d.id;

-- Prevent re-insert of semantically duplicated rows in the future.
-- Unique expression index uses a stable fingerprint for tags.
CREATE UNIQUE INDEX IF NOT EXISTS ux_osm_raw_entities_semantic
ON osm.raw_entities (
    osm_type,
    province_id,
    lower(trim(coalesce(province_name, ''))),
    md5((tags::jsonb)::text)
);

COMMIT;

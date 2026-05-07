-- Ground truth: column comments, admin resolution VIEW, sync metadata (idempotent fragments).
-- Run against PostgreSQL after prq.ground_truth exists.

-- ---------------------------------------------------------------------------
-- Optional: sync run log + row-level last touch (Typesense crawl audit)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ath.typesense_ground_truth_sync_run (
    id              SERIAL PRIMARY KEY,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    collection      TEXT NOT NULL,
    records_scanned INT DEFAULT 0,
    records_upserted INT DEFAULT 0,
    filter_province_id INT,
    notes           TEXT
);

CREATE INDEX IF NOT EXISTS idx_typesense_gt_sync_run_started
    ON ath.typesense_ground_truth_sync_run (started_at DESC);

ALTER TABLE prq.ground_truth
    ADD COLUMN IF NOT EXISTS last_sync_run_id INTEGER REFERENCES ath.typesense_ground_truth_sync_run(id);
ALTER TABLE prq.ground_truth
    ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_ground_truth_last_seen ON prq.ground_truth (last_seen_at DESC);

-- ---------------------------------------------------------------------------
-- Column comments (IDs are lineage / old_id namespace — join mat.*.old_id + admin_version)
-- ---------------------------------------------------------------------------
COMMENT ON TABLE prq.ground_truth IS
    'Chuẩn tham chiếu địa chỉ (Typesense/Google/manual). province_id/district_id/ward_id là mã cùng không gian với mat.*.old_id sau ánh xạ (join mat với admin_version=2). old_* là lineage tiền cải cách (join mat với admin_version=1).';

COMMENT ON COLUMN prq.ground_truth.id IS 'PK; thường trùng document id Typesense.';
COMMENT ON COLUMN prq.ground_truth.province_id IS 'Lineage post-reform: join mat.province.old_id WHERE admin_version = 2 (và is_deleted).';
COMMENT ON COLUMN prq.ground_truth.district_id IS 'Lineage post-reform: join mat.district.old_id WHERE admin_version = 2.';
COMMENT ON COLUMN prq.ground_truth.ward_id IS 'Lineage post-reform: join mat.ward.old_id WHERE admin_version = 2.';
COMMENT ON COLUMN prq.ground_truth.old_province_id IS 'Lineage pre-reform: join mat.province.old_id WHERE admin_version = 1.';
COMMENT ON COLUMN prq.ground_truth.old_district_id IS 'Lineage pre-reform: join mat.district.old_id WHERE admin_version = 1.';
COMMENT ON COLUMN prq.ground_truth.old_ward_id IS 'Lineage pre-reform: join mat.ward.old_id WHERE admin_version = 1.';
COMMENT ON COLUMN prq.ground_truth.last_sync_run_id IS 'Khóa tới ath.typesense_ground_truth_sync_run — lần crawl gần nhất ghi nhận bản ghi này.';
COMMENT ON COLUMN prq.ground_truth.last_seen_at IS 'Thời điểm bản ghi được upsert từ Typesense lần cuối.';

-- ---------------------------------------------------------------------------
-- VIEW: one row GT + tên đơn vị HC v1 (pre-reform) và v2 (post-reform)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW prq.v_ground_truth_admin AS
SELECT
    gt.id,
    gt.address,
    gt.old_address,
    gt.address_eng,
    gt.old_address_eng,
    gt.latitude,
    gt.longitude,
    gt.popular,
    gt.source_system,
    gt.data_quality_score,
    gt.is_validated,
    gt.created_at,
    gt.updated_at,
    gt.last_sync_run_id,
    gt.last_seen_at,
    -- Post-reform (admin_version = 2)
    gt.province_id   AS province_id_post,
    gt.district_id   AS district_id_post,
    gt.ward_id       AS ward_id_post,
    p2.province_name AS province_name_post,
    d2.district_name AS district_name_post,
    w2.ward_name     AS ward_name_post,
    -- Pre-reform (admin_version = 1)
    gt.old_province_id AS province_id_pre,
    gt.old_district_id AS district_id_pre,
    gt.old_ward_id     AS ward_id_pre,
    p.province_name   AS province_name_pre,
    d.district_name   AS district_name_pre,
    w.ward_name       AS ward_name_pre
FROM prq.ground_truth gt
LEFT JOIN mat.province p ON gt.old_province_id = p.old_id
    AND p.is_deleted = FALSE AND p.admin_version = 1
LEFT JOIN mat.district d ON gt.old_district_id = d.old_id
    AND d.is_deleted = FALSE AND (d.is_active IS NOT DISTINCT FROM TRUE) AND d.admin_version = 1
LEFT JOIN mat.ward w ON gt.old_ward_id = w.old_id
    AND w.is_deleted = FALSE AND (w.is_active IS NOT DISTINCT FROM TRUE) AND w.admin_version = 1
LEFT JOIN mat.province p2 ON gt.province_id = p2.old_id
    AND p2.is_deleted = FALSE AND p2.admin_version = 2
LEFT JOIN mat.district d2 ON gt.district_id = d2.old_id
    AND d2.is_deleted = FALSE AND (d2.is_active IS NOT DISTINCT FROM TRUE) AND d2.admin_version = 2
LEFT JOIN mat.ward w2 ON gt.ward_id = w2.old_id
    AND w2.is_deleted = FALSE AND (w2.is_active IS NOT DISTINCT FROM TRUE) AND w2.admin_version = 2;

COMMENT ON VIEW prq.v_ground_truth_admin IS
    'Ground truth kèm tên P/D/Xã: v1 = old_* + mat admin_version=1; v2 = province_id/district_id/ward_id + mat admin_version=2. LEFT JOIN để vẫn thấy bản ghi thiếu khớp master.';

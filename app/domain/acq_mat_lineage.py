"""
Canonical business join: queue administrative lineage ↔ mat.* masters (admin_version = 1).

Queue columns `old_province_id`, `old_district_id`, `old_ward_id` match `mat.*.old_id`
with `admin_version = 1` (see project rule `address-queue-mat-lineage`).

Prefer this over joining `province_id` / `district_id` / `ward_id` on the queue when resolving
meaning against master administrative data. For denormed IDs on the queue, always join `mat` with
matching `admin_version`; use `COUNT(DISTINCT acq.id)` in diagnostics when the same business id
can appear in more than one mat row (e.g. v1 + v2). Current master slices use `is_active` (not
`is_current`, removed from schema after migration `20260512_mat_is_active_drop_is_current.sql`).
"""

from __future__ import annotations

# Contractual predicates (match business SQL exactly)
# Prefer one active v1 master per old_id (is_deleted / is_active).
JOIN_QUEUE_PROVINCE_V1_LINEAGE = (
    "JOIN mat.province p ON acq.old_province_id = p.old_id AND p.admin_version = 1 "
    "AND COALESCE(p.is_deleted, FALSE) = FALSE AND COALESCE(p.is_active, TRUE) = TRUE"
)
JOIN_QUEUE_DISTRICT_V1_LINEAGE = (
    "JOIN mat.district d ON acq.old_district_id = d.old_id AND d.admin_version = 1 "
    "AND COALESCE(d.is_deleted, FALSE) = FALSE AND COALESCE(d.is_active, TRUE) = TRUE"
)
JOIN_QUEUE_WARD_V1_LINEAGE = (
    "JOIN mat.ward w ON acq.old_ward_id = w.old_id AND w.admin_version = 1 "
    "AND COALESCE(w.is_deleted, FALSE) = FALSE AND COALESCE(w.is_active, TRUE) = TRUE"
)


def sql_count_queue_rows_full_lineage_v1_resolution() -> str:
    """INNER joins — discrete queue rows whose lineage resolves to three v1 masters (DISTINCT acq.id)."""
    return (
        "SELECT COUNT(DISTINCT acq.id)::bigint AS queue_rows_matching_lineage_triple_v1_master\n"
        "FROM prq.address_cleansing_queue AS acq\n"
        f"{JOIN_QUEUE_PROVINCE_V1_LINEAGE}\n"
        f"{JOIN_QUEUE_DISTRICT_V1_LINEAGE}\n"
        f"{JOIN_QUEUE_WARD_V1_LINEAGE}\n"
    ).strip()

"""Read-only diagnostics: queue lineage vs mat, ward_mapping (canonical old_* joins)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[2]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from sqlalchemy import text

from app.core.database import engine
from app.domain.acq_mat_lineage import sql_count_queue_rows_full_lineage_v1_resolution


def _configure_stdout_utf8() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _safe_print_blob(obj: object) -> None:
    payload = json.dumps(obj, indent=2, ensure_ascii=False)
    try:
        print(payload, flush=True)
    except UnicodeEncodeError:
        print(json.dumps(obj, indent=2, ensure_ascii=True), flush=True)


def main() -> None:
    _configure_stdout_utf8()
    print("Connecting...", flush=True)

    snippets: list[tuple[str, str]] = [
        (
            "queue_overview",
            """
            SELECT COUNT(*) AS total_rows,
                   COUNT(*) FILTER (WHERE old_province_id IS NULL) AS null_old_province,
                   COUNT(*) FILTER (WHERE old_district_id IS NULL) AS null_old_district,
                   COUNT(*) FILTER (WHERE old_ward_id IS NULL) AS null_old_ward,
                   COUNT(*) FILTER (WHERE province_id IS NULL) AS null_denorm_province,
                   COUNT(*) FILTER (WHERE district_id IS NULL) AS null_denorm_district,
                   COUNT(*) FILTER (WHERE ward_id IS NULL) AS null_denorm_ward,
                   COUNT(DISTINCT province_id) AS distinct_denorm_province_id,
                   COUNT(DISTINCT district_id) AS distinct_denorm_district_id,
                   COUNT(DISTINCT ward_id) AS distinct_denorm_ward_id
            FROM prq.address_cleansing_queue
            """,
        ),
        (
            "lineage_provinceResolvable_rowCount",
            """
            SELECT COUNT(DISTINCT acq.id)::bigint AS distinct_queue_rows_match_province_lineage_v1
            FROM prq.address_cleansing_queue acq
            JOIN mat.province p ON acq.old_province_id = p.old_id AND p.admin_version = 1
              AND COALESCE(p.is_deleted, FALSE) = FALSE AND COALESCE(p.is_current, TRUE) = TRUE
            """,
        ),
        (
            "lineage_districtResolvable_rowCount",
            """
            SELECT COUNT(DISTINCT acq.id)::bigint AS distinct_queue_rows_match_district_lineage_v1
            FROM prq.address_cleansing_queue acq
            JOIN mat.district d ON acq.old_district_id = d.old_id AND d.admin_version = 1
              AND COALESCE(d.is_deleted, FALSE) = FALSE AND COALESCE(d.is_current, TRUE) = TRUE
            """,
        ),
        (
            "lineage_wardResolvable_rowCount",
            """
            SELECT COUNT(DISTINCT acq.id)::bigint AS distinct_queue_rows_match_ward_lineage_v1
            FROM prq.address_cleansing_queue acq
            JOIN mat.ward w ON acq.old_ward_id = w.old_id AND w.admin_version = 1
              AND COALESCE(w.is_deleted, FALSE) = FALSE AND COALESCE(w.is_current, TRUE) = TRUE
            """,
        ),
        (
            "mat_v1_duplicate_old_id_smoke",
            """
            SELECT 'province'::text AS rel,
                   (SELECT COUNT(*) FROM (
                     SELECT old_id FROM mat.province WHERE admin_version = 1 AND old_id IS NOT NULL
                     GROUP BY old_id HAVING COUNT(*) > 1
                   ) t)::bigint AS duplicate_old_id_keys
            UNION ALL
            SELECT 'district',
                   (SELECT COUNT(*) FROM (
                     SELECT old_id FROM mat.district WHERE admin_version = 1 AND old_id IS NOT NULL
                     GROUP BY old_id HAVING COUNT(*) > 1
                   ) t)::bigint
            UNION ALL
            SELECT 'ward',
                   (SELECT COUNT(*) FROM (
                     SELECT old_id FROM mat.ward WHERE admin_version = 1 AND old_id IS NOT NULL
                     GROUP BY old_id HAVING COUNT(*) > 1
                   ) t)::bigint
            """,
        ),
        (
            "lineage_triple_inner_join_rowCount_CANONICAL",
            sql_count_queue_rows_full_lineage_v1_resolution(),
        ),
        (
            "fk_snapshot_admin_histogram_denorm_FK_DIAGNOSTIC",
            """
            SELECT 'Province'::text AS level, p.admin_version::text AS av,
                   COUNT(DISTINCT acq.id)::bigint AS queue_rows
            FROM prq.address_cleansing_queue acq JOIN mat.province p ON acq.province_id = p.province_id
              AND COALESCE(p.is_deleted, FALSE) = FALSE
            GROUP BY p.admin_version
            UNION ALL
            SELECT 'District', d.admin_version::text, COUNT(DISTINCT acq.id)::bigint
            FROM prq.address_cleansing_queue acq JOIN mat.district d ON acq.district_id = d.district_id
              AND COALESCE(d.is_deleted, FALSE) = FALSE
            GROUP BY d.admin_version
            UNION ALL
            SELECT 'Ward', w.admin_version::text, COUNT(DISTINCT acq.id)::bigint
            FROM prq.address_cleansing_queue acq JOIN mat.ward w ON acq.ward_id = w.ward_id
              AND COALESCE(w.is_deleted, FALSE) = FALSE
            GROUP BY w.admin_version
            ORDER BY level, av
            """,
        ),
        (
            "mat_old_id_fill_rate_current_only",
            """
            SELECT 'province'::text AS rel, p.admin_version::text AS av,
                   COUNT(*)::bigint AS rows,
                   COUNT(old_id)::bigint AS with_old_id
            FROM mat.province p
            WHERE COALESCE(p.is_deleted, FALSE) = FALSE AND p.is_current = TRUE
            GROUP BY p.admin_version
            UNION ALL
            SELECT 'district', d.admin_version::text,
                   COUNT(*)::bigint, COUNT(d.old_id)::bigint
            FROM mat.district d
            WHERE COALESCE(d.is_deleted, FALSE) = FALSE AND d.is_current = TRUE
            GROUP BY d.admin_version
            UNION ALL
            SELECT 'ward', w.admin_version::text,
                   COUNT(*)::bigint, COUNT(w.old_id)::bigint
            FROM mat.ward w
            WHERE COALESCE(w.is_deleted, FALSE) = FALSE AND w.is_current = TRUE
            GROUP BY w.admin_version
            ORDER BY rel, av
            """,
        ),
        (
            "ward_mapping_inventory",
            """
            SELECT COUNT(*)::bigint AS total_rows,
                   COUNT(*) FILTER (
                     WHERE ward_id_old IS NOT NULL AND ward_id_new IS NOT NULL
                       AND COALESCE(is_deleted, FALSE) = FALSE
                   )::bigint AS active_old_new_pairs
            FROM mat.ward_mapping
            """,
        ),
        (
            "distinct_lineage_v1_wards_and_ward_mapping_overlap",
            """
            WITH lw AS (
              SELECT DISTINCT wl.ward_id AS ward_id_lineage_v1
              FROM prq.address_cleansing_queue acq
              JOIN mat.ward wl ON acq.old_ward_id = wl.old_id AND wl.admin_version = 1
                AND COALESCE(wl.is_deleted, FALSE) = FALSE AND COALESCE(wl.is_current, TRUE) = TRUE
            )
            SELECT COUNT(*)::bigint AS distinct_lineage_v1_ward_ids,
                   COUNT(*) FILTER (
                     WHERE EXISTS (
                       SELECT 1 FROM mat.ward_mapping wm
                       WHERE wm.ward_id_old = lw.ward_id_lineage_v1
                         AND wm.ward_id_new IS NOT NULL
                         AND COALESCE(wm.is_deleted, FALSE) = FALSE
                     )
                   )::bigint AS lineage_wards_hit_ward_mapping
            FROM lw
            """,
        ),
        (
            "queue_rows_ward_mapping_via_lineage_ward_id",
            """
            WITH per_acq AS (
              SELECT acq.id,
                     bool_or(
                       wm.ward_id_new IS NOT NULL
                       AND COALESCE(wm.is_deleted, FALSE) = FALSE
                     ) AS has_ward_mapping
              FROM prq.address_cleansing_queue acq
              JOIN mat.ward wl ON acq.old_ward_id = wl.old_id AND wl.admin_version = 1
                AND COALESCE(wl.is_deleted, FALSE) = FALSE AND COALESCE(wl.is_current, TRUE) = TRUE
              LEFT JOIN mat.ward_mapping wm ON wm.ward_id_old = wl.ward_id
              WHERE acq.old_ward_id IS NOT NULL
              GROUP BY acq.id
            )
            SELECT COUNT(*)::bigint AS queue_rows_non_null_old_ward,
                   COUNT(*) FILTER (WHERE has_ward_mapping)::bigint
                     AS rows_with_mapping_for_lineage_v1_ward
            FROM per_acq
            """,
        ),
        (
            "denorm_alignment_same_admin_version_and_hierarchy",
            """
            WITH base AS (
              SELECT id, province_id, district_id, ward_id
              FROM prq.address_cleansing_queue
              WHERE province_id IS NOT NULL
                AND district_id IS NOT NULL
                AND ward_id IS NOT NULL
            ),
            aligned AS (
              SELECT DISTINCT acq.id
              FROM prq.address_cleansing_queue acq
              INNER JOIN mat.province p
                ON p.province_id = acq.province_id
                AND COALESCE(p.is_deleted, FALSE) = FALSE
              INNER JOIN mat.district d
                ON d.district_id = acq.district_id
                AND d.admin_version = p.admin_version
                AND d.province_id = acq.province_id
                AND COALESCE(d.is_deleted, FALSE) = FALSE
              INNER JOIN mat.ward w
                ON w.ward_id = acq.ward_id
                AND w.admin_version = p.admin_version
                AND w.district_id = acq.district_id
                AND COALESCE(w.is_deleted, FALSE) = FALSE
              WHERE acq.province_id IS NOT NULL
                AND acq.district_id IS NOT NULL
                AND acq.ward_id IS NOT NULL
            ),
            aligned_current AS (
              SELECT DISTINCT acq.id
              FROM prq.address_cleansing_queue acq
              INNER JOIN mat.province p
                ON p.province_id = acq.province_id
                AND COALESCE(p.is_deleted, FALSE) = FALSE
                AND COALESCE(p.is_current, TRUE) = TRUE
              INNER JOIN mat.district d
                ON d.district_id = acq.district_id
                AND d.admin_version = p.admin_version
                AND d.province_id = acq.province_id
                AND COALESCE(d.is_deleted, FALSE) = FALSE
                AND COALESCE(d.is_current, TRUE) = TRUE
              INNER JOIN mat.ward w
                ON w.ward_id = acq.ward_id
                AND w.admin_version = p.admin_version
                AND w.district_id = acq.district_id
                AND COALESCE(w.is_deleted, FALSE) = FALSE
                AND COALESCE(w.is_current, TRUE) = TRUE
              WHERE acq.province_id IS NOT NULL
                AND acq.district_id IS NOT NULL
                AND acq.ward_id IS NOT NULL
            )
            SELECT
              (SELECT COUNT(*)::bigint FROM prq.address_cleansing_queue) AS total_queue_rows,
              (SELECT COUNT(*)::bigint FROM base) AS rows_with_all_three_denorm_fk,
              (SELECT COUNT(*)::bigint FROM aligned) AS rows_aligned_same_av_hierarchy,
              (SELECT COUNT(*)::bigint FROM aligned_current)
                AS rows_aligned_same_av_hierarchy_current_only,
              (SELECT COUNT(*)::bigint FROM base)
                - (SELECT COUNT(*)::bigint FROM aligned) AS rows_fail_alignment_or_hierarchy
            """,
        ),
        (
            "denorm_version_tuple_histogram_ambiguous_join",
            """
            SELECT p.admin_version AS province_av,
                   d.admin_version AS district_av,
                   w.admin_version AS ward_av,
                   COUNT(DISTINCT acq.id)::bigint AS distinct_queue_rows
            FROM prq.address_cleansing_queue acq
            JOIN mat.province p
              ON acq.province_id = p.province_id
              AND COALESCE(p.is_deleted, FALSE) = FALSE
            JOIN mat.district d
              ON acq.district_id = d.district_id
              AND COALESCE(d.is_deleted, FALSE) = FALSE
            JOIN mat.ward w
              ON acq.ward_id = w.ward_id
              AND COALESCE(w.is_deleted, FALSE) = FALSE
            WHERE acq.province_id IS NOT NULL
              AND acq.district_id IS NOT NULL
              AND acq.ward_id IS NOT NULL
            GROUP BY p.admin_version, d.admin_version, w.admin_version
            ORDER BY distinct_queue_rows DESC, province_av, district_av, ward_av
            """,
        ),
    ]

    results: dict = {}
    with engine.connect() as c:
        for title, sql in snippets:
            print(f"Running: {title}...", flush=True)
            rows = c.execute(text(sql)).mappings().all()
            results[title] = [dict(x) for x in rows]
            for r in rows:
                print(f"  {dict(r)}", flush=True)

    overview = (results.get("queue_overview") or [{}])[0]
    canonical = (
        results.get("lineage_triple_inner_join_rowCount_CANONICAL") or [{}]
    )[0]
    total_rows = float(overview.get("total_rows") or 0)
    triple_ok = float(canonical.get("queue_rows_matching_lineage_triple_v1_master") or 0)
    pct_triple = round(100.0 * triple_ok / total_rows, 2) if total_rows else 0.0

    wm_lin = (
        results.get("queue_rows_ward_mapping_via_lineage_ward_id") or [{}]
    )[0]
    q_wm = float(wm_lin.get("queue_rows_non_null_old_ward") or 0)
    m_wm = float(wm_lin.get("rows_with_mapping_for_lineage_v1_ward") or 0)
    pct_wm_lineage_rows = round(100.0 * m_wm / q_wm, 2) if q_wm else 0.0

    lw_ov = (
        results.get("distinct_lineage_v1_wards_and_ward_mapping_overlap") or [{}]
    )[0]
    dl = float(lw_ov.get("distinct_lineage_v1_ward_ids") or 0)
    hit = float(lw_ov.get("lineage_wards_hit_ward_mapping") or 0)
    pct_lineage_distinct_in_wm = round(100.0 * hit / dl, 2) if dl else 0.0

    decision = {
        "pct_queue_rows_matching_lineage_triple_v1_MASTER": pct_triple,
        "pct_queue_rows_with_old_ward_mapped_via_ward_mapping_lineageWARD": pct_wm_lineage_rows,
        "pct_distinct_lineage_v1_wards_in_mat_ward_mapping": pct_lineage_distinct_in_wm,
        "recommended_path": [],
        "avoid_using_denormalized_FK_join_for_master_semantics_without_fallback": True,
        "canonical_join_note": (
            ".cursor/rules/address-queue-mat-lineage.mdc "
            "| app/domain/acq_mat_lineage.py"
        ),
    }

    if pct_triple >= 95:
        decision["recommended_path"].append(
            "Lineage triple coverage is healthy; INNER join lineage for analytics/tests."
        )
    elif pct_triple >= 70:
        decision["recommended_path"].append(
            "Repair NULL/mismatched old_* lineage vs mat.old_id until triple coverage climbs."
        )
    else:
        decision["recommended_path"].append(
            "Low lineage triple coverage; prioritize back-fill of lineage keys."
        )

    if pct_wm_lineage_rows >= 40 or pct_lineage_distinct_in_wm >= 40:
        decision["recommended_path"].append(
            "Use mat.ward_mapping keyed by lineage v1 ward_id (wl from old_ward_id->mat.old_id)."
        )

    print("\n=== DECISION (data-driven) ===", flush=True)
    _safe_print_blob(decision)

    # --- Explicit gates: admin_version alignment (denorm P/D/W) ---
    dup_rows = results.get("mat_v1_duplicate_old_id_smoke") or []
    dup_pass = all(int(r.get("duplicate_old_id_keys") or 0) == 0 for r in dup_rows)

    align_row = (results.get("denorm_alignment_same_admin_version_and_hierarchy") or [{}])[0]
    total_q = int(align_row.get("total_queue_rows") or 0)
    three_fk = int(align_row.get("rows_with_all_three_denorm_fk") or 0)
    aligned_ok = int(align_row.get("rows_aligned_same_av_hierarchy") or 0)
    aligned_cur = int(align_row.get("rows_aligned_same_av_hierarchy_current_only") or 0)
    fail_align = int(align_row.get("rows_fail_alignment_or_hierarchy") or 0)
    pct_aligned = (
        round(100.0 * aligned_ok / three_fk, 2) if three_fk else None
    )
    pct_aligned_cur = (
        round(100.0 * aligned_cur / three_fk, 2) if three_fk else None
    )

    triple_pct = float(decision["pct_queue_rows_matching_lineage_triple_v1_MASTER"])
    lineage_pass = triple_pct >= 99.9

    denorm_pass = three_fk == 0 or fail_align == 0
    denorm_current_pass = three_fk == 0 or (aligned_cur == three_fk)

    gates = {
        "G1_mat_v1_duplicate_old_id_all_zero": {
            "pass": dup_pass,
            "detail": dup_rows,
        },
        "G2_lineage_triple_inner_coverage_pct_ge_99_9": {
            "pass": lineage_pass,
            "pct": triple_pct,
        },
        "G3_denorm_P_D_W_same_admin_version_and_geo_hierarchy": {
            "pass": denorm_pass,
            "rows_all_three_fk": three_fk,
            "rows_aligned": aligned_ok,
            "rows_failed": fail_align,
            "pct_aligned_of_three_fk": pct_aligned,
            "note": (
                "exists mat rows p,d,w with equal admin_version, "
                "d.province_id=queue.province_id, w.district_id=queue.district_id"
            ),
        },
        "G4_denorm_aligned_also_is_current_on_all_three": {
            "pass": denorm_current_pass,
            "rows_all_three_fk": three_fk,
            "rows_aligned_current": aligned_cur,
            "pct_aligned_current_of_three_fk": pct_aligned_cur,
        },
    }
    print("\n=== GATES (PASS / FAIL) — admin_version & lineage ===", flush=True)
    _safe_print_blob(gates)
    print(
        "\nNote: denorm_version_tuple_histogram_ambiguous_join — "
        "sum of buckets can exceed queue rows if same business id exists "
        "under multiple mat.admin_version (one queue row matches several tuples).",
        flush=True,
    )


if __name__ == "__main__":
    main()

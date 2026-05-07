"""Phase 4.2 — Audit pilot run results against prq.ground_truth.

Compares the most recently DONE rows in prq.address_cleansing_queue against
the ground-truth standard for the same raw_address, computing exact-match
percentage, mean confidences, and ACS decision distribution.

Usage:
    python scripts/diagnostics/audit_pilot_vs_gt.py --window-minutes 30 --limit 1000
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

from app.core.database import engine

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

LOGGER = logging.getLogger("audit_pilot_vs_gt")


def _normalize_for_compare(s: str | None) -> str:
    if not s:
        return ""
    out = s.lower().strip()
    out = " ".join(out.split())
    return out.rstrip(", ")


def run(window_minutes: int = 30, limit: int = 1000, output: str | None = None) -> dict:
    sql = text(
        f"""
        SELECT
            q.id,
            q.raw_address,
            q.address_standardized,
            q.processing_status,
            q.processing_method,
            q.error_message,
            q.phobert_confidence_score,
            q.mgte_confidence_score,
            q.acs_score,
            q.acs_decision,
            q.address_epoch,
            q.latitude AS q_lat,
            q.longitude AS q_lon,
            g.address AS gt_address,
            g.latitude AS gt_lat,
            g.longitude AS gt_lon
        FROM prq.address_cleansing_queue q
        LEFT JOIN prq.ground_truth g ON g.old_address = q.raw_address
        WHERE q.updated_at > now() - interval '{int(window_minutes)} minutes'
          AND q.processing_status IN ('DONE','ERROR','COMPLETED')
        ORDER BY q.updated_at DESC
        LIMIT :limit
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"limit": int(limit)}).mappings().all()

    LOGGER.info("Audit pulled %d recent rows from queue", len(rows))

    total = len(rows)
    matched = 0
    has_gt = 0
    error_rows = 0
    sum_phobert = 0.0
    n_phobert = 0
    sum_mgte = 0.0
    n_mgte = 0
    sum_acs = 0.0
    n_acs = 0
    decision_counts: dict[str, int] = {}
    epoch_counts: dict[str, int] = {}
    lat_lon_filled = 0
    diff_examples: list[dict] = []

    for r in rows:
        if r["processing_status"] == "ERROR":
            error_rows += 1
        if r.get("phobert_confidence_score") is not None:
            sum_phobert += float(r["phobert_confidence_score"])
            n_phobert += 1
        if r.get("mgte_confidence_score") is not None:
            sum_mgte += float(r["mgte_confidence_score"])
            n_mgte += 1
        if r.get("acs_score") is not None:
            sum_acs += float(r["acs_score"])
            n_acs += 1
        decision = r.get("acs_decision") or "NULL"
        decision_counts[decision] = decision_counts.get(decision, 0) + 1
        epoch = r.get("address_epoch") or "NULL"
        epoch_counts[epoch] = epoch_counts.get(epoch, 0) + 1
        if r.get("q_lat") is not None and r.get("q_lon") is not None:
            lat_lon_filled += 1
        if r.get("gt_address"):
            has_gt += 1
            if _normalize_for_compare(r["address_standardized"]) == _normalize_for_compare(r["gt_address"]):
                matched += 1
            elif len(diff_examples) < 5:
                diff_examples.append({
                    "id": r["id"],
                    "raw": r["raw_address"],
                    "got": r["address_standardized"],
                    "gt": r["gt_address"],
                })

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_minutes": window_minutes,
        "rows_audited": total,
        "rows_with_ground_truth": has_gt,
        "exact_match_pct": (100.0 * matched / has_gt) if has_gt > 0 else None,
        "error_count": error_rows,
        "error_rate_pct": (100.0 * error_rows / total) if total > 0 else 0.0,
        "lat_lon_filled_pct": (100.0 * lat_lon_filled / total) if total > 0 else 0.0,
        "phobert_confidence_mean": (sum_phobert / n_phobert) if n_phobert else None,
        "mgte_confidence_mean": (sum_mgte / n_mgte) if n_mgte else None,
        "acs_score_mean": (sum_acs / n_acs) if n_acs else None,
        "acs_decision_distribution": decision_counts,
        "address_epoch_distribution": epoch_counts,
        "diff_examples": diff_examples,
    }

    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if output:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        LOGGER.info("Wrote audit summary to %s", out_path)

    return summary


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="Audit pilot run vs prq.ground_truth")
    parser.add_argument("--window-minutes", type=int, default=30)
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--output", default=None, help="Optional JSON path to persist the summary")
    args = parser.parse_args()
    run(window_minutes=args.window_minutes, limit=args.limit, output=args.output)


if __name__ == "__main__":
    main()

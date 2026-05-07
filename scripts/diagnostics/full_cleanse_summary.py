"""Phase 4.4 — Generate post-cleanse summary report.

Aggregates the most recent batch of processed queue rows (default: last 24 h)
into a JSON summary covering status, confidence means, ACS distribution and
error counts. The output filename is timestamped under reports/.

Usage:
    python scripts/diagnostics/full_cleanse_summary.py
    python scripts/diagnostics/full_cleanse_summary.py --window-hours 12 --output reports/custom.json
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

LOGGER = logging.getLogger("full_cleanse_summary")


def run(window_hours: int = 24, output: str | None = None) -> dict:
    where = f"updated_at > now() - interval '{int(window_hours)} hours'"
    with engine.connect() as conn:
        status_rows = conn.execute(
            text(
                f"""
                SELECT processing_status, COUNT(*) AS n,
                       AVG(phobert_confidence_score) AS phobert_mean,
                       AVG(mgte_confidence_score)    AS mgte_mean,
                       AVG(acs_score)                AS acs_mean
                FROM prq.address_cleansing_queue
                WHERE {where}
                GROUP BY processing_status
                ORDER BY processing_status
                """
            )
        ).mappings().all()

        decision_rows = conn.execute(
            text(
                f"""
                SELECT acs_decision, COUNT(*) AS n
                FROM prq.address_cleansing_queue
                WHERE {where}
                GROUP BY acs_decision
                ORDER BY n DESC
                """
            )
        ).mappings().all()

        epoch_rows = conn.execute(
            text(
                f"""
                SELECT address_epoch, COUNT(*) AS n
                FROM prq.address_cleansing_queue
                WHERE {where}
                GROUP BY address_epoch
                ORDER BY n DESC
                """
            )
        ).mappings().all()

        latlon = conn.execute(
            text(
                f"""
                SELECT
                    COUNT(*) FILTER (WHERE latitude IS NOT NULL AND longitude IS NOT NULL) AS with_coords,
                    COUNT(*) AS total
                FROM prq.address_cleansing_queue
                WHERE {where}
                """
            )
        ).mappings().first()

        error_examples = conn.execute(
            text(
                f"""
                SELECT id, raw_address, error_message
                FROM prq.address_cleansing_queue
                WHERE {where} AND processing_status = 'ERROR' AND error_message IS NOT NULL
                ORDER BY updated_at DESC
                LIMIT 10
                """
            )
        ).mappings().all()

    def _f(x):
        return float(x) if x is not None else None

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_hours": window_hours,
        "status_breakdown": [
            {
                "status": r["processing_status"],
                "count": r["n"],
                "phobert_mean": _f(r["phobert_mean"]),
                "mgte_mean": _f(r["mgte_mean"]),
                "acs_mean": _f(r["acs_mean"]),
            }
            for r in status_rows
        ],
        "acs_decision_distribution": [
            {"decision": r["acs_decision"], "count": r["n"]} for r in decision_rows
        ],
        "address_epoch_distribution": [
            {"epoch": r["address_epoch"], "count": r["n"]} for r in epoch_rows
        ],
        "lat_lon_coverage": {
            "with_coords": int(latlon["with_coords"]) if latlon else 0,
            "total": int(latlon["total"]) if latlon else 0,
            "pct": (
                (100.0 * float(latlon["with_coords"]) / float(latlon["total"]))
                if latlon and latlon["total"]
                else 0.0
            ),
        },
        "error_examples": [
            {"id": r["id"], "raw": r["raw_address"], "error": r["error_message"]}
            for r in error_examples
        ],
    }

    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if not output:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output = f"reports/full_cleanse_summary_{ts}.json"
    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    LOGGER.info("Wrote summary to %s", out_path)

    return summary


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="Post-cleanse summary report")
    parser.add_argument("--window-hours", type=int, default=24)
    parser.add_argument("--output", default=None, help="Override output JSON path (default reports/full_cleanse_summary_<ts>.json)")
    args = parser.parse_args()
    run(window_hours=args.window_hours, output=args.output)


if __name__ == "__main__":
    main()

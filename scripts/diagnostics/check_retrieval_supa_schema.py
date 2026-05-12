"""Smoke-check: ath.retrieval_eval_run + prq.supa_benchmark_run.eval_metrics_json."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from sqlalchemy import text

from app.core.database import engine


def main() -> int:
    with engine.connect() as c:
        n1 = c.execute(text("SELECT COUNT(*) FROM ath.retrieval_eval_run")).scalar()
        n2 = c.execute(text("SELECT COUNT(*) FROM prq.supa_benchmark_run")).scalar()
        col_em = c.execute(
            text(
                """
                SELECT COUNT(*) FROM information_schema.columns
                WHERE table_schema = 'prq' AND table_name = 'supa_benchmark_run'
                  AND column_name = 'eval_metrics_json'
                """
            )
        ).scalar()
        col_stratum = c.execute(
            text(
                """
                SELECT COUNT(*) FROM information_schema.columns
                WHERE table_schema = 'prq' AND table_name = 'supa_benchmark_specimen'
                  AND column_name = 'stratum_code'
                """
            )
        ).scalar()
        n3 = c.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'ath' AND table_name = 'supa_stratified_eval_summary'"
            )
        ).scalar()
    print("ath.retrieval_eval_run rows:", n1)
    print("prq.supa_benchmark_run rows:", n2)
    print("eval_metrics_json column (1=yes):", col_em)
    print("supa_benchmark_specimen.stratum_code column (1=yes):", col_stratum)
    print("ath.supa_stratified_eval_summary table exists (1=yes):", n3)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

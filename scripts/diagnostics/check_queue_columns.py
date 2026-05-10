"""Check whether prq.address_cleansing_queue has expected pipeline columns."""

from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[2]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from sqlalchemy import text

from app.core.database import engine

COLS = [
    "acs_score",
    "acs_decision",
    "s_text",
    "s_sem",
    "v_hierarchy",
    "v_temporal",
    "address_epoch",
    "mgte_confidence_score",
    "phobert_confidence_score",
    "latitude",
    "longitude",
]


def main() -> None:
    with engine.connect() as c:
        for col in COLS:
            n = c.execute(
                text(
                    """
                    SELECT COUNT(*) FROM information_schema.columns
                    WHERE table_schema='prq' AND table_name='address_cleansing_queue'
                      AND column_name=:c
                    """
                ),
                {"c": col},
            ).scalar()
            print(f"{col}: {'OK' if n else 'MISSING'}")


if __name__ == "__main__":
    main()

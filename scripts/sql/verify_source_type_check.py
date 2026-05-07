"""Verify check_source_type constraint definition (Phase 1.1 sanity check)."""

from sqlalchemy import text

from app.core.database import engine


def main() -> None:
    sql = text(
        """
        SELECT pg_get_constraintdef(c.oid)
        FROM pg_constraint c
        WHERE c.conrelid = 'prq.address_clean_corpus'::regclass
          AND c.conname = 'check_source_type'
        """
    )
    with engine.connect() as conn:
        row = conn.execute(sql).first()
    print("check_source_type:", row[0] if row else "MISSING")


if __name__ == "__main__":
    main()

"""Inspect current pgvector / vector-column / vector-index state."""

from sqlalchemy import text

from app.core.database import engine


def main() -> None:
    with engine.connect() as conn:
        ext = conn.execute(text("SELECT extname, extversion FROM pg_extension WHERE extname='vector'")).first()
        print("pg_extension['vector']:", ext)

        cols = conn.execute(text(
            """
            SELECT column_name, data_type, udt_name
            FROM information_schema.columns
            WHERE table_schema='prq' AND table_name='address_clean_corpus'
              AND column_name LIKE '%embedding%'
            ORDER BY column_name
            """
        )).all()
        print("embedding columns:")
        for c in cols:
            print(" ", tuple(c))

        try:
            sample = conn.execute(text(
                """SELECT COUNT(*) FILTER (WHERE mgte_embedding IS NOT NULL) AS mgte_n,
                          COUNT(*) FILTER (WHERE phobert_embedding IS NOT NULL) AS phobert_n,
                          COUNT(*) AS total
                   FROM prq.address_clean_corpus"""
            )).first()
            print("embedding fill counts:", tuple(sample))
        except Exception as exc:
            print("embedding count error:", exc)

        idx = conn.execute(text(
            """SELECT indexname, indexdef FROM pg_indexes
               WHERE schemaname='prq' AND tablename='address_clean_corpus'
                 AND indexname ILIKE '%vector%'"""
        )).all()
        print("vector indexes:")
        for i in idx:
            print(" ", tuple(i))


if __name__ == "__main__":
    main()

"""Phase 1 diagnostics: row counts and component fill rates."""

from sqlalchemy import text

from app.core.database import engine


QUERIES = [
    ("ground_truth (address>5)", "SELECT COUNT(*) FROM prq.ground_truth WHERE address IS NOT NULL AND length(trim(address)) > 5"),
    ("clean_corpus total", "SELECT COUNT(*) FROM prq.address_clean_corpus"),
    ("clean_corpus by source_type",
     "SELECT source_type, COUNT(*) FROM prq.address_clean_corpus GROUP BY source_type ORDER BY 1"),
    ("clean_corpus extended-label NON-NULL fill rate (overall)",
     """SELECT
        COUNT(*) AS total,
        COUNT(*) FILTER (WHERE (address_components ->> 'FLR') IS NOT NULL) AS flr_filled,
        COUNT(*) FILTER (WHERE (address_components ->> 'RM') IS NOT NULL) AS rm_filled,
        COUNT(*) FILTER (WHERE (address_components ->> 'NHB') IS NOT NULL) AS nhb_filled,
        COUNT(*) FILTER (WHERE (address_components ->> 'BLD') IS NOT NULL) AS bld_filled,
        COUNT(*) FILTER (WHERE (address_components ->> 'POI') IS NOT NULL) AS poi_filled
        FROM prq.address_clean_corpus"""),
    ("clean_corpus extended-label fill rate for recently updated (last 5 min)",
     """SELECT
        COUNT(*) AS recently_updated,
        COUNT(*) FILTER (WHERE (address_components ->> 'FLR') IS NOT NULL) AS flr,
        COUNT(*) FILTER (WHERE (address_components ->> 'RM') IS NOT NULL) AS rm,
        COUNT(*) FILTER (WHERE (address_components ->> 'NHB') IS NOT NULL) AS nhb,
        COUNT(*) FILTER (WHERE (address_components ->> 'BLD') IS NOT NULL) AS bld,
        COUNT(*) FILTER (WHERE (address_components ->> 'POI') IS NOT NULL) AS poi
        FROM prq.address_clean_corpus
        WHERE updated_at > now() - interval '5 minutes'"""),
    ("queue total", "SELECT COUNT(*) FROM prq.address_cleansing_queue"),
    ("queue PENDING/missing standardized",
     "SELECT COUNT(*) FROM prq.address_cleansing_queue WHERE processing_status = 'PENDING' OR address_standardized IS NULL"),
]


def main() -> None:
    with engine.connect() as conn:
        for label, q in QUERIES:
            try:
                rows = conn.execute(text(q)).fetchall()
            except Exception as exc:
                print(f"-- {label}: ERROR {exc}")
                continue
            print(f"-- {label}")
            for r in rows:
                print("   ", tuple(r))


if __name__ == "__main__":
    main()

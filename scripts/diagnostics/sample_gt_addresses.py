"""Sample GT addresses to confirm whether extended-label markers appear in text."""

import sys

from sqlalchemy import text

from app.core.database import engine
from scripts.migration.migrate_ground_truth_to_clean_corpus import _extract_components

# Force stdout to UTF-8 on Windows so we can print Vietnamese diacritics.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


SAMPLES = """
SELECT g.address, p.province_name, d.district_name, w.ward_name
FROM prq.ground_truth g
LEFT JOIN mat.province p ON p.old_id = g.province_id AND p.admin_version = 2
LEFT JOIN mat.district d ON d.old_id = g.district_id AND d.admin_version = 2
LEFT JOIN mat.ward w ON w.old_id = g.ward_id AND w.admin_version = 2
WHERE g.address ~* '\\m(t[aầ]ng|l[aầ]u|ph[oò]ng|t[oò]a|block|chung c[uư]|tr[uư][oơ]ng|kp\\.?|khu ph[oố])\\M'
LIMIT 20
"""

PATTERN_HITS = """
SELECT
    COUNT(*) FILTER (WHERE address ~* '\\mt[aầ]ng\\M') AS tang,
    COUNT(*) FILTER (WHERE address ~* '\\ml[aầ]u\\M') AS lau,
    COUNT(*) FILTER (WHERE address ~* '\\mph[oò]ng\\M') AS phong,
    COUNT(*) FILTER (WHERE address ~* '\\mt[oò]a\\M') AS toa,
    COUNT(*) FILTER (WHERE address ~* '\\mblock\\M') AS block,
    COUNT(*) FILTER (WHERE address ~* '\\mchung c[uư]\\M') AS cc,
    COUNT(*) FILTER (WHERE address ~* '\\mtr[uư][oơ]ng\\M') AS truong,
    COUNT(*) FILTER (WHERE address ~* '\\m(kp|khu ph[oố])\\M') AS kp
FROM prq.ground_truth
WHERE address IS NOT NULL
"""


def main() -> None:
    with engine.connect() as conn:
        print("-- Pattern hits across all GT rows:")
        row = conn.execute(text(PATTERN_HITS)).first()
        if row:
            print("    tang/lau/phong/toa/block/cc/truong/kp =", tuple(row))

        print("\n-- 20 GT samples that contain at least one keyword:")
        rows = conn.execute(text(SAMPLES)).mappings().all()
        for r in rows:
            comps = _extract_components(r["address"], r.get("province_name"), r.get("district_name"), r.get("ward_name"))
            extras = {k: comps[k] for k in ("FLR", "RM", "NHB", "BLD", "POI") if comps[k]}
            print(f"    addr: {r['address'][:120]}")
            print(f"      extras: {extras}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
SUPA-Bench: extract (read-only from prq.ground_truth) → perturb → store in prq.supa_*;
fill predictions via import-preds (CSV) from your normalization run; eval; export TeX macros.

Does NOT insert/update/delete prq.ground_truth (invariant).

Why there is NO built-in "normalize" calling production_pipeline here:
  production_pipeline targets prq.address_cleansing_queue columns and batch semantics.
  Binding it blindly to supa_benchmark_specimen would hide model/config versions and risk
  touching production paths. Scientific reporting requires an explicit artifact chain:
  export-specimens → (you run the normalizer you declare in the paper) → import-preds.

Usage:
  # One-shot demo (see docs/07-scientific-reports/SUPA-Benchmark-Runbook.md):
  # Omit --seed on extract/workflow → random rng_seed each invocation (new cohort + noise).
  # Pass --seed <int> when you need a fixed cohort for reproducible papers.
  python scripts/experiments/supa_benchmark.py workflow --n 1000
  python scripts/experiments/supa_benchmark.py workflow --n 1000 --seed 42
  python scripts/experiments/supa_benchmark.py workflow --skip-extract --run-id 1 --preds preds.csv --source-note "..."
  # Smoke-test (pred = ref v2 oracle — not for paper numbers):
  python scripts/experiments/supa_benchmark.py workflow --skip-extract --run-id 1 --preds-demo-ref-v2
  # Or create a preds CSV tutorial-style:
  python scripts/experiments/supa_benchmark.py make-demo-preds --from reports/supa_workflow_specimens_latest.csv --out reports/supa_preds_filled.csv

  python scripts/experiments/supa_benchmark.py extract --n 10000
  python scripts/experiments/supa_benchmark.py extract --n 10000 --seed 42
  python scripts/experiments/supa_benchmark.py export-specimens --out reports/supa_specimens_run1.csv
  python scripts/experiments/supa_benchmark.py import-preds --csv reports/supa_preds_run1.csv --source-note "..."
  python scripts/experiments/supa_benchmark.py replicate --n-runs 20 --mode sweep-seed --n 1000 --preds-demo-ref-v2
  python scripts/experiments/supa_benchmark.py replicate --n-runs 20 --mode sweep-seed --seed-start 42 --n 1000 --preds-demo-ref-v2

  python scripts/experiments/supa_benchmark.py extract-stratified --n 2000 --seed 42
  python scripts/experiments/supa_benchmark.py replicate-stratified --k-runs 5 --n 2000 --base-seed 42 --preds-demo-ref-v2

  python scripts/experiments/supa_benchmark.py aggregate-runs --min-run-id 10 --max-run-id 59 --out-json reports/agg.json --out-md reports/agg.md
  python scripts/experiments/supa_benchmark.py aggregate-runs --from-batch-json reports/supa_benchmark_last_batch_range.json --persist-ath --methodology-version strat-v1

Prerequisite DDL (Windows-friendly — no psql required):
  python scripts/sql/apply_sql_file.py scripts/migration/20260209_prq_supa_benchmark_tables.sql
  python scripts/sql/apply_sql_file.py scripts/migration/20260512_retrieval_eval_and_supa_metrics.sql
  python scripts/sql/apply_sql_file.py scripts/migration/20260513_supa_stratified_specimen_and_ath_summary.sql
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import random
import time
import re
import secrets
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
_src = ROOT / "src"
if _src.is_dir() and str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import ProgrammingError

from app.ai.metrics import compute_metrics_by_stratum, compute_supa_quality_metrics
from app.core.database import engine

NOISE_PROFILE_DEFAULT = "SUP-1.0.0"
NOISE_PROFILE_D2_HIGH = "SUP-D2-1.0.0"
STRATIFICATION_RULES_DEFAULT = "strat-v1"
LAST_METRICS = ROOT / "reports" / "supa_benchmark_last_metrics.json"
LAST_RUN_ID = ROOT / "reports" / "supa_benchmark_last_run_id.txt"
LAST_IMPORT_MANIFEST = ROOT / "reports" / "supa_benchmark_last_import_manifest.json"
DEFAULT_TEX = ROOT / "docs" / "scientific-report" / "vnai-supa-generated-metrics.tex"


def supa_metrics_path_for_run(run_id: int) -> Path:
    return ROOT / "reports" / f"supa_metrics_run_{int(run_id)}.json"


def _retention_prune_supa_runs(keep: int) -> list[int]:
    """Keep the `keep` newest runs by id; delete older prq.supa_benchmark_run rows (CASCADE specimens)."""
    if keep <= 0:
        return []
    with engine.connect() as conn:
        ids = [int(r[0]) for r in conn.execute(text("SELECT id FROM prq.supa_benchmark_run ORDER BY id DESC")).all()]
    if len(ids) <= keep:
        return []
    doomed = ids[keep:]
    with engine.begin() as conn:
        for bid in doomed:
            conn.execute(text("DELETE FROM prq.supa_benchmark_run WHERE id = :id"), {"id": bid})
    print(
        f"retention: deleted {len(doomed)} older supa_benchmark_run row(s); kept newest {keep}.",
        file=sys.stderr,
    )
    return doomed


def _persist_supa_eval_artifacts(run_id: int, metrics: dict) -> None:
    per_path = supa_metrics_path_for_run(run_id)
    per_path.parent.mkdir(parents=True, exist_ok=True)
    per_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE prq.supa_benchmark_run SET eval_metrics_json = CAST(:j AS jsonb) WHERE id = :id"
                ),
                {"j": json.dumps(metrics, ensure_ascii=False), "id": int(run_id)},
            )
    except ProgrammingError as exc:
        print(
            f"WARN: eval_metrics_json column missing? Apply scripts/migration/20260512_retrieval_eval_and_supa_metrics.sql ({exc})",
            file=sys.stderr,
        )


def _git_head() -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(ROOT),
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip()[:40]
    except Exception:
        return None


def _norm_for_em(s: str | None) -> str:
    if s is None:
        return ""
    t = unicodedata.normalize("NFC", str(s)).strip()
    t = re.sub(r"\s+", " ", t)
    return t


def _resolve_supa_rng_seed(seed: int | None) -> int:
    """Ground-truth ordering + synthetic noise both depend on rng_seed.

    If *seed* is None, draw a cryptographically strong 31-bit integer so each
    script invocation samples a different cohort unless the user pins --seed.
    """
    if seed is not None:
        return int(seed)
    auto = secrets.randbelow(2**31 - 1) + 1
    print(
        f"SUPA rng_seed={auto} (auto — cohort + noise differ each run; use --seed <int> to fix for replication)",
        file=sys.stderr,
    )
    return auto


def apply_noise(address_v2: str, rng: random.Random, profile: str) -> str:
    """Deterministic given rng state. Operates on v2 reference (modern canonical string).
    
    Upgraded with realistic Vietnamese noise patterns:
    - Admin abbreviations (Q., P., TP., etc.) and joined forms (Q1, P12).
    - Regional slang (Ngõ/Ngách <-> Hẻm/Kiệt) and slash variants (sẹc, -).
    - IME errors (Telex/VNI: dđ, aâ, misplaced/missing tone marks).
    - Structural noise (Prefixes/Suffixes: Gần, Đối diện, Tòa nhà...).
    - Random CASE transformations (UPPER/lower).
    """
    s = (address_v2 or "").strip()
    if not s:
        return s

    # 1. Internal Helpers (capturing rng for determinism)
    def _abbreviate(text: str, prob: float) -> str:
        # Standard administrative units
        mapping = [
            (r"(?i)\bthành phố\b", ["TP.", "TP", "tp", "T.P"]),
            (r"(?i)\bquận\b", ["Q.", "Q", "q", "Quận"]),
            (r"(?i)\bhuyện\b", ["H.", "H", "h", "Huyện"]),
            (r"(?i)\bphường\b", ["P.", "P", "p", "Phường"]),
            (r"(?i)\bđường\b", ["Đ.", "đ.", "D.", "d.", "duong", "Đ"]),
        ]
        for pattern, choices in mapping:
            if rng.random() < prob:
                text = re.sub(pattern, rng.choice(choices), text)
        
        # Joined forms: Q. 1 -> Q1, P. 12 -> P12, Q. BT -> Q.BT
        if rng.random() < prob:
            text = re.sub(r"\b([QP])\.\s+(\d+)\b", r"\1\2", text)
            text = re.sub(r"\b([QP])\s+(\d+)\b", r"\1\2", text)
        if rng.random() < 0.20:
            text = re.sub(r"\bQ\.\s+([A-Z]{2,})\b", r"Q.\1", text)
        return text

    def _apply_slang_and_slashes(text: str, prob: float) -> str:
        # Ngõ/Ngách <-> Hẻm/Kiệt (Northern vs Southern preference)
        slangs = {
            r"(?i)\bngõ\b": ["hẻm", "kiệt", "ngo"],
            r"(?i)\bngách\b": ["hẻm", "kiệt", "ngach"],
            r"(?i)\bhẻm\b": ["ngõ", "kiệt", "hem"],
        }
        for pattern, choices in slangs.items():
            if rng.random() < prob:
                text = re.sub(pattern, rng.choice(choices), text)
        
        # Slashes: 123/45 -> 123 sẹc 45, 123-45
        if "/" in text and rng.random() < prob:
            variant = rng.choice([" sẹc ", " sec ", "-", " / ", " /", "/ "])
            text = text.replace("/", variant)
        return text

    def _apply_ime_errors(text: str, prob: float) -> str:
        # Telex/VNI double tap: đ -> dđ, đd; â -> aâ
        if rng.random() < prob:
            text = text.replace("đ", rng.choice(["dđ", "đd", "d"])).replace("Đ", rng.choice(["DĐ", "ĐD", "D"]))
        if rng.random() < prob * 0.5:
            text = text.replace("â", "aâ").replace("Â", "AÂ")
        
        # Misplaced marks (Hòa vs Hoà) - common in different input methods
        if rng.random() < prob:
            marks = [("òa", "oà"), ("óa", "oá"), ("úy", "uý"), ("òe", "oè"), ("óe", "oé")]
            p, r = rng.choice(marks)
            text = text.replace(p, r)
        
        # Missing marks at end of word (fast typing)
        if rng.random() < prob * 0.4:
            words = text.split()
            if words:
                idx = rng.randint(0, len(words) - 1)
                w = words[idx]
                if len(w) > 3:
                    w_clean = "".join(c for c in unicodedata.normalize("NFD", w) if unicodedata.category(c) != "Mn")
                    words[idx] = w_clean
                    text = " ".join(words)
        return text

    # 2. Main Logic based on Profile
    if profile == NOISE_PROFILE_DEFAULT:
        # Standard noise: Common abbreviations, some slang, light typos
        prefixes = ["Gần ", "Đối diện ", "Khu vực ", "Chỗ ", "Ngay ", "Sau lưng ", ""]
        suffixes = ["", " (liên hệ)", " - ghi chú", " (tầng 2)"]
        if rng.random() < 0.40: s = rng.choice(prefixes) + s
        if rng.random() < 0.20: s = s + rng.choice(suffixes)

        s = _abbreviate(s, 0.65)
        s = _apply_slang_and_slashes(s, 0.30)
        s = _apply_ime_errors(s, 0.15)
        
        if rng.random() < 0.05: s = s.upper()
        if rng.random() < 0.05: s = s.lower()
        
        # Spacing noise
        if rng.random() < 0.25: s = s.replace(", ", " ,  ")
        if rng.random() < 0.15: s = re.sub(r"\s+", "  ", s)
        return s.strip()

    if profile == NOISE_PROFILE_D2_HIGH:
        # High noise: Aggressive abbreviations, slang, severe typos, and NO ACCENTS
        # Note: Apply text replacements BEFORE stripping marks to ensure regex matches
        
        prefixes = ["Gần ", "Đối diện ", "Chỗ ", "Ngay ", "Sau lưng ", "Cạnh ", "Phía sau ", "Tầng trệt ", ""]
        if rng.random() < 0.60: s = rng.choice(prefixes) + s

        s = _abbreviate(s, 0.90) # Very high chance of abbreviations
        s = _apply_slang_and_slashes(s, 0.60)
        
        # Severe character-level typos
        if len(s) > 10:
            # Transpose characters
            if rng.random() < 0.50:
                i = rng.randint(1, len(s) - 2)
                s = s[:i] + s[i + 1] + s[i] + s[i + 2 :]
            # Repeat characters (stuttering)
            if rng.random() < 0.30:
                i = rng.randint(0, len(s) - 1)
                s = s[:i] + s[i] + s[i] + s[i + 1 :]

        # Strip all marks (unaccented) - major semantic loss
        s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
        
        if rng.random() < 0.15: s = s.upper()
        
        # Aggressive punctuation/spacing noise
        if rng.random() < 0.60: s = s.replace(", ", ",") # Remove spaces after commas
        if rng.random() < 0.30: s = re.sub(r"\s+", "   ", s) # Triple spacing
        
        return s.strip()

    return s


def noise_profile_for_stratum(stratum: str) -> str:
    if stratum == "D2":
        return NOISE_PROFILE_D2_HIGH
    return NOISE_PROFILE_DEFAULT


def _postgis_available(conn: Connection) -> bool:
    try:
        v = conn.execute(text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'postgis')")).scalar()
        return bool(v)
    except Exception:
        return False


def _normalize_light_addr(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower().strip())


def _temporal_signal_row(r: dict) -> bool:
    pairs = (
        ("ward_id", "old_ward_id"),
        ("district_id", "old_district_id"),
        ("province_id", "old_province_id"),
    )
    for a, b in pairs:
        v1, v2 = r.get(a), r.get(b)
        if v1 is not None and v2 is not None:
            try:
                if int(v1) != int(v2):
                    return True
            except (TypeError, ValueError):
                continue
    ao, av = r.get("old_address"), r.get("address")
    if not (ao and av):
        return False
    return _normalize_light_addr(str(ao)) != _normalize_light_addr(str(av))


_URBAN_COMPLEX_RE = re.compile(
    r"(ngõ|ngách|hẻm|kiệt|sn\b|lô\s*\d|đường\s+số|hem|ngo\s)", re.IGNORECASE
)


def _urban_signal_row(r: dict) -> bool:
    try:
        if int(r.get("popular") or 0) >= 500:
            return True
    except (TypeError, ValueError):
        pass
    addr = r.get("address") or ""
    return bool(_URBAN_COMPLEX_RE.search(str(addr)))


def _md5_order_key(row_id: int, seed: int) -> str:
    return hashlib.md5(f"{int(row_id)}:{int(seed)}".encode()).hexdigest()


def _boundary_dist_deg_for_gps_ids(conn: Connection, ids: list[int]) -> dict[int, float]:
    out: dict[int, float] = {}
    if not ids:
        return out
    chunk = 400
    for i in range(0, len(ids), chunk):
        part = ids[i : i + chunk]
        try:
            q = text(
                """
                SELECT gt.id,
                  MIN(ST_Distance(
                    ST_Boundary(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(ap.geojson::text), 4326))),
                    ST_SetSRID(ST_Point(gt.longitude::double precision, gt.latitude::double precision), 4326),
                    true
                  )) AS ddeg
                FROM prq.ground_truth gt
                INNER JOIN mat.area_polygon ap
                  ON ap.unit_level = 'ward' AND ap.admin_version = 2 AND ap.geojson IS NOT NULL
                  AND ap.unit_id = gt.ward_id
                WHERE gt.id = ANY(:ids)
                  AND gt.latitude IS NOT NULL AND gt.longitude IS NOT NULL
                  AND gt.ward_id IS NOT NULL
                GROUP BY gt.id
                """
            )
            rows = conn.execute(q, {"ids": part}).mappings().all()
            for row in rows:
                d = row.get("ddeg")
                if d is not None:
                    out[int(row["id"])] = float(d)
        except Exception:
            continue
    return out


def _classify_primary_stratum(
    r: dict, boundary_deg: dict[int, float], boundary_thresh_deg: float, postgis: bool
) -> str:
    rid = int(r["id"])
    if postgis and rid in boundary_deg and boundary_deg[rid] < boundary_thresh_deg:
        return "D4"
    if _temporal_signal_row(r):
        return "D3"
    if _urban_signal_row(r):
        return "D1"
    if (not postgis) and r.get("latitude") is not None and r.get("longitude") is not None:
        return "D4"
    return "D2"


def _stratified_select_rows(
    pool: list[dict],
    n: int,
    seed: int,
    conn: Connection,
) -> tuple[list[tuple[dict, str]], list[str]]:
    warnings: list[str] = []
    postgis = _postgis_available(conn)
    boundary_deg: dict[int, float] = {}
    if postgis:
        gps_ids = [
            int(x["id"])
            for x in pool
            if x.get("latitude") is not None
            and x.get("longitude") is not None
            and x.get("ward_id") is not None
        ]
        boundary_deg = _boundary_dist_deg_for_gps_ids(conn, gps_ids)
    else:
        warnings.append("PostGIS unavailable: D4 cohort uses GPS-only proxy rows (no boundary distance).")

    thresh = 0.0011
    primary: dict[str, list[dict]] = {"D1": [], "D2": [], "D3": [], "D4": []}
    for r in pool:
        st = _classify_primary_stratum(r, boundary_deg, thresh, postgis)
        primary[st].append(r)

    def sort_pool(rows: list[dict]) -> list[dict]:
        return sorted(rows, key=lambda x: _md5_order_key(int(x["id"]), seed))

    n_d1 = int(round(n * 0.40))
    n_d2 = int(round(n * 0.20))
    n_d3 = int(round(n * 0.30))
    n_d4 = max(0, n - n_d1 - n_d2 - n_d3)
    quotas = {"D1": n_d1, "D2": n_d2, "D3": n_d3, "D4": n_d4}

    chosen: list[tuple[dict, str]] = []
    used: set[int] = set()

    def take_from(stratum: str, need: int) -> int:
        got = 0
        for r in sort_pool(primary[stratum]):
            if got >= need:
                break
            rid = int(r["id"])
            if rid in used:
                continue
            used.add(rid)
            chosen.append((r, stratum))
            got += 1
        return got

    for st, need in quotas.items():
        g = take_from(st, need)
        if g < need:
            warnings.append(f"{st}: wanted {need} got {g}")

    if len(chosen) < n:
        for r in sort_pool(pool):
            if len(chosen) >= n:
                break
            rid = int(r["id"])
            if rid in used:
                continue
            used.add(rid)
            chosen.append((r, "D2"))

    if len(chosen) > n:
        chosen = chosen[:n]

    d4_have = sum(1 for _, st in chosen if st == "D4")
    if quotas["D4"] > 0 and d4_have < quotas["D4"] * 0.5 and postgis:
        warnings.append("D4: few rows within ward-boundary distance threshold; review polygon coverage.")

    return chosen, warnings


def cmd_extract_stratified(
    n: int,
    seed: int | None,
    strat_version: str,
    notes: str | None,
    max_pool_rows: int,
) -> int:
    seed = _resolve_supa_rng_seed(seed)
    git_c = _git_head()
    pool_sql = text(
        """
        SELECT g.id, g.address, g.old_address, g.latitude, g.longitude,
               g.ward_id, g.old_ward_id, g.district_id, g.old_district_id,
               g.province_id, g.old_province_id, COALESCE(g.popular, 0) AS popular
        FROM prq.ground_truth g
        WHERE g.address IS NOT NULL AND trim(g.address) <> ''
          AND g.old_address IS NOT NULL AND trim(g.old_address) <> ''
        ORDER BY md5(g.id::text || ':' || :seed_s)
        LIMIT :lim
        """
    )
    notes_extra = f"stratified_rules={strat_version}; quotas=D1:40% D2:20% D3:30% D4:10%; max_pool={max_pool_rows}"
    full_notes = f"{notes}; {notes_extra}" if notes else notes_extra

    with engine.connect() as conn:
        pool = conn.execute(pool_sql, {"lim": int(max_pool_rows), "seed_s": str(seed)}).mappings().all()
        pool_l = [dict(x) for x in pool]
        chosen, warns = _stratified_select_rows(pool_l, int(n), int(seed), conn)

    if not chosen:
        print("extract-stratified: empty cohort (check ground_truth filters / pool).", file=sys.stderr)
        return 2

    realized = len(chosen)
    ins_run = text(
        """
        INSERT INTO prq.supa_benchmark_run
            (n_requested, n_realized, rng_seed, noise_profile_id, git_commit, notes)
        VALUES (:nq, :nr, :seed, :prof, :gc, :notes)
        RETURNING id
        """
    )
    ins_sp = text(
        """
        INSERT INTO prq.supa_benchmark_specimen
            (run_id, local_idx, ground_truth_id, ref_address_v2, ref_address_v1,
             noisy_raw_address, stratum_code, latitude, longitude, latency_ms)
        VALUES (:run_id, :li, :gtid, :v2, :v1, :noisy, :stratum, :lat, :lon, NULL)
        """
    )

    warn_suffix = " | WARN: " + " ; ".join(warns) if warns else ""
    with engine.begin() as conn:
        run_id = conn.execute(
            ins_run,
            {
                "nq": n,
                "nr": realized,
                "seed": seed,
                "prof": f"STRATIFIED-{strat_version}",
                "gc": git_c,
                "notes": full_notes + warn_suffix,
            },
        ).scalar_one()
        rng = random.Random(seed)
        for i, (r, stratum) in enumerate(chosen):
            prof = noise_profile_for_stratum(stratum)
            noisy = apply_noise(str(r["address"]), rng, prof)
            lat = r.get("latitude")
            lon = r.get("longitude")
            conn.execute(
                ins_sp,
                {
                    "run_id": run_id,
                    "li": i + 1,
                    "gtid": int(r["id"]),
                    "v2": str(r["address"]),
                    "v1": str(r["old_address"]),
                    "noisy": noisy,
                    "stratum": stratum,
                    "lat": float(lat) if lat is not None else None,
                    "lon": float(lon) if lon is not None else None,
                },
            )

    LAST_RUN_ID.parent.mkdir(parents=True, exist_ok=True)
    LAST_RUN_ID.write_text(str(run_id), encoding="utf-8")
    print(
        f"SUPA extract-stratified OK: run_id={run_id}, n_realized={realized}, seed={seed}, version={strat_version}",
        file=sys.stderr,
    )
    if warns:
        for w in warns:
            print(f"extract-stratified WARN: {w}", file=sys.stderr)
    return 0


def cmd_extract(n: int, seed: int | None, profile: str, notes: str | None) -> int:
    seed = _resolve_supa_rng_seed(seed)
    git_c = _git_head()
    sel_sql = text(
        """
        SELECT g.id, g.address, g.old_address
        FROM prq.ground_truth g
        WHERE g.address IS NOT NULL AND trim(g.address) <> ''
          AND g.old_address IS NOT NULL AND trim(g.old_address) <> ''
        ORDER BY md5(g.id::text || ':' || :seed_s)
        LIMIT :lim
        """
    )
    ins_run = text(
        """
        INSERT INTO prq.supa_benchmark_run
            (n_requested, n_realized, rng_seed, noise_profile_id, git_commit, notes)
        VALUES (:nq, :nr, :seed, :prof, :gc, :notes)
        RETURNING id
        """
    )
    ins_sp = text(
        """
        INSERT INTO prq.supa_benchmark_specimen
            (run_id, local_idx, ground_truth_id, ref_address_v2, ref_address_v1, noisy_raw_address)
        VALUES (:run_id, :li, :gtid, :v2, :v1, :noisy)
        """
    )

    with engine.connect() as conn:
        rows = conn.execute(sel_sql, {"lim": n, "seed_s": str(seed)}).mappings().all()
    realized = len(rows)
    if realized == 0:
        print("No rows matched filters on prq.ground_truth.", file=sys.stderr)
        return 2

    with engine.begin() as conn:
        run_id = conn.execute(
            ins_run,
            {
                "nq": n,
                "nr": realized,
                "seed": seed,
                "prof": profile,
                "gc": git_c,
                "notes": notes,
            },
        ).scalar_one()
        rng = random.Random(seed)
        for i, r in enumerate(rows):
            noisy = apply_noise(str(r["address"]), rng, profile)
            conn.execute(
                ins_sp,
                {
                    "run_id": run_id,
                    "li": i + 1,
                    "gtid": int(r["id"]),
                    "v2": str(r["address"]),
                    "v1": str(r["old_address"]),
                    "noisy": noisy,
                },
            )

    LAST_RUN_ID.parent.mkdir(parents=True, exist_ok=True)
    LAST_RUN_ID.write_text(str(run_id), encoding="utf-8")
    print(f"SUPA extract OK: run_id={run_id}, n_realized={realized}, seed={seed}, profile={profile}")
    return 0


def _latest_run_id(conn: Connection) -> int | None:
    row = conn.execute(
        text("SELECT id FROM prq.supa_benchmark_run ORDER BY id DESC LIMIT 1")
    ).scalar_one_or_none()
    return int(row) if row is not None else None


def cmd_eval(run_id: int | None) -> int:
    metrics: dict = {}
    with engine.connect() as conn:
        rid = run_id
        if rid is None:
            rid = _latest_run_id(conn)
        if rid is None:
            print("No supa_benchmark_run rows.", file=sys.stderr)
            return 2

        run_row = conn.execute(
            text(
                "SELECT n_requested, n_realized, rng_seed, noise_profile_id, git_commit, created_at "
                "FROM prq.supa_benchmark_run WHERE id = :id"
            ),
            {"id": rid},
        ).mappings().first()
        if not run_row:
            print(f"run_id {rid} not found", file=sys.stderr)
            return 2

        try:
            specs = conn.execute(
                text(
                    """
                    SELECT ref_address_v2, ref_address_v1, pred_standardized,
                           stratum_code, latency_ms
                    FROM prq.supa_benchmark_specimen WHERE run_id = :id
                    ORDER BY local_idx
                    """
                ),
                {"id": rid},
            ).mappings().all()
        except ProgrammingError:
            specs = conn.execute(
                text(
                    """
                    SELECT ref_address_v2, ref_address_v1, pred_standardized,
                           NULL AS stratum_code, NULL AS latency_ms
                    FROM prq.supa_benchmark_specimen WHERE run_id = :id
                    ORDER BY local_idx
                    """
                ),
                {"id": rid},
            ).mappings().all()

        n_total = len(specs)
        scored = [s for s in specs if s["pred_standardized"] is not None and str(s["pred_standardized"]).strip()]
        n_scored = len(scored)

        em_v2 = em_v1 = None
        if n_scored > 0:
            ok2 = sum(
                1
                for s in scored
                if _norm_for_em(s["pred_standardized"]) == _norm_for_em(s["ref_address_v2"])
            )
            ok1 = sum(
                1
                for s in scored
                if _norm_for_em(s["pred_standardized"]) == _norm_for_em(s["ref_address_v1"])
            )
            em_v2 = round(100.0 * ok2 / n_scored, 4)
            em_v1 = round(100.0 * ok1 / n_scored, 4)

        iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        ca = run_row["created_at"]
        if hasattr(ca, "isoformat"):
            created_s = ca.isoformat()
        else:
            created_s = str(ca)
        metrics = {
            "utc_iso": iso,
            "run_id": int(rid),
            "run_created_at": created_s,
            "metrics_json_path": str(supa_metrics_path_for_run(int(rid)).resolve()),
            "n_requested": int(run_row["n_requested"]),
            "n_realized": int(run_row["n_realized"]),
            "n_specimens_table": n_total,
            "n_scored": n_scored,
            "em_v2_pct": em_v2,
            "em_v1_pct": em_v1,
            "rng_seed": int(run_row["rng_seed"]),
            "noise_profile_id": str(run_row["noise_profile_id"]),
            "git_commit": run_row["git_commit"],
            "note": (
                "em_v2/em_v1 are exact-match rates on specimens with non-null pred_standardized; "
                "NFC trim collapse spaces. Component F1 uses normalized token match (see app.ai.metrics)."
            ),
        }

        if n_scored > 0:
            preds = [str(s["pred_standardized"] or "") for s in scored]
            refs2 = [str(s["ref_address_v2"] or "") for s in scored]
            refs1 = [str(s["ref_address_v1"] or "") for s in scored]
            lat_list = [s.get("latency_ms") for s in scored]
            qm = compute_supa_quality_metrics(preds, refs2, latencies_ms=lat_list, ground_truths_v1=refs1)
            for k in (
                "f1_duong_pct",
                "f1_phuong_pct",
                "f1_quan_pct",
                "f1_tinh_pct",
                "precision_duong_pct",
                "recall_duong_pct",
                "latency_mean_ms",
                "latency_p95_ms",
                "throughput_addr_per_s",
                "n_latency_samples",
                "component_f1",
            ):
                if k in qm:
                    metrics[k] = qm[k]
            if metrics.get("n_latency_samples", 0) > 0:
                metrics["latency_ms_semantics"] = (
                    "prq.supa_benchmark_specimen.latency_ms: pipeline values if present in import CSV; "
                    "otherwise per-row wall time for UPDATE pred_standardized during import-preds "
                    "(see reports/supa_benchmark_last_import_manifest.json → latency_ms_fill)."
                )
            row_dicts = [dict(s) for s in scored]
            by_st = compute_metrics_by_stratum(row_dicts)
            if by_st:
                metrics["by_stratum"] = by_st

    LAST_METRICS.parent.mkdir(parents=True, exist_ok=True)
    LAST_METRICS.write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _persist_supa_eval_artifacts(int(rid), metrics)
    print(json.dumps(metrics, indent=2, ensure_ascii=False))
    return 0


def _tex_escape(s: str) -> str:
    return (
        s.replace("\\", r"\textbackslash{}")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("_", r"\_")
        .replace("%", r"\%")
        .replace("#", r"\#")
        .replace("&", r"\&")
    )


def _fmt_pct(x: float | None) -> str:
    if x is None:
        return r"---"
    return f"{x:.4f}"


def build_tex(metrics: dict) -> str:
    iso = metrics.get("utc_iso") or "---"
    lines = [
        "% " + "=" * 72,
        "% AUTO-GENERATED by scripts/experiments/supa_benchmark.py export-tex",
        f"% UTC: {iso}",
        "% " + "=" * 72,
        "",
        r"\providecommand{\VNASUPARunId}{" + _tex_escape(str(metrics.get("run_id", "---"))) + "}",
        r"\providecommand{\VNASUPANRequested}{" + _tex_escape(str(metrics.get("n_requested", "---"))) + "}",
        r"\providecommand{\VNASUPANRealized}{" + _tex_escape(str(metrics.get("n_realized", "---"))) + "}",
        r"\providecommand{\VNASUPANSpecimens}{" + _tex_escape(str(metrics.get("n_specimens_table", "---"))) + "}",
        r"\providecommand{\VNASUPANScored}{" + _tex_escape(str(metrics.get("n_scored", "---"))) + "}",
        r"\providecommand{\VNASUPAEMvTwoPct}{" + _fmt_pct(metrics.get("em_v2_pct")) + "}",
        r"\providecommand{\VNASUPAEMvOnePct}{" + _fmt_pct(metrics.get("em_v1_pct")) + "}",
        r"\providecommand{\VNASUPANoiseProfile}{" + _tex_escape(str(metrics.get("noise_profile_id", "---"))) + "}",
        r"\providecommand{\VNASUPASeed}{" + _tex_escape(str(metrics.get("rng_seed", "---"))) + "}",
        r"\providecommand{\VNASUPAGitCommit}{" + _tex_escape(str(metrics.get("git_commit") or "---")) + "}",
        "",
    ]
    return "\n".join(lines) + "\n"


def _read_last_run_id_file() -> int | None:
    if not LAST_RUN_ID.is_file():
        return None
    try:
        return int(LAST_RUN_ID.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def cmd_export_specimens(run_id: int | None, out_csv: Path) -> int:
    with engine.connect() as conn:
        rid = run_id if run_id is not None else _latest_run_id(conn)
        if rid is None:
            print("No run_id (pass --run-id or run extract first).", file=sys.stderr)
            return 2
        try:
            rows = conn.execute(
                text(
                    """
                    SELECT id, run_id, local_idx, ground_truth_id,
                           noisy_raw_address, ref_address_v2, ref_address_v1,
                           stratum_code, latitude, longitude, latency_ms
                    FROM prq.supa_benchmark_specimen
                    WHERE run_id = :rid
                    ORDER BY local_idx
                    """
                ),
                {"rid": rid},
            ).mappings().all()
        except ProgrammingError:
            rows = conn.execute(
                text(
                    """
                    SELECT id, run_id, local_idx, ground_truth_id,
                           noisy_raw_address, ref_address_v2, ref_address_v1
                    FROM prq.supa_benchmark_specimen
                    WHERE run_id = :rid
                    ORDER BY local_idx
                    """
                ),
                {"rid": rid},
            ).mappings().all()
    if not rows:
        print(f"No specimens for run_id={rid}", file=sys.stderr)
        return 2
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    sample = dict(rows[0])
    fieldnames = [
        "specimen_id",
        "run_id",
        "local_idx",
        "ground_truth_id",
        "noisy_raw_address",
        "ref_address_v2",
        "ref_address_v1",
        "pred_standardized",
    ]
    if "stratum_code" in sample:
        fieldnames.extend(["stratum_code", "latitude", "longitude", "latency_ms"])
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            row_out = {
                "specimen_id": r["id"],
                "run_id": r["run_id"],
                "local_idx": r["local_idx"],
                "ground_truth_id": r["ground_truth_id"],
                "noisy_raw_address": r["noisy_raw_address"] or "",
                "ref_address_v2": r["ref_address_v2"] or "",
                "ref_address_v1": r["ref_address_v1"] or "",
                "pred_standardized": "",
            }
            if "stratum_code" in sample:
                row_out["stratum_code"] = r.get("stratum_code") or ""
                row_out["latitude"] = r.get("latitude") if r.get("latitude") is not None else ""
                row_out["longitude"] = r.get("longitude") if r.get("longitude") is not None else ""
                row_out["latency_ms"] = r.get("latency_ms") if r.get("latency_ms") is not None else ""
            w.writerow(row_out)
    print(f"Wrote {out_csv} ({len(rows)} rows, run_id={rid})")
    return 0


DEMO_PREDS_COPY_SN = (
    "demo: pred_standardized copied from ref_address_v2 — oracle sanity / runbook smoke only; "
    "not a model artifact"
)


def cmd_make_demo_preds(from_csv: Path, out_csv: Path, column: str) -> int:
    """Write specimen_id + pred_standardized from a specimen export CSV (tutorial / smoke EM check)."""
    if column not in ("ref_address_v2", "ref_address_v1"):
        print("--column must be ref_address_v2 or ref_address_v1", file=sys.stderr)
        return 2
    if not from_csv.is_file():
        print(f"Missing specimens CSV: {from_csv.resolve()}", file=sys.stderr)
        return 2
    with from_csv.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            print("Empty CSV header", file=sys.stderr)
            return 2
        fn = [x.strip() for x in reader.fieldnames if x]
        if "specimen_id" not in fn:
            print("CSV must include specimen_id (export-specimens format).", file=sys.stderr)
            return 2
        if column not in fn:
            print(f"CSV missing column {column!r}", file=sys.stderr)
            return 2
        rows_out: list[dict[str, str]] = []
        for row in reader:
            sid = (row.get("specimen_id") or "").strip()
            pred = (row.get(column) or "").strip()
            if sid:
                rows_out.append({"specimen_id": sid, "pred_standardized": pred})
    if not rows_out:
        print("No data rows in specimens CSV.", file=sys.stderr)
        return 2
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["specimen_id", "pred_standardized"])
        w.writeheader()
        w.writerows(rows_out)
    print(f"Wrote demo preds ({len(rows_out)} rows): {out_csv.resolve()}")
    return 0


def cmd_import_preds(
    csv_path: Path,
    source_note: str,
    dry_run: bool,
    measure_row_latency: bool = True,
) -> int:
    """CSV columns: either (specimen_id, pred_standardized) or (run_id, local_idx, pred_standardized).

    When the CSV has no ``latency_ms`` column (or a row leaves it blank) and the DB has
    ``prq.supa_benchmark_specimen.latency_ms`` (migration 20260513), each successful
    ``UPDATE`` of ``pred_standardized`` is timed; the wall-clock milliseconds for that
    statement are stored as ``latency_ms`` for that specimen. This records **DB write /
    round-trip** latency for ingest, not model inference — use CSV ``latency_ms`` when
    your pipeline exports per-address inference time.
    """
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        raw = f.read()

    def _pred_key_from_reader(r: csv.DictReader) -> tuple[dict[str, str], str | None]:
        fnmap = {x.strip().lower(): x for x in (r.fieldnames or []) if x}
        for k in ("pred_standardized", "pred", "prediction", "address_standardized"):
            if k in fnmap:
                return fnmap, fnmap[k]
        return fnmap, None

    sample = raw[:4096]
    dialect_candidates: list[type[csv.Dialect] | csv.Dialect] = [csv.excel]
    try:
        sniffed = csv.Sniffer().sniff(sample)
        dialect_candidates.insert(0, sniffed)
    except csv.Error:
        pass

    reader: csv.DictReader | None = None
    fn: dict[str, str]
    pred_key: str | None = None
    for d in dialect_candidates:
        cand = csv.DictReader(io.StringIO(raw), dialect=d)
        if not cand.fieldnames:
            continue
        fn0, pk0 = _pred_key_from_reader(cand)
        if pk0 is not None:
            reader = cand
            fn = fn0
            pred_key = pk0
            break

    if reader is None:
        reader = csv.DictReader(io.StringIO(raw))
    if not reader.fieldnames:
        print("Empty CSV", file=sys.stderr)
        return 2
    fn = {x.strip().lower(): x for x in reader.fieldnames if x}
    has_sid = "specimen_id" in fn
    has_pair = "run_id" in fn and "local_idx" in fn
    lat_csv_key = None
    for cand in ("latency_ms", "latency", "infer_latency_ms"):
        if cand in fn:
            lat_csv_key = fn[cand]
            break
    if pred_key is None:
        _, pred_key = _pred_key_from_reader(reader)
    if pred_key is None:
        print(
            "CSV must include pred column: pred_standardized (or pred / prediction / address_standardized)",
            file=sys.stderr,
        )
        return 2
    if not has_sid and not has_pair:
        print(
            "CSV must include specimen_id OR (run_id + local_idx)",
            file=sys.stderr,
        )
        return 2

    upd_by_sid = text(
        """
        UPDATE prq.supa_benchmark_specimen
        SET pred_standardized = :pred
        WHERE id = :sid
        """
    )
    upd_by_sid_lat = text(
        """
        UPDATE prq.supa_benchmark_specimen
        SET pred_standardized = :pred, latency_ms = :lat
        WHERE id = :sid
        """
    )
    upd_by_pair = text(
        """
        UPDATE prq.supa_benchmark_specimen
        SET pred_standardized = :pred
        WHERE run_id = :rid AND local_idx = :lidx
        """
    )
    upd_by_pair_lat = text(
        """
        UPDATE prq.supa_benchmark_specimen
        SET pred_standardized = :pred, latency_ms = :lat
        WHERE run_id = :rid AND local_idx = :lidx
        """
    )
    upd_lat_only_sid = text(
        "UPDATE prq.supa_benchmark_specimen SET latency_ms = :lat WHERE id = :sid"
    )
    upd_lat_only_pair = text(
        "UPDATE prq.supa_benchmark_specimen SET latency_ms = :lat "
        "WHERE run_id = :rid AND local_idx = :lidx"
    )

    rows_read = 0
    rows_updated = 0
    n_latency_from_csv = 0
    n_latency_from_import_wall_ms = 0
    errors: list[str] = []

    with engine.begin() as conn:
        lat_supported = False
        try:
            conn.execute(text("SELECT latency_ms FROM prq.supa_benchmark_specimen LIMIT 1"))
            lat_supported = True
        except ProgrammingError:
            pass

        for row in reader:
            rows_read += 1
            pred_val = (row.get(pred_key) or "").strip()
            if not pred_val:
                continue
            lat_val: float | None = None
            if lat_csv_key:
                raw_lat = (row.get(lat_csv_key) or "").strip()
                if raw_lat:
                    try:
                        lat_val = float(raw_lat)
                    except ValueError:
                        errors.append(f"row {rows_read}: bad latency {raw_lat!r}")
                        continue
            use_csv_lat = lat_val is not None
            try:
                if has_sid:
                    sid_s = (row.get(fn["specimen_id"]) or "").strip()
                    if not sid_s:
                        continue
                    sid = int(sid_s)
                    if dry_run:
                        rows_updated += 1
                        if use_csv_lat:
                            n_latency_from_csv += 1
                        elif measure_row_latency and lat_supported:
                            n_latency_from_import_wall_ms += 1
                    else:
                        if use_csv_lat and lat_supported:
                            r = conn.execute(
                                upd_by_sid_lat, {"pred": pred_val, "lat": lat_val, "sid": sid}
                            )
                            rows_updated += int(r.rowcount or 0)
                            if int(r.rowcount or 0) > 0:
                                n_latency_from_csv += 1
                        elif use_csv_lat and not lat_supported:
                            r = conn.execute(upd_by_sid, {"pred": pred_val, "sid": sid})
                            rows_updated += int(r.rowcount or 0)
                            errors.append(
                                f"row {rows_read}: CSV latency present but DB has no latency_ms column "
                                f"(apply migration 20260513_supa_stratified_specimen_and_ath_summary.sql)"
                            )
                        else:
                            t0 = time.perf_counter()
                            r = conn.execute(upd_by_sid, {"pred": pred_val, "sid": sid})
                            t1 = time.perf_counter()
                            measured_ms = (t1 - t0) * 1000.0
                            rows_updated += int(r.rowcount or 0)
                            if (
                                lat_supported
                                and measure_row_latency
                                and int(r.rowcount or 0) > 0
                            ):
                                conn.execute(
                                    upd_lat_only_sid,
                                    {"lat": round(measured_ms, 6), "sid": sid},
                                )
                                n_latency_from_import_wall_ms += 1
                else:
                    rid = int((row.get(fn["run_id"]) or "").strip())
                    lidx = int((row.get(fn["local_idx"]) or "").strip())
                    if dry_run:
                        rows_updated += 1
                        if use_csv_lat:
                            n_latency_from_csv += 1
                        elif measure_row_latency and lat_supported:
                            n_latency_from_import_wall_ms += 1
                    else:
                        if use_csv_lat and lat_supported:
                            r = conn.execute(
                                upd_by_pair_lat,
                                {"pred": pred_val, "lat": lat_val, "rid": rid, "lidx": lidx},
                            )
                            rows_updated += int(r.rowcount or 0)
                            if int(r.rowcount or 0) > 0:
                                n_latency_from_csv += 1
                        elif use_csv_lat and not lat_supported:
                            r = conn.execute(
                                upd_by_pair, {"pred": pred_val, "rid": rid, "lidx": lidx}
                            )
                            rows_updated += int(r.rowcount or 0)
                            errors.append(
                                f"row {rows_read}: CSV latency present but DB has no latency_ms column "
                                f"(apply migration 20260513_supa_stratified_specimen_and_ath_summary.sql)"
                            )
                        else:
                            t0 = time.perf_counter()
                            r = conn.execute(
                                upd_by_pair, {"pred": pred_val, "rid": rid, "lidx": lidx}
                            )
                            t1 = time.perf_counter()
                            measured_ms = (t1 - t0) * 1000.0
                            rows_updated += int(r.rowcount or 0)
                            if (
                                lat_supported
                                and measure_row_latency
                                and int(r.rowcount or 0) > 0
                            ):
                                conn.execute(
                                    upd_lat_only_pair,
                                    {
                                        "lat": round(measured_ms, 6),
                                        "rid": rid,
                                        "lidx": lidx,
                                    },
                                )
                                n_latency_from_import_wall_ms += 1
            except ProgrammingError as pe:
                if use_csv_lat:
                    errors.append(f"row {rows_read}: latency_ms column missing? Apply migration ({pe})")
                else:
                    errors.append(f"row {rows_read}: {pe}")
            except (TypeError, ValueError) as e:
                errors.append(f"row {rows_read}: {e}")

    iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if dry_run:
        latency_fill_summary = "dry_run"
    elif n_latency_from_csv > 0 and n_latency_from_import_wall_ms > 0:
        latency_fill_summary = "mixed_csv_and_import_wall_ms"
    elif n_latency_from_csv > 0:
        latency_fill_summary = "csv_column"
    elif n_latency_from_import_wall_ms > 0:
        latency_fill_summary = "import_pred_update_wall_ms_per_row"
    else:
        latency_fill_summary = "none"
    manifest = {
        "utc_iso": iso,
        "csv_path": str(csv_path.resolve()),
        "dry_run": dry_run,
        "rows_read": rows_read,
        "rows_updated": rows_updated,
        "source_note": source_note,
        "git_commit_at_import": _git_head(),
        "latency_ms_fill": {
            "summary": latency_fill_summary,
            "rows_with_csv_latency": n_latency_from_csv,
            "rows_with_measured_import_wall_ms": n_latency_from_import_wall_ms,
            "measure_row_latency": bool(measure_row_latency),
            "db_latency_ms_column": lat_supported,
            "semantics_note": (
                "import_pred_update_wall_ms_per_row: latency_ms = time for UPDATE pred_standardized "
                "(DB round-trip), not model inference. Export latency_ms from your normalizer CSV for "
                "pipeline timings."
            ),
        },
        "errors": errors[:50],
    }
    LAST_IMPORT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    LAST_IMPORT_MANIFEST.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    if errors:
        return 1
    return 0


SPECIMENS_LATEST = ROOT / "reports" / "supa_workflow_specimens_latest.csv"
LAST_BATCH_RANGE = ROOT / "reports" / "supa_benchmark_last_batch_range.json"
AGGREGATE_JSON_DEFAULT = ROOT / "reports" / "supa_benchmark_aggregate_last.json"
AGGREGATE_MD_DEFAULT = ROOT / "reports" / "supa_benchmark_aggregate_last.md"


def _json_obj(val: object) -> dict:
    if val is None:
        return {}
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            return {}
    return {}


def _stat_summary(values: list[float]) -> dict:
    import statistics

    if not values:
        return {"n": 0, "mean": None, "stdev": None, "min": None, "max": None}
    n = len(values)
    mean = float(statistics.mean(values))
    stdev = float(statistics.stdev(values)) if n > 1 else 0.0
    return {
        "n": n,
        "mean": round(mean, 6),
        "stdev": round(stdev, 6),
        "min": round(min(values), 6),
        "max": round(max(values), 6),
    }


AGG_NUMERIC_ROLLUP_KEYS = (
    "em_v2_pct",
    "em_v1_pct",
    "f1_duong_pct",
    "f1_phuong_pct",
    "f1_quan_pct",
    "f1_tinh_pct",
    "latency_mean_ms",
    "latency_p95_ms",
    "throughput_addr_per_s",
)


def _collect_numeric_series(rows_chrono: list, key: str) -> list[float]:
    out: list[float] = []
    for r in rows_chrono:
        m = _json_obj(r.get("eval_metrics_json"))
        v = m.get(key)
        if isinstance(v, (int, float)):
            out.append(float(v))
    return out


def _persist_ath_stratified_summary(
    payload: dict,
    methodology_version: str,
    k_runs: int,
    n_per_run: int | None,
    notes_extra: str | None,
) -> None:
    filt = payload.get("filter") or {}
    rmin, rmax = filt.get("min_run_id"), filt.get("max_run_id")
    if rmin is None or rmax is None:
        runs = payload.get("runs") or []
        if runs:
            ids = [int(x["run_id"]) for x in runs]
            rmin, rmax = min(ids), max(ids)
        else:
            return
    notes = notes_extra or ""
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ath.supa_stratified_eval_summary
                        (methodology_version, k_runs, n_per_run, run_id_min, run_id_max,
                         metrics_json, notes, git_commit)
                    VALUES (:mv, :k, :npr, :rmin, :rmax, CAST(:j AS jsonb), :notes, :gc)
                    """
                ),
                {
                    "mv": methodology_version[:500],
                    "k": int(k_runs),
                    "npr": int(n_per_run) if n_per_run is not None else 0,
                    "rmin": int(rmin),
                    "rmax": int(rmax),
                    "j": json.dumps(payload, ensure_ascii=False),
                    "notes": notes[:4000] if notes else None,
                    "gc": _git_head(),
                },
            )
        print(
            f"aggregate-runs: persisted ath.supa_stratified_eval_summary run_id {rmin}-{rmax}",
            file=sys.stderr,
        )
    except ProgrammingError as exc:
        print(f"WARN: --persist-ath skipped ({exc})", file=sys.stderr)


def cmd_aggregate_supa(
    last_n: int,
    min_run_id: int | None,
    max_run_id: int | None,
    from_batch_json: Path | None,
    out_json: Path,
    out_md: Path | None,
    persist_ath: bool,
    methodology_version: str,
    persist_notes: str | None,
) -> int:
    """Summarize metrics from prq.supa_benchmark_run.eval_metrics_json (EM, F1, latency when present)."""
    batch_notes: str | None = None
    batch_k_runs: int | None = None
    if from_batch_json is not None:
        if not from_batch_json.is_file():
            print(f"aggregate-runs: missing {from_batch_json}", file=sys.stderr)
            return 2
        meta = json.loads(from_batch_json.read_text(encoding="utf-8"))
        min_run_id = int(meta["first_run_id"])
        max_run_id = int(meta["last_run_id"])
        batch_notes = meta.get("notes")
        if meta.get("k_runs") is not None:
            try:
                batch_k_runs = int(meta["k_runs"])
            except (TypeError, ValueError):
                batch_k_runs = None

    if from_batch_json is None and last_n < 1:
        print("aggregate-runs: --last-n must be >= 1", file=sys.stderr)
        return 2
    range_mode = min_run_id is not None and max_run_id is not None
    if max_run_id is not None and min_run_id is None:
        print("aggregate-runs: --max-run-id requires --min-run-id", file=sys.stderr)
        return 2
    if range_mode and int(max_run_id) < int(min_run_id):
        print("aggregate-runs: --max-run-id must be >= --min-run-id", file=sys.stderr)
        return 2

    if range_mode:
        sql = text(
            """
            SELECT id, created_at, rng_seed, n_realized, noise_profile_id, git_commit, eval_metrics_json
            FROM prq.supa_benchmark_run
            WHERE id >= :min_id AND id <= :max_id
            ORDER BY id ASC
            """
        )
        params = {"min_id": int(min_run_id), "max_id": int(max_run_id)}
    else:
        sql = text(
            """
            SELECT id, created_at, rng_seed, n_realized, noise_profile_id, git_commit, eval_metrics_json
            FROM prq.supa_benchmark_run
            WHERE (:min_id IS NULL OR id >= :min_id)
            ORDER BY id DESC
            LIMIT :lim
            """
        )
        params = {"lim": int(last_n), "min_id": int(min_run_id) if min_run_id is not None else None}

    with engine.connect() as conn:
        rows = conn.execute(sql, params).mappings().all()
    chrono = list(rows) if range_mode else list(reversed(rows))

    em2: list[float] = []
    em1: list[float] = []
    run_rows: list[dict] = []
    for r in chrono:
        m = _json_obj(r.get("eval_metrics_json"))
        v2 = m.get("em_v2_pct")
        v1 = m.get("em_v1_pct")
        if isinstance(v2, (int, float)):
            em2.append(float(v2))
        if isinstance(v1, (int, float)):
            em1.append(float(v1))
        ca = r.get("created_at")
        created_s = ca.isoformat() if hasattr(ca, "isoformat") else str(ca)
        rr = {
            "run_id": int(r["id"]),
            "created_at": created_s,
            "rng_seed": int(r["rng_seed"]) if r.get("rng_seed") is not None else None,
            "n_realized": int(r["n_realized"]) if r.get("n_realized") is not None else None,
            "noise_profile_id": str(r["noise_profile_id"]) if r.get("noise_profile_id") is not None else None,
            "em_v2_pct": float(v2) if isinstance(v2, (int, float)) else None,
            "em_v1_pct": float(v1) if isinstance(v1, (int, float)) else None,
            "n_scored": m.get("n_scored"),
            "f1_tinh_pct": m.get("f1_tinh_pct"),
            "f1_phuong_pct": m.get("f1_phuong_pct"),
        }
        run_rows.append(rr)

    rollup_metrics = {
        k: _stat_summary(_collect_numeric_series(chrono, k)) for k in AGG_NUMERIC_ROLLUP_KEYS
    }

    iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "utc_iso": iso,
        "git_head_at_aggregate": _git_head(),
        "filter": {
            "last_n": last_n if not range_mode else None,
            "min_run_id": min_run_id,
            "max_run_id": max_run_id if range_mode else None,
            "range_mode": range_mode,
        },
        "batch_notes": batch_notes,
        "n_rows_loaded": len(chrono),
        "em_v2_pct": _stat_summary(em2),
        "em_v1_pct": _stat_summary(em1),
        "rollup_metrics": rollup_metrics,
        "runs": run_rows,
            "note": (
                "Rollup from eval_metrics_json per run. Oracle demo (--preds-demo-ref-v2) yields em_v2 ~ 100. "
                "F1 keys require eval after metrics upgrade + migration 20260513. "
                "latency_ms / throughput: filled from CSV column when present; otherwise import-preds records "
                "per-row UPDATE wall time (see reports/supa_benchmark_last_import_manifest.json latency_ms_fill) "
                "unless --no-measured-latency."
            ),
    }

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    if out_md is not None:
        filt_desc = (
            f"run_id {min_run_id}-{max_run_id} (inclusive)"
            if range_mode
            else f"last_n={last_n}, min_run_id={min_run_id}"
        )
        lines = [
            f"<!-- AUTO-GENERATED {iso} by supa_benchmark.py aggregate-runs -->",
            "",
            "## SUPA aggregate report",
            "",
            f"- Rows loaded: **{len(chrono)}** ({filt_desc})",
            f"- EM@v2: n={payload['em_v2_pct']['n']}, mean={payload['em_v2_pct']['mean']}, "
            f"stdev={payload['em_v2_pct']['stdev']}, min={payload['em_v2_pct']['min']}, max={payload['em_v2_pct']['max']}",
            f"- EM@v1: n={payload['em_v1_pct']['n']}, mean={payload['em_v1_pct']['mean']}, "
            f"stdev={payload['em_v1_pct']['stdev']}, min={payload['em_v1_pct']['min']}, max={payload['em_v1_pct']['max']}",
            "",
        ]
        for key in AGG_NUMERIC_ROLLUP_KEYS:
            if key in ("em_v2_pct", "em_v1_pct"):
                continue
            blk = rollup_metrics.get(key) or {}
            if blk.get("n"):
                lines.append(
                    f"- **{key}**: n={blk['n']}, mean={blk['mean']}, stdev={blk['stdev']}, "
                    f"min={blk['min']}, max={blk['max']}"
                )
        lines.extend(
            [
                "",
                "| run_id | rng_seed | n_realized | em_v2_pct | em_v1_pct | f1_tinh_pct | f1_phuong_pct |",
                "|--------|----------|------------|-----------|-----------|-------------|---------------|",
            ]
        )
        for rr in run_rows:
            lines.append(
                f"| {rr['run_id']} | {rr['rng_seed']} | {rr['n_realized']} | "
                f"{rr['em_v2_pct'] if rr['em_v2_pct'] is not None else '—'} | "
                f"{rr['em_v1_pct'] if rr['em_v1_pct'] is not None else '—'} | "
                f"{rr.get('f1_tinh_pct') if rr.get('f1_tinh_pct') is not None else '—'} | "
                f"{rr.get('f1_phuong_pct') if rr.get('f1_phuong_pct') is not None else '—'} |"
            )
        lines.append("")
        out_md.parent.mkdir(parents=True, exist_ok=True)
        out_md.write_text("\n".join(lines), encoding="utf-8")
        print(f"wrote_markdown={out_md.resolve()}", file=sys.stderr)

    print(f"wrote_json={out_json.resolve()}", file=sys.stderr)

    if persist_ath:
        k_eff = int(batch_k_runs) if batch_k_runs is not None else len(chrono)
        npr = None
        if chrono:
            try:
                npr = int(chrono[0].get("n_realized") or 0)
            except (TypeError, ValueError):
                npr = None
        _persist_ath_stratified_summary(
            payload,
            methodology_version=methodology_version or STRATIFICATION_RULES_DEFAULT,
            k_runs=max(k_eff, 1),
            n_per_run=npr,
            notes_extra=persist_notes or batch_notes,
        )
    return 0


def cmd_replicate(
    n_runs: int,
    mode: str,
    seed_start: int | None,
    seed_fixed: int,
    n: int,
    profile: str,
    notes: str | None,
    retention: int,
    specimens_out: Path,
    preds_csv: Path | None,
    preds_demo_ref_v2: bool,
    source_note: str | None,
    export_tex_last: bool,
    skip_import: bool,
) -> int:
    """
    Repeat SUPA extract → export-specimens → [import-preds] → eval for cohort statistics.
    mode=sweep-seed: seeds base, base+1, … with base = --seed-start or (if omitted) one random
    base per script run. repeat-determinism: same --seed every iteration (default 42).
    """
    if n_runs < 1:
        print("replicate: n-runs must be >= 1", file=sys.stderr)
        return 2
    if mode not in ("sweep-seed", "repeat-determinism"):
        print("replicate: --mode must be sweep-seed or repeat-determinism", file=sys.stderr)
        return 2
    if not skip_import and not preds_demo_ref_v2 and preds_csv is None:
        print(
            "replicate: provide --preds + --source-note, or --preds-demo-ref-v2, or --skip-import",
            file=sys.stderr,
        )
        return 2

    sweep_base: int | None = None
    if mode == "sweep-seed":
        sweep_base = int(seed_start) if seed_start is not None else _resolve_supa_rng_seed(None)

    first_batch_run_id: int | None = None
    last_batch_run_id: int | None = None

    for i in range(n_runs):
        if mode == "sweep-seed":
            assert sweep_base is not None
            seed = int(sweep_base) + i
        else:
            seed = int(seed_fixed)

        print("", file=sys.stderr)
        print(f"=== replicate {i + 1}/{n_runs} seed={seed} mode={mode} ===", file=sys.stderr)

        code = cmd_extract(n, seed, profile, notes)
        if code != 0:
            return code
        run_id = _read_last_run_id_file()
        if run_id is None:
            print("replicate: missing run_id after extract", file=sys.stderr)
            return 2
        if first_batch_run_id is None:
            first_batch_run_id = int(run_id)
        last_batch_run_id = int(run_id)

        code = cmd_export_specimens(run_id, specimens_out)
        if code != 0:
            return code

        preds_path_for_import: Path | None = None
        source_for_import = source_note or ""

        if skip_import:
            pass
        elif preds_demo_ref_v2:
            demo_out = ROOT / "reports" / "supa_benchmark_demo_preds_ref_v2.csv"
            code = cmd_make_demo_preds(specimens_out, demo_out, "ref_address_v2")
            if code != 0:
                return code
            preds_path_for_import = demo_out.resolve()
            source_for_import = DEMO_PREDS_COPY_SN
        elif preds_csv is not None:
            preds_path_for_import = Path(preds_csv).resolve()
            if not preds_path_for_import.is_file():
                print(f"replicate: preds file missing: {preds_path_for_import}", file=sys.stderr)
                return 2
            if not (source_note or "").strip():
                print("replicate: --preds requires --source-note", file=sys.stderr)
                return 2
            source_for_import = source_note or ""

        if preds_path_for_import is not None:
            code = cmd_import_preds(preds_path_for_import, source_note=source_for_import, dry_run=False)
            if code != 0:
                return code

        code = cmd_eval(run_id)
        if code != 0:
            return code

        if export_tex_last and i == n_runs - 1:
            code = cmd_export_tex(LAST_METRICS, DEFAULT_TEX)
            if code != 0:
                return code

        if retention > 0:
            _retention_prune_supa_runs(retention)

    print("", file=sys.stderr)
    print(f"replicate OK: completed {n_runs} run(s).", file=sys.stderr)
    if first_batch_run_id is not None and last_batch_run_id is not None:
        print("", file=sys.stderr)
        print(
            "replicate: summarize this batch (scoped to run_id range):",
            file=sys.stderr,
        )
        print(
            f"  python scripts/experiments/supa_benchmark.py aggregate-runs "
            f"--min-run-id {first_batch_run_id} --max-run-id {last_batch_run_id} "
            f"--out-json reports/supa_benchmark_aggregate_batch_{first_batch_run_id}_{last_batch_run_id}.json "
            f"--out-md reports/supa_benchmark_aggregate_batch_{first_batch_run_id}_{last_batch_run_id}.md",
            file=sys.stderr,
        )
        meta = {
            "first_run_id": first_batch_run_id,
            "last_run_id": last_batch_run_id,
            "n_runs": n_runs,
            "notes": notes,
            "utc_iso": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        LAST_BATCH_RANGE.parent.mkdir(parents=True, exist_ok=True)
        LAST_BATCH_RANGE.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        print(f"replicate: wrote batch range → {LAST_BATCH_RANGE.resolve()}", file=sys.stderr)
    return 0


def cmd_replicate_stratified(
    k_runs: int,
    n: int,
    base_seed: int | None,
    strat_version: str,
    notes: str | None,
    max_pool_rows: int,
    specimens_out: Path,
    preds_csv: Path | None,
    preds_demo_ref_v2: bool,
    source_note: str | None,
    retention: int,
    export_tex_last: bool,
    skip_import: bool,
) -> int:
    """K independent stratified cohorts (default seed stride +1000 per run)."""
    if k_runs < 1:
        print("replicate-stratified: --k-runs must be >= 1", file=sys.stderr)
        return 2
    if not skip_import and not preds_demo_ref_v2 and preds_csv is None:
        print(
            "replicate-stratified: provide --preds + --source-note, or --preds-demo-ref-v2, or --skip-import",
            file=sys.stderr,
        )
        return 2

    sweep_base = int(base_seed) if base_seed is not None else _resolve_supa_rng_seed(None)
    first_batch_run_id: int | None = None
    last_batch_run_id: int | None = None

    for i in range(k_runs):
        seed = int(sweep_base) + 1000 * i
        print("", file=sys.stderr)
        print(f"=== replicate-stratified {i + 1}/{k_runs} seed={seed} ===", file=sys.stderr)

        code = cmd_extract_stratified(n, seed, strat_version, notes, max_pool_rows)
        if code != 0:
            return code
        run_id = _read_last_run_id_file()
        if run_id is None:
            print("replicate-stratified: missing run_id after extract-stratified", file=sys.stderr)
            return 2
        if first_batch_run_id is None:
            first_batch_run_id = int(run_id)
        last_batch_run_id = int(run_id)

        code = cmd_export_specimens(run_id, specimens_out)
        if code != 0:
            return code

        preds_path_for_import: Path | None = None
        source_for_import = source_note or ""

        if skip_import:
            pass
        elif preds_demo_ref_v2:
            demo_out = ROOT / "reports" / "supa_benchmark_demo_preds_ref_v2.csv"
            code = cmd_make_demo_preds(specimens_out, demo_out, "ref_address_v2")
            if code != 0:
                return code
            preds_path_for_import = demo_out.resolve()
            source_for_import = DEMO_PREDS_COPY_SN
        elif preds_csv is not None:
            preds_path_for_import = Path(preds_csv).resolve()
            if not preds_path_for_import.is_file():
                print(f"replicate-stratified: preds file missing: {preds_path_for_import}", file=sys.stderr)
                return 2
            if not (source_note or "").strip():
                print("replicate-stratified: --preds requires --source-note", file=sys.stderr)
                return 2
            source_for_import = source_note or ""

        if preds_path_for_import is not None:
            code = cmd_import_preds(preds_path_for_import, source_note=source_for_import, dry_run=False)
            if code != 0:
                return code

        code = cmd_eval(run_id)
        if code != 0:
            return code

        if export_tex_last and i == k_runs - 1:
            code = cmd_export_tex(LAST_METRICS, DEFAULT_TEX)
            if code != 0:
                return code

        if retention > 0:
            _retention_prune_supa_runs(retention)

    print("", file=sys.stderr)
    print(f"replicate-stratified OK: completed {k_runs} run(s).", file=sys.stderr)
    if first_batch_run_id is not None and last_batch_run_id is not None:
        print("", file=sys.stderr)
        print(
            "replicate-stratified: summarize this batch:",
            file=sys.stderr,
        )
        print(
            f"  python scripts/experiments/supa_benchmark.py aggregate-runs "
            f"--min-run-id {first_batch_run_id} --max-run-id {last_batch_run_id} "
            f"--out-json reports/supa_benchmark_aggregate_stratified_{first_batch_run_id}_{last_batch_run_id}.json "
            f"--out-md reports/supa_benchmark_aggregate_stratified_{first_batch_run_id}_{last_batch_run_id}.md "
            f"--persist-ath --methodology-version {strat_version}",
            file=sys.stderr,
        )
        meta = {
            "first_run_id": first_batch_run_id,
            "last_run_id": last_batch_run_id,
            "n_runs": k_runs,
            "k_runs": k_runs,
            "batch_kind": "stratified",
            "stratification_version": strat_version,
            "notes": notes,
            "utc_iso": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        LAST_BATCH_RANGE.parent.mkdir(parents=True, exist_ok=True)
        LAST_BATCH_RANGE.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        print(f"replicate-stratified: wrote batch range → {LAST_BATCH_RANGE.resolve()}", file=sys.stderr)
    return 0


def cmd_workflow(
    n: int,
    seed: int | None,
    profile: str,
    notes: str | None,
    specimens_out: Path,
    preds_csv: Path | None,
    preds_demo_ref_v2: bool,
    source_note: str | None,
    skip_extract: bool,
    run_id_override: int | None,
) -> int:
    """
    Scripted demo sequence for repeated testing:
    extract (unless skip) → export-specimens → [import-preds if CSV] → eval → export-tex.
    """
    phases: list[tuple[str, int]] = []

    if not skip_extract:
        code = cmd_extract(n, seed, profile, notes)
        phases.append(("extract", code))
        if code != 0:
            print("workflow: extract failed.", file=sys.stderr)
            return code
        run_id = _read_last_run_id_file()
    else:
        with engine.connect() as conn:
            run_id = run_id_override or _latest_run_id(conn)
        if run_id is None:
            print("workflow: need --run-id or --skip-extract=false with existing run.", file=sys.stderr)
            return 2

    phases.append(("export-specimens", 0))
    code = cmd_export_specimens(run_id, specimens_out)
    phases[-1] = ("export-specimens", code)
    if code != 0:
        print("workflow: export-specimens failed.", file=sys.stderr)
        return code

    preds_path_for_import: Path | None = None
    source_for_import = source_note or ""

    if preds_demo_ref_v2:
        demo_out = ROOT / "reports" / "supa_benchmark_demo_preds_ref_v2.csv"
        code = cmd_make_demo_preds(specimens_out, demo_out, "ref_address_v2")
        phases.append(("make-demo-preds(ref_v2)", code))
        if code != 0:
            print("workflow: make-demo-preds failed.", file=sys.stderr)
            return code
        preds_path_for_import = demo_out.resolve()
        source_for_import = DEMO_PREDS_COPY_SN
    elif preds_csv is not None:
        preds_path_for_import = Path(preds_csv).resolve()
        if not preds_path_for_import.is_file():
            print(f"workflow: preds file missing: {preds_path_for_import}", file=sys.stderr)
            print(
                "  Fix: export → fill pipeline → save CSV path, or run:\n"
                "    python scripts/experiments/supa_benchmark.py make-demo-preds \\\n"
                f"      --from {specimens_out} \\\n"
                "      --out reports/supa_preds_filled.csv\n"
                "  Smoke (oracle EM sanity): add --preds-demo-ref-v2 instead of --preds.",
                file=sys.stderr,
            )
            return 2
        if not (source_note or "").strip():
            print("workflow: --preds requires --source-note for provenance.", file=sys.stderr)
            return 2
        source_for_import = source_note or ""

    if preds_path_for_import is not None:
        code = cmd_import_preds(preds_path_for_import, source_note=source_for_import, dry_run=False)
        phases.append(("import-preds", code))
        if code != 0:
            print("workflow: import-preds failed.", file=sys.stderr)
            return code
    elif not preds_demo_ref_v2:
        print("")
        print("=" * 72)
        print("WORKFLOW STOP: Missing --preds")
        print("  1. Fill column pred_standardized in:", specimens_out.resolve())
        print("  2. Re-run:")
        print(
            "     python scripts/experiments/supa_benchmark.py workflow "
            f"--skip-extract --run-id {run_id} --preds YOUR.csv --source-note \"...\""
        )
        print("  Or oracle smoke test (copies ref v2 into preds; see runbook SUPA-BENCH-RUNBOOK 1.B smoke).")
        print(
            "     python scripts/experiments/supa_benchmark.py workflow "
            f"--skip-extract --run-id {run_id} --preds-demo-ref-v2"
        )
        print("=" * 72)

    code = cmd_eval(run_id)
    phases.append(("eval", code))
    if code != 0:
        return code

    code = cmd_export_tex(LAST_METRICS, DEFAULT_TEX)
    phases.append(("export-tex", code))
    if code != 0:
        return code

    print("")
    print("workflow OK:", ", ".join(f"{p}={c}" for p, c in phases))
    print("SUPA macros updated:", DEFAULT_TEX.resolve())
    print(
        "Rebuild PDF (from docs/scientific-report): "
        "xelatex vnai-chapters-master.tex (twice)",
    )
    return 0


def cmd_export_tex(path_json: Path, out_tex: Path) -> int:
    if not path_json.is_file():
        print(f"Missing metrics JSON: {path_json}", file=sys.stderr)
        return 2
    metrics = json.loads(path_json.read_text(encoding="utf-8"))
    tex = build_tex(metrics)
    out_tex.parent.mkdir(parents=True, exist_ok=True)
    out_tex.write_text(tex, encoding="utf-8")
    print(f"Wrote {out_tex}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_ext = sub.add_parser("extract", help="Sample from prq.ground_truth (read-only) into supa tables")
    p_ext.add_argument("--n", type=int, required=True, help="Target sample size")
    p_ext.add_argument(
        "--seed",
        type=int,
        default=None,
        help="RNG + cohort ordering; omit for a new random cohort every run (logged to stderr)",
    )
    p_ext.add_argument("--noise-profile", type=str, default=NOISE_PROFILE_DEFAULT)
    p_ext.add_argument("--notes", type=str, default=None)

    p_exs = sub.add_parser(
        "extract-stratified",
        help="Stratified sample D1/D2/D3/D4 quotas (default 40/20/30/10 pct) from prq.ground_truth",
    )
    p_exs.add_argument("--n", type=int, default=2000, help="Total cohort size (paper default 2000)")
    p_exs.add_argument(
        "--seed",
        type=int,
        default=None,
        help="RNG + ordering; omit for random cohort (logged to stderr)",
    )
    p_exs.add_argument(
        "--strat-version",
        type=str,
        default=STRATIFICATION_RULES_DEFAULT,
        help="Label stored in run.notes / methodology (e.g. strat-v1)",
    )
    p_exs.add_argument(
        "--max-pool-rows",
        type=int,
        default=100_000,
        help="Max ground_truth rows scanned for stratification (safety cap)",
    )
    p_exs.add_argument("--notes", type=str, default=None)

    p_ev = sub.add_parser("eval", help="Compute EM@ v1/v2 vs pred_standardized; write JSON")
    p_ev.add_argument("--run-id", type=int, default=None)

    p_exs = sub.add_parser(
        "export-specimens",
        help="CSV for external normalization (noisy_raw_address + ids; empty pred column)",
    )
    p_exs.add_argument("--run-id", type=int, default=None)
    p_exs.add_argument("--out", type=str, required=True)

    p_imp = sub.add_parser(
        "import-preds",
        help="Load pred_standardized from CSV (after your pipeline); writes import manifest JSON",
    )
    p_imp.add_argument("--csv", type=str, required=True)
    p_imp.add_argument(
        "--source-note",
        type=str,
        required=True,
        help="Provenance for the paper, e.g. production_pipeline commit=... config=... GPU=...",
    )
    p_imp.add_argument("--dry-run", action="store_true")
    p_imp.add_argument(
        "--no-measured-latency",
        action="store_true",
        help=(
            "When CSV has no latency column (or blank cells), do not fill latency_ms from timed "
            "pred UPDATE (restores pre-20260514 behavior; eval rollup latency n stays 0 unless CSV supplies it)."
        ),
    )

    p_tx = sub.add_parser("export-tex", help="vnai-supa-generated-metrics.tex from metrics JSON")
    p_tx.add_argument("--metrics-json", type=str, default=str(LAST_METRICS))
    p_tx.add_argument("--out", type=str, default=str(DEFAULT_TEX))

    p_wf = sub.add_parser(
        "workflow",
        help=(
            "Run extract→export-specimens→[import-preds]→eval→export-tex in one go "
            "(for demo; omit --preds to stop after exporting CSV)."
        ),
    )
    p_wf.add_argument("--n", type=int, default=10000, help="Sample size (ignored if --skip-extract)")
    p_wf.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Same as extract: omit = random cohort/noise each invocation",
    )
    p_wf.add_argument("--noise-profile", type=str, default=NOISE_PROFILE_DEFAULT)
    p_wf.add_argument("--notes", type=str, default=None)
    p_wf.add_argument(
        "--specimens-out",
        type=str,
        default=str(SPECIMENS_LATEST),
        help="CSV path for export-specimens step",
    )
    p_wf.add_argument(
        "--preds",
        type=str,
        default=None,
        help="CSV with pred_standardized; if omitted, prints next-step instructions",
    )
    p_wf.add_argument(
        "--preds-demo-ref-v2",
        action="store_true",
        help=(
            "After export, build reports/supa_benchmark_demo_preds_ref_v2.csv from ref_address_v2 "
            "(oracle copy; smoke / runbook only — not publication metrics)."
        ),
    )
    p_wf.add_argument(
        "--source-note",
        type=str,
        default=None,
        help="Required when --preds is set (provenance manifest); ignored when --preds-demo-ref-v2",
    )

    p_demo = sub.add_parser(
        "make-demo-preds",
        help="Write specimen_id + pred_standardized from ref v1/v2 (tutorial / oracle smoke)",
    )
    p_demo.add_argument("--from", dest="from_csv", type=str, required=True, help="Specimen CSV from export-specimens")
    p_demo.add_argument("--out", type=str, required=True, help="Output CSV (pred_standardized column)")
    p_demo.add_argument(
        "--column",
        type=str,
        choices=("ref_address_v2", "ref_address_v1"),
        default="ref_address_v2",
        help="Which reference column copies into pred_standardized",
    )
    p_wf.add_argument(
        "--skip-extract",
        action="store_true",
        help="Skip extract; use --run-id (or latest run) for export/eval",
    )
    p_wf.add_argument("--run-id", type=int, default=None)

    p_rep = sub.add_parser(
        "replicate",
        help="Many SUPA runs: extract→export→[import]→eval; optional retention of newest N runs",
    )
    p_rep.add_argument("--n-runs", type=int, required=True)
    p_rep.add_argument("--mode", choices=("sweep-seed", "repeat-determinism"), required=True)
    p_rep.add_argument(
        "--seed-start",
        type=int,
        default=None,
        help="sweep-seed: base seed for i=0 (omit = random base each script run, then base+1, …)",
    )
    p_rep.add_argument(
        "--seed",
        type=int,
        default=42,
        help="repeat-determinism: fixed seed every iteration (default 42)",
    )
    p_rep.add_argument("--n", type=int, required=True, help="Cohort size per extract")
    p_rep.add_argument("--noise-profile", type=str, default=NOISE_PROFILE_DEFAULT)
    p_rep.add_argument("--notes", type=str, default=None)
    p_rep.add_argument(
        "--retention",
        type=int,
        default=0,
        help="After each iteration, keep only the newest N supa_benchmark_run rows (0=disable)",
    )
    p_rep.add_argument("--specimens-out", type=str, default=str(SPECIMENS_LATEST))
    p_rep.add_argument("--preds", type=str, default=None)
    p_rep.add_argument(
        "--preds-demo-ref-v2",
        action="store_true",
        help="Oracle preds from ref v2 (smoke only — not publication metrics)",
    )
    p_rep.add_argument("--source-note", type=str, default=None)
    p_rep.add_argument(
        "--export-tex-last",
        action="store_true",
        help="After the final eval, regenerate docs/scientific-report/vnai-supa-generated-metrics.tex (LaTeX metrics)",
    )
    p_rep.add_argument(
        "--skip-import",
        action="store_true",
        help="Skip import-preds (eval may show n_scored=0 unless preds were filled elsewhere)",
    )

    p_rst = sub.add_parser(
        "replicate-stratified",
        help="K independent stratified extracts (seed += 1000 each) → export → [import] → eval",
    )
    p_rst.add_argument("--k-runs", type=int, required=True, help="Number of independent cohorts (paper: 5)")
    p_rst.add_argument("--n", type=int, default=2000, help="Cohort size per run")
    p_rst.add_argument(
        "--base-seed",
        type=int,
        default=None,
        help="First rng seed; omit = random base then base+1000*i",
    )
    p_rst.add_argument("--strat-version", type=str, default=STRATIFICATION_RULES_DEFAULT)
    p_rst.add_argument("--max-pool-rows", type=int, default=100_000)
    p_rst.add_argument("--notes", type=str, default=None)
    p_rst.add_argument("--retention", type=int, default=0)
    p_rst.add_argument("--specimens-out", type=str, default=str(SPECIMENS_LATEST))
    p_rst.add_argument("--preds", type=str, default=None)
    p_rst.add_argument("--preds-demo-ref-v2", action="store_true")
    p_rst.add_argument("--source-note", type=str, default=None)
    p_rst.add_argument("--export-tex-last", action="store_true")
    p_rst.add_argument("--skip-import", action="store_true")

    p_agg = sub.add_parser(
        "aggregate-runs",
        help="Summarize EM@v1/v2 from eval_metrics_json (use --min-run-id + --max-run-id after replicate)",
    )
    p_agg.add_argument("--last-n", type=int, default=50, help="Tail mode: take N newest runs (ignored if min+max set)")
    p_agg.add_argument(
        "--min-run-id",
        type=int,
        default=None,
        help="Optional lower bound run id (use with --max-run-id for exact batch)",
    )
    p_agg.add_argument(
        "--max-run-id",
        type=int,
        default=None,
        help="Optional upper bound run id (batch mode when both min and max set)",
    )
    p_agg.add_argument(
        "--from-batch-json",
        type=str,
        default=None,
        help=f"Read first_run_id/last_run_id from JSON (e.g. {LAST_BATCH_RANGE.name} after replicate)",
    )
    p_agg.add_argument(
        "--out-json",
        type=str,
        default=str(AGGREGATE_JSON_DEFAULT),
        help="Summary JSON output path",
    )
    p_agg.add_argument(
        "--out-md",
        type=str,
        default=str(AGGREGATE_MD_DEFAULT),
        help="Markdown table output path (set empty string to skip)",
    )
    p_agg.add_argument(
        "--persist-ath",
        action="store_true",
        help="INSERT summary row into ath.supa_stratified_eval_summary (requires migration 20260513)",
    )
    p_agg.add_argument(
        "--methodology-version",
        type=str,
        default=STRATIFICATION_RULES_DEFAULT,
        help="methodology_version column when using --persist-ath",
    )
    p_agg.add_argument(
        "--persist-notes",
        type=str,
        default=None,
        help="Optional notes stored with ath summary row",
    )

    ns = ap.parse_args()
    if ns.cmd == "make-demo-preds":
        return cmd_make_demo_preds(Path(ns.from_csv).resolve(), Path(ns.out).resolve(), ns.column)
    if ns.cmd == "extract":
        return cmd_extract(ns.n, ns.seed, ns.noise_profile, ns.notes)
    if ns.cmd == "extract-stratified":
        return cmd_extract_stratified(
            int(ns.n),
            ns.seed,
            str(ns.strat_version),
            ns.notes,
            int(ns.max_pool_rows),
        )
    if ns.cmd == "eval":
        return cmd_eval(ns.run_id)
    if ns.cmd == "export-specimens":
        return cmd_export_specimens(ns.run_id, Path(ns.out).resolve())
    if ns.cmd == "import-preds":
        return cmd_import_preds(
            Path(ns.csv).resolve(),
            source_note=ns.source_note,
            dry_run=ns.dry_run,
            measure_row_latency=not bool(getattr(ns, "no_measured_latency", False)),
        )
    if ns.cmd == "export-tex":
        return cmd_export_tex(Path(ns.metrics_json).resolve(), Path(ns.out).resolve())
    if ns.cmd == "workflow":
        if getattr(ns, "preds_demo_ref_v2", False) and ns.preds:
            print(
                "workflow: use either --preds or --preds-demo-ref-v2, not both.",
                file=sys.stderr,
            )
            return 2
        return cmd_workflow(
            n=ns.n,
            seed=ns.seed,
            profile=ns.noise_profile,
            notes=ns.notes,
            specimens_out=Path(ns.specimens_out).resolve(),
            preds_csv=Path(ns.preds).resolve() if ns.preds else None,
            preds_demo_ref_v2=bool(getattr(ns, "preds_demo_ref_v2", False)),
            source_note=ns.source_note,
            skip_extract=ns.skip_extract,
            run_id_override=ns.run_id,
        )
    if ns.cmd == "replicate":
        if getattr(ns, "preds_demo_ref_v2", False) and ns.preds:
            print("replicate: use either --preds or --preds-demo-ref-v2, not both.", file=sys.stderr)
            return 2
        return cmd_replicate(
            n_runs=int(ns.n_runs),
            mode=str(ns.mode),
            seed_start=ns.seed_start,
            seed_fixed=int(ns.seed),
            n=int(ns.n),
            profile=ns.noise_profile,
            notes=ns.notes,
            retention=int(ns.retention),
            specimens_out=Path(ns.specimens_out).resolve(),
            preds_csv=Path(ns.preds).resolve() if ns.preds else None,
            preds_demo_ref_v2=bool(getattr(ns, "preds_demo_ref_v2", False)),
            source_note=ns.source_note,
            export_tex_last=bool(getattr(ns, "export_tex_last", False)),
            skip_import=bool(getattr(ns, "skip_import", False)),
        )
    if ns.cmd == "replicate-stratified":
        if getattr(ns, "preds_demo_ref_v2", False) and ns.preds:
            print(
                "replicate-stratified: use either --preds or --preds-demo-ref-v2, not both.",
                file=sys.stderr,
            )
            return 2
        return cmd_replicate_stratified(
            k_runs=int(ns.k_runs),
            n=int(ns.n),
            base_seed=getattr(ns, "base_seed", None),
            strat_version=str(ns.strat_version),
            notes=ns.notes,
            max_pool_rows=int(ns.max_pool_rows),
            specimens_out=Path(ns.specimens_out).resolve(),
            preds_csv=Path(ns.preds).resolve() if ns.preds else None,
            preds_demo_ref_v2=bool(getattr(ns, "preds_demo_ref_v2", False)),
            source_note=ns.source_note,
            retention=int(ns.retention),
            export_tex_last=bool(getattr(ns, "export_tex_last", False)),
            skip_import=bool(getattr(ns, "skip_import", False)),
        )
    if ns.cmd == "aggregate-runs":
        md_path: Path | None
        if getattr(ns, "out_md", None) in (None, "", "none", "NONE"):
            md_path = None
        else:
            md_path = Path(ns.out_md).resolve()
        return cmd_aggregate_supa(
            last_n=int(ns.last_n),
            min_run_id=getattr(ns, "min_run_id", None),
            max_run_id=getattr(ns, "max_run_id", None),
            from_batch_json=Path(ns.from_batch_json).resolve() if getattr(ns, "from_batch_json", None) else None,
            out_json=Path(ns.out_json).resolve(),
            out_md=md_path,
            persist_ath=bool(getattr(ns, "persist_ath", False)),
            methodology_version=str(getattr(ns, "methodology_version", "") or STRATIFICATION_RULES_DEFAULT),
            persist_notes=getattr(ns, "persist_notes", None),
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

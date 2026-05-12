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
  # One-shot demo (see docs/scientific-report/SUPA-BENCH-RUNBOOK.md):
  python scripts/experiments/supa_benchmark.py workflow --n 1000 --seed 42
  python scripts/experiments/supa_benchmark.py workflow --skip-extract --run-id 1 --preds preds.csv --source-note "..."
  # Smoke-test (pred = ref v2 oracle — not for paper numbers):
  python scripts/experiments/supa_benchmark.py workflow --skip-extract --run-id 1 --preds-demo-ref-v2
  # Or create a preds CSV tutorial-style:
  python scripts/experiments/supa_benchmark.py make-demo-preds --from reports/supa_workflow_specimens_latest.csv --out reports/supa_preds_filled.csv

  python scripts/experiments/supa_benchmark.py extract --n 10000 --seed 42
  python scripts/experiments/supa_benchmark.py export-specimens --out reports/supa_specimens_run1.csv
  python scripts/experiments/supa_benchmark.py import-preds --csv reports/supa_preds_run1.csv --source-note "..."
  python scripts/experiments/supa_benchmark.py eval --run-id 1
  python scripts/experiments/supa_benchmark.py export-tex

Prerequisite DDL (Windows-friendly — no psql required):
  python scripts/sql/apply_sql_file.py scripts/migration/20260209_prq_supa_benchmark_tables.sql
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import random
import re
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text

from app.core.database import engine

NOISE_PROFILE_DEFAULT = "SUP-1.0.0"
LAST_METRICS = ROOT / "reports" / "supa_benchmark_last_metrics.json"
LAST_RUN_ID = ROOT / "reports" / "supa_benchmark_last_run_id.txt"
LAST_IMPORT_MANIFEST = ROOT / "reports" / "supa_benchmark_last_import_manifest.json"
DEFAULT_TEX = ROOT / "docs" / "scientific-report" / "vnai-supa-generated-metrics.tex"


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


def apply_noise(address_v2: str, rng: random.Random, profile: str) -> str:
    """Deterministic given rng state. Operates on v2 reference (modern canonical string)."""
    s = (address_v2 or "").strip()
    if not s:
        return s
    if profile == NOISE_PROFILE_DEFAULT:
        prefixes = ["Gần ", "Đối diện ", "Khu vực ", ""]
        suffixes = ["", " (liên hệ)", "  --  ghi chú", ""]
        if rng.random() < 0.40:
            s = rng.choice(prefixes) + s
        if rng.random() < 0.30:
            s = s + rng.choice(suffixes)
        if rng.random() < 0.25:
            s = s.replace(", ", " ,  ")
        if rng.random() < 0.15:
            s = re.sub(r"\s+", "  ", s)
        return s.strip()
    return s


def cmd_extract(n: int, seed: int, profile: str, notes: str | None) -> int:
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

        specs = conn.execute(
            text(
                "SELECT ref_address_v2, ref_address_v1, pred_standardized "
                "FROM prq.supa_benchmark_specimen WHERE run_id = :id"
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
        metrics = {
            "utc_iso": iso,
            "run_id": rid,
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
                "NFC trim collapse spaces."
            ),
        }

    LAST_METRICS.parent.mkdir(parents=True, exist_ok=True)
    LAST_METRICS.write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
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
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(
                {
                    "specimen_id": r["id"],
                    "run_id": r["run_id"],
                    "local_idx": r["local_idx"],
                    "ground_truth_id": r["ground_truth_id"],
                    "noisy_raw_address": r["noisy_raw_address"] or "",
                    "ref_address_v2": r["ref_address_v2"] or "",
                    "ref_address_v1": r["ref_address_v1"] or "",
                    "pred_standardized": "",
                }
            )
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
) -> int:
    """CSV columns: either (specimen_id, pred_standardized) or (run_id, local_idx, pred_standardized)."""
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
    upd_by_pair = text(
        """
        UPDATE prq.supa_benchmark_specimen
        SET pred_standardized = :pred
        WHERE run_id = :rid AND local_idx = :lidx
        """
    )

    rows_read = 0
    rows_updated = 0
    errors: list[str] = []

    with engine.begin() as conn:
        for row in reader:
            rows_read += 1
            pred_val = (row.get(pred_key) or "").strip()
            if not pred_val:
                continue
            try:
                if has_sid:
                    sid_s = (row.get(fn["specimen_id"]) or "").strip()
                    if not sid_s:
                        continue
                    sid = int(sid_s)
                    if dry_run:
                        rows_updated += 1
                    else:
                        r = conn.execute(upd_by_sid, {"pred": pred_val, "sid": sid})
                        rows_updated += int(r.rowcount or 0)
                else:
                    rid = int((row.get(fn["run_id"]) or "").strip())
                    lidx = int((row.get(fn["local_idx"]) or "").strip())
                    if dry_run:
                        rows_updated += 1
                    else:
                        r = conn.execute(
                            upd_by_pair, {"pred": pred_val, "rid": rid, "lidx": lidx}
                        )
                        rows_updated += int(r.rowcount or 0)
            except (TypeError, ValueError) as e:
                errors.append(f"row {rows_read}: {e}")

    iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest = {
        "utc_iso": iso,
        "csv_path": str(csv_path.resolve()),
        "dry_run": dry_run,
        "rows_read": rows_read,
        "rows_updated": rows_updated,
        "source_note": source_note,
        "git_commit_at_import": _git_head(),
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


def cmd_workflow(
    n: int,
    seed: int,
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
    p_ext.add_argument("--seed", type=int, default=42)
    p_ext.add_argument("--noise-profile", type=str, default=NOISE_PROFILE_DEFAULT)
    p_ext.add_argument("--notes", type=str, default=None)

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
    p_wf.add_argument("--seed", type=int, default=42)
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

    ns = ap.parse_args()
    if ns.cmd == "make-demo-preds":
        return cmd_make_demo_preds(Path(ns.from_csv).resolve(), Path(ns.out).resolve(), ns.column)
    if ns.cmd == "extract":
        return cmd_extract(ns.n, ns.seed, ns.noise_profile, ns.notes)
    if ns.cmd == "eval":
        return cmd_eval(ns.run_id)
    if ns.cmd == "export-specimens":
        return cmd_export_specimens(ns.run_id, Path(ns.out).resolve())
    if ns.cmd == "import-preds":
        return cmd_import_preds(
            Path(ns.csv).resolve(),
            source_note=ns.source_note,
            dry_run=ns.dry_run,
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
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

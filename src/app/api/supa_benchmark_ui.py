"""SUPA-Bench Console API: read metrics + optional subprocess actions (feature-flag)."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from app.api.deps import get_current_user
from app.api.experiments_history import _json_ready
from app.core.config import Config
from app.core.database import engine
from app.paths import repo_root
from app.services.supa_cli_runner import run_supa_benchmark

router = APIRouter()

_SAFE_REL = re.compile(r"^[a-zA-Z0-9_./\-]+$")


def _require_supa_ui_actions() -> None:
    if not Config.SUPA_BENCHMARK_UI_ACTIONS:
        raise HTTPException(
            status_code=403,
            detail="SUPA benchmark UI actions are disabled. Set SUPA_BENCHMARK_UI_ACTIONS=1 in .env.",
        )


def _repo_relative_path(rel: str) -> Path:
    """Resolve rel under repo root; reject traversal."""
    rel = rel.strip().replace("\\", "/")
    if not rel or ".." in rel or rel.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid path")
    if not _SAFE_REL.match(rel):
        raise HTTPException(status_code=400, detail="Path contains disallowed characters")
    root = repo_root().resolve()
    full = (root / rel).resolve()
    if not str(full).startswith(str(root)):
        raise HTTPException(status_code=400, detail="Path escapes repository root")
    return full


def _reports_output_path(rel: str) -> Path:
    p = _repo_relative_path(rel)
    reports = (repo_root() / "reports").resolve()
    if not str(p).startswith(str(reports)):
        raise HTTPException(status_code=400, detail="Output must be under reports/")
    return p


def _run_cli_and_response(argv: list[str]) -> dict[str, Any]:
    timeout = Config.SUPA_BENCHMARK_CLI_TIMEOUT_SEC
    try:
        code, out, err = run_supa_benchmark(argv, timeout_sec=timeout)
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="SUPA CLI timeout") from None
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    last_id = _read_last_run_id_file()
    return {
        "exit_code": code,
        "stdout": out,
        "stderr": err,
        "last_run_id_hint": last_id,
        "ok": code == 0,
    }


def _read_last_run_id_file() -> int | None:
    p = repo_root() / "reports" / "supa_benchmark_last_run_id.txt"
    if not p.is_file():
        return None
    try:
        return int(p.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return None


@router.get("/supa-runs/{run_id}", summary="SUPA run detail + specimen counts")
def get_supa_run(
    run_id: int,
    current_user: str = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    sql = text(
        """
        SELECT id, created_at, n_requested, n_realized, rng_seed, noise_profile_id,
               git_commit, notes, eval_metrics_json
        FROM prq.supa_benchmark_run
        WHERE id = :id
        """
    )
    try:
        with engine.connect() as conn:
            row = conn.execute(sql, {"id": int(run_id)}).mappings().first()
    except ProgrammingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not row:
        raise HTTPException(status_code=404, detail="run not found")
    d = dict(row)
    d["eval_metrics_json"] = _json_ready(d.get("eval_metrics_json"))
    if hasattr(d.get("created_at"), "isoformat"):
        d["created_at"] = d["created_at"].isoformat()

    specimen_total = None
    stratum_counts: dict[str, int] = {}
    try:
        with engine.connect() as conn:
            specimen_total = conn.execute(
                text("SELECT COUNT(*) FROM prq.supa_benchmark_specimen WHERE run_id = :id"),
                {"id": int(run_id)},
            ).scalar_one()
            srows = conn.execute(
                text(
                    """
                    SELECT COALESCE(NULLIF(TRIM(stratum_code), ''), 'UNLABELED') AS sc, COUNT(*)::int AS c
                    FROM prq.supa_benchmark_specimen
                    WHERE run_id = :id
                    GROUP BY 1
                    ORDER BY 1
                    """
                ),
                {"id": int(run_id)},
            ).mappings().all()
            stratum_counts = {str(r["sc"]): int(r["c"]) for r in srows}
    except ProgrammingError:
        stratum_counts = {}

    d["specimen_count"] = int(specimen_total) if specimen_total is not None else None
    d["stratum_counts"] = stratum_counts
    return {"run": d}


@router.get("/supa-stratified-summaries", summary="ath.supa_stratified_eval_summary rows")
def list_supa_stratified_summaries(
    current_user: str = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=200),
) -> dict[str, Any]:
    del current_user
    sql = text(
        """
        SELECT id, created_at, methodology_version, k_runs, n_per_run,
               run_id_min, run_id_max, metrics_json, notes, git_commit
        FROM ath.supa_stratified_eval_summary
        ORDER BY id DESC
        LIMIT :lim
        """
    )
    try:
        with engine.connect() as conn:
            rows = conn.execute(sql, {"lim": int(limit)}).mappings().all()
    except ProgrammingError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"ath.supa_stratified_eval_summary missing — apply migration 20260513: {exc}",
        ) from exc
    out = []
    for r in rows:
        d = dict(r)
        d["metrics_json"] = _json_ready(d.get("metrics_json"))
        if hasattr(d.get("created_at"), "isoformat"):
            d["created_at"] = d["created_at"].isoformat()
        out.append(d)
    return {"summaries": out}


@router.get("/supa-publication-baseline", summary="Pinned aggregate JSON for Ch.9.5.1 comparison")
def get_publication_baseline(
    current_user: str = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    rel = Config.SUPA_PUBLICATION_BASELINE_JSON
    path = (repo_root() / rel).resolve() if not os.path.isabs(rel) else Path(rel).resolve()
    if not path.is_file():
        return {
            "path": str(rel),
            "resolved": str(path),
            "payload": None,
            "message": "Baseline JSON file not found; set SUPA_PUBLICATION_BASELINE_JSON or add the report file.",
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail=f"Could not read baseline: {exc}") from exc
    return {"path": str(rel), "resolved": str(path), "payload": payload, "message": None}


class SupaAggregatePreviewBody(BaseModel):
    last_n: int | None = Field(default=None, ge=1, le=5000)
    min_run_id: int | None = None
    max_run_id: int | None = None
    from_batch_json: str | None = Field(
        default=None,
        description="Relative path under repo, e.g. reports/supa_benchmark_last_batch_range.json",
    )
    persist_ath: bool = False
    methodology_version: str = "strat-v1"
    persist_notes: str | None = None


@router.post("/supa-aggregate-preview", summary="Run aggregate-runs → JSON (temp file); optional persist-ath")
def supa_aggregate_preview(
    body: SupaAggregatePreviewBody,
    current_user: str = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    _require_supa_ui_actions()
    range_mode = body.min_run_id is not None and body.max_run_id is not None
    batch_path: Path | None = None
    if body.from_batch_json:
        batch_path = _repo_relative_path(body.from_batch_json)
        if not batch_path.is_file():
            raise HTTPException(status_code=400, detail="from_batch_json file not found")
    elif not range_mode and (body.last_n is None or body.last_n < 1):
        raise HTTPException(status_code=400, detail="Provide last_n or min_run_id+max_run_id or from_batch_json")

    fd, tmp_json = tempfile.mkstemp(suffix=".json", prefix="supa_agg_")
    os.close(fd)
    try:
        argv: list[str] = [
            "aggregate-runs",
            "--out-json",
            tmp_json,
            "--out-md",
            "none",
        ]
        if batch_path is not None:
            argv += ["--from-batch-json", str(batch_path)]
        elif range_mode:
            argv += ["--min-run-id", str(int(body.min_run_id)), "--max-run-id", str(int(body.max_run_id))]
        else:
            argv += ["--last-n", str(int(body.last_n or 50))]
        if body.persist_ath:
            argv.append("--persist-ath")
            argv += ["--methodology-version", body.methodology_version or "strat-v1"]
            if body.persist_notes:
                argv += ["--persist-notes", body.persist_notes]

        timeout = Config.SUPA_BENCHMARK_CLI_TIMEOUT_SEC
        code, out, err = run_supa_benchmark(argv, timeout_sec=timeout)
        payload: Any = None
        try:
            payload = json.loads(Path(tmp_json).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = None
        return {
            "exit_code": code,
            "stdout": out,
            "stderr": err,
            "payload": payload,
        }
    finally:
        try:
            os.unlink(tmp_json)
        except OSError:
            pass


# ─── Actions (subprocess) ───────────────────────────────────────────────────


class SupaExtractBody(BaseModel):
    n: int = Field(..., ge=1, le=500_000)
    seed: int | None = None
    noise_profile: str | None = None
    notes: str | None = None


class SupaExtractStratifiedBody(BaseModel):
    n: int = Field(default=2000, ge=1, le=500_000)
    seed: int | None = None
    strat_version: str = "strat-v1"
    max_pool_rows: int = Field(default=100_000, ge=1000, le=5_000_000)
    notes: str | None = None


class SupaEvalBody(BaseModel):
    run_id: int | None = None


class SupaExportSpecimensBody(BaseModel):
    run_id: int | None = None
    out_relative: str = Field(default="reports/supa_ui_export_specimens.csv")

    @field_validator("out_relative")
    @classmethod
    def _check_out(cls, v: str) -> str:
        p = v.strip().replace("\\", "/")
        if not p.startswith("reports/"):
            raise ValueError("out_relative must start with reports/")
        return p


class SupaExportTexBody(BaseModel):
    metrics_json_relative: str | None = None
    out_relative: str = Field(default="docs/scientific-report/vnai-supa-generated-metrics.tex")

    @field_validator("out_relative", "metrics_json_relative")
    @classmethod
    def _paths(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if ".." in v:
            raise ValueError("invalid path")
        return v


class SupaWorkflowBody(BaseModel):
    n: int = Field(default=10000, ge=1, le=500_000)
    seed: int | None = None
    noise_profile: str | None = None
    notes: str | None = None
    specimens_out_relative: str = Field(default="reports/supa_workflow_specimens_latest.csv")
    preds_relative: str | None = None
    preds_demo_ref_v2: bool = False
    source_note: str | None = None
    skip_extract: bool = False
    run_id: int | None = None


class SupaMakeDemoPredsBody(BaseModel):
    from_relative: str
    out_relative: str
    column: Literal["ref_address_v2", "ref_address_v1"] = "ref_address_v2"


class SupaReplicateBody(BaseModel):
    n_runs: int = Field(..., ge=1)
    mode: Literal["sweep-seed", "repeat-determinism"]
    seed_start: int | None = None
    seed: int = 42
    n: int = Field(..., ge=1, le=500_000)
    noise_profile: str | None = None
    notes: str | None = None
    retention: int = Field(default=0, ge=0, le=10_000)
    specimens_out_relative: str = Field(default="reports/supa_workflow_specimens_latest.csv")
    preds_relative: str | None = None
    preds_demo_ref_v2: bool = False
    source_note: str | None = None
    export_tex_last: bool = False
    skip_import: bool = False


class SupaReplicateStratifiedBody(BaseModel):
    k_runs: int = Field(..., ge=1)
    n: int = Field(default=2000, ge=1, le=500_000)
    base_seed: int | None = None
    strat_version: str = "strat-v1"
    max_pool_rows: int = Field(default=100_000, ge=1000, le=5_000_000)
    notes: str | None = None
    retention: int = Field(default=0, ge=0, le=10_000)
    specimens_out_relative: str = Field(default="reports/supa_workflow_specimens_latest.csv")
    preds_relative: str | None = None
    preds_demo_ref_v2: bool = False
    source_note: str | None = None
    export_tex_last: bool = False
    skip_import: bool = False


@router.post("/supa-actions/extract")
def supa_action_extract(
    body: SupaExtractBody,
    current_user: str = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    _require_supa_ui_actions()
    argv = ["extract", "--n", str(body.n)]
    if body.seed is not None:
        argv += ["--seed", str(body.seed)]
    if body.noise_profile:
        argv += ["--noise-profile", body.noise_profile]
    if body.notes:
        argv += ["--notes", body.notes]
    return _run_cli_and_response(argv)


@router.post("/supa-actions/extract-stratified")
def supa_action_extract_stratified(
    body: SupaExtractStratifiedBody,
    current_user: str = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    _require_supa_ui_actions()
    argv = [
        "extract-stratified",
        "--n",
        str(body.n),
        "--strat-version",
        body.strat_version,
        "--max-pool-rows",
        str(body.max_pool_rows),
    ]
    if body.seed is not None:
        argv += ["--seed", str(body.seed)]
    if body.notes:
        argv += ["--notes", body.notes]
    return _run_cli_and_response(argv)


@router.post("/supa-actions/eval")
def supa_action_eval(
    body: SupaEvalBody,
    current_user: str = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    _require_supa_ui_actions()
    argv = ["eval"]
    if body.run_id is not None:
        argv += ["--run-id", str(body.run_id)]
    return _run_cli_and_response(argv)


@router.post("/supa-actions/export-specimens")
def supa_action_export_specimens(
    body: SupaExportSpecimensBody,
    current_user: str = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    _require_supa_ui_actions()
    out_path = _reports_output_path(body.out_relative)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    argv = ["export-specimens", "--out", str(out_path)]
    if body.run_id is not None:
        argv += ["--run-id", str(body.run_id)]
    return {**_run_cli_and_response(argv), "out_path": str(out_path)}


@router.get("/supa-runs/{run_id}/export-specimens-csv", summary="Download specimens CSV (temp export)")
def download_supa_export_specimens(
    run_id: int,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
) -> FileResponse:
    del current_user
    _require_supa_ui_actions()
    fd, tmp = tempfile.mkstemp(suffix=".csv", prefix=f"supa_specimens_{run_id}_")
    os.close(fd)
    tmp_path = Path(tmp)
    argv = ["export-specimens", "--run-id", str(int(run_id)), "--out", str(tmp_path)]
    res = _run_cli_and_response(argv)
    if not res["ok"] or not tmp_path.is_file():
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise HTTPException(
            status_code=400,
            detail={"exit_code": res["exit_code"], "stderr": res["stderr"], "stdout": res["stdout"]},
        )
    background_tasks.add_task(lambda p=tmp_path: p.unlink(missing_ok=True))
    return FileResponse(
        path=str(tmp_path),
        filename=f"supa_specimens_run_{run_id}.csv",
        media_type="text/csv",
    )


@router.post("/supa-actions/import-preds")
async def supa_action_import_preds(
    current_user: str = Depends(get_current_user),
    file: UploadFile = File(...),
    source_note: str = Form(...),
    dry_run: bool = Form(default=False),
    no_measured_latency: bool = Form(default=False),
) -> dict[str, Any]:
    del current_user
    _require_supa_ui_actions()
    suffix = Path(file.filename or "preds.csv").suffix or ".csv"
    fd, tmp = tempfile.mkstemp(suffix=suffix, prefix="supa_import_")
    os.close(fd)
    tmp_path = Path(tmp)
    try:
        data = await file.read()
        tmp_path.write_bytes(data)
        argv = ["import-preds", "--csv", str(tmp_path), "--source-note", source_note]
        if dry_run:
            argv.append("--dry-run")
        if no_measured_latency:
            argv.append("--no-measured-latency")
        return _run_cli_and_response(argv)
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass


@router.post("/supa-actions/export-tex")
def supa_action_export_tex(
    body: SupaExportTexBody,
    current_user: str = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    _require_supa_ui_actions()
    argv = ["export-tex"]
    if body.metrics_json_relative:
        mj = _repo_relative_path(body.metrics_json_relative)
        argv += ["--metrics-json", str(mj)]
    out_p = _repo_relative_path(body.out_relative)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    argv += ["--out", str(out_p)]
    return {**_run_cli_and_response(argv), "out_path": str(out_p)}


@router.post("/supa-actions/workflow")
def supa_action_workflow(
    body: SupaWorkflowBody,
    current_user: str = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    _require_supa_ui_actions()
    if body.preds_demo_ref_v2 and body.preds_relative:
        raise HTTPException(status_code=400, detail="Use either preds_relative or preds_demo_ref_v2, not both")
    spec = _reports_output_path(body.specimens_out_relative)
    spec.parent.mkdir(parents=True, exist_ok=True)
    argv = [
        "workflow",
        "--n",
        str(body.n),
        "--specimens-out",
        str(spec),
    ]
    if body.seed is not None:
        argv += ["--seed", str(body.seed)]
    if body.noise_profile:
        argv += ["--noise-profile", body.noise_profile]
    if body.notes:
        argv += ["--notes", body.notes]
    if body.skip_extract:
        argv.append("--skip-extract")
    if body.run_id is not None:
        argv += ["--run-id", str(body.run_id)]
    if body.preds_relative:
        pr = _repo_relative_path(body.preds_relative)
        argv += ["--preds", str(pr)]
        if body.source_note:
            argv += ["--source-note", body.source_note]
    elif body.preds_demo_ref_v2:
        argv.append("--preds-demo-ref-v2")
    return {**_run_cli_and_response(argv), "specimens_out": str(spec)}


@router.post("/supa-actions/make-demo-preds")
def supa_action_make_demo_preds(
    body: SupaMakeDemoPredsBody,
    current_user: str = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    _require_supa_ui_actions()
    src = _reports_output_path(body.from_relative)
    if not src.is_file():
        raise HTTPException(status_code=400, detail="from_relative file not found")
    dst = _reports_output_path(body.out_relative)
    dst.parent.mkdir(parents=True, exist_ok=True)
    argv = [
        "make-demo-preds",
        "--from",
        str(src),
        "--out",
        str(dst),
        "--column",
        body.column,
    ]
    return {**_run_cli_and_response(argv), "out_path": str(dst)}


@router.post("/supa-actions/replicate")
def supa_action_replicate(
    body: SupaReplicateBody,
    current_user: str = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    _require_supa_ui_actions()
    cap = Config.SUPA_BENCHMARK_MAX_REPLICATE_RUNS
    if body.n_runs > cap:
        raise HTTPException(
            status_code=400,
            detail=f"n_runs exceeds limit {cap} (SUPA_BENCHMARK_MAX_REPLICATE_RUNS)",
        )
    if body.preds_demo_ref_v2 and body.preds_relative:
        raise HTTPException(status_code=400, detail="Use either preds_relative or preds_demo_ref_v2, not both")
    spec = _reports_output_path(body.specimens_out_relative)
    spec.parent.mkdir(parents=True, exist_ok=True)
    argv = [
        "replicate",
        "--n-runs",
        str(body.n_runs),
        "--mode",
        body.mode,
        "--n",
        str(body.n),
        "--retention",
        str(body.retention),
        "--specimens-out",
        str(spec),
        "--seed",
        str(body.seed),
    ]
    if body.seed_start is not None:
        argv += ["--seed-start", str(body.seed_start)]
    if body.noise_profile:
        argv += ["--noise-profile", body.noise_profile]
    if body.notes:
        argv += ["--notes", body.notes]
    if body.preds_relative:
        argv += ["--preds", str(_repo_relative_path(body.preds_relative))]
        if body.source_note:
            argv += ["--source-note", body.source_note]
    elif body.preds_demo_ref_v2:
        argv.append("--preds-demo-ref-v2")
        if body.source_note:
            argv += ["--source-note", body.source_note]
    if body.export_tex_last:
        argv.append("--export-tex-last")
    if body.skip_import:
        argv.append("--skip-import")
    return {**_run_cli_and_response(argv), "specimens_out": str(spec)}


@router.post("/supa-actions/replicate-stratified")
def supa_action_replicate_stratified(
    body: SupaReplicateStratifiedBody,
    current_user: str = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    _require_supa_ui_actions()
    cap = Config.SUPA_BENCHMARK_MAX_REPLICATE_RUNS
    if body.k_runs > cap:
        raise HTTPException(
            status_code=400,
            detail=f"k_runs exceeds limit {cap} (SUPA_BENCHMARK_MAX_REPLICATE_RUNS)",
        )
    if body.preds_demo_ref_v2 and body.preds_relative:
        raise HTTPException(status_code=400, detail="Use either preds_relative or preds_demo_ref_v2, not both")
    spec = _reports_output_path(body.specimens_out_relative)
    spec.parent.mkdir(parents=True, exist_ok=True)
    argv = [
        "replicate-stratified",
        "--k-runs",
        str(body.k_runs),
        "--n",
        str(body.n),
        "--strat-version",
        body.strat_version,
        "--max-pool-rows",
        str(body.max_pool_rows),
        "--retention",
        str(body.retention),
        "--specimens-out",
        str(spec),
    ]
    if body.base_seed is not None:
        argv += ["--base-seed", str(body.base_seed)]
    if body.notes:
        argv += ["--notes", body.notes]
    if body.preds_relative:
        argv += ["--preds", str(_repo_relative_path(body.preds_relative))]
        if body.source_note:
            argv += ["--source-note", body.source_note]
    elif body.preds_demo_ref_v2:
        argv.append("--preds-demo-ref-v2")
        if body.source_note:
            argv += ["--source-note", body.source_note]
    if body.export_tex_last:
        argv.append("--export-tex-last")
    if body.skip_import:
        argv.append("--skip-import")
    return {**_run_cli_and_response(argv), "specimens_out": str(spec)}

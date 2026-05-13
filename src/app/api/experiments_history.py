"""Experiment history: SUPA runs + retrieval eval runs (DB-backed)."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from app.api.deps import get_current_user
from app.core.database import engine

router = APIRouter()


def _json_ready(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return val
    if isinstance(val, (bytes, memoryview)):
        try:
            return json.loads(val.decode("utf-8"))
        except Exception:
            return None
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            return val
    return val


@router.get("/supa-runs", summary="List SUPA benchmark runs + eval metrics")
def list_supa_runs(
    current_user: str = Depends(get_current_user),
    limit: int = Query(200, ge=1, le=2000),
) -> dict[str, Any]:
    del current_user
    sql = text(
        """
        SELECT id, created_at, n_requested, n_realized, rng_seed, noise_profile_id,
               git_commit, notes, eval_metrics_json
        FROM prq.supa_benchmark_run
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
            detail=f"Database schema missing SUPA tables or column: {exc}",
        ) from exc
    out = []
    for r in rows:
        d = dict(r)
        d["eval_metrics_json"] = _json_ready(d.get("eval_metrics_json"))
        if hasattr(d.get("created_at"), "isoformat"):
            d["created_at"] = d["created_at"].isoformat()
        out.append(d)
    return {"runs": out}


def _mount_supa_benchmark_ui_routes() -> None:
    """Bundle SUPA console/read routes on the same router as list endpoints.

    Keeps a single ``include_router(..., prefix="/experiments")`` in ``server.py`` so
    deployments cannot accidentally register list routes without the SUPA UI paths.
    """
    from app.api import supa_benchmark_ui as _supa_ui

    router.include_router(_supa_ui.router)

_mount_supa_benchmark_ui_routes()


@router.get("/retrieval-runs", summary="List Siamese/mGTE retrieval evaluation runs")
def list_retrieval_runs(
    current_user: str = Depends(get_current_user),
    limit: int = Query(200, ge=1, le=2000),
) -> dict[str, Any]:
    del current_user
    sql = text(
        """
        SELECT id, created_at, model_name, limit_pairs, top_k_max, metrics_json, notes, git_commit
        FROM ath.retrieval_eval_run
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
            detail=f"Table ath.retrieval_eval_run missing — apply migration 20260512_retrieval_eval_and_supa_metrics.sql: {exc}",
        ) from exc
    out = []
    for r in rows:
        d = dict(r)
        d["metrics_json"] = _json_ready(d.get("metrics_json"))
        if hasattr(d.get("created_at"), "isoformat"):
            d["created_at"] = d["created_at"].isoformat()
        out.append(d)
    return {"runs": out}

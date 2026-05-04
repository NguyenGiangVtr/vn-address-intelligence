"""Shared persistence helpers for AI job outputs.

This module stores training history rows and benchmark baseline snapshots in
the project database so pipeline jobs can record results without going through
the UI.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Mapping, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.database import BenchmarkModelBaseline, SessionLocal, TrainingHistory


def record_training_history(
    *,
    version: str,
    accuracy: float,
    f1_score: float,
    loss: float,
    samples_count: int,
    notes: Optional[str] = None,
) -> None:
    """Append one training run to ath.training_history."""
    session = SessionLocal()
    try:
        session.add(
            TrainingHistory(
                version=version[:20],
                accuracy=accuracy,
                f1_score=f1_score,
                loss=loss,
                samples_count=samples_count,
                notes=notes,
            )
        )
        session.commit()
    finally:
        session.close()


def upsert_benchmark_baseline(
    *,
    model_key: str,
    model_name: str,
    f1: float,
    throughput: float,
    cost_per_million: float,
    google_match: float,
    sample_size: int,
    notes: Optional[str] = None,
) -> None:
    """Upsert a benchmark baseline row in ath.benchmark_model_baselines."""
    session = SessionLocal()
    try:
        row = session.query(BenchmarkModelBaseline).filter(BenchmarkModelBaseline.model_key == model_key).one_or_none()
        if row is None:
            row = BenchmarkModelBaseline(model_key=model_key)
            session.add(row)

        row.model_name = model_name
        row.f1 = f1
        row.throughput = throughput
        row.cost_per_million = cost_per_million
        row.google_match = google_match
        row.sample_size = sample_size
        row.notes = notes

        session.commit()
    finally:
        session.close()


def upsert_benchmark_baselines(
    metrics_by_model: Mapping[str, Mapping[str, Any]],
    *,
    notes: Optional[str] = None,
) -> int:
    """Persist multiple benchmark rows and return how many were written."""
    display_names = {
        "phobert": "PhoBERT",
        "siamese": "Siamese (mGTE)",
        "llm": "LLM (Qwen3)",
    }
    written = 0

    for model_key, metric in metrics_by_model.items():
        model_name = str(metric.get("name") or display_names.get(model_key, model_key))
        f1 = float(metric.get("f1", 0.0))
        throughput = float(metric.get("throughput", 0.0))
        cost_per_million = float(metric.get("costPerMillion", 0.0))
        google_match = float(metric.get("googleMatch", 0.0))
        sample_size = int(metric.get("sampleSize", metric.get("n_samples", 0)) or 0)

        upsert_benchmark_baseline(
            model_key=model_key,
            model_name=model_name,
            f1=f1,
            throughput=throughput,
            cost_per_million=cost_per_million,
            google_match=google_match,
            sample_size=sample_size,
            notes=notes,
        )
        written += 1

    return written
"""
Evaluate Siamese/mGTE retriever: R@k, top-1 exact, MRR, NDCG.

Pairs (query, gold) = (old_address, address) from prq.ground_truth.
Corpus = deduplicated gold strings (same protocol as historical script).
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

from app.core.database import SessionLocal, engine


def _dcg(relevances: list[int]) -> float:
    return sum(rel / math.log2(i + 2) for i, rel in enumerate(relevances))


def _ndcg_at_k(hits: list[int], k: int) -> float:
    gains = hits[:k]
    best = sorted(gains, reverse=True)
    denom = _dcg(best)
    return (_dcg(gains) / denom) if denom else 0.0


def _load_eval_pairs(limit: int) -> list[tuple[str, str]]:
    sql = text(
        """
        SELECT old_address, address
        FROM prq.ground_truth
        WHERE old_address IS NOT NULL AND address IS NOT NULL
        ORDER BY id DESC
        LIMIT :limit
        """
    )
    session = SessionLocal()
    try:
        rows = session.execute(sql, {"limit": int(limit)}).mappings().all()
    finally:
        session.close()
    return [(r["old_address"], r["address"]) for r in rows]


def _git_head() -> str | None:
    try:
        root = Path(__file__).resolve().parents[3]
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(root),
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip()[:40]
    except Exception:
        return None


def _parse_k_list(raw: str) -> list[int]:
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    ks: list[int] = []
    for p in parts:
        k = int(p)
        if k < 1:
            raise ValueError(f"Invalid k (must be >= 1): {p!r}")
        ks.append(k)
    return sorted(set(ks))


def evaluate_retrieval(
    model_name: str,
    top_k: int,
    limit: int,
    k_list: list[int],
) -> dict:
    """Run retrieval metrics; returns a JSON-serializable dict."""
    if top_k < 1:
        raise ValueError("top_k must be >= 1")
    k_list = sorted({int(k) for k in k_list if int(k) >= 1})
    if not k_list:
        raise ValueError("k_list must be non-empty")
    max_k_needed = max(max(k_list), top_k)

    from app.ai.models.siamese_mgte import SiameseMGTE

    pairs = _load_eval_pairs(limit)
    corpus = list({gold for _, gold in pairs})
    retriever = SiameseMGTE(model_name=model_name)
    retriever.encode_corpus(corpus)

    recall_hits = {k: 0 for k in k_list}
    top1_hits = 0
    mrr = 0.0
    ndcg = 0.0

    for query, gold in pairs:
        preds = retriever.retrieve_top_k(query, top_k=max_k_needed)
        ranked = [p[0] for p in preds]
        hits = [1 if x == gold else 0 for x in ranked]
        if hits and hits[0]:
            top1_hits += 1
        for kk in k_list:
            cap = min(kk, len(hits))
            if cap > 0 and any(hits[:cap]):
                recall_hits[kk] += 1
        rank = next((i + 1 for i, h in enumerate(hits) if h), None)
        if rank:
            mrr += 1.0 / rank
        ndcg += _ndcg_at_k(hits, top_k)

    n = len(pairs)
    denom = max(1, n)

    metrics: dict = {
        "n_pairs": n,
        "corpus_unique_addresses": len(corpus),
        "top_k_for_mrr_ndcg": top_k,
        "k_list_evaluated": k_list,
        "top1_exact_rate": top1_hits / denom,
        "mrr_at_top_k": mrr / denom,
        f"ndcg_at_{top_k}": ndcg / denom,
    }
    for kk in k_list:
        metrics[f"recall_at_{kk}"] = recall_hits[kk] / denom
    return metrics


def _persist_retrieval_run(
    model_name: str,
    limit: int,
    top_k: int,
    metrics: dict,
    notes: str | None,
    git_commit: str | None,
) -> int | None:
    ins = text(
        """
        INSERT INTO ath.retrieval_eval_run
            (model_name, limit_pairs, top_k_max, metrics_json, notes, git_commit)
        VALUES
            (:model_name, :limit_pairs, :top_k_max, CAST(:metrics_json AS jsonb), :notes, :git_commit)
        RETURNING id
        """
    )
    payload = {
        "model_name": model_name,
        "limit_pairs": int(limit),
        "top_k_max": int(top_k),
        "metrics_json": json.dumps(metrics, ensure_ascii=False),
        "notes": notes,
        "git_commit": git_commit,
    }
    with engine.begin() as conn:
        rid = conn.execute(ins, payload).scalar_one()
    return int(rid)


def run_cli(
    model_name: str,
    top_k: int,
    limit: int,
    k_list: list[int],
    out_json: Path | None,
    persist_db: bool,
    notes: str | None,
) -> dict:
    iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    git_c = _git_head()
    metrics_core = evaluate_retrieval(model_name, top_k, limit, k_list)
    record: dict = {
        "utc_iso": iso,
        "pythonpath_head": sys.path[:3],
        "model_name": model_name,
        "limit": int(limit),
        "top_k": int(top_k),
        "git_commit": git_c,
        "notes": notes,
        **metrics_core,
    }
    if out_json is not None:
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if persist_db:
        db_id = _persist_retrieval_run(
            model_name=model_name,
            limit=limit,
            top_k=top_k,
            metrics=record,
            notes=notes,
            git_commit=git_c,
        )
        record["retrieval_eval_run_id"] = db_id

    n = metrics_core["n_pairs"]
    denom = max(1, n)
    print(f"samples={n}")
    print(f"top1_exact_rate={metrics_core['top1_exact_rate']:.4f}")
    for kk in k_list:
        print(f"recall_at_{kk}={metrics_core[f'recall_at_{kk}']:.4f}")
    print(f"mrr@{top_k}={metrics_core['mrr_at_top_k']:.4f}")
    print(f"ndcg@{top_k}={metrics_core[f'ndcg_at_{top_k}']:.4f}")
    if out_json:
        print(f"wrote_json={out_json.resolve()}")
    if persist_db:
        print(f"db_row=ath.retrieval_eval_run id={record.get('retrieval_eval_run_id')}")
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Siamese/mGTE retriever (R@k, MRR, NDCG)")
    parser.add_argument("--model-name", default="Alibaba-NLP/gte-multilingual-base")
    parser.add_argument("--top-k", type=int, default=10, help="Rank depth for MRR/NDCG denominators")
    parser.add_argument("--limit", type=int, default=2000)
    parser.add_argument(
        "--k-list",
        type=str,
        default="1,3,5,10",
        help="Comma-separated k values for recall@k (each capped by retrieved list length)",
    )
    parser.add_argument(
        "--out-json",
        type=str,
        default=None,
        help="Write full run record (metrics + provenance) to this JSON file",
    )
    parser.add_argument(
        "--persist-db",
        action="store_true",
        help="INSERT completed run into ath.retrieval_eval_run (requires migration)",
    )
    parser.add_argument("--notes", type=str, default=None)
    args = parser.parse_args()
    k_list = _parse_k_list(args.k_list)
    out_path = Path(args.out_json).resolve() if args.out_json else None
    run_cli(
        model_name=args.model_name,
        top_k=args.top_k,
        limit=args.limit,
        k_list=k_list,
        out_json=out_path,
        persist_db=bool(args.persist_db),
        notes=args.notes,
    )


if __name__ == "__main__":
    main()

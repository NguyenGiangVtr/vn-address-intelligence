"""
Evaluate retriever with Top-k, MRR, NDCG.
"""

from __future__ import annotations

import argparse
import math

from sqlalchemy import text

from app.ai.models.siamese_mgte import SiameseMGTE
from app.core.database import SessionLocal


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


def evaluate(model_name: str, top_k: int, limit: int) -> None:
    pairs = _load_eval_pairs(limit)
    corpus = list({gold for _, gold in pairs})
    retriever = SiameseMGTE(model_name=model_name)
    retriever.encode_corpus(corpus)

    top1 = 0
    top5 = 0
    mrr = 0.0
    ndcg = 0.0

    for query, gold in pairs:
        preds = retriever.retrieve_top_k(query, top_k=top_k)
        ranked = [p[0] for p in preds]
        hits = [1 if x == gold else 0 for x in ranked]
        if hits and hits[0]:
            top1 += 1
        if any(hits[: min(5, len(hits))]):
            top5 += 1
        rank = next((i + 1 for i, h in enumerate(hits) if h), None)
        if rank:
            mrr += 1.0 / rank
        ndcg += _ndcg_at_k(hits, top_k)

    n = max(1, len(pairs))
    print(f"samples={n}")
    print(f"top1={top1/n:.4f}")
    print(f"top5={top5/n:.4f}")
    print(f"mrr@{top_k}={mrr/n:.4f}")
    print(f"ndcg@{top_k}={ndcg/n:.4f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Siamese retriever")
    parser.add_argument("--model-name", default="Alibaba-NLP/gte-multilingual-base")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--limit", type=int, default=2000)
    args = parser.parse_args()
    evaluate(args.model_name, args.top_k, args.limit)


if __name__ == "__main__":
    main()

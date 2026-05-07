"""
Build old/new address training pairs and fine-tune mGTE Siamese model.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from sentence_transformers import InputExample, SentenceTransformer, losses
from torch.utils.data import DataLoader
from sqlalchemy import text

from app.core.database import SessionLocal


@dataclass
class AddressPair:
    old_address: str
    new_address: str
    label: float


def load_pairs(limit: int = 20000) -> list[AddressPair]:
    sql = text(
        """
        SELECT old_address, address
        FROM prq.ground_truth
        WHERE old_address IS NOT NULL
          AND address IS NOT NULL
          AND length(trim(old_address)) > 5
          AND length(trim(address)) > 5
        ORDER BY id
        LIMIT :limit
        """
    )
    session = SessionLocal()
    try:
        rows = session.execute(sql, {"limit": int(limit)}).mappings().all()
    finally:
        session.close()

    pairs = [AddressPair(r["old_address"].strip(), r["address"].strip(), 1.0) for r in rows]
    return pairs


def train(output_dir: str, model_name: str, limit: int, epochs: int, batch_size: int, lr: float) -> None:
    pairs = load_pairs(limit=limit)
    examples = [InputExample(texts=[p.old_address, p.new_address], label=p.label) for p in pairs]
    model = SentenceTransformer(model_name, trust_remote_code=True)
    train_loader = DataLoader(examples, shuffle=True, batch_size=batch_size)
    train_loss = losses.CosineSimilarityLoss(model=model)
    warmup_steps = max(100, int(len(train_loader) * epochs * 0.1))
    model.fit(
        train_objectives=[(train_loader, train_loss)],
        epochs=epochs,
        warmup_steps=warmup_steps,
        optimizer_params={"lr": lr},
        output_path=output_dir,
        show_progress_bar=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Siamese mGTE on ground_truth old/new pairs")
    parser.add_argument("--output", default="models/mgte-siamese-vn")
    parser.add_argument("--model-name", default="Alibaba-NLP/gte-multilingual-base")
    parser.add_argument("--limit", type=int, default=20000)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=2e-5)
    args = parser.parse_args()
    train(args.output, args.model_name, args.limit, args.epochs, args.batch_size, args.lr)


if __name__ == "__main__":
    main()

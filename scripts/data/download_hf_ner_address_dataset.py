"""
Download and snapshot Hugging Face ner-address-standard-dataset.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from datasets import load_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Download HF NER address dataset snapshot")
    parser.add_argument("--dataset", default="dathuynh1108/ner-address-standard-dataset")
    parser.add_argument("--output-dir", default="data/hf_snapshots")
    parser.add_argument("--train-limit", type=int, default=50000)
    parser.add_argument("--test-limit", type=int, default=5000)
    args = parser.parse_args()

    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    train_split = load_dataset(args.dataset, split=f"train[:{args.train_limit}]")
    test_split = load_dataset(args.dataset, split=f"test[:{args.test_limit}]")

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snapshot_dir = out_dir / f"{args.dataset.replace('/', '_')}_{ts}"
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    train_path = snapshot_dir / "train.jsonl"
    test_path = snapshot_dir / "test.jsonl"
    meta_path = snapshot_dir / "metadata.json"

    with train_path.open("w", encoding="utf-8") as f:
        for item in train_split:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    with test_path.open("w", encoding="utf-8") as f:
        for item in test_split:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    metadata = {
        "dataset": args.dataset,
        "captured_at_utc": ts,
        "train_count": len(train_split),
        "test_count": len(test_split),
        "files": {"train": str(train_path), "test": str(test_path)},
    }
    meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

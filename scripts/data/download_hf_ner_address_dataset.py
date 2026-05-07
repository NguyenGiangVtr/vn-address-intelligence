"""
Download and snapshot Hugging Face ner-address-standard-dataset.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from itertools import islice
from pathlib import Path

from datasets import load_dataset


def _take_records(dataset: str, split: str, limit: int, streaming: bool) -> list[dict]:
    ds = load_dataset(dataset, split=split, streaming=streaming)
    if streaming:
        return list(islice(ds, limit))
    return [ds[i] for i in range(min(limit, len(ds)))]


def main() -> None:
    parser = argparse.ArgumentParser(description="Download HF NER address dataset snapshot")
    parser.add_argument("--dataset", default="dathuynh1108/ner-address-standard-dataset")
    parser.add_argument("--output-dir", default="data/hf_snapshots")
    parser.add_argument("--train-limit", type=int, default=50000)
    parser.add_argument("--test-limit", type=int, default=5000)
    parser.add_argument(
        "--streaming",
        action="store_true",
        help="Force Hugging Face streaming mode (more robust, avoids shard generation errors).",
    )
    args = parser.parse_args()

    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    train_records: list[dict]
    test_records: list[dict]
    used_streaming = bool(args.streaming)

    try:
        train_records = _take_records(args.dataset, "train", args.train_limit, streaming=used_streaming)
        test_records = _take_records(args.dataset, "test", args.test_limit, streaming=used_streaming)
    except Exception as exc:
        if used_streaming:
            raise
        print(
            "Normal load_dataset mode failed; retrying with streaming=True. "
            f"Original error: {type(exc).__name__}: {exc}"
        )
        used_streaming = True
        train_records = _take_records(args.dataset, "train", args.train_limit, streaming=True)
        test_records = _take_records(args.dataset, "test", args.test_limit, streaming=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snapshot_dir = out_dir / f"{args.dataset.replace('/', '_')}_{ts}"
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    train_path = snapshot_dir / "train.jsonl"
    test_path = snapshot_dir / "test.jsonl"
    meta_path = snapshot_dir / "metadata.json"

    with train_path.open("w", encoding="utf-8") as f:
        for item in train_records:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    with test_path.open("w", encoding="utf-8") as f:
        for item in test_records:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    metadata = {
        "dataset": args.dataset,
        "captured_at_utc": ts,
        "streaming": used_streaming,
        "train_count": len(train_records),
        "test_count": len(test_records),
        "files": {"train": str(train_path), "test": str(test_path)},
    }
    meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

"""
Gate NER model by validation F1 threshold.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Check NER F1 threshold from training_log.json")
    parser.add_argument("--training-log", required=True, help="Path to training_log.json")
    parser.add_argument("--min-f1", type=float, default=0.85, help="Minimum eval_f1 required")
    args = parser.parse_args()

    log_path = Path(args.training_log)
    payload = json.loads(log_path.read_text(encoding="utf-8"))
    f1 = float(payload.get("eval_results", {}).get("eval_f1", 0.0))
    print(f"eval_f1={f1:.4f}, threshold={args.min_f1:.4f}")
    if f1 < args.min_f1:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

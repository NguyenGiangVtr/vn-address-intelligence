"""Ensure repository root is on sys.path when running `python scripts/ops/<script>.py`."""

from __future__ import annotations

import sys
from pathlib import Path


def ensure_repo_root() -> Path:
    # scripts/ops/this_file.py -> parents[2] == repo root
    root = Path(__file__).resolve().parents[2]
    s = str(root)
    if s not in sys.path:
        sys.path.insert(0, s)
    return root

#!/usr/bin/env python3
"""CLI entry for retrieval eval (sets PYTHONPATH via repo bootstrap)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from app.ai.evaluate_retriever import main

if __name__ == "__main__":
    main()

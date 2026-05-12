"""Ensure Python can import `app` when running `python scripts/.../<script>.py` from repo root."""

from __future__ import annotations

import sys
from pathlib import Path


def ensure_repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in [here.parent, *here.parents]:
        if (p / "pyproject.toml").is_file():
            repo = p
            break
    else:
        repo = Path(__file__).resolve().parents[2]
    if (repo / "src" / "app" / "__init__.py").is_file():
        s = str(repo / "src")
    else:
        s = str(repo)
    if s not in sys.path:
        sys.path.insert(0, s)
    return repo

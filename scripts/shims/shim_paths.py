"""Shared path helpers for shims in this directory (importable when cwd/sys.path includes this folder)."""
from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in [here.parent, *here.parents]:
        if (p / "pyproject.toml").is_file():
            return p
    raise RuntimeError("Could not find repository root (pyproject.toml)")

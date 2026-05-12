"""
Insert sys.path entries so `import app` works when running scripts by file path.
Invoke at the top of entry scripts (before `from app...`). Safe to call multiple times.
"""
from __future__ import annotations

import sys
from pathlib import Path


def install() -> None:
    here = Path(__file__).resolve()
    for p in [here.parent, *here.parents]:
        if not (p / "pyproject.toml").is_file():
            continue
        if (p / "src" / "app" / "__init__.py").is_file():
            s = str(p / "src")
        elif (p / "app" / "__init__.py").is_file():
            s = str(p)
        else:
            s = str(p)
        if s not in sys.path:
            sys.path.insert(0, s)
        return

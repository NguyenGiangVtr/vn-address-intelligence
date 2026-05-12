"""Internal: run ``scripts/ops/<name>`` with runpy."""
from __future__ import annotations

import runpy
import sys
from pathlib import Path


def run_ops_script(ops_filename: str) -> None:
    shim_dir = Path(__file__).resolve().parent
    if str(shim_dir) not in sys.path:
        sys.path.insert(0, str(shim_dir))
    from shim_paths import repo_root

    target = repo_root() / "scripts" / "ops" / ops_filename
    runpy.run_path(str(target), run_name="__main__")

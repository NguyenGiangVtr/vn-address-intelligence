"""Run `scripts/experiments/supa_benchmark.py` as subprocess (same behavior as CLI)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from app.paths import repo_root

ALLOWED_SUBCOMMANDS = frozenset(
    {
        "extract",
        "extract-stratified",
        "eval",
        "export-specimens",
        "import-preds",
        "export-tex",
        "workflow",
        "make-demo-preds",
        "replicate",
        "replicate-stratified",
        "aggregate-runs",
    }
)

SCRIPT_REL = Path("scripts") / "experiments" / "supa_benchmark.py"


def supa_benchmark_script_path() -> Path:
    return repo_root() / SCRIPT_REL


def build_pythonpath_env(base: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(base or os.environ)
    root = repo_root()
    src = root / "src"
    sep = ";" if os.name == "nt" else ":"
    extra = str(src) if src.is_dir() else ""
    prev = env.get("PYTHONPATH", "")
    if extra:
        env["PYTHONPATH"] = f".{sep}{extra}" + (f"{sep}{prev}" if prev else "")
    else:
        env["PYTHONPATH"] = f".{sep}{prev}" if prev else "."
    return env


def run_supa_benchmark(
    argv: list[str],
    *,
    timeout_sec: float | None,
) -> tuple[int, str, str]:
    """
    argv: arguments after script name, e.g. ["extract", "--n", "100"].
    Returns (exit_code, stdout, stderr).
    """
    if not argv:
        raise ValueError("argv must not be empty")
    sub = argv[0]
    if sub not in ALLOWED_SUBCOMMANDS:
        raise ValueError(f"disallowed subcommand: {sub!r}")
    root = repo_root()
    script = supa_benchmark_script_path()
    if not script.is_file():
        raise FileNotFoundError(f"Missing SUPA script: {script}")
    cmd = [sys.executable, str(script), *argv]
    proc = subprocess.run(
        cmd,
        cwd=str(root),
        env=build_pythonpath_env(),
        capture_output=True,
        text=True,
        timeout=timeout_sec,
    )
    return proc.returncode, proc.stdout or "", proc.stderr or ""

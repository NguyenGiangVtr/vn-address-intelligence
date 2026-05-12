"""
Single source for repository root and canonical paths (legacy root + src layout).
Walk upward from this file until pyproject.toml is found.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Iterable


@lru_cache(maxsize=1)
def repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in [here.parent, *here.parents]:
        if (p / "pyproject.toml").is_file():
            return p
    raise RuntimeError("Could not locate repository root (no pyproject.toml above app.paths)")


def ai_config_yaml() -> Path:
    """Canonical AI YAML; prefers existing file (src layout, then legacy app/)."""
    root = repo_root()
    candidates = (
        root / "src" / "app" / "ai" / "config.yaml",
        root / "app" / "ai" / "config.yaml",
    )
    for c in candidates:
        if c.is_file():
            return c
    return candidates[0]


def ai_config_yaml_relative_posix() -> str:
    """Default path string relative to repo root (for APIs/CLI help)."""
    try:
        return ai_config_yaml().relative_to(repo_root()).as_posix()
    except ValueError:
        return ai_config_yaml().as_posix()


def docs_dir() -> Path:
    return repo_root() / "docs"


def paths_for_import_app() -> list[Path]:
    """
    Directories to prepend to sys.path so `import app` works without editable install.
    Prefer src layout when present.
    """
    root = repo_root()
    if (root / "src" / "app" / "__init__.py").is_file():
        return [root / "src"]
    if (root / "app" / "__init__.py").is_file():
        return [root]
    return [root]


def ensure_import_path() -> None:
    """Prepend paths so `import app` resolves (for scripts run as files)."""
    import sys

    for p in paths_for_import_app():
        s = str(p)
        if s not in sys.path:
            sys.path.insert(0, s)


def resolve_repo_path(rel_or_abs: str) -> Path:
    """Resolve a path that may be relative to cwd or to repo root."""
    p = Path(rel_or_abs)
    if p.is_absolute():
        return p.resolve()
    if p.exists():
        return p.resolve()
    cand = repo_root() / p
    if cand.exists():
        return cand.resolve()
    return (repo_root() / p).resolve()

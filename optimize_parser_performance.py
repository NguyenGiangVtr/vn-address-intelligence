"""Compatibility: `from optimize_parser_performance import ...` and CLI (repo root only)."""
import importlib.util
from pathlib import Path
import runpy


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in [here.parent, *here.parents]:
        if (p / "pyproject.toml").is_file():
            return p
    return here.parent


_OPS = _repo_root() / "scripts" / "ops" / "optimize_parser_performance.py"
_spec = importlib.util.spec_from_file_location("vnai.optimize_parser_performance.ops", _OPS)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader
_spec.loader.exec_module(_mod)


def __getattr__(name):
    return getattr(_mod, name)


def __dir__():
    return sorted(set(dir(_mod)))


if __name__ == "__main__":
    runpy.run_path(str(_OPS), run_name="__main__")

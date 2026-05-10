"""Compatibility: `from optimize_parser_performance import ...` and CLI."""
import importlib.util
from pathlib import Path
import runpy

_OPS = Path(__file__).resolve().parent / "scripts" / "ops" / "optimize_parser_performance.py"
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

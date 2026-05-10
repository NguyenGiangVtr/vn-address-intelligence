"""Compatibility launcher — implementation: scripts/ops/check_raw_join.py"""
import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parent / "scripts" / "ops" / "check_raw_join.py"), run_name="__main__")

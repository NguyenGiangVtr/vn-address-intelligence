"""Compatibility launcher — implementation: scripts/ops/temp_debug_lookup.py"""
import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parent / "scripts" / "ops" / "temp_debug_lookup.py"), run_name="__main__")

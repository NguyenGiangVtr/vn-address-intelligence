"""Compatibility launcher — implementation: scripts/ops/setup_vector_indexes.py"""
import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parent / "scripts" / "ops" / "setup_vector_indexes.py"), run_name="__main__")

"""Compatibility launcher — implementation: scripts/ops/compute_embeddings.py"""
import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parent / "scripts" / "ops" / "compute_embeddings.py"), run_name="__main__")

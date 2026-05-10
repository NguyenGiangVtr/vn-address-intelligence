"""Compatibility launcher — implementation: scripts/ops/quick_corpus_setup.py"""
import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parent / "scripts" / "ops" / "quick_corpus_setup.py"), run_name="__main__")

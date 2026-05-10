"""Compatibility launcher — implementation: scripts/ops/test_corpus_simple.py"""
import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parent / "scripts" / "ops" / "test_corpus_simple.py"), run_name="__main__")

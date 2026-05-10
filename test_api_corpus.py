"""Compatibility launcher — implementation: scripts/ops/test_api_corpus.py"""
import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parent / "scripts" / "ops" / "test_api_corpus.py"), run_name="__main__")

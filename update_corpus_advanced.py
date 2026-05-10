"""Compatibility launcher — implementation: scripts/ops/update_corpus_advanced.py"""
import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parent / "scripts" / "ops" / "update_corpus_advanced.py"), run_name="__main__")

"""Compatibility launcher — implementation: scripts/ops/fix_corpus_names.py"""
import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parent / "scripts" / "ops" / "fix_corpus_names.py"), run_name="__main__")

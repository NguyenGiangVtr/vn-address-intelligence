"""Compatibility launcher — implementation: scripts/ops/fix_parser_503.py"""
import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parent / "scripts" / "ops" / "fix_parser_503.py"), run_name="__main__")

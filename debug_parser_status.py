"""Compatibility launcher — implementation: scripts/ops/debug_parser_status.py"""
import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parent / "scripts" / "ops" / "debug_parser_status.py"), run_name="__main__")

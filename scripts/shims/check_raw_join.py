"""Delegate to scripts/ops/check_raw_join.py — run: python scripts/shims/check_raw_join.py"""
from __future__ import annotations

from _launch import run_ops_script

if __name__ == "__main__":
    run_ops_script("check_raw_join.py")

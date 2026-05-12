"""Delegate to scripts/ops/compute_embeddings.py — run: python scripts/shims/compute_embeddings.py"""
from __future__ import annotations

from _launch import run_ops_script

if __name__ == "__main__":
    run_ops_script("compute_embeddings.py")

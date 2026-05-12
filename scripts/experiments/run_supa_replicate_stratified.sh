#!/usr/bin/env bash
# Wrapper: SUPA stratified replicate. Example (oracle smoke):
#   bash scripts/experiments/run_supa_replicate_stratified.sh --k-runs 5 --n 2000 --preds-demo-ref-v2
# Real preds:
#   bash scripts/experiments/run_supa_replicate_stratified.sh --k-runs 5 --n 2000 --preds reports/p.csv --source-note "..."
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}:${ROOT}/src:${PYTHONPATH:-}"
exec python scripts/experiments/supa_benchmark.py replicate-stratified "$@"

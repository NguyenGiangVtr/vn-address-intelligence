#!/usr/bin/env bash
# SUPA-Bench — repeatable demo (bash). Omit SEED for random cohort each run; set SEED=42 to pin.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}:${ROOT}/src"

N="${N:-1000}"
NOISE="${NOISE_PROFILE:-SUP-1.0.0}"
SPEC_OUT="${SPECIMENS_OUT:-reports/supa_workflow_specimens_latest.csv}"

SEED_ARGS=()
if [[ -n "${SEED:-}" ]]; then
  SEED_ARGS=(--seed "$SEED")
fi

SKIP=()
RUN=()
if [[ "${SKIP_EXTRACT:-0}" == "1" ]]; then
  SKIP+=(--skip-extract)
  [[ -n "${RUN_ID:-}" ]] && RUN+=(--run-id "$RUN_ID")
fi

PRED=()
if [[ "${DEMO_PREDS_REF_V2:-0}" == "1" ]]; then
  [[ -z "${PREDS_CSV:-}" ]] || { echo "DEMO_PREDS_REF_V2=1 excludes PREDS_CSV"; exit 2; }
  PRED+=(--preds-demo-ref-v2)
elif [[ -n "${PREDS_CSV:-}" ]]; then
  [[ -n "${SOURCE_NOTE:-}" ]] || { echo "PREDS_CSV requires SOURCE_NOTE"; exit 2; }
  PRED+=(--preds "$PREDS_CSV" --source-note "$SOURCE_NOTE")
fi

echo ">>> python scripts/experiments/supa_benchmark.py workflow ..."
python scripts/experiments/supa_benchmark.py workflow \
  --n "$N" --noise-profile "$NOISE" \
  --specimens-out "$SPEC_OUT" \
  "${SEED_ARGS[@]}" \
  "${SKIP[@]}" "${RUN[@]}" "${PRED[@]}"

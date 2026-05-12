#!/usr/bin/env bash
# SUPA-Bench — replicate runs (bash). sweep-seed: omit SEED_START for random sweep base each script run.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}:${ROOT}/src"

N_RUNS="${N_RUNS:-20}"
MODE="${MODE:-sweep-seed}"
N="${N:-1000}"
NOISE_PROFILE="${NOISE_PROFILE:-SUP-1.0.0}"
RETENTION="${RETENTION:-0}"
SPECIMENS_OUT="${SPECIMENS_OUT:-reports/supa_workflow_specimens_latest.csv}"

ARGS=(scripts/experiments/supa_benchmark.py replicate
  --n-runs "$N_RUNS"
  --mode "$MODE"
  --n "$N"
  --noise-profile "$NOISE_PROFILE"
  --retention "$RETENTION"
  --specimens-out "$SPECIMENS_OUT")

if [[ "$MODE" == "sweep-seed" ]]; then
  [[ -n "${SEED_START:-}" ]] && ARGS+=(--seed-start "$SEED_START")
else
  ARGS+=(--seed "${SEED:-42}")
fi

if [[ "${SKIP_IMPORT:-0}" == "1" ]]; then
  ARGS+=(--skip-import)
elif [[ -n "${PREDS_CSV:-}" ]]; then
  [[ -n "${SOURCE_NOTE:-}" ]] || { echo "PREDS_CSV requires SOURCE_NOTE"; exit 2; }
  ARGS+=(--preds "$PREDS_CSV" --source-note "$SOURCE_NOTE")
elif [[ "${DEMO_PREDS_REF_V2:-1}" == "1" ]]; then
  ARGS+=(--preds-demo-ref-v2)
else
  echo "Set SKIP_IMPORT=1, or PREDS_CSV+SOURCE_NOTE, or DEMO_PREDS_REF_V2=1 (default)."
  exit 2
fi

if [[ "${EXPORT_TEX_LAST:-0}" == "1" ]]; then
  ARGS+=(--export-tex-last)
fi

echo ">>> python ${ARGS[*]}"
python "${ARGS[@]}"

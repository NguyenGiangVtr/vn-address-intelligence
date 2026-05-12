#!/usr/bin/env bash
# Full VNAI flow (bash).
# Env: SKIP_TRAIN=1 | SKIP_DB=1 | OPTIONAL_DB=1 (audit fail → skip experiment + pipeline)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
export PYTHONPATH="."

PIPELINE_LIMIT="${PIPELINE_LIMIT:-25}"
TRAIN_OUT="${TRAIN_OUT:-models/phobert-ner-vn-flow-last}"

mkdir -p reports
AUDIT_JSON="reports/audit_acq_admin_bridge_last.json"
TRAIN_LOG="${TRAIN_OUT}/training_log.json"
EXP_CSV="reports/experiment_results.csv"

python -m py_compile \
  scripts/diagnostics/audit_acq_admin_bridge.py \
  scripts/flow/generate_scientific_report_metrics.py \
  app/ai/train_ner.py \
  app/ai/production_pipeline.py \
  app/ai/experiment_runner.py \
  app/ai/report_generator.py

python scripts/labeling/run_prelabeler_labeling_cases.py
python scripts/test/test_prelabeler_regression.py

if [[ "${SKIP_DB:-0}" != "1" ]]; then
  if python scripts/diagnostics/audit_acq_admin_bridge.py --write-json "$AUDIT_JSON"; then
    python -m app.ai.experiment_runner --config app/ai/config.yaml --no-llm
    python app/ai/production_pipeline.py --config app/ai/config.yaml --limit "$PIPELINE_LIMIT"
  else
    if [[ "${OPTIONAL_DB:-0}" == "1" ]]; then
      echo "WARN: audit failed; skipping experiment_runner and production_pipeline (OPTIONAL_DB=1)."
    else
      echo "ERROR: audit failed. Use SKIP_DB=1 or OPTIONAL_DB=1 to continue without DB steps." >&2
      exit 1
    fi
  fi
else
  echo "SKIP_DB=1: skipping audit / experiment / pipeline"
fi

if [[ "${SKIP_TRAIN:-0}" != "1" ]]; then
  python app/ai/train_ner.py \
    --hf-dataset dathuynh1108/ner-address-standard-dataset \
    --hf-max-train 4000 \
    --hf-max-eval 800 \
    --epochs 1 \
    --batch-size 8 \
    --output "$TRAIN_OUT"
else
  echo "SKIP_TRAIN=1: skipping NER train"
fi

TL=()
[[ -f "$TRAIN_LOG" ]] && TL=(--training-log "$TRAIN_LOG")
AJ=()
[[ -f "$AUDIT_JSON" ]] && AJ=(--audit-json "$AUDIT_JSON")
EC=()
[[ -f "$EXP_CSV" ]] && EC=(--experiment-csv "$EXP_CSV")
python scripts/flow/generate_scientific_report_metrics.py "${TL[@]}" "${AJ[@]}" "${EC[@]}"

echo "Done. Next: (cd docs/scientific-report && xelatex vnai-chapters-master.tex)"

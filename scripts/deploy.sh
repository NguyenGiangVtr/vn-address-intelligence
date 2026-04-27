#!/usr/bin/env bash
# Backward-compatible wrapper. Canonical script: scripts/deployment/deploy.sh
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "$SCRIPT_DIR/deployment/deploy.sh" "$@"

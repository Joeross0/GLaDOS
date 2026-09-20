#!/usr/bin/env bash
# Run this on a RunPod PyTorch GPU pod after the repo and adapter are on disk.
set -euo pipefail

ROOT="${GLADOS_ROOT:-/workspace/GLaDOS}"
cd "$ROOT"

if [[ ! -d data/finetune/adapter ]]; then
  echo "Copy data/finetune/adapter onto this pod first."
  exit 1
fi

if [[ -z "${GLADOS_SERVE_TOKEN:-}" ]]; then
  echo "Export GLADOS_SERVE_TOKEN to a long random string before serving."
  exit 1
fi

python -m pip install -e ".[finetune]"
export GLADOS_SERVE_HOST="${GLADOS_SERVE_HOST:-0.0.0.0}"
export GLADOS_SERVE_PORT="${GLADOS_SERVE_PORT:-11435}"
exec python -m glados finetune --serve --host "$GLADOS_SERVE_HOST" --port "$GLADOS_SERVE_PORT" --token "$GLADOS_SERVE_TOKEN"

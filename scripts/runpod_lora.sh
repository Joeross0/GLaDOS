#!/usr/bin/env bash
# Run this on a RunPod PyTorch GPU pod after the repo and adapter are on disk.
set -euo pipefail

ROOT="${GLADOS_ROOT:-/workspace/GLaDOS}"
cd "$ROOT"

if [[ ! -f data/finetune/adapter/adapter_model.safetensors ]]; then
  echo "Copy data/finetune/adapter onto this pod first (need adapter_model.safetensors)."
  exit 1
fi

if [[ -z "${GLADOS_SERVE_TOKEN:-}" ]]; then
  echo "Export GLADOS_SERVE_TOKEN to a long random string before serving."
  exit 1
fi

python - <<'PY'
import torch
print("cuda", torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else "none")
if not torch.cuda.is_available():
    raise SystemExit("This image has no CUDA torch. Pick a RunPod PyTorch GPU template.")
PY

# Keep the image's CUDA torch. Only add the LoRA serve extras.
python -m pip install -q transformers peft bitsandbytes accelerate loguru pydantic onnxruntime
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:$PYTHONPATH}"
export GLADOS_SERVE_HOST="${GLADOS_SERVE_HOST:-0.0.0.0}"
export GLADOS_SERVE_PORT="${GLADOS_SERVE_PORT:-11435}"
exec python -m glados finetune --serve --host "$GLADOS_SERVE_HOST" --port "$GLADOS_SERVE_PORT" --token "$GLADOS_SERVE_TOKEN"

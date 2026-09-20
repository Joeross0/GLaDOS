"""ONNX Runtime execution providers."""

from __future__ import annotations

import os

import onnxruntime as ort


def session_providers() -> list[str]:
    if os.environ.get("GLADOS_ONNX_CPU") == "1":
        return ["CPUExecutionProvider"]
    providers = [name for name in ort.get_available_providers() if name not in {"TensorrtExecutionProvider", "CoreMLExecutionProvider"}]
    if "CUDAExecutionProvider" in providers:
        return ["CUDAExecutionProvider", "CPUExecutionProvider"]
    return ["CPUExecutionProvider"]

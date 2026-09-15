from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import cv2
from loguru import logger
import numpy as np
from numpy.typing import NDArray

from ..audio_io.vad import VAD

if TYPE_CHECKING:
    from ..core.engine import Glados

TARGET_RATE = 16000
CHUNK_SAMPLES = 512  # 32 ms at 16 kHz


def _resample(samples: NDArray[np.float32], source_rate: int) -> NDArray[np.float32]:
    if source_rate == TARGET_RATE or samples.size == 0:
        return samples.astype(np.float32, copy=False)
    new_count = max(1, int(round(samples.size * TARGET_RATE / source_rate)))
    old_x = np.linspace(0.0, 1.0, samples.size, endpoint=False)
    new_x = np.linspace(0.0, 1.0, new_count, endpoint=False)
    return np.interp(new_x, old_x, samples).astype(np.float32)


class MediaBridge:
    """Push browser microphone and camera data into the running GLaDOS engine."""

    def __init__(self, engine: Glados) -> None:
        self._engine = engine
        self._lock = threading.Lock()
        self._audio_buffer = np.zeros(0, dtype=np.float32)
        self._vad = VAD()
        self._vad_threshold = 0.8

    def ingest_audio(self, raw: bytes, sample_rate: int) -> int:
        if len(raw) < 4 or len(raw) % 4:
            return 0
        samples = np.frombuffer(raw, dtype=np.float32)
        samples = _resample(samples, sample_rate)
        queued = 0
        with self._lock:
            if self._audio_buffer.size:
                samples = np.concatenate([self._audio_buffer, samples])
            while samples.size >= CHUNK_SAMPLES:
                chunk = samples[:CHUNK_SAMPLES]
                samples = samples[CHUNK_SAMPLES:]
                vad_value = float(np.asarray(self._vad(np.expand_dims(chunk, 0))).reshape(-1)[0])
                self._engine.audio_io.get_sample_queue().put((chunk, vad_value > self._vad_threshold))
                queued += 1
            self._audio_buffer = samples
        return queued

    def ingest_jpeg(self, raw: bytes) -> bool:
        if self._engine.vision_processor is None:
            return False
        encoded = np.frombuffer(raw, dtype=np.uint8)
        frame = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        if frame is None:
            logger.warning("Portal camera frame could not be decoded.")
            return False
        self._engine.vision_processor.push_remote_frame(frame)
        return True

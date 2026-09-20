"""Detect when the microphone transcribed GLaDOS's own speech."""

from __future__ import annotations

import re
import threading
import time

from Levenshtein import distance

_NON_ALNUM = re.compile(r"[^a-z0-9\s]+")


def normalize_utterance(text: str) -> str:
    """Lowercase, strip punctuation, and collapse whitespace."""
    cleaned = _NON_ALNUM.sub(" ", (text or "").lower())
    return " ".join(cleaned.split())


def is_similar_utterance(left: str, right: str, threshold: float = 0.72) -> bool:
    """Return True if two spoken lines are the same idea or one contains the other."""
    a = normalize_utterance(left)
    b = normalize_utterance(right)
    if not a or not b:
        return False
    if a in b or b in a:
        return True
    longest = max(len(a), len(b))
    if longest < 8:
        return a == b
    return (1.0 - distance(a, b) / longest) >= threshold


class SpokenTranscriptFilter:
    """Remember recent TTS so ASR can drop speaker echo and room tail."""

    def __init__(self, hangover_s: float = 1.6, max_remembered: int = 12) -> None:
        self._hangover_s = hangover_s
        self._max_remembered = max_remembered
        self._lock = threading.Lock()
        self._recent: list[str] = []
        self._last_spoken_at = 0.0
        self._speaking = False

    def remember(self, text: str) -> None:
        normalized = normalize_utterance(text)
        if not normalized:
            return
        with self._lock:
            self._recent.append(text)
            if len(self._recent) > self._max_remembered:
                self._recent = self._recent[-self._max_remembered :]
            self._last_spoken_at = time.time()

    def mark_speaking(self, speaking: bool) -> None:
        with self._lock:
            self._speaking = speaking
            if not speaking:
                self._last_spoken_at = time.time()

    def should_ignore_listening(self) -> bool:
        with self._lock:
            if self._speaking:
                return True
            if self._last_spoken_at <= 0:
                return False
            return (time.time() - self._last_spoken_at) < self._hangover_s

    def is_echo(self, text: str) -> bool:
        heard = normalize_utterance(text)
        if not heard:
            return True
        with self._lock:
            recent = list(self._recent)
        return any(is_similar_utterance(heard, spoken) for spoken in recent)

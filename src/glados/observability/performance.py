from __future__ import annotations

from collections import deque
import threading
from typing import Any


class PerformanceStats:
    """Rolling timings for the TUI mind / performance views."""

    def __init__(self, window: int = 20) -> None:
        self._lock = threading.Lock()
        self._llm_wait: deque[float] = deque(maxlen=window)
        self._first_token: deque[float] = deque(maxlen=window)
        self._llm_total: deque[float] = deque(maxlen=window)
        self._vision: deque[float] = deque(maxlen=window)
        self._last: dict[str, Any] = {}

    def record_llm(
        self,
        *,
        lane: str,
        wait_s: float | None,
        first_token_s: float | None,
        total_s: float | None,
    ) -> None:
        with self._lock:
            if wait_s is not None:
                self._llm_wait.append(float(wait_s))
            if first_token_s is not None:
                self._first_token.append(float(first_token_s))
            if total_s is not None:
                self._llm_total.append(float(total_s))
            self._last.update(
                {
                    "lane": lane,
                    "wait_s": wait_s,
                    "first_token_s": first_token_s,
                    "total_s": total_s,
                }
            )

    def record_vision(self, seconds: float) -> None:
        with self._lock:
            self._vision.append(float(seconds))
            self._last["vision_s"] = float(seconds)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "last": dict(self._last),
                "avg_wait_s": self._avg(self._llm_wait),
                "avg_first_token_s": self._avg(self._first_token),
                "avg_llm_s": self._avg(self._llm_total),
                "avg_vision_s": self._avg(self._vision),
                "samples_llm": len(self._llm_total),
                "samples_vision": len(self._vision),
            }

    @staticmethod
    def _avg(values: deque[float]) -> float | None:
        if not values:
            return None
        return sum(values) / len(values)

from __future__ import annotations

import threading
import time
from typing import Any


class VisionState:
    """Thread-safe store for the latest vision description."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._description: str | None = None
        self._change_score: float | None = None
        self._updated_at: float | None = None

    def update(self, description: str, change_score: float | None = None) -> None:
        """Update the latest vision description."""
        with self._lock:
            self._description = description
            self._change_score = change_score
            self._updated_at = time.time()

    def note_scan(self, change_score: float) -> None:
        """Refresh the live change score without claiming a new caption."""
        with self._lock:
            self._change_score = change_score

    def snapshot(self) -> str | None:
        """Return the latest vision description, if available."""
        with self._lock:
            return self._description

    def details(self) -> tuple[str | None, float | None, float | None]:
        """Return description, change score, and update timestamp."""
        with self._lock:
            return self._description, self._change_score, self._updated_at

    def as_message(self) -> dict[str, Any] | None:
        """Return the vision context as a system message or None if empty."""
        description = self.snapshot()
        if not description:
            return None
        return {"role": "system", "content": f"[vision] {description}"}

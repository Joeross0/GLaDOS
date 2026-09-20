"""Size background workers from the machine instead of a fixed guess."""

from __future__ import annotations

import os


def cpu_count() -> int:
    return max(1, os.cpu_count() or 1)


def recommended_worker_count(reserve: int = 2, floor: int = 4, ceiling: int = 16) -> int:
    """Leave a couple of cores for audio, vision, and the TUI."""
    available = max(floor, cpu_count() - max(0, reserve))
    return max(floor, min(ceiling, available))


def resolve_worker_count(configured: int | None, *, floor: int = 4, ceiling: int = 16) -> int:
    """0 or None means auto. A positive value is an explicit cap."""
    if configured and configured > 0:
        return max(1, min(ceiling, configured))
    return recommended_worker_count(floor=floor, ceiling=ceiling)

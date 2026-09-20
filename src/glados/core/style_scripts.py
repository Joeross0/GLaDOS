"""Local style-script feed for cadence imitation.

Pastes stay on disk under data/ and are never committed.
"""

from __future__ import annotations

from pathlib import Path

STYLE_SCRIPTS_PREFIX = "STYLE REFERENCE — cadence and tone only."
MAX_STYLE_CHARS = 48_000
DEFAULT_PATH = Path("data/style_scripts.txt")


def wrap_style_scripts(raw: str) -> str | None:
    text = raw.strip()
    if not text:
        return None
    if len(text) > MAX_STYLE_CHARS:
        text = text[:MAX_STYLE_CHARS] + "\n[truncated]"
    return (
        f"{STYLE_SCRIPTS_PREFIX}\n"
        "Use this as voice and cadence reference.\n\n"
        f"{text}"
    )


def load_style_scripts(path: Path = DEFAULT_PATH) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def save_style_scripts(raw: str, path: Path = DEFAULT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = raw.strip()
    if not text:
        if path.exists():
            path.unlink()
        return
    path.write_text(text + "\n", encoding="utf-8")

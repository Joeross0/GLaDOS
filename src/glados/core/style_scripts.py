"""Local style-script feed for cadence imitation.

Pastes stay on disk under data/ and are never committed.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

STYLE_SCRIPTS_PREFIX = "STYLE REFERENCE — cadence and tone only."
MAX_STYLE_CHARS = 48_000
DEFAULT_PATH = Path("data/style_scripts.txt")


def style_scripts_path(path: Path = DEFAULT_PATH) -> Path:
    if path.is_absolute():
        return path
    return (Path.cwd() / path).resolve()


def ensure_style_scripts_file(path: Path = DEFAULT_PATH) -> Path:
    target = style_scripts_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_text("", encoding="utf-8")
    return target


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
    target = style_scripts_path(path)
    if not target.is_file():
        return ""
    return target.read_text(encoding="utf-8")


def save_style_scripts(raw: str, path: Path = DEFAULT_PATH) -> None:
    target = style_scripts_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    text = raw.strip()
    if not text:
        if target.exists():
            target.unlink()
        return
    target.write_text(text + "\n", encoding="utf-8")


def open_style_scripts_in_editor(path: Path = DEFAULT_PATH) -> Path:
    target = ensure_style_scripts_file(path)
    for command in (
        ["cursor", "-g", str(target)],
        ["cursor", str(target)],
        ["code", "-g", str(target)],
        ["code", str(target)],
    ):
        try:
            subprocess.Popen(command, shell=False)
            return target
        except FileNotFoundError:
            continue
        except OSError:
            continue
    if sys.platform == "win32":
        os.startfile(target)  # type: ignore[attr-defined]
        return target
    opener = "open" if sys.platform == "darwin" else "xdg-open"
    subprocess.Popen([opener, str(target)])
    return target

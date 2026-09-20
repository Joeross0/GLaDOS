"""Train a compact local voice model from dumped scripts.

This is not GPU fine-tuning. It extracts announcement lines, writes a small
style card, and retrieves matching lines per turn so the 8B model leans
toward the corpus without swallowing the whole dump every request.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .style_scripts import style_scripts_path

STYLE_MODEL_PREFIX = "TRAINED VOICE —"
SCRIPTS_DIR = Path("data/scripts")
MODEL_DIR = Path("data/style_model")
LINES_PATH = MODEL_DIR / "lines.json"
CARD_PATH = MODEL_DIR / "card.txt"
QUOTE_RE = re.compile(r'"([^"]{12,500})"')
NOISE = re.compile(
    r"(download|play|translated to|see also|if the player|during the level|test chamber)",
    re.IGNORECASE,
)
WORD_RE = re.compile(r"[a-z']{3,}")


def scripts_dir() -> Path:
    path = SCRIPTS_DIR
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def collect_source_files() -> list[Path]:
    files: list[Path] = []
    folder = scripts_dir()
    for pattern in ("*.txt", "*.md"):
        files.extend(sorted(folder.glob(pattern)))
    main = style_scripts_path()
    if main.is_file() and main.stat().st_size > 0 and main not in files:
        files.append(main)
    return files


def extract_lines(text: str) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    for match in QUOTE_RE.findall(text):
        cleaned = re.sub(r"\s+", " ", match).strip()
        cleaned = re.sub(r"\[/?[^\]]+\]", "", cleaned).strip()
        if len(cleaned) < 16 or NOISE.search(cleaned):
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        lines.append(cleaned)
    return lines


def _tokenize(text: str) -> set[str]:
    return set(WORD_RE.findall(text.casefold()))


def retrieve_lines(query: str, lines: list[str], limit: int = 5) -> list[str]:
    query_words = _tokenize(query)
    if not query_words or not lines:
        return lines[:limit]
    scored: list[tuple[float, str]] = []
    for line in lines:
        words = _tokenize(line)
        if not words:
            continue
        overlap = len(query_words & words)
        score = overlap / (len(query_words) ** 0.5)
        if score <= 0:
            continue
        scored.append((score, line))
    scored.sort(key=lambda item: (-item[0], len(item[1])))
    picks = [line for _, line in scored[:limit]]
    if len(picks) < limit:
        for line in lines:
            if line not in picks:
                picks.append(line)
            if len(picks) >= limit:
                break
    return picks


def build_card(lines: list[str]) -> str:
    samples = retrieve_lines(
        "welcome test science facility protocol cake safety chamber subject",
        lines,
        limit=8,
    )
    sample_block = "\n".join(f"- {line}" for line in samples)
    return (
        f"{STYLE_MODEL_PREFIX} {len(lines)} local announcement lines.\n"
        "Write like these lines: calm PA, fake courtesy, then a petty scientific insult. "
        "These are voice weights, not live events. Do not recap the whole corpus.\n"
        f"{sample_block}"
    )


@dataclass
class StyleModel:
    lines: list[str]
    card: str

    def examples_for(self, query: str, limit: int = 5) -> str | None:
        if not self.lines:
            return None
        picks = retrieve_lines(query, self.lines, limit=limit)
        if not picks:
            return None
        block = "\n".join(f"- {line}" for line in picks)
        return (
            f"{STYLE_MODEL_PREFIX} matching lines for this turn. Imitate cadence only.\n"
            f"{block}"
        )


def train_style_model() -> StyleModel:
    texts = [path.read_text(encoding="utf-8", errors="ignore") for path in collect_source_files()]
    lines: list[str] = []
    seen: set[str] = set()
    for text in texts:
        for line in extract_lines(text):
            key = line.casefold()
            if key in seen:
                continue
            seen.add(key)
            lines.append(line)
    card = build_card(lines) if lines else ""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    LINES_PATH.write_text(json.dumps(lines, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    CARD_PATH.write_text(card, encoding="utf-8")
    return StyleModel(lines=lines, card=card)


def load_style_model() -> StyleModel | None:
    if not LINES_PATH.is_file():
        return None
    try:
        lines = json.loads(LINES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(lines, list):
        return None
    cleaned = [str(line) for line in lines if isinstance(line, str) and line.strip()]
    card = CARD_PATH.read_text(encoding="utf-8") if CARD_PATH.is_file() else build_card(cleaned)
    return StyleModel(lines=cleaned, card=card)


def sources_newer_than_model() -> bool:
    if not LINES_PATH.is_file():
        return True
    model_mtime = LINES_PATH.stat().st_mtime
    for path in collect_source_files():
        try:
            if path.stat().st_mtime > model_mtime:
                return True
        except OSError:
            continue
    return False

from __future__ import annotations

import re

_SPACED_LETTERS = re.compile(r"(?<![A-Za-z])(?:[A-Za-z](?:[\s.\-]+)){2,}[A-Za-z](?![A-Za-z])")
_SINGLE_LETTER_RUN = re.compile(r"(?<![A-Za-z])(?:[A-Za-z]\s+){2,}[A-Za-z](?![A-Za-z])")
_CONTRACTIONS = (
    (re.compile(r"\bdont\b", re.I), "don't"),
    (re.compile(r"\bwont\b", re.I), "won't"),
    (re.compile(r"\bcant\b", re.I), "can't"),
    (re.compile(r"\bim\b", re.I), "I'm"),
    (re.compile(r"\bive\b", re.I), "I've"),
    (re.compile(r"\bill\b", re.I), "I'll"),
    (re.compile(r"\byoure\b", re.I), "you're"),
    (re.compile(r"\btheyre\b", re.I), "they're"),
    (re.compile(r"\bwhats\b", re.I), "what's"),
    (re.compile(r"\bthats\b", re.I), "that's"),
    (re.compile(r"\bheres\b", re.I), "here's"),
    (re.compile(r"\bhows\b", re.I), "how's"),
    (re.compile(r"\bwheres\b", re.I), "where's"),
)


def collapse_spaced_letters(text: str) -> str:
    """Turn 'Y O U' or 'Y. O. U.' into 'YOU'."""
    return _SPACED_LETTERS.sub(lambda match: re.sub(r"[^A-Za-z]", "", match.group(0)), text)


def sanitize_spoken_text(text: str) -> str:
    """Local cleanup before TTS and the dialog: glue spelled letters, tidy grammar."""
    if not text or not text.strip():
        return ""
    cleaned = collapse_spaced_letters(text)
    cleaned = _SINGLE_LETTER_RUN.sub(lambda match: re.sub(r"\s+", "", match.group(0)), cleaned)
    cleaned = cleaned.replace("\n", " ").replace("\r", " ")
    # ASCII dashes are invisible to this voice; commas actually pause.
    cleaned = re.sub(r"\s*[—–−\-]{1,3}\s*", ", ", cleaned)
    cleaned = re.sub(r"\s*;\s*", ". ", cleaned)
    cleaned = re.sub(r"\s*:\s*", ", ", cleaned)
    cleaned = _insert_clause_commas(cleaned)
    cleaned = re.sub(r"\s+([,.!?])", r"\1", cleaned)
    cleaned = re.sub(r"([.!?])([A-Za-z])", r"\1 \2", cleaned)
    cleaned = re.sub(r",,+", ",", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    for pattern, replacement in _CONTRACTIONS:
        cleaned = pattern.sub(replacement, cleaned)
    cleaned = re.sub(r"\bi\b", "I", cleaned)
    cleaned = _capitalize_sentences(cleaned)
    if _looks_like_keysmash(cleaned):
        return ""
    return cleaned


def _insert_clause_commas(text: str) -> str:
    """Add a comma before a late conjunction so the line is not one breath."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    out: list[str] = []
    for sentence in sentences:
        if "," in sentence or len(sentence.split()) < 10:
            out.append(sentence)
            continue
        out.append(
            re.sub(
                r"^((?:\S+\s+){4,}\S+)\s+(and|but|so|because|though|which|while)\b",
                r"\1, \2",
                sentence,
                count=1,
                flags=re.I,
            )
        )
    return " ".join(out)


def _capitalize_sentences(text: str) -> str:
    pieces = re.split(r"(?<=[.!?])\s+", text)
    fixed: list[str] = []
    for piece in pieces:
        piece = piece.strip()
        if not piece:
            continue
        fixed.append(piece[0].upper() + piece[1:] if len(piece) > 1 else piece.upper())
    return " ".join(fixed)


def _looks_like_keysmash(text: str) -> bool:
    letters = re.sub(r"[^a-zA-Z]", "", text)
    spaces = text.count(" ")
    if len(letters) >= 40 and spaces < 3:
        return True
    words = re.findall(r"[A-Za-z]+", text)
    if len(words) >= 8:
        vowels = sum(ch.lower() in "aeiou" for ch in letters) / max(len(letters), 1)
        if vowels < 0.22:
            return True
    return False

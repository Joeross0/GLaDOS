from __future__ import annotations

import re

_SPACED_LETTERS = re.compile(r"(?<![A-Za-z])(?:[A-Za-z](?:[\s.\-]+)){2,}[A-Za-z](?![A-Za-z])")


def collapse_spaced_letters(text: str) -> str:
    """Turn 'Y O U' or 'Y. O. U.' into 'YOU'."""
    return _SPACED_LETTERS.sub(lambda match: re.sub(r"[^A-Za-z]", "", match.group(0)), text)

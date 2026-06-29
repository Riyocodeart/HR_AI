"""
parser.cleaner
==============
Pre-processing for raw JD text before LLM parsing.

Single responsibility: produce a clean, normalised, boilerplate-free
string ready for the prompt builder. Never mutates input — always
returns a new string.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable

from .utils import get_logger

log = get_logger(__name__)


# Sentence-level boilerplate fragments that distract the model.
# Add to this list cautiously — false positives strip real content.
_BOILERPLATE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?im)^.*equal\s+opportunity\s+employer.*$"),
    re.compile(r"(?im)^.*we\s+are\s+an\s+equal.*$"),
    re.compile(r"(?im)^.*apply\s+now.*$"),
    re.compile(r"(?im)^.*click\s+(here|the\s+link)\s+to\s+apply.*$"),
    re.compile(r"(?im)^.*all\s+qualified\s+applicants.*$"),
    re.compile(r"(?im)^.*by\s+submitting\s+your\s+(application|resume).*$"),
    re.compile(r"(?im)^.*©\s*\d{4}.*$"),
)

# Zero-width / format characters that copy/paste from PDFs love to inject.
_INVISIBLE = re.compile(r"[\u200b-\u200f\u202a-\u202e\ufeff]")

# Bullet-like glyphs we normalise to "- " so the LLM sees consistent lists.
_BULLET_GLYPHS = re.compile(r"[•·◦▪▫■□●○]+\s*")


class JDCleaner:
    """
    Clean raw JD text deterministically.

    Parameters
    ----------
    max_chars : int
        Hard cap so an absurdly long JD never blows the Qwen context window.
        Truncation is right-side (keep the start where the meta lives).
    strip_boilerplate : bool
        Toggle the boilerplate regex pass — disable for pristine inputs.
    """

    def __init__(self, max_chars: int = 12_000, strip_boilerplate: bool = True) -> None:
        self.max_chars = max_chars
        self.strip_boilerplate = strip_boilerplate

    # ── Public API ───────────────────────────────────────────────────────
    def clean(self, text: str) -> str:
        """Return cleaned JD text. Empty input → empty output."""
        if not text:
            return ""

        out = self._normalise_unicode(text)
        out = self._strip_invisibles(out)
        out = self._normalise_bullets(out)
        if self.strip_boilerplate:
            out = self._strip_boilerplate(out)
        out = self._collapse_whitespace(out)
        out = self._truncate(out)

        log.debug("Cleaned JD: %d -> %d chars", len(text), len(out))
        return out

    # ── Steps ────────────────────────────────────────────────────────────
    @staticmethod
    def _normalise_unicode(text: str) -> str:
        return unicodedata.normalize("NFKC", text)

    @staticmethod
    def _strip_invisibles(text: str) -> str:
        return _INVISIBLE.sub("", text)

    @staticmethod
    def _normalise_bullets(text: str) -> str:
        return _BULLET_GLYPHS.sub("- ", text)

    @staticmethod
    def _strip_boilerplate(text: str) -> str:
        for pat in _BOILERPLATE_PATTERNS:
            text = pat.sub("", text)
        return text

    @staticmethod
    def _collapse_whitespace(text: str) -> str:
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _truncate(self, text: str) -> str:
        if len(text) <= self.max_chars:
            return text
        log.warning("JD truncated %d -> %d chars", len(text), self.max_chars)
        return text[: self.max_chars]

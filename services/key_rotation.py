from __future__ import annotations

import os
import re
from threading import Lock
from typing import Iterable

from services.config import (
    GEMINI_API_KEY_ENV,
    GEMINI_API_KEY_PREFIX,
    GEMINI_API_KEYS_ENV,
)

try:
    from google.api_core.exceptions import ResourceExhausted, TooManyRequests
except Exception:  # pragma: no cover - optional dependency
    ResourceExhausted = TooManyRequests = None

_SPLIT_RE = re.compile(r"[\s,;]+")
_NUMBERED_ENV_RE = re.compile(rf"^{re.escape(GEMINI_API_KEY_PREFIX)}(\d+)$")
_EXHAUSTION_MARKERS = (
    "resource exhausted",
    "resourceexhausted",
    "quota exceeded",
    "quota",
    "rate limit",
    "too many requests",
    "429",
    "exhausted",
    "limit reached",
    "error 46",
)


def _dedupe(items: Iterable[str]) -> list[str]:
    seen = set()
    out: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def normalize_api_keys(value) -> list[str]:
    if value is None:
        return []

    if isinstance(value, (list, tuple, set)):
        raw_values = list(value)
    else:
        raw_values = _SPLIT_RE.split(str(value).strip())

    cleaned = []
    for item in raw_values:
        if item is None:
            continue
        text = str(item).strip()
        if text:
            cleaned.append(text)
    return _dedupe(cleaned)


def load_gemini_api_keys(api_key=None) -> list[str]:
    """
    Load one or more Gemini keys from an explicit value and/or environment.

    Supported environment variables:
      - GEMINI_API_KEYS      : comma, newline, semicolon, or space separated
      - GEMINI_API_KEY_1...n : numbered fallbacks in priority order
      - GEMINI_API_KEY       : legacy single-key fallback
    """
    keys: list[str] = []

    def add(value) -> None:
        for key in normalize_api_keys(value):
            if key not in keys:
                keys.append(key)

    add(api_key)
    add(os.getenv(GEMINI_API_KEYS_ENV))

    numbered = []
    for env_name, env_value in os.environ.items():
        match = _NUMBERED_ENV_RE.match(env_name)
        if match and env_value:
            numbered.append((int(match.group(1)), env_value))
    for _, env_value in sorted(numbered, key=lambda item: item[0]):
        add(env_value)

    add(os.getenv(GEMINI_API_KEY_ENV))
    return keys


def is_key_exhaustion_error(exc: Exception) -> bool:
    resource_types = tuple(
        t for t in (ResourceExhausted, TooManyRequests) if isinstance(t, type)
    )
    if resource_types and isinstance(exc, resource_types):
        return True

    parts = [exc.__class__.__name__, str(exc)]
    text = " ".join(part for part in parts if part).lower()
    return any(marker in text for marker in _EXHAUSTION_MARKERS)


class KeyRotationState:
    _lock = Lock()
    _positions: dict[tuple[str, ...], int] = {}

    @classmethod
    def current_index(cls, pool: tuple[str, ...]) -> int:
        with cls._lock:
            return cls._positions.get(pool, 0)

    @classmethod
    def mark_success(cls, pool: tuple[str, ...], index: int) -> None:
        with cls._lock:
            cls._positions[pool] = index

    @classmethod
    def mark_exhausted(cls, pool: tuple[str, ...], index: int) -> None:
        with cls._lock:
            cls._positions[pool] = (index + 1) % len(pool)

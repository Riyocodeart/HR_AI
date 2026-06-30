"""
services.regex_service
======================
Offline regex-based JD parser. This is the last fallback in the parsing
chain — runs locally, no network, no LLM, always produces *something*.

Delegates to the existing ``core.parser.parse_jd`` so we don't fork the
implementation. The wrapper only exists to give the chain a uniform
``parse(text) -> dict`` interface.
"""

from __future__ import annotations

from typing import Any

from core.logger import get_logger
from core.parser import parse_jd as _regex_parse

log = get_logger(__name__)


def parse(text: str) -> dict[str, Any]:
    """
    Parse JD text using the offline regex parser.

    Returns the legacy-shape dict with ``_source="offline-regex"``
    stamped on it. Never raises — even an empty result is returned
    (with empty fields) rather than an exception.
    """
    try:
        result = dict(_regex_parse(text) or {})
    except Exception as exc:  # noqa: BLE001
        log.exception("regex.parse raised: %s", exc)
        result = {}
    result["_source"] = "offline-regex"
    return result


__all__ = ["parse"]

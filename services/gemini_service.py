"""
services.gemini_service
=======================
Gemini API surface for JD parsing. This module does **not** reimplement
Gemini — it wraps the existing functions in ``core.parser`` so the rest
of the codebase has a single, stable import path.

Public API
----------
* ``is_available()``      — ``bool`` (any keys configured?)
* ``parse_text(text)``    — parse a JD string, returns legacy-shape dict
* ``parse_upload(file)``  — parse a Streamlit ``UploadedFile`` (PDF/DOCX/TXT)

Design notes
------------
* Both ``parse_*`` functions resolve API keys themselves through
  :func:`core.helpers.gemini_keys` so callers never need to thread keys
  around.
* The underlying ``core.parser`` returns ``_source="gemini"`` on
  success and ``_source="offline-regex"`` when Gemini failed and its
  internal fallback fired. We surface that flag unchanged so the
  orchestrator (``services.jd_service``) can decide what to do.
"""

from __future__ import annotations

from typing import Any

from core.helpers import gemini_keys, has_gemini as _has_gemini
from core.logger import get_logger

# Delegate to the user's existing implementation — do NOT rewrite it.
from core.parser import (  # noqa: F401 — re-exported for advanced callers
    parse_jd_with_ai as _parse_text_with_ai,
    parse_jd_from_upload_with_ai as _parse_upload_with_ai,
)

log = get_logger(__name__)


# ─── Availability ──────────────────────────────────────────────────────────────
def is_available() -> bool:
    """True iff at least one Gemini API key is configured."""
    return _has_gemini()


# ─── Parse interfaces ──────────────────────────────────────────────────────────
def parse_text(text: str) -> dict[str, Any]:
    """
    Parse a JD string via Gemini. Returns the legacy-shape dict
    (``role``, ``company``, flat ``skills``, …).

    On Gemini failure ``_source`` will be ``"offline-regex"`` (Gemini's
    own internal regex fallback fired) — the orchestrator uses that to
    decide whether to retry with Qwen.
    """
    keys = gemini_keys()
    if not keys:
        log.info("gemini.parse_text: no API keys configured")
        return {"_source": "no-gemini-keys"}
    return dict(_parse_text_with_ai(text, api_key=keys) or {})


def parse_upload(uploaded_file) -> tuple[dict[str, Any], str]:
    """
    Parse a Streamlit ``UploadedFile`` via Gemini.

    Returns ``(jd_dict, raw_text)`` so the caller can stash the raw text
    in session_state alongside the parsed dict.
    """
    keys = gemini_keys()
    if not keys:
        log.info("gemini.parse_upload: no API keys configured")
        return ({"_source": "no-gemini-keys"}, "")
    jd, text = _parse_upload_with_ai(uploaded_file, api_key=keys)
    return dict(jd or {}), (text or "")


__all__ = ["is_available", "parse_text", "parse_upload"]
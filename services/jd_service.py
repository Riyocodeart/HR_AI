"""
services.jd_service
===================
The three-tier JD parsing orchestrator. Routes a JD through Gemini →
Qwen → Regex, stops at the first layer that produces a usable result,
and renders the typing animation around whichever layer ran.

This is the single canonical entry point for all JD parsing in the app.
Pages should call ``parse_jd_chain()`` and never reach for the
engine-specific services directly.

Public API
----------
* ``parse_jd_chain(jd_text, container)``
    Runs the full chain. Returns the legacy-shape dict (for the existing
    scorer / chatbot / email generator) and stashes the rich Qwen-shape
    dict on ``st.session_state.jd_data_full`` (for the LinkedIn tab).
    Returns ``None`` only if every single layer failed.

Layer order rationale
---------------------
1. **Gemini** first when keys are present — it's accurate and fast.
2. **Qwen** when Gemini is unavailable or errored — fully offline, ~5s
   on the 1.5B model. Honest second choice for hackathon submission.
3. **Regex** is the safety net. Never throws. Always returns *something*.
"""

from __future__ import annotations

from typing import Any, Optional

import streamlit as st

from core.logger import get_logger
from core.session import log_activity
from parser.cleaner import JDCleaner
from services import gemini_service, ollama_service, regex_service
from services.ollama_service import OllamaError
from ui.animations import (
    animate_reveal,
    gemini_to_qwen_shape,
    qwen_to_legacy_shape,
    render_parsing_animation,
)

log = get_logger(__name__)


# Single shared instance — cleaning is stateless so safe to reuse.
_JD_CLEANER = JDCleaner()


# ─── Helpers ───────────────────────────────────────────────────────────────────
def _finalize(legacy: dict, rich: dict, engine_label: str, container) -> dict:
    """Common tail: stash the rich shape and play the typing animation."""
    st.session_state.jd_data_full = rich
    animate_reveal(rich, container=container, engine_label=engine_label)
    return legacy


# ─── Public API ────────────────────────────────────────────────────────────────
def parse_jd_chain(jd_text: str, container) -> Optional[dict[str, Any]]:
    """
    Three-tier parsing pipeline. Returns the legacy-shape JD dict on
    success, ``None`` if every layer failed.

    The ``container`` is the Streamlit ``DeltaGenerator`` (usually
    ``st.column``) into which the typing animation will render.
    """
    if not jd_text or not jd_text.strip():
        container.warning("JD text is empty.")
        return None

    # ── Pre-clean (parser.cleaner.JDCleaner) ───────────────────────────────
    # Strip boilerplate ("Apply now", "Equal opportunity"), invisible chars,
    # bullet glyphs and collapse whitespace BEFORE any engine sees the text.
    # Was inline in the legacy app.py — now lives here so it applies to
    # Gemini and Regex paths too, not just Qwen.
    jd_text = _JD_CLEANER.clean(jd_text)

    # ── Layer 1 · Gemini ──────────────────────────────────────────────────
    if gemini_service.is_available():
        try:
            gemini_dict = gemini_service.parse_text(jd_text)
            if gemini_dict.get("_source") == "gemini":
                rich = gemini_to_qwen_shape(gemini_dict)
                log_activity("Parsed JD with Gemini · cloud", kind="success")
                return _finalize(gemini_dict, rich, "Gemini · cloud extraction", container)
            # Gemini call returned but its internal regex fallback fired —
            # fall through to Qwen rather than accept the regex result yet.
            log.info("Gemini returned a regex-fallback result; trying Qwen")
        except Exception as exc:  # noqa: BLE001
            log.warning("Gemini failed: %s — trying Qwen", exc)
            container.warning(f"Gemini failed ({exc}) — trying offline Qwen…")

    # ── Layer 2 · Qwen 2.5 (offline) ──────────────────────────────────────
    if ollama_service.is_reachable():
        try:
            qwen_dict = render_parsing_animation(
                ollama_service.get_parser(), jd_text, container=container,
            )
            st.session_state.jd_data_full = qwen_dict
            legacy = qwen_to_legacy_shape(qwen_dict)
            legacy["_source"] = "qwen-offline"
            log_activity("Parsed JD with Qwen 2.5 · offline", kind="success")
            return legacy
        except OllamaError as exc:
            log.warning("Ollama unreachable mid-call: %s", exc)
            container.warning(f"Ollama unreachable ({exc}) — falling back to regex…")
        except Exception as exc:  # noqa: BLE001
            log.warning("Qwen parsing error: %s", exc)
            container.warning(f"Qwen parsing error ({exc}) — falling back to regex…")
    else:
        log.info("Ollama not reachable — skipping Qwen layer")
        container.info("⚠ Ollama daemon not detected — using regex fallback.")

    # ── Layer 3 · Regex (always succeeds) ─────────────────────────────────
    try:
        regex_dict = regex_service.parse(jd_text)
        rich = gemini_to_qwen_shape(regex_dict)
        log_activity("Parsed JD with regex fallback", kind="warning")
        return _finalize(regex_dict, rich, "Offline · regex extraction", container)
    except Exception as exc:  # noqa: BLE001
        log.exception("All JD parsing layers failed")
        container.error(f"All JD parsing layers failed: {exc}")
        return None


__all__ = ["parse_jd_chain"]
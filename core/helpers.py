"""
core.helpers
============
Small cross-cutting helpers that were inline in ``app.py``. Kept tiny on
purpose — anything bigger than a handful of lines belongs in services/ or
ui/.
"""

from __future__ import annotations

import os
from typing import Iterable

import streamlit as st

from .constants import SCORE_HIGH_MIN, SCORE_MID_MIN


# ─── Gemini API keys ────────────────────────────────────────────────────────────
def gemini_keys() -> list[str]:
    """
    Return the user's Gemini API keys from session_state, env vars, or
    Streamlit secrets — in that priority order. Returns ``[]`` when none
    are configured (no Gemini path; the chain will fall through to Qwen).
    """
    # 1. Sidebar text-area (interactive). Read both the new and the legacy keys
    #    so the unified reader works regardless of which sidebar code wrote.
    raw = (
        st.session_state.get("gemini_api_keys_raw")
        or st.session_state.get("_gemini_api_keys_input")
        or ""
    )
    keys = [k.strip() for k in raw.replace(",", "\n").splitlines() if k.strip()]
    if keys:
        return keys

    # 2. Environment
    env_val = os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY") or ""
    keys = [k.strip() for k in env_val.replace(",", "\n").splitlines() if k.strip()]
    if keys:
        return keys

    # 3. Streamlit secrets (deployed environments)
    try:
        sec = st.secrets.get("gemini", {})
        if isinstance(sec, dict):
            v = sec.get("api_keys") or sec.get("api_key") or ""
            if isinstance(v, str):
                v = [v]
            return [str(k).strip() for k in (v or []) if str(k).strip()]
    except Exception:  # noqa: BLE001 — secrets may not exist
        pass

    return []


def has_gemini() -> bool:
    """True iff any Gemini key is configured."""
    return bool(gemini_keys())


# ─── Score-band visual helper ───────────────────────────────────────────────────
def score_band(score: float | int | None) -> str:
    """
    Map a numeric score to a CSS class suffix:
    ``"high"`` (>= 70), ``"mid"`` (>= 45), ``"low"`` (< 45).
    """
    try:
        s = float(score)
    except (TypeError, ValueError):
        return "low"
    if s >= SCORE_HIGH_MIN:
        return "high"
    if s >= SCORE_MID_MIN:
        return "mid"
    return "low"


# ─── Formatting ─────────────────────────────────────────────────────────────────
def humanise_count(n: int | None) -> str:
    """Format integers for the dashboard ('1.2k', '450', '—' for None)."""
    if n is None:
        return "—"
    try:
        n = int(n)
    except (TypeError, ValueError):
        return "—"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}k"
    return str(n)


def truthy_list(it: Iterable | None) -> list:
    """Convenience: turn a possibly-None iterable into a list of truthy values."""
    if not it:
        return []
    return [x for x in it if x]

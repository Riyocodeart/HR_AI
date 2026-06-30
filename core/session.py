"""
core.session
============
Centralised Streamlit ``session_state`` initialisation.

Call ``init()`` once at the top of app.py. It seeds every key the rest of
the app expects, so individual pages can read state without defensive
``.get()`` calls everywhere.
"""

from __future__ import annotations

from typing import Any

import streamlit as st


# Anything new pages need at startup goes here — not scattered across files.
_DEFAULTS: dict[str, Any] = {
    # JD parsing state
    "jd_data": None,
    "jd_data_full": None,    # rich Qwen-shape dict (for LinkedIn tab)
    "jd_text": None,
    "jd_source": None,       # "gemini" | "qwen-offline" | "offline-regex"
    "_jd_file_hash": None,

    # Candidates / scoring
    "candidates_df": None,
    "scored_df": None,
    "score_source": None,
    "col_map": {},
    "name_col_detected": None,
    "rejected_df": None,         # Blueprint Step 5/6 — rejected by data quality
    "jsonl_auto_path": None,     # cached candidates.jsonl discovery

    # LinkedIn URLs
    "linkedin_url": None,
    "xray_url": None,

    # Email automation
    "selected_candidates": [],
    "email_drafts": {},
    "send_log": [],

    # Navigation
    "active_tab": "overview",

    # Chatbot
    "chat_history": [],

    # Activity feed (Wave 1 — for the Overview dashboard)
    "activity_log": [],
}


def init() -> None:
    """Seed any missing keys in ``st.session_state``. Idempotent."""
    for key, value in _DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value


def log_activity(message: str, kind: str = "info") -> None:
    """
    Append a one-line event to the rolling activity feed shown on the
    Overview page. Kept tiny on purpose — we only keep the last 30 events.

    Parameters
    ----------
    message : str
        Human-readable line, e.g. ``"Parsed JD with Qwen 2.5 · 8.4s"``.
    kind : str
        Visual category: ``"info" | "success" | "warning" | "error"``.
    """
    import time
    log = st.session_state.get("activity_log") or []
    log.insert(0, {"ts": time.time(), "msg": message, "kind": kind})
    st.session_state.activity_log = log[:30]
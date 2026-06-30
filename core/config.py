"""
core.config
===========
Boot-time configuration. Call ``setup_page()`` first in app.py, before
anything else from Streamlit is rendered.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from .constants import APP_ICON, APP_NAME


# ─── Filesystem ─────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = PROJECT_ROOT / "jd_schema.json"


def setup_page() -> None:
    """Configure Streamlit's page-level settings. Must be the first ``st.*`` call."""
    st.set_page_config(
        page_title=APP_NAME,
        page_icon=APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "About": f"{APP_NAME} — Offline-first recruiting suite. "
                     "Powered by Gemini · Qwen 2.5 · Regex fallback chain.",
        },
    )

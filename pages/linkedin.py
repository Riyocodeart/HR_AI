"""
pages.linkedin
==============
The dedicated LinkedIn search tab. All UI logic lives in
``ui.linkedin_tab`` (built earlier as part of the LinkedIn-tab split) —
this page is the canonical router entry point.

Behaviour is unchanged from the legacy ``app.py`` block.
"""

from __future__ import annotations

import streamlit as st

from ui.linkedin_tab import render_linkedin_tab


def render() -> None:
    """Render the LinkedIn search tab using the rich Qwen-shape JD dict."""
    render_linkedin_tab(st.session_state.jd_data_full)

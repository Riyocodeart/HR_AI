"""
app.py
======
NexRecruit AI — Streamlit entry point.

This file does exactly four things:

    1. Boot:    page config + theme + session_state defaults
    2. Sidebar: render left-rail navigation
    3. Dispatch: route to the active page's render() function
    4. Nothing else.

All business logic lives in ``services/``.
All UI primitives live in ``ui/``.
All page implementations live in ``pages/``.

If you find yourself adding more than 5 lines here, you're probably
adding the wrong thing — push it into the appropriate layer instead.
"""

from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

import streamlit as st

# ─── Layer 1: boot ──────────────────────────────────────────────────────────────
from core.config import setup_page
from core.session import init as init_session
from ui.styles import apply as apply_theme

setup_page()
apply_theme()
init_session()


# ─── Layer 2: sidebar ───────────────────────────────────────────────────────────
from ui.sidebar import render as render_sidebar

render_sidebar()


# ─── Layer 3: page dispatch ─────────────────────────────────────────────────────
# Map active_tab → page render() function. Adding a new page is a one-line edit.
from pages import overview, recruiter, linkedin, analytics, chatbot, email

PAGE_DISPATCH = {
    "overview":  overview.render,
    "recruiter": recruiter.render,
    "linkedin":  linkedin.render,
    "analytics": analytics.render,
    "chatbot":   chatbot.render,
    "email":     email.render,
}

active = st.session_state.get("active_tab") or "overview"
PAGE_DISPATCH.get(active, overview.render)()
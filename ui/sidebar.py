"""
ui.sidebar
==========
The left-hand navigation rail. Matches the reference Command-Center
screenshots: brand mark, vertical nav with active state, "Integrations"
status panel, and pipeline-step indicator at the bottom.

Public entry point
------------------
``render() -> None``
    Renders the sidebar and writes the chosen tab into
    ``st.session_state.active_tab``. Nothing returned — the caller reads
    state.
"""

from __future__ import annotations

import streamlit as st

from core.constants import APP_NAME, APP_TAGLINE, TABS
from core.helpers import has_gemini


# Names of integrations to display in the status panel.
# Truthy-check is done at render time, so adding a new row is one line.
def _integration_rows() -> list[tuple[str, bool]]:
    return [
        ("Gemini API",   has_gemini()),
        ("Ollama Local", True),   # Always shown; the parser checks at call-time
        ("LinkedIn",     bool(st.session_state.get("jd_data"))),
        ("Gmail",        False),  # Toggle when Gmail OAuth is wired up
    ]


def _brand() -> None:
    """Render the NexRecruit logo + tagline at the top of the sidebar."""
    # NB: APP_NAME contains "NexRecruit AI" — we colour the "AI" purple.
    name = APP_NAME
    if name.endswith(" AI"):
        name_html = f'{name[:-3]}<em>AI</em>'
    else:
        name_html = name

    st.markdown(
        f"""
        <div class="brand-row">
            <div class="brand-hex">⬡</div>
            <div class="brand-name">{name_html}</div>
        </div>
        <div class="brand-sub">{APP_TAGLINE}</div>
        <hr class="sidebar-divider"/>
        """,
        unsafe_allow_html=True,
    )


def _navigation() -> None:
    """Render the vertical nav. Active tab gets `kind='primary'` for the CSS hook."""
    st.markdown('<div class="sidebar-section">Navigation</div>', unsafe_allow_html=True)

    active = st.session_state.get("active_tab", "overview")
    for tab_id, icon, label in TABS:
        is_active = (tab_id == active)
        if st.button(
            f"{icon}   {label}",
            key=f"nav_{tab_id}",
            use_container_width=True,
            type=("primary" if is_active else "secondary"),
        ):
            st.session_state.active_tab = tab_id
            st.rerun()


def _integrations() -> None:
    """Render the colored 'Connected / Missing' integration status panel."""
    st.markdown('<hr class="sidebar-divider"/>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-section">Integrations</div>', unsafe_allow_html=True)

    rows_html = []
    for name, connected in _integration_rows():
        cls = "status-on" if connected else "status-off"
        label = "Connected" if connected else "Missing"
        rows_html.append(
            f'<div class="row"><span>{name}</span>'
            f'<span class="{cls}">{label}</span></div>'
        )
    st.markdown(
        f'<div class="integrations-card">{"".join(rows_html)}</div>',
        unsafe_allow_html=True,
    )


def _pipeline_progress() -> None:
    """Tiny indicator showing how far through the recruiter pipeline you are."""
    has_jd     = bool(st.session_state.get("jd_data"))
    has_cands  = st.session_state.get("candidates_df") is not None
    has_score  = st.session_state.get("scored_df") is not None
    has_export = bool(st.session_state.get("send_log"))

    steps = [
        ("01", "Upload JD",       has_jd),
        ("02", "Upload Cands",    has_cands),
        ("03", "Score & Rank",    has_score),
        ("04", "Export / Email",  has_export),
    ]

    st.markdown('<div class="sidebar-section" style="margin-top:0.5rem">Pipeline Steps</div>',
                unsafe_allow_html=True)

    pill_html = []
    for num, label, done in steps:
        color = "var(--green)" if done else "var(--text-faint)"
        bg    = "var(--green-bg)" if done else "var(--bg-nested)"
        border= "var(--green)" if done else "var(--border)"
        pill_html.append(f"""
        <div style="display:flex;align-items:center;gap:0.6rem;padding:0.3rem 1rem;
                    font-family:'JetBrains Mono',monospace;font-size:0.72rem;">
          <span style="display:inline-flex;align-items:center;justify-content:center;
                       width:22px;height:22px;border-radius:6px;
                       background:{bg};border:1px solid {border};color:{color};
                       font-weight:600;font-size:0.65rem;letter-spacing:0.05em">{num}</span>
          <span style="color:{color}">{label}</span>
        </div>""")
    st.markdown("".join(pill_html), unsafe_allow_html=True)


def _gemini_keys_input() -> None:
    """Optional textarea so the user can paste Gemini keys without env vars."""
    with st.expander("⚙ Gemini API Keys", expanded=False):
        st.text_area(
            "Paste one key per line",
            key="gemini_api_keys_raw",
            height=80,
            placeholder="AIzaSy…\nAIzaSy…",
            label_visibility="collapsed",
        )


# ─── Public API ────────────────────────────────────────────────────────────────
def render() -> None:
    """Render the entire sidebar. Idempotent on each Streamlit rerun."""
    with st.sidebar:
        _brand()
        _navigation()
        _integrations()
        _pipeline_progress()
        st.markdown('<hr class="sidebar-divider"/>', unsafe_allow_html=True)
        _gemini_keys_input()

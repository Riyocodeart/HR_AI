"""
pages.overview
==============
The Command Center landing page. Mirrors the reference screenshot:

    ┌────────────────────────────────────────────────────────────────────┐
    │ Welcome to the Command Center, <name>                       Deploy │
    │                                                                    │
    │ PIPELINE STATUS ROW                                                │
    │ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐                       │
    │ │ Roles  │ │ JDs    │ │ Cands  │ │ Pipeline│                      │
    │ └────────┘ └────────┘ └────────┘ └────────┘                       │
    │                                                                    │
    │ ┌────────────────┐  ┌────────────────┐  ┌─────────────────┐       │
    │ │ Quick upload   │  │ Top candidates │  │ Activity feed   │       │
    │ │                │  │                │  │                 │       │
    │ │                │  │                │  │ AI Suggestions  │       │
    │ └────────────────┘  └────────────────┘  └─────────────────┘       │
    │                                                                    │
    │ ┌────────────────────────────┐  ┌────────────────────────────┐    │
    │ │ Recent AI Insights         │  │ Latest JD Parsed           │    │
    │ └────────────────────────────┘  └────────────────────────────┘    │
    └────────────────────────────────────────────────────────────────────┘

All KPI values are computed from real session_state — no fake numbers
unless the data isn't there yet (then we show ``"—"`` or empty states).
"""

from __future__ import annotations

import random

import streamlit as st

from ui.components import (
    activity_item,
    candidate_row,
    dash_card,
    empty_state,
    metric_card,
    page_hero,
    section_label,
)


# ─── Helpers ───────────────────────────────────────────────────────────────────
def _kpi_values() -> dict[str, int]:
    """Read session_state to compute KPI numbers shown in the top row."""
    jd     = st.session_state.get("jd_data")
    cands  = st.session_state.get("candidates_df")
    scored = st.session_state.get("scored_df")
    sent   = st.session_state.get("send_log") or []

    return {
        "open_roles":   1 if jd else 0,
        "jds_parsed":   1 if jd else 0,   # session-scoped count
        "candidates":   (len(cands) if cands is not None else 0),
        "matches":      (
            int((scored["score"] >= 70).sum())
            if scored is not None and "score" in scored.columns
            else 0
        ),
        "emails_sent":  len(sent),
    }


def _synthetic_sparkline(seed: int, n: int = 12, low: int = 4, high: int = 22) -> list[int]:
    """Deterministic sparkline data so the dashboard doesn't reshuffle on rerun."""
    rng = random.Random(seed)
    return [rng.randint(low, high) for _ in range(n)]


# ─── Sections ──────────────────────────────────────────────────────────────────
def _pipeline_status_row() -> None:
    """Top row of 4 metric cards — the visual signature of the dashboard."""
    k = _kpi_values()
    section_label("Pipeline Status Row")

    c1, c2, c3, c4 = st.columns(4, gap="medium")
    with c1:
        metric_card(
            "Open Roles",
            k["open_roles"],
            icon="◆",
            spark=_synthetic_sparkline(1),
            spark_kind="line",
        )
    with c2:
        metric_card(
            "New JDs Parsed",
            k["jds_parsed"],
            icon="▤",
            spark=_synthetic_sparkline(2),
            spark_kind="bars",
        )
    with c3:
        metric_card(
            "Candidate Matches",
            k["matches"],
            icon="◑",
            spark=_synthetic_sparkline(3),
            spark_kind="bars",
        )
    with c4:
        metric_card(
            "Interview Pipeline",
            k["emails_sent"],
            icon="⬡",
            spark=_synthetic_sparkline(4),
            spark_kind="line",
        )


def _quick_upload_card() -> None:
    """Mini-version of the recruiter Step 01 — one click to jump there."""
    with dash_card("Create New Role & Upload JD"):
        jd = st.session_state.get("jd_data")
        if jd:
            st.markdown(
                f"<div style='color:var(--text-dim);font-size:0.88rem;line-height:1.7'>"
                f"Current role: <strong style='color:#fff'>{jd.get('role', '—')}</strong><br>"
                f"Company: <span style='color:#fff'>{jd.get('company', '—')}</span><br>"
                f"Location: <span style='color:#fff'>{jd.get('location', '—')}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("→  Continue in Recruiter", key="ov_to_recr", use_container_width=True):
                st.session_state.active_tab = "recruiter"
                st.rerun()
        else:
            empty_state("Upload a JD in the Recruiter tab to begin")
            if st.button("→  Go to Recruiter", key="ov_to_recr_empty", use_container_width=True):
                st.session_state.active_tab = "recruiter"
                st.rerun()


def _top_candidates_card() -> None:
    """Top 5 scored candidates. Falls back to the empty state if none yet."""
    with dash_card("Top Candidate Matches", subtitle="Last session"):
        scored = st.session_state.get("scored_df")
        if scored is None or len(scored) == 0:
            empty_state("Score candidates to see top matches", hex_icon="◑")
            return

        # Detect name column (the existing scorer puts it in `name_col_detected`).
        name_col = st.session_state.get("name_col_detected") or "Name"
        top = scored.head(5)
        for _, row in top.iterrows():
            candidate_row(
                name=str(row.get(name_col, "Anonymous")),
                role=str(row.get("Role", row.get("Title", "—"))) if hasattr(row, "get") else "—",
                score=row.get("score") if hasattr(row, "get") else None,
            )


def _activity_feed_card() -> None:
    """Recent Activity feed. Real events come from ``core.session.log_activity``."""
    with dash_card("Recent Activity Feed"):
        log = st.session_state.get("activity_log") or []
        if not log:
            # Seed with a friendly intro item so the panel isn't blank.
            activity_item(
                "Welcome to NexRecruit AI. Start by uploading a JD →",
                ts=None, kind="info",
            )
            return
        for entry in log[:6]:
            activity_item(
                entry.get("msg", "—"),
                ts=entry.get("ts"),
                kind=entry.get("kind", "info"),
            )


def _ai_suggestions_card() -> None:
    """Static AI-suggestion tile shown beneath the activity feed."""
    jd = st.session_state.get("jd_data")
    if jd:
        skill_hint = ", ".join((jd.get("skills") or [])[:3]) or "—"
        tip = f"Strong candidates for this role likely have: {skill_hint}."
    else:
        tip = "Upload a JD to see AI-generated sourcing suggestions."

    st.markdown(
        f"""
        <div class="dash-card" style="border-color:var(--border-purple)">
          <div class="dash-card-head">
            <h3 class="dash-card-title">AI Suggestions
              <span class="dash-card-title-sub">· auto-generated</span>
            </h3>
          </div>
          <div style="color:var(--text-dim);font-size:0.88rem;line-height:1.6">
            {tip}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _ai_insights_card() -> None:
    """Lower-left card: insight bullets pulled from the current JD."""
    with dash_card("Recent AI Insights"):
        jd = st.session_state.get("jd_data")
        if not jd:
            empty_state("Insights appear after you parse a JD")
            return
        skills = jd.get("skills") or []
        bullets = [
            f"Highest-demand skills: {', '.join(skills[:4]) or '—'}",
            f"Experience target: {jd.get('experience_min', '?')}–{jd.get('experience_max', '?')} yrs",
            f"Industry focus: {jd.get('industry', '—')}",
            f"Source engine: {st.session_state.get('jd_source', 'unknown')}",
        ]
        st.markdown(
            "<div style='font-size:0.9rem;line-height:1.9;color:var(--text-dim)'>"
            + "".join(f"<div>• {b}</div>" for b in bullets)
            + "</div>",
            unsafe_allow_html=True,
        )


def _latest_jd_card() -> None:
    """Lower-right card: snapshot of the most recently parsed JD."""
    with dash_card("Latest JD Parsed"):
        jd = st.session_state.get("jd_data")
        if not jd:
            empty_state("No JD parsed yet")
            return

        rows = [
            ("👤  Role",        jd.get("role", "—")),
            ("🏢  Company",     jd.get("company", "—")),
            ("📍  Location",    jd.get("location", "—")),
            ("📅  Experience",  f"{jd.get('experience_min', '?')}–{jd.get('experience_max', '?')} yrs"),
            ("📊  Industry",    jd.get("industry", "—")),
            ("🎓  Education",   jd.get("education", "—")),
        ]
        st.markdown(
            "<div style='display:grid;grid-template-columns:1fr 1fr;gap:0.6rem 1.4rem'>"
            + "".join(
                f"<div><span style='color:var(--text-dim);font-size:0.74rem;"
                f"font-family:JetBrains Mono,monospace'>{lbl}</span><br>"
                f"<span style='color:#fff;font-weight:500'>{val}</span></div>"
                for lbl, val in rows
            )
            + "</div>",
            unsafe_allow_html=True,
        )


# ─── Public entry point ────────────────────────────────────────────────────────
def render() -> None:
    """Render the Overview / Command Center page."""
    page_hero(
        "Welcome to the Command Center",
        accent_word="Command Center",
        subtitle="Real-time recruiting telemetry",
        show_deploy=True,
    )

    _pipeline_status_row()
    st.markdown("<br>", unsafe_allow_html=True)

    # Three-column dashboard row
    left, mid, right = st.columns([1.1, 1.3, 1.0], gap="medium")
    with left:
        _quick_upload_card()
    with mid:
        _top_candidates_card()
    with right:
        _activity_feed_card()
        _ai_suggestions_card()

    # Bottom two-column row
    bl, br = st.columns(2, gap="medium")
    with bl:
        _ai_insights_card()
    with br:
        _latest_jd_card()

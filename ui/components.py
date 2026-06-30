"""
ui.components
=============
Reusable presentational primitives. Every function:

* Takes plain Python args (no Streamlit state coupling).
* Renders by calling ``st.markdown(..., unsafe_allow_html=True)``.
* Returns ``None``.

These are the building blocks for pages/overview.py and the Recruiter tab.
"""

from __future__ import annotations

import time
from typing import Iterable, Sequence

import streamlit as st

from core.helpers import score_band


# ─── Hero header ───────────────────────────────────────────────────────────────
def page_hero(
    title: str,
    *,
    subtitle: str | None = None,
    accent_word: str | None = None,
    show_deploy: bool = True,
) -> None:
    """
    Page header that mirrors the reference 'Welcome to the Command Center'.

    Parameters
    ----------
    title : str
        Main headline.
    accent_word : str | None
        If given, this word is highlighted in purple (e.g. the user's name).
    subtitle : str | None
        Small uppercase mono caption below the title.
    show_deploy : bool
        Whether to render the purple ``Deploy`` button on the right.
    """
    rendered_title = title
    if accent_word and accent_word in title:
        rendered_title = title.replace(accent_word, f"<em>{accent_word}</em>")

    sub_html = (
        f'<div class="page-hero-sub">{subtitle}</div>' if subtitle else ""
    )

    deploy_html = (
        '<button class="deploy-btn">Deploy</button>' if show_deploy else ""
    )

    st.markdown(
        f"""
        <div class="page-hero">
          <div>
            <h1 class="page-hero-title">{rendered_title}</h1>
            {sub_html}
          </div>
          <div class="page-hero-actions">{deploy_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─── Section label ─────────────────────────────────────────────────────────────
def section_label(text: str) -> None:
    """Small uppercase mono label used as a section header."""
    st.markdown(f'<div class="section-label">{text}</div>', unsafe_allow_html=True)


# ─── Metric card ───────────────────────────────────────────────────────────────
def _spark_svg(values: Sequence[float], *, kind: str = "line") -> str:
    """Tiny inline SVG sparkline. ``kind`` is ``"line"`` or ``"bars"``."""
    if not values:
        return ""
    w, h = 110, 38
    vmax = max(values) or 1
    vmin = min(values)
    span = (vmax - vmin) or 1

    if kind == "bars":
        n = len(values)
        gap = 2
        bw = (w - gap * (n - 1)) / n
        bars = []
        for i, v in enumerate(values):
            bh = max(2, (v - vmin) / span * (h - 4))
            x = i * (bw + gap)
            y = h - bh
            # gradient by index — purple → cyan
            bars.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{bh:.1f}" '
                f'rx="2" fill="url(#spark-grad)"/>'
            )
        return (
            f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'xmlns="http://www.w3.org/2000/svg">'
            f'<defs><linearGradient id="spark-grad" x1="0" x2="1">'
            f'<stop offset="0" stop-color="#7c3aed"/>'
            f'<stop offset="1" stop-color="#22d3ee"/>'
            f'</linearGradient></defs>'
            f'{"".join(bars)}</svg>'
        )

    # line
    n = len(values)
    if n < 2:
        return ""
    step = w / (n - 1)
    points = " ".join(
        f"{i*step:.1f},{(h - (v - vmin) / span * (h - 4) - 2):.1f}"
        for i, v in enumerate(values)
    )
    return (
        f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        f'xmlns="http://www.w3.org/2000/svg">'
        f'<defs><linearGradient id="spark-grad" x1="0" x2="1">'
        f'<stop offset="0" stop-color="#7c3aed"/>'
        f'<stop offset="1" stop-color="#22d3ee"/>'
        f'</linearGradient></defs>'
        f'<polyline points="{points}" fill="none" stroke="url(#spark-grad)" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
        f'</svg>'
    )


def metric_card(
    label: str,
    value: str | int | float,
    *,
    icon: str = "▦",
    spark: Sequence[float] | None = None,
    spark_kind: str = "line",
    delta: str | None = None,
    delta_direction: str = "up",
) -> None:
    """
    KPI tile used in the dashboard "Pipeline Status Row".

    Parameters
    ----------
    label : str
        Uppercase mono label (e.g. ``"OPEN ROLES"``).
    value : str | int | float
        Big headline number.
    icon : str
        Small glyph in the top-right corner of the card.
    spark : list[float] | None
        Optional sparkline values rendered as SVG. ``None`` = no chart.
    spark_kind : str
        ``"line"`` or ``"bars"``.
    delta : str | None
        Optional caption underneath the value (e.g. ``"+12% this week"``).
    delta_direction : str
        ``"up"`` (green) or ``"down"`` (red).
    """
    spark_html = _spark_svg(spark or [], kind=spark_kind)
    delta_html = (
        f'<div class="metric-card-delta {"down" if delta_direction == "down" else ""}">{delta}</div>'
        if delta else ""
    )

    st.markdown(
        f"""
        <div class="metric-card">
          <div class="metric-card-head">
            <div class="metric-card-label">{label}</div>
            <div class="metric-card-icon">{icon}</div>
          </div>
          <div class="metric-card-body">
            <div>
              <div class="metric-card-value">{value}</div>
              {delta_html}
            </div>
            <div class="metric-card-spark">{spark_html}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─── Dashboard card wrapper (open/close so callers can put st.* inside) ────────
class dash_card:
    """
    Context manager for a uniform dark dashboard card.

    Usage
    -----
    >>> with dash_card("Top Candidate Matches", subtitle="Last 24 hours"):
    ...     st.dataframe(top_candidates_df)
    """

    def __init__(self, title: str, *, subtitle: str | None = None) -> None:
        self.title = title
        self.subtitle = subtitle

    def __enter__(self) -> None:
        sub = (
            f'<span class="dash-card-title-sub">{self.subtitle}</span>'
            if self.subtitle else ""
        )
        st.markdown(
            f"""
            <div class="dash-card">
              <div class="dash-card-head">
                <h3 class="dash-card-title">{self.title} {sub}</h3>
              </div>
            """,
            unsafe_allow_html=True,
        )
        return None

    def __exit__(self, *exc) -> None:
        st.markdown("</div>", unsafe_allow_html=True)


# ─── Candidate row (for the "Top Matches" list) ────────────────────────────────
def candidate_row(
    name: str,
    role: str | None,
    score: float | int | None,
) -> None:
    """One row in the Top Matches list. Avatar from initials, colored score."""
    initials = "".join(p[0] for p in name.split()[:2]).upper() or "?"
    band = score_band(score)
    try:
        score_text = f"{float(score):.0f}" if score is not None else "—"
    except (TypeError, ValueError):
        score_text = "—"
    role_text = role or "—"

    st.markdown(
        f"""
        <div class="cand-row">
          <div class="cand-avatar">{initials}</div>
          <div>
            <div class="cand-name">{name}</div>
            <div class="cand-meta">{role_text}</div>
          </div>
          <span class="tag tag-match">Match</span>
          <span class="cand-score {band}">{score_text}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─── Activity item ─────────────────────────────────────────────────────────────
_KIND_ICONS = {"info": "◐", "success": "✓", "warning": "!", "error": "✗"}


def activity_item(message: str, ts: float | None = None, kind: str = "info") -> None:
    """One row in the Recent Activity feed."""
    icon = _KIND_ICONS.get(kind, "◐")
    ago = _humanise_ts(ts) if ts else ""
    st.markdown(
        f"""
        <div class="activity-item">
          <div class="activity-dot">{icon}</div>
          <div>
            <div class="activity-msg">{message}</div>
            <div class="activity-ts">{ago}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _humanise_ts(ts: float) -> str:
    diff = max(0, int(time.time() - ts))
    if diff < 60:    return f"{diff}s ago"
    if diff < 3600:  return f"{diff // 60}m ago"
    if diff < 86400: return f"{diff // 3600}h ago"
    return f"{diff // 86400}d ago"


# ─── Empty state ──────────────────────────────────────────────────────────────
def empty_state(message: str, *, hex_icon: str = "⬡") -> None:
    """Dashed placeholder shown where data is not yet available."""
    st.markdown(
        f"""
        <div class="empty-state">
          <div class="hex">{hex_icon}</div>
          <div class="msg">{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

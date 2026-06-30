"""
services.analytics_service
==========================
Pure computation helpers for the Analytics page. Deliberately Streamlit-free
so they can be unit-tested in isolation. The actual rendering lives in
``pages/analytics.py`` (Wave 3).

Public API
----------
* ``score_distribution(scored_df)``   — bands + counts for the histogram
* ``pipeline_funnel(state)``          — funnel counts from session state
* ``skill_demand(jd, scored_df)``     — top skills × candidate match counts
* ``source_breakdown(scored_df)``     — Gemini vs Qwen vs Regex usage
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from core.constants import SCORE_HIGH_MIN, SCORE_MID_MIN


def score_distribution(scored_df: pd.DataFrame | None) -> dict[str, int]:
    """
    Bucket candidate scores into ``high / mid / low`` bands. Returns
    ``{"high": int, "mid": int, "low": int, "total": int}``.
    """
    if scored_df is None or "score" not in getattr(scored_df, "columns", []):
        return {"high": 0, "mid": 0, "low": 0, "total": 0}
    s = scored_df["score"]
    return {
        "high":  int((s >= SCORE_HIGH_MIN).sum()),
        "mid":   int(((s >= SCORE_MID_MIN) & (s < SCORE_HIGH_MIN)).sum()),
        "low":   int((s < SCORE_MID_MIN).sum()),
        "total": int(len(s)),
    }


def pipeline_funnel(state: dict[str, Any]) -> list[tuple[str, int]]:
    """
    Compute funnel counts from session state. Returns an ordered list of
    ``(stage_name, count)`` tuples — the order matters for rendering.
    """
    jd       = state.get("jd_data")
    cands    = state.get("candidates_df")
    scored   = state.get("scored_df")
    selected = state.get("selected_candidates") or []
    sent     = state.get("send_log") or []

    n_cands  = len(cands) if cands is not None else 0
    n_score  = len(scored) if scored is not None else 0
    n_high   = score_distribution(scored)["high"]
    n_sel    = len(selected)
    n_sent   = len(sent)

    return [
        ("JDs",            1 if jd else 0),
        ("Sourced",        n_cands),
        ("Scored",         n_score),
        ("High matches",   n_high),
        ("Selected",       n_sel),
        ("Outreach sent",  n_sent),
    ]


def skill_demand(
    jd: dict[str, Any] | None,
    scored_df: pd.DataFrame | None,
    limit: int = 6,
) -> list[tuple[str, int]]:
    """
    For each JD-required skill, count how many candidates mention it.
    Returns ``[(skill, count), …]`` sorted descending; truncated to
    ``limit``.

    Falls back to an empty list if either side is missing.
    """
    if not jd or scored_df is None or len(scored_df) == 0:
        return []

    skills = jd.get("skills") or []
    if not skills:
        return []

    # Best-effort: look for skill strings anywhere in the row's text columns.
    text_cols = [c for c in scored_df.columns if scored_df[c].dtype == object]
    if not text_cols:
        return []
    haystack = scored_df[text_cols].fillna("").astype(str).agg(" ".join, axis=1).str.lower()

    counts = []
    for skill in skills[:20]:  # cap for perf
        needle = str(skill).strip().lower()
        if not needle:
            continue
        counts.append((skill, int(haystack.str.contains(needle, regex=False).sum())))
    counts.sort(key=lambda t: t[1], reverse=True)
    return counts[:limit]


def source_breakdown(scored_df: pd.DataFrame | None) -> dict[str, int]:
    """Count how candidates were scored: Gemini vs Qwen vs Regex."""
    if scored_df is None or "score_source" not in getattr(scored_df, "columns", []):
        return {}
    return scored_df["score_source"].value_counts().to_dict()


__all__ = [
    "score_distribution",
    "pipeline_funnel",
    "skill_demand",
    "source_breakdown",
]

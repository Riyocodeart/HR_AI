"""
pages.analytics
===============
Analytics dashboard for the scored-candidate pool. Logic preserved
verbatim from the legacy ``app.py``; only imports were reorganised.

The page reads ``st.session_state.scored_df`` and renders KPI cards,
score distribution, source breakdown, and a recruiter-funnel view.

Dependencies
------------
* ``services.analytics_service`` — pure-Python helpers (no Streamlit)
* ``core.helpers``               — score_band
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.helpers import score_band
from services import analytics_service


def _score_badge(score) -> str:
    return f"score-{score_band(score)}"


def render() -> None:
    """Render the analytics page."""

    st.markdown("""
    <div class="page-header">
      <div class="page-header-pill">📊 &nbsp; Analytics Dashboard</div>
      <h1>Candidate <span class="glow">Insights</span></h1>
      <p>Score distribution · Skill gaps · Location · Experience</p>
    </div>""", unsafe_allow_html=True)

    if st.session_state.scored_df is None:
        st.info("Score candidates in the Recruiter tab first to see analytics.")
    else:
        scored = st.session_state.scored_df
        jd     = st.session_state.jd_data or {}

        # ── Summary Metrics ──
        m1, m2, m3, m4, m5 = st.columns(5)
        top70 = len(scored[scored["total_score"] >= 70])
        top45 = len(scored[(scored["total_score"] >= 45) & (scored["total_score"] < 70)])
        low   = len(scored[scored["total_score"] < 45])
        for col, val, lbl in [
            (m1, len(scored), "Total"),
            (m2, top70, "Strong ≥70"),
            (m3, top45, "Good 45-69"),
            (m4, low, "Weak <45"),
            (m5, round(float(scored["total_score"].mean()), 1), "Avg Score"),
        ]:
            col.markdown(f'<div class="metric-card"><div class="m-value">{val}</div><div class="m-label">{lbl}</div></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        ch1, ch2 = st.columns(2)
        with ch1:
            st.markdown('<div class="dark-card">', unsafe_allow_html=True)
            st.markdown("**Score Distribution**")
            bins = [0,20,40,60,70,80,100]
            labels = ["0-20","21-40","41-60","61-70","71-80","81-100"]
            cuts = pd.cut(scored["total_score"], bins=bins, labels=labels, right=True)
            dist = cuts.value_counts().reindex(labels).fillna(0)
            st.bar_chart(dist)
            st.markdown('</div>', unsafe_allow_html=True)

        with ch2:
            st.markdown('<div class="dark-card">', unsafe_allow_html=True)
            st.markdown("**Score Sub-Components (avg)**")
            avg_cols = {}
            for c in ["skill_score","role_score","signal_score","experience_score"]:
                if c in scored.columns:
                    avg_cols[c.replace("_score","").title()] = round(float(scored[c].mean()), 1)
            if avg_cols:
                st.bar_chart(pd.Series(avg_cols))
            else:
                st.info("No sub-score columns found.")
            st.markdown('</div>', unsafe_allow_html=True)

        # Skill gap chart
        if "missing_skills" in scored.columns:
            all_missing = []
            for cell in scored["missing_skills"].dropna():
                for s in str(cell).split(","):
                    s = s.strip()
                    if s and s.lower() not in ("none","nan",""):
                        all_missing.append(s.lower())
            if all_missing:
                miss_counts = pd.Series(all_missing).value_counts().head(12)
                st.markdown('<div class="dark-card">', unsafe_allow_html=True)
                st.markdown("**Top Missing Skills (Skill Gap)**")
                st.bar_chart(miss_counts)
                st.caption("These required skills are absent in the most candidates — prime areas for training or sourcing.")
                st.markdown('</div>', unsafe_allow_html=True)

        # Location breakdown
        col_map = st.session_state.col_map or {}
        loc_col = col_map.get("location") or ("location" if "location" in scored.columns else None)
        if loc_col and loc_col in scored.columns:
            ch3, ch4 = st.columns(2)
            with ch3:
                st.markdown('<div class="dark-card">', unsafe_allow_html=True)
                st.markdown("**Candidates by Location**")
                loc_counts = scored[loc_col].value_counts().head(10)
                st.bar_chart(loc_counts)
                st.markdown('</div>', unsafe_allow_html=True)

            exp_col = col_map.get("experience") or ("experience" if "experience" in scored.columns else None)
            if exp_col and exp_col in scored.columns:
                with ch4:
                    st.markdown('<div class="dark-card">', unsafe_allow_html=True)
                    st.markdown("**Experience Distribution (years)**")
                    import re
                    def _trynum(v):
                        m = re.search(r"\d+", str(v))
                        return float(m.group()) if m else None
                    exp_vals = scored[exp_col].apply(_trynum).dropna()
                    if not exp_vals.empty:
                        exp_bins = pd.cut(exp_vals, bins=[0,2,4,6,8,10,15,30], labels=["0-2","3-4","5-6","7-8","9-10","11-15","15+"])
                        st.bar_chart(exp_bins.value_counts().sort_index())
                    st.markdown('</div>', unsafe_allow_html=True)

        # Top candidates table
        st.markdown("#### 🏆 Top 10 Candidates")
        name_col = st.session_state.name_col_detected
        display_cols = ["rank","total_score","skill_score","role_score","signal_score","matched_skills"]
        if name_col and name_col in scored.columns:
            display_cols = [name_col] + display_cols
        st.dataframe(scored[display_cols].head(10), use_container_width=True)



"""
ui.linkedin_tab
===============
Standalone "LinkedIn Search Query" tab.

Why a separate module?
----------------------
The recruiter is going to iterate aggressively on this — search-query
craft (Boolean operators, X-ray syntax, location modifiers, seniority
synonyms, …) is its own little discipline. Keeping it out of the main
parser flow means changes here never risk regressing the rest of the
pipeline.

This module ships with a generator that mirrors the current behaviour
in ``core.linkedin`` (simple keywords + Google X-ray). It is the
*placeholder* you'll replace with the smarter version later.

Public API
----------
* ``render_linkedin_tab(jd_data: dict | None)``
    Drop this into your tab router; renders the whole UI.
* ``build_queries(jd_data: dict) -> dict``
    Pure function — handy for unit tests / API endpoints.
"""

from __future__ import annotations

import urllib.parse
from typing import Any

import streamlit as st


# ─────────────────────────────────────────────────────────────────────────────
# Query generation (pure)
# ─────────────────────────────────────────────────────────────────────────────
def _quote(value: str) -> str:
    """Wrap a multi-word string in quotes for Boolean search."""
    value = value.strip()
    if not value:
        return ""
    return f'"{value}"' if " " in value else value


def _flatten_skills(jd: dict[str, Any], limit: int = 6) -> list[str]:
    """Pull the most relevant skill terms across the schema buckets."""
    skills = jd.get("skills") or {}
    pool: list[str] = []
    pool.extend(skills.get("required") or [])
    pool.extend(jd.get("programming_languages") or [])
    pool.extend(jd.get("frameworks") or [])
    pool.extend(jd.get("cloud_platforms") or [])
    pool.extend(jd.get("databases") or [])
    pool.extend(skills.get("preferred") or [])

    seen: set[str] = set()
    out: list[str] = []
    for s in pool:
        if not s:
            continue
        k = s.casefold()
        if k in seen:
            continue
        seen.add(k)
        out.append(s)
        if len(out) >= limit:
            break
    return out


def build_queries(jd_data: dict[str, Any]) -> dict[str, str]:
    """
    Generate the three search artefacts we surface in the UI.

    Returns
    -------
    {
        "boolean_string": "...",   # paste-into-LinkedIn-Recruiter
        "linkedin_url":   "...",   # LinkedIn People Search
        "xray_url":       "...",   # Google site:linkedin.com/in
    }
    """
    title = (jd_data.get("job_title") or "").strip()
    company = (jd_data.get("company_name") or "").strip()
    location = (jd_data.get("location") or "").strip()
    skills = _flatten_skills(jd_data)

    # Boolean string — what a recruiter pastes into LinkedIn Recruiter.
    parts: list[str] = []
    if title:
        parts.append(_quote(title))
    if skills:
        parts.append("(" + " OR ".join(_quote(s) for s in skills) + ")")
    if company:
        parts.append(_quote(company))
    boolean_string = " AND ".join(p for p in parts if p)

    # LinkedIn People Search URL
    keywords = " ".join(p for p in [title, company, *skills[:3]] if p).strip()
    li_params = {"keywords": keywords}
    if location:
        li_params["location"] = location
    linkedin_url = (
        "https://www.linkedin.com/search/results/people/?"
        + urllib.parse.urlencode(li_params, quote_via=urllib.parse.quote)
    )

    # Google X-ray — more precise company filtering
    xray_parts = ["site:linkedin.com/in"]
    if company:
        xray_parts.append(_quote(company))
    if title:
        xray_parts.append(_quote(title))
    if location:
        xray_parts.append(_quote(location))
    for s in skills[:3]:
        xray_parts.append(_quote(s))
    xray_q = " ".join(p for p in xray_parts if p)
    xray_url = "https://www.google.com/search?q=" + urllib.parse.quote(xray_q)

    return {
        "boolean_string": boolean_string,
        "linkedin_url": linkedin_url,
        "xray_url": xray_url,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Streamlit rendering
# ─────────────────────────────────────────────────────────────────────────────
_TAB_STYLE = """
<style>
.li-tab-hero {
  background: linear-gradient(135deg, rgba(10,102,194,0.18), rgba(124,58,237,0.10));
  border: 1px solid rgba(10,102,194,0.28);
  border-radius: 18px;
  padding: 1.6rem 1.8rem;
  margin-bottom: 1.4rem;
}
.li-tab-hero h2 {
  font-family: 'Syne', sans-serif;
  font-weight: 800;
  font-size: 1.7rem;
  margin: 0 0 0.4rem;
  color: #fff;
}
.li-tab-hero p {
  font-family: 'Outfit', sans-serif;
  color: rgba(255,255,255,0.65);
  margin: 0;
  font-size: 0.95rem;
}
.li-query-card {
  background: rgba(10,102,194,0.06);
  border: 1px solid rgba(10,102,194,0.22);
  border-radius: 14px;
  padding: 1.1rem 1.25rem;
  margin-bottom: 0.9rem;
}
.li-query-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.66rem;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: #0a66c2;
  margin-bottom: 0.5rem;
}
.li-query-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.85rem;
  color: #e5e7eb;
  word-break: break-all;
  line-height: 1.6;
}
.li-empty {
  border: 1.5px dashed rgba(10,102,194,0.30);
  border-radius: 14px;
  padding: 3rem 2rem;
  text-align: center;
  color: rgba(255,255,255,0.35);
  font-family: 'Outfit', sans-serif;
}
</style>
"""


def render_linkedin_tab(jd_data: dict[str, Any] | None) -> None:
    """
    Render the standalone LinkedIn-search tab.

    Parameters
    ----------
    jd_data : dict | None
        The parsed JD from ``st.session_state['jd_data']``. If ``None``
        we show a friendly empty state pointing back to the Recruiter tab.
    """
    st.markdown(_TAB_STYLE, unsafe_allow_html=True)

    st.markdown(
        """
        <div class="li-tab-hero">
          <h2>LinkedIn Search Query <span style="color:#0a66c2">·</span></h2>
          <p>Boolean strings, People Search URLs, and Google X-ray queries —
          generated from the parsed JD. Iterate here without touching the
          parser.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not jd_data:
        st.markdown(
            """
            <div class="li-empty">
              ⬡<br><br>
              <span style="font-family:'JetBrains Mono',monospace;font-size:0.7rem;
                           letter-spacing:0.14em;text-transform:uppercase">
                Parse a JD in the Recruiter tab to generate searches.
              </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    queries = build_queries(jd_data)

    # ── Targeting summary ──
    target_l, target_r = st.columns([2, 1])
    with target_l:
        st.markdown("#### Targeting")
        st.markdown(
            f"- **Role:** {jd_data.get('job_title') or '—'}\n"
            f"- **Company:** {jd_data.get('company_name') or '—'}\n"
            f"- **Location:** {jd_data.get('location') or '—'}\n"
            f"- **Top skills:** {', '.join(_flatten_skills(jd_data, limit=5)) or '—'}"
        )
    with target_r:
        st.markdown("#### Open")
        st.link_button("→ LinkedIn", queries["linkedin_url"], use_container_width=True)
        st.link_button("→ Google X-ray", queries["xray_url"], use_container_width=True)

    st.divider()

    # ── Boolean string ──
    st.markdown(
        f"""
        <div class="li-query-card">
          <div class="li-query-label">⬡ Boolean — paste into LinkedIn Recruiter</div>
          <div class="li-query-value">{queries['boolean_string'] or '<em>not enough signal in JD</em>'}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if queries["boolean_string"]:
        st.code(queries["boolean_string"], language="text")

    # ── LinkedIn People Search URL ──
    st.markdown(
        f"""
        <div class="li-query-card">
          <div class="li-query-label">🔗 LinkedIn People Search URL</div>
          <div class="li-query-value">{queries['linkedin_url']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── X-ray URL ──
    st.markdown(
        f"""
        <div class="li-query-card">
          <div class="li-query-label">🔍 Google X-ray (site:linkedin.com/in)</div>
          <div class="li-query-value">{queries['xray_url']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("✏ Tweak query manually"):
        edited = st.text_area(
            "Boolean string",
            value=queries["boolean_string"],
            height=120,
            help="Edit and re-build the LinkedIn / X-ray URLs from your version.",
        )
        if st.button("Rebuild URLs from edited Boolean"):
            # Cheap rebuild: throw the edited string straight into both URLs
            st.session_state["custom_linkedin_url"] = (
                "https://www.linkedin.com/search/results/people/?"
                + urllib.parse.urlencode({"keywords": edited}, quote_via=urllib.parse.quote)
            )
            st.session_state["custom_xray_url"] = (
                "https://www.google.com/search?q="
                + urllib.parse.quote(f"site:linkedin.com/in {edited}")
            )
            st.success("✓ URLs rebuilt — see the buttons below.")

        if st.session_state.get("custom_linkedin_url"):
            st.link_button("→ Open edited LinkedIn URL",
                           st.session_state["custom_linkedin_url"])
            st.link_button("→ Open edited X-ray URL",
                           st.session_state["custom_xray_url"])

    st.caption(
        "💡 The Boolean string targets LinkedIn Recruiter; the X-ray URL "
        "tends to be more precise for company-specific filtering on public profiles."
    )

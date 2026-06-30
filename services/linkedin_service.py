"""
services.linkedin_service
=========================
LinkedIn sourcing primitives:

* URL generation for People Search and Google X-ray (delegates to the
  existing ``core.linkedin`` module).
* ``build_queries`` — builds the Boolean / People-Search-URL / X-ray-URL
  bundle used by the dedicated LinkedIn tab.

Centralising the query-building here means the LinkedIn tab can iterate
on the search-string craft (synonyms, seniority modifiers, location
expansions, etc.) without touching the rest of the pipeline.
"""

from __future__ import annotations

import urllib.parse
from typing import Any

from core.linkedin import (  # noqa: F401 — re-export
    generate_linkedin_url,
    generate_xray_search_url,
)


# ─── Query bundle (rich Qwen-shape input) ──────────────────────────────────────
def _quote(value: str) -> str:
    """Wrap a multi-word string in quotes for Boolean / X-ray search."""
    value = value.strip()
    if not value:
        return ""
    return f'"{value}"' if " " in value else value


def _top_skills(jd: dict[str, Any], limit: int = 6) -> list[str]:
    """Pull the most relevant skill terms across the rich-shape schema buckets."""
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
    Build the three search artefacts shown in the LinkedIn tab.

    Accepts the *rich* (Qwen-shape) JD dict. Returns a dict with:

    * ``boolean_string``  — paste into LinkedIn Recruiter
    * ``linkedin_url``    — LinkedIn People Search
    * ``xray_url``        — Google site:linkedin.com/in
    """
    title    = (jd_data.get("job_title") or "").strip()
    company  = (jd_data.get("company_name") or "").strip()
    location = (jd_data.get("location") or "").strip()
    skills   = _top_skills(jd_data)

    # Boolean string
    parts: list[str] = []
    if title:   parts.append(_quote(title))
    if skills:  parts.append("(" + " OR ".join(_quote(s) for s in skills) + ")")
    if company: parts.append(_quote(company))
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

    # Google X-ray
    xray_parts = ["site:linkedin.com/in"]
    if company:  xray_parts.append(_quote(company))
    if title:    xray_parts.append(_quote(title))
    if location: xray_parts.append(_quote(location))
    for s in skills[:3]:
        xray_parts.append(_quote(s))
    xray_url = (
        "https://www.google.com/search?q="
        + urllib.parse.quote(" ".join(p for p in xray_parts if p))
    )

    return {
        "boolean_string": boolean_string,
        "linkedin_url":   linkedin_url,
        "xray_url":       xray_url,
    }


__all__ = [
    "generate_linkedin_url",
    "generate_xray_search_url",
    "build_queries",
]

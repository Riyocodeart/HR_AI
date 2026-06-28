"""
ui.jd_parser_animation
======================
Streamlit helpers that render the JD-parsing step with a "typing in motion"
feel — fields appear progressively, mimicking the way an LLM streams tokens.

The animation deliberately runs *after* the parse is complete (we have
the full dict in hand) so we get smooth, predictable reveals without
exposing partial/invalid JSON to the user.

Public surface
--------------
* ``render_parsing_animation(parser, jd_text, container=None)``
    Runs the parse and animates the reveal of each field. Returns the
    final parsed dict (also stashed in ``st.session_state.jd_data``).

* ``animate_reveal(jd_data, container=None)``
    Pure-animation variant: if you've already parsed and just want to
    re-render the typewriter effect from cached data.

* ``qwen_to_legacy_shape(qwen_dict)``
    Adapter that maps the new Qwen output to the legacy dict shape that
    downstream consumers (existing scorer, chatbot, email generator,
    LinkedIn URL helpers in core.linkedin) expect.

* ``gemini_to_qwen_shape(legacy_dict)``
    Reverse adapter — converts the flat legacy dict (from Gemini or the
    regex fallback) into the rich Qwen shape so the LinkedIn tab and the
    typing animation work identically across engines.

* ``extract_text_from_upload(uploaded_file)``
    Pulls raw text out of a Streamlit ``UploadedFile`` (PDF / DOCX / TXT).
"""

from __future__ import annotations

import io
import time
from typing import Any

import streamlit as st


# ─────────────────────────────────────────────────────────────────────────────
# Style — drop-in, scoped to this card so it never leaks into the rest of app.
# ─────────────────────────────────────────────────────────────────────────────
_STYLE = """
<style>
.jd-stream-card {
  background: linear-gradient(180deg, rgba(124,58,237,0.06), rgba(124,58,237,0.015));
  border: 1px solid rgba(124,58,237,0.18);
  border-radius: 14px;
  padding: 1.2rem 1.4rem;
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  min-height: 320px;
}
.jd-stream-head {
  font-family: 'Syne', sans-serif;
  font-size: 0.7rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #a78bfa;
  margin-bottom: 0.9rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.jd-stream-head::before {
  content: "";
  width: 7px; height: 7px; border-radius: 50%;
  background: #a78bfa;
  box-shadow: 0 0 12px #a78bfa;
  animation: pulse 1.1s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 0.4; transform: scale(0.9); }
  50%      { opacity: 1;   transform: scale(1.15); }
}
.jd-row {
  display: grid;
  grid-template-columns: 180px 1fr;
  gap: 1rem;
  padding: 0.35rem 0;
  border-bottom: 1px dashed rgba(124,58,237,0.10);
  font-size: 0.88rem;
}
.jd-row:last-child { border-bottom: none; }
.jd-key {
  color: #9ca3af;
  font-size: 0.72rem;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  padding-top: 2px;
}
.jd-val {
  color: #e5e7eb;
  font-family: 'Outfit', system-ui, sans-serif;
  font-weight: 500;
  word-break: break-word;
}
.jd-val .none { color: #4b5563; font-style: italic; }
.jd-chip {
  display: inline-block;
  margin: 2px 4px 2px 0;
  padding: 2px 9px;
  border-radius: 999px;
  background: rgba(124,58,237,0.14);
  border: 1px solid rgba(124,58,237,0.30);
  color: #c4b5fd;
  font-size: 0.74rem;
  font-family: 'JetBrains Mono', monospace;
}
.caret { color: #a78bfa; animation: blink 0.9s steps(2) infinite; }
@keyframes blink { 50% { opacity: 0; } }
</style>
"""


# Recruiter-friendly display labels.
_LABELS: dict[str, str] = {
    "job_title": "Job Title",
    "company_name": "Company",
    "department": "Department",
    "industry": "Industry",
    "domain": "Domain",
    "location": "Location",
    "work_mode": "Work Mode",
    "employment_type": "Employment Type",
    "experience": "Experience",
    "education": "Education",
    "skills": "Skills",
    "programming_languages": "Programming Languages",
    "frameworks": "Frameworks",
    "libraries": "Libraries",
    "cloud_platforms": "Cloud Platforms",
    "databases": "Databases",
    "devops_tools": "DevOps Tools",
    "tools": "Tools",
    "responsibilities": "Responsibilities",
    "certifications": "Certifications",
    "soft_skills": "Soft Skills",
    "languages": "Languages",
    "keywords": "Keywords",
    "salary": "Salary",
    "notice_period": "Notice Period",
    "travel_requirement": "Travel",
    "shift": "Shift",
}


# Per-field reveal speed (seconds between word chunks). Tune to taste.
_WORD_DELAY = 0.018
_FIELD_DELAY = 0.10


# ─────────────────────────────────────────────────────────────────────────────
# Internal rendering helpers
# ─────────────────────────────────────────────────────────────────────────────
def _format_value_html(value: Any, partial: str | None = None) -> str:
    """Convert any JSON-y value into the HTML fragment we display."""
    if partial is not None:
        return f'{partial}<span class="caret">▌</span>'

    if value is None or value == "":
        return '<span class="none">—</span>'

    if isinstance(value, dict):
        # Mostly the experience object
        mn = value.get("minimum_years")
        mx = value.get("maximum_years")
        if mn is None and mx is None:
            return '<span class="none">—</span>'
        if mx is None:
            return f"{mn}+ years"
        if mn is None:
            return f"up to {mx} years"
        if mn == mx:
            return f"{mn} years"
        return f"{mn}–{mx} years"

    if isinstance(value, list):
        if not value:
            return '<span class="none">—</span>'
        return "".join(f'<span class="jd-chip">{str(v)}</span>' for v in value)

    return str(value)


def _value_to_words(value: Any) -> list[str]:
    """Tokenise a value into 'words' we reveal one at a time."""
    if value is None or value == "":
        return ["—"]
    if isinstance(value, list):
        return [str(v) for v in value] or ["—"]
    if isinstance(value, dict):
        return [_format_value_html(value)]
    return str(value).split(" ") or ["—"]


def _animate_field(
    placeholder,
    key: str,
    value: Any,
    *,
    word_delay: float,
) -> None:
    """Reveal one field, word-by-word, into ``placeholder``."""
    label = _LABELS.get(key, key.replace("_", " ").title())

    if isinstance(value, list):
        # Chips reveal one-by-one
        revealed: list[str] = []
        for chip in value:
            revealed.append(f'<span class="jd-chip">{chip}</span>')
            placeholder.markdown(
                f'<div class="jd-row"><div class="jd-key">{label}</div>'
                f'<div class="jd-val">{"".join(revealed)}'
                f'<span class="caret">▌</span></div></div>',
                unsafe_allow_html=True,
            )
            time.sleep(word_delay)
        placeholder.markdown(
            f'<div class="jd-row"><div class="jd-key">{label}</div>'
            f'<div class="jd-val">{_format_value_html(value)}</div></div>',
            unsafe_allow_html=True,
        )
        return

    if isinstance(value, dict) or value is None or value == "":
        # Render in one shot — no useful per-token animation
        placeholder.markdown(
            f'<div class="jd-row"><div class="jd-key">{label}</div>'
            f'<div class="jd-val">{_format_value_html(value)}</div></div>',
            unsafe_allow_html=True,
        )
        return

    # Scalar string — word-by-word
    words = str(value).split(" ")
    buf: list[str] = []
    for w in words:
        buf.append(w)
        partial = " ".join(buf)
        placeholder.markdown(
            f'<div class="jd-row"><div class="jd-key">{label}</div>'
            f'<div class="jd-val">{partial}<span class="caret">▌</span></div></div>',
            unsafe_allow_html=True,
        )
        time.sleep(word_delay)
    placeholder.markdown(
        f'<div class="jd-row"><div class="jd-key">{label}</div>'
        f'<div class="jd-val">{_format_value_html(value)}</div></div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────
def animate_reveal(
    jd_data: dict[str, Any],
    container=None,
    *,
    word_delay: float = _WORD_DELAY,
    field_delay: float = _FIELD_DELAY,
    engine_label: str = "Qwen 2.5 · streaming extraction",
) -> None:
    """
    Animate an existing parsed-JD dict.

    Accepts either the rich Qwen shape (``job_title``, nested ``skills``…)
    or the legacy flat shape (``role``, flat ``skills``…). Legacy dicts are
    auto-converted via :func:`gemini_to_qwen_shape` so the visual is
    consistent regardless of which engine produced the data.

    Parameters
    ----------
    engine_label : str
        Text shown in the card header — e.g. ``"Gemini · cloud extraction"``
        or ``"Offline regex"``.
    """
    # Auto-detect shape: if legacy (`role` present, `job_title` absent),
    # convert so the field labels and ordering line up with _LABELS.
    if "role" in jd_data and "job_title" not in jd_data:
        jd_data = gemini_to_qwen_shape(jd_data)

    target = container if container is not None else st
    target.markdown(_STYLE, unsafe_allow_html=True)
    target.markdown(
        f'<div class="jd-stream-card"><div class="jd-stream-head">{engine_label}</div>',
        unsafe_allow_html=True,
    )

    for key in _LABELS:
        if key not in jd_data:
            continue
        placeholder = target.empty()
        _animate_field(placeholder, key, jd_data[key], word_delay=word_delay)
        time.sleep(field_delay)

    target.markdown("</div>", unsafe_allow_html=True)


def render_parsing_animation(
    parser,
    jd_text: str,
    container=None,
    *,
    word_delay: float = _WORD_DELAY,
    field_delay: float = _FIELD_DELAY,
) -> dict[str, Any]:
    """
    Run ``parser.parse(jd_text)`` and animate the reveal.

    Parameters
    ----------
    parser : parser.JDParser
        A pre-constructed parser (so we don't pay client-init cost on rerun).
    jd_text : str
        Raw or cleaned JD text.
    container : st.delta_generator.DeltaGenerator | None
        Where to render. Defaults to the top-level ``st``.

    Returns
    -------
    dict
        The parsed JD. Also stored in ``st.session_state["jd_data"]``.
    """
    target = container if container is not None else st

    target.markdown(_STYLE, unsafe_allow_html=True)
    status_area = target.empty()
    status_area.markdown(
        '<div class="jd-stream-card"><div class="jd-stream-head">'
        'Qwen 2.5 · contacting local model…</div></div>',
        unsafe_allow_html=True,
    )

    # Heavy work: synchronous call to Ollama.
    jd_data = parser.parse(jd_text)

    # Reset the card and stream fields.
    status_area.empty()
    animate_reveal(jd_data, container=target, word_delay=word_delay, field_delay=field_delay)
    return jd_data


# ─────────────────────────────────────────────────────────────────────────────
# Legacy-shape adapter
# ─────────────────────────────────────────────────────────────────────────────
def qwen_to_legacy_shape(qwen: dict[str, Any]) -> dict[str, Any]:
    """
    Translate the new Qwen output dict into the *flat* shape that the
    existing ``app.py`` consumers (scorer, chatbot grounding, email
    generator, ``core.linkedin``) read from ``st.session_state.jd_data``.

    Field mapping
    -------------
    * ``job_title``            → ``role``
    * ``company_name``         → ``company``
    * ``experience.minimum_years`` → ``experience_min``
    * ``experience.maximum_years`` → ``experience_max``
    * ``skills.required + preferred`` → ``skills`` (flat, dedup)
    * ``education`` (list)     → ``education`` (joined string)

    Pass-through (unchanged): ``location``, ``industry``, ``domain``,
    ``employment_type``, ``work_mode``, ``responsibilities``, ``keywords``,
    plus all six tech taxonomy buckets.
    """
    if not qwen:
        return {}

    qwen = dict(qwen)  # don't mutate caller's dict

    skills_obj = qwen.get("skills") or {}
    required = list(skills_obj.get("required") or [])
    preferred = list(skills_obj.get("preferred") or [])

    # Dedup-preserving flat list (required first)
    seen: set[str] = set()
    flat_skills: list[str] = []
    for s in required + preferred:
        if not s:
            continue
        k = s.casefold()
        if k in seen:
            continue
        seen.add(k)
        flat_skills.append(s)

    exp = qwen.get("experience") or {}
    edu = qwen.get("education") or []
    edu_str = ", ".join(edu) if isinstance(edu, list) else (edu or "")

    legacy = {
        # Old field names downstream code reads:
        "role":            qwen.get("job_title"),
        "company":         qwen.get("company_name"),
        "location":        qwen.get("location"),
        "industry":        qwen.get("industry"),
        "domain":          qwen.get("domain"),
        "employment_type": qwen.get("employment_type"),
        "work_mode":       qwen.get("work_mode"),
        "education":       edu_str,
        "experience_min":  exp.get("minimum_years"),
        "experience_max":  exp.get("maximum_years"),
        "skills":          flat_skills,
        "summary":         (qwen.get("responsibilities") or [None])[0],

        # Pass-through extras (keep them around for the chatbot / report):
        "responsibilities":      qwen.get("responsibilities", []),
        "soft_skills":           qwen.get("soft_skills", []),
        "certifications":        qwen.get("certifications", []),
        "languages":             qwen.get("languages", []),
        "keywords":              qwen.get("keywords", []),
        "tools":                 qwen.get("tools", []),
        "programming_languages": qwen.get("programming_languages", []),
        "frameworks":            qwen.get("frameworks", []),
        "libraries":             qwen.get("libraries", []),
        "cloud_platforms":       qwen.get("cloud_platforms", []),
        "databases":             qwen.get("databases", []),
        "devops_tools":          qwen.get("devops_tools", []),
        "salary":                qwen.get("salary"),
        "notice_period":         qwen.get("notice_period"),
        "travel_requirement":    qwen.get("travel_requirement"),
        "shift":                 qwen.get("shift"),
        "department":            qwen.get("department"),

        # Provenance flag so the UI can show "Qwen (offline)" badge:
        "_source":               "qwen-offline",
    }
    return legacy


# ─────────────────────────────────────────────────────────────────────────────
# Reverse adapter — legacy/Gemini/regex shape  →  rich Qwen shape
# ─────────────────────────────────────────────────────────────────────────────
def gemini_to_qwen_shape(legacy: dict[str, Any]) -> dict[str, Any]:
    """
    Translate the *flat* legacy dict (what ``core.parser`` / Gemini returns)
    into the *rich* shape that the LinkedIn tab and the typing animation
    expect.

    Field mapping (inverse of :func:`qwen_to_legacy_shape`):

    * ``role``            → ``job_title``
    * ``company``         → ``company_name``
    * ``experience_min``  → ``experience.minimum_years``
    * ``experience_max``  → ``experience.maximum_years``
    * ``skills`` (flat list) → ``skills.required`` (all of them; Gemini /
      regex do not distinguish required vs preferred, so ``preferred`` is
      left empty)
    * ``education`` (string) → ``education`` (single-item list)

    Tech taxonomy buckets (``programming_languages``, ``frameworks``, …) are
    preserved if they happen to be present, otherwise emitted as empty lists.
    """
    if not legacy:
        return {}

    legacy = dict(legacy)

    # Normalise skills → list
    raw_skills = legacy.get("skills") or []
    if isinstance(raw_skills, str):
        raw_skills = [s.strip() for s in raw_skills.split(",") if s.strip()]
    elif not isinstance(raw_skills, list):
        raw_skills = []

    # Normalise education → list
    raw_edu = legacy.get("education")
    if isinstance(raw_edu, str):
        edu_list = [raw_edu] if raw_edu.strip() else []
    elif isinstance(raw_edu, list):
        edu_list = raw_edu
    else:
        edu_list = []

    # If the legacy dict has a `summary`, use it as a responsibility seed
    responsibilities = legacy.get("responsibilities") or []
    if not responsibilities and legacy.get("summary"):
        responsibilities = [legacy["summary"]]

    rich = {
        "job_title":       legacy.get("role"),
        "company_name":    legacy.get("company"),
        "department":      legacy.get("department"),
        "employment_type": legacy.get("employment_type"),
        "work_mode":       legacy.get("work_mode"),
        "location":        legacy.get("location"),
        "experience": {
            "minimum_years": legacy.get("experience_min"),
            "maximum_years": legacy.get("experience_max"),
        },
        "education":       edu_list,
        "skills": {
            "required":  list(raw_skills),
            "preferred": [],
        },
        "responsibilities":  responsibilities,
        "tools":             legacy.get("tools", []) or [],
        "certifications":    legacy.get("certifications", []) or [],
        "soft_skills":       legacy.get("soft_skills", []) or [],
        "industry":          legacy.get("industry"),
        "domain":            legacy.get("domain"),
        "salary":            legacy.get("salary"),
        "notice_period":     legacy.get("notice_period"),
        "travel_requirement":legacy.get("travel_requirement"),
        "shift":             legacy.get("shift"),
        "languages":         legacy.get("languages", []) or [],
        "keywords":          legacy.get("keywords", []) or [],

        # Tech taxonomy — Gemini/regex don't categorise, so default to [].
        # If a richer legacy payload happens to include them, pass through.
        "programming_languages": legacy.get("programming_languages", []) or [],
        "frameworks":            legacy.get("frameworks", []) or [],
        "libraries":             legacy.get("libraries", []) or [],
        "cloud_platforms":       legacy.get("cloud_platforms", []) or [],
        "databases":             legacy.get("databases", []) or [],
        "devops_tools":          legacy.get("devops_tools", []) or [],
    }
    return rich


# ─────────────────────────────────────────────────────────────────────────────
# File-text extraction for Streamlit UploadedFile
# ─────────────────────────────────────────────────────────────────────────────
def extract_text_from_upload(uploaded_file) -> str:
    """
    Pull raw text out of a Streamlit ``UploadedFile`` (PDF / DOCX / TXT).

    Returns ``""`` on unsupported extensions or read errors — the caller
    is expected to surface that gracefully (e.g. via ``st.error``).
    """
    if uploaded_file is None:
        return ""

    name = (uploaded_file.name or "").lower()
    data = uploaded_file.getvalue()

    try:
        if name.endswith(".txt"):
            return data.decode("utf-8", errors="ignore")

        if name.endswith(".docx"):
            from docx import Document  # type: ignore
            doc = Document(io.BytesIO(data))
            return "\n".join(par.text for par in doc.paragraphs)

        if name.endswith(".pdf"):
            try:
                from pypdf import PdfReader  # type: ignore
            except ImportError:
                from PyPDF2 import PdfReader  # type: ignore
            reader = PdfReader(io.BytesIO(data))
            return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:  # noqa: BLE001 — best-effort
        return ""

    return ""
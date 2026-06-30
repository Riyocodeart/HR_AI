"""
services.chatbot_service
========================
Conversational layer for the AI Sourcing Chatbot. Uses Gemini under the
hood (via ``core.parser``-style provider lookup) with the parsed JD and
scored candidate list as grounding context.

Public API
----------
* ``answer(question, history, jd, scored_df)``
    Returns the assistant's reply as a string. Never raises — falls back
    to a clear error message the UI can show inline.
* ``suggested_prompts(jd)``
    Returns 3-4 starter prompts contextualised to the current JD.
"""

from __future__ import annotations

from typing import Any, Iterable

from core.helpers import gemini_keys
from core.logger import get_logger

log = get_logger(__name__)


# ─── Suggested prompts ─────────────────────────────────────────────────────────
def suggested_prompts(jd: dict[str, Any] | None) -> list[str]:
    """Return contextual prompt suggestions based on the parsed JD."""
    if not jd:
        return [
            "What does a strong candidate for a data role look like?",
            "Suggest sourcing channels for niche AI talent.",
            "How do I write a Boolean LinkedIn query?",
        ]
    role    = jd.get("role") or "this role"
    company = jd.get("company") or "this company"
    return [
        f"Summarise the top candidates for {role}.",
        f"What skill gaps exist in our pipeline for {role}?",
        f"Suggest a sourcing strategy for {role} at {company}.",
        "Which candidates should we shortlist first and why?",
    ]


# ─── Conversation ──────────────────────────────────────────────────────────────
def _grounding_block(jd: dict[str, Any] | None, scored_df) -> str:
    """Compose a short context block to ground the model in the current data."""
    lines = []
    if jd:
        lines.append("CURRENT JOB DESCRIPTION:")
        lines.append(f"  Role: {jd.get('role', '—')}")
        lines.append(f"  Company: {jd.get('company', '—')}")
        lines.append(f"  Location: {jd.get('location', '—')}")
        lines.append(f"  Skills: {', '.join((jd.get('skills') or [])[:8]) or '—'}")
        lines.append(
            f"  Experience: {jd.get('experience_min', '?')}–"
            f"{jd.get('experience_max', '?')} yrs"
        )
    if scored_df is not None and len(scored_df) > 0:
        top = scored_df.head(5)
        lines.append("\nTOP 5 CANDIDATES (truncated):")
        for _, row in top.iterrows():
            name = row.get("name") or row.get("Name") or "?"
            score = row.get("score", "—")
            lines.append(f"  • {name} — score {score}")
    return "\n".join(lines) or "(no JD parsed yet)"


def answer(
    question: str,
    history: Iterable[dict[str, str]],
    jd: dict[str, Any] | None = None,
    scored_df=None,
) -> str:
    """
    Generate a reply. ``history`` is a list of ``{"role": "user"|"assistant",
    "content": str}`` dicts. Returns the assistant's text.

    Falls back to a templated error message rather than raising so the
    chatbot tab can render it inline.
    """
    keys = gemini_keys()
    if not keys:
        return (
            "I need a Gemini API key to answer. Add one in the sidebar and try "
            "again — once a key is present I'll have full access to your parsed "
            "JD and scored candidate list as grounding context."
        )

    # The user already had a Gemini provider abstraction (`get_provider("gemini", …)`)
    # in their codebase. We try it; if anything goes sideways, we degrade
    # gracefully.
    try:
        from services.key_rotation import get_provider  # type: ignore
    except ImportError:
        return _no_provider_response(question, jd, scored_df)

    try:
        provider = get_provider("gemini", keys)
        prompt = (
            f"{_grounding_block(jd, scored_df)}\n\n"
            f"USER QUESTION: {question}\n\n"
            "Answer concisely. Reference specific candidates or skills from the "
            "context when relevant. If the context is empty, say so honestly."
        )
        # Most provider implementations expose `.generate(prompt) -> str`
        # or `.chat(messages) -> str`. We try both.
        if hasattr(provider, "chat"):
            return str(provider.chat([{"role": "user", "content": prompt}]))
        if hasattr(provider, "generate"):
            return str(provider.generate(prompt))
    except Exception as exc:  # noqa: BLE001
        log.exception("chatbot answer failed")
        return f"⚠ Chatbot call failed: {exc}"

    return _no_provider_response(question, jd, scored_df)


def _no_provider_response(question: str, jd, scored_df) -> str:
    """Used when no provider is available — gives a useful textual fallback."""
    return (
        f"I couldn't reach a Gemini provider for this answer. "
        f"Question received: {question!r}. "
        f"Grounding snapshot:\n\n{_grounding_block(jd, scored_df)}"
    )


__all__ = ["answer", "suggested_prompts"]

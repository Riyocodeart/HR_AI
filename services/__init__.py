"""
services
========
Service layer for the recruiting app. Each module exposes a small,
stable public surface that the pages/ layer calls. Internally, services
delegate to ``core/*`` (existing implementations) or ``parser/`` (offline
Qwen).

Layout
------
* ``jd_service``        — Three-tier orchestrator (Gemini → Qwen → Regex)
* ``gemini_service``    — Gemini API wrapper
* ``ollama_service``    — Ollama / Qwen 2.5 wrapper
* ``regex_service``     — Offline regex fallback wrapper
* ``scoring_service``   — Candidate scoring (re-exports core.scorer)
* ``linkedin_service``  — Search-URL builders (re-exports core.linkedin)
* ``export_service``    — Excel / CSV export (re-exports core.exporter)
* ``gmail_service``     — OAuth + templated outreach
* ``analytics_service`` — Pure-Python KPI / funnel / distribution helpers
* ``chatbot_service``   — Conversational layer (Gemini-backed)
* ``key_rotation``      — (existing) Gemini key rotation / loading
"""
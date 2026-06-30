"""
services.ollama_service
=======================
Thin service wrapper around the offline ``parser/`` package (Qwen 2.5 via
Ollama). Centralises:

* The cached ``JDParser`` factory (so we don't re-init the Ollama client
  on every Streamlit rerun).
* A reachability probe so the orchestrator can decide whether to skip
  this layer without paying a 30-second timeout.
* A uniform ``parse(text) -> dict`` interface that callers in
  :mod:`services.jd_service` can rely on.

Public API
----------
* ``get_parser()``        — cached :class:`parser.JDParser` instance
* ``is_reachable()``      — ``bool``, completes in < 200 ms
* ``parse(text)``         — calls Qwen, returns rich-shape dict
* ``OllamaError``         — re-exported for ``except`` clauses upstream
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from core.config import SCHEMA_PATH
from core.constants import (
    OLLAMA_HOST,
    QWEN_MODEL,
    QWEN_SEED,
    QWEN_TEMPERATURE,
    QWEN_TIMEOUT_SEC,
)
from core.logger import get_logger
from parser import JDParser, OllamaError  # re-export OllamaError

log = get_logger(__name__)


# ─── Cached parser ──────────────────────────────────────────────────────────────
@st.cache_resource
def get_parser() -> JDParser:
    """Return a process-wide :class:`JDParser` configured from ``core.constants``."""
    return JDParser(
        model=QWEN_MODEL,
        host=OLLAMA_HOST,
        schema_path=SCHEMA_PATH if SCHEMA_PATH.exists() else None,
        temperature=QWEN_TEMPERATURE,
        seed=QWEN_SEED,
        timeout=QWEN_TIMEOUT_SEC,
    )


# ─── Reachability probe ────────────────────────────────────────────────────────
def is_reachable(timeout: float = 0.5) -> bool:
    """
    Quick probe to see if Ollama daemon is up. Short timeout so callers
    can skip the Qwen layer fast when the daemon isn't running.
    """
    try:
        import requests
        resp = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=timeout)
        return resp.ok
    except Exception:  # noqa: BLE001
        return False


def has_model(model: str = QWEN_MODEL, timeout: float = 0.8) -> bool:
    """Verify that ``model`` is installed locally. Returns ``False`` on any error."""
    try:
        import requests
        resp = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=timeout)
        resp.raise_for_status()
        installed = [m.get("name", "") for m in resp.json().get("models", [])]
        return any(model in m for m in installed)
    except Exception:  # noqa: BLE001
        return False


# ─── Parse (uniform with the other engine wrappers) ─────────────────────────────
def parse(text: str) -> dict[str, Any]:
    """
    Parse JD text via Qwen (Ollama). Returns the rich Qwen-shape dict.

    Raises
    ------
    OllamaError
        Daemon unreachable or model rejected the call.
    """
    return get_parser().parse(text)


__all__ = ["get_parser", "is_reachable", "has_model", "parse", "OllamaError"]

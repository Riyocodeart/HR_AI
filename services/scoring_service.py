"""
services.scoring_service
========================
Candidate scoring service. Delegates to the existing ``core.scorer``
module — this wrapper exists only so the rest of the codebase has a
single, stable import path.

Public API
----------
* ``load_candidates(file)``       — read CSV/Excel into a DataFrame
* ``detect_columns(df, jd, ...)`` — auto-map dataset columns to schema
* ``score_candidates(df, jd, ...)`` — run holistic scoring

The original signatures are preserved verbatim — see ``core/scorer.py``
for parameter docs.
"""

from __future__ import annotations

from core.scorer import (  # noqa: F401 — re-export
    detect_columns,
    load_candidates,
    score_candidates,
)

__all__ = ["load_candidates", "detect_columns", "score_candidates"]

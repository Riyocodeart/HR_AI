"""
core.logger
===========
Thin re-export so the rest of the application has a single import path for
logging. Internally it delegates to ``parser.utils.get_logger`` which already
handles consistent formatting and the ``LOG_LEVEL`` env-var.

Usage
-----
>>> from core.logger import get_logger
>>> log = get_logger(__name__)
>>> log.info("Parsed JD in %.1fs", elapsed)
"""

from __future__ import annotations

from parser.utils import get_logger  # noqa: F401  (re-export)

__all__ = ["get_logger"]

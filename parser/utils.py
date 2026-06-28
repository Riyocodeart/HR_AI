"""
parser.utils
============
Cross-cutting helpers used by the JD parser.

Public surface
--------------
* ``get_logger(name)``            — Consistent logger (level via ``LOG_LEVEL`` env).
* ``retry(times, exceptions)``    — Tiny retry decorator with exponential back-off.
* ``read_text_file(path)``        — Best-effort raw-text extractor for txt/md/docx/pdf.
* ``stable_hash(text)``           — Deterministic hash of cleaned JD (for caching).
"""

from __future__ import annotations

import functools
import hashlib
import logging
import os
import time
from pathlib import Path
from typing import Callable, Iterable, Type, TypeVar

T = TypeVar("T")

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────
_LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_LOG_DATEFMT = "%H:%M:%S"
_configured = False


def _configure_root() -> None:
    """Idempotently configure the root logger once."""
    global _configured
    if _configured:
        return
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format=_LOG_FORMAT,
        datefmt=_LOG_DATEFMT,
    )
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger with consistent formatting."""
    _configure_root()
    return logging.getLogger(name)


# ─────────────────────────────────────────────────────────────────────────────
# Retry
# ─────────────────────────────────────────────────────────────────────────────
def retry(
    times: int = 2,
    exceptions: Iterable[Type[BaseException]] = (Exception,),
    backoff: float = 0.5,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Retry the wrapped callable up to ``times`` additional attempts on the
    listed exception classes. Exponential back-off keyed on ``backoff``.

    Example
    -------
    >>> @retry(times=2, exceptions=(json.JSONDecodeError,))
    ... def call(): ...
    """
    exc_tuple = tuple(exceptions)

    def _decorator(func: Callable[..., T]) -> Callable[..., T]:
        log = get_logger(func.__module__)

        @functools.wraps(func)
        def _wrapped(*args, **kwargs) -> T:
            attempt = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except exc_tuple as exc:
                    if attempt >= times:
                        log.error("'%s' failed after %d retries: %s",
                                  func.__name__, times, exc)
                        raise
                    delay = backoff * (2 ** attempt)
                    log.warning("'%s' attempt %d failed (%s) — retrying in %.2fs",
                                func.__name__, attempt + 1, exc, delay)
                    time.sleep(delay)
                    attempt += 1
        return _wrapped
    return _decorator


# ─────────────────────────────────────────────────────────────────────────────
# File readers (best-effort, never raise — return "" on failure)
# ─────────────────────────────────────────────────────────────────────────────
def read_text_file(path: str | os.PathLike) -> str:
    """
    Extract raw text from a JD file (.txt / .md / .docx / .pdf).

    Returns an empty string on unsupported extensions or read errors so
    callers can degrade gracefully rather than crash the pipeline.
    """
    p = Path(path)
    if not p.exists():
        get_logger(__name__).warning("File does not exist: %s", p)
        return ""

    ext = p.suffix.lower()
    try:
        if ext in {".txt", ".md"}:
            return p.read_text(encoding="utf-8", errors="ignore")

        if ext == ".docx":
            from docx import Document  # type: ignore
            doc = Document(str(p))
            return "\n".join(par.text for par in doc.paragraphs)

        if ext == ".pdf":
            try:
                from pypdf import PdfReader  # type: ignore
            except ImportError:  # pragma: no cover
                from PyPDF2 import PdfReader  # type: ignore
            reader = PdfReader(str(p))
            return "\n".join((page.extract_text() or "") for page in reader.pages)

        get_logger(__name__).warning("Unsupported extension: %s", ext)
        return ""
    except Exception as exc:  # noqa: BLE001 — best-effort
        get_logger(__name__).exception("read_text_file failed for %s: %s", p, exc)
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# Hashing
# ─────────────────────────────────────────────────────────────────────────────
def stable_hash(text: str) -> str:
    """SHA-256 hex digest of ``text``. Useful for caching parser results."""
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()

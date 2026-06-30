"""
ui.animations
=============
Canonical import path for animated UI helpers. Today this is a thin
re-export from ``ui.jd_parser_animation`` so we have one location to add
new animations (status spinners, success confetti, etc.) without
breaking existing imports.
"""

from __future__ import annotations

from .jd_parser_animation import (  # noqa: F401
    animate_reveal,
    render_parsing_animation,
    qwen_to_legacy_shape,
    gemini_to_qwen_shape,
    extract_text_from_upload,
)

__all__ = [
    "animate_reveal",
    "render_parsing_animation",
    "qwen_to_legacy_shape",
    "gemini_to_qwen_shape",
    "extract_text_from_upload",
]

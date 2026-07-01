"""
core.constants
==============
Application-wide constants. The single source of truth for things that are
read by both the parser and the UI (model names, ports, palette tokens).

If you change the dark-mode palette, change it here — not in CSS files.
"""

from __future__ import annotations

# ─── Ollama / Qwen ──────────────────────────────────────────────────────────────
OLLAMA_HOST = "http://localhost:11434"
QWEN_MODEL = "qwen2.5:1.5b"
QWEN_SEED = 42
QWEN_TEMPERATURE = 0.0
QWEN_TIMEOUT_SEC = 120

# ─── App identity ───────────────────────────────────────────────────────────────
APP_NAME = "NexRecruit AI"
APP_TAGLINE = "AI-POWERED RECRUITING SUITE"
APP_ICON = "⬡"

# ─── Tabs (id, icon, label) — single source of truth for sidebar order ──────────
TABS: list[tuple[str, str, str]] = [
    ("overview",  "▦",  "Overview"),
    ("recruiter", "⬡",  "Recruiter"),
    ("analytics", "◫",  "Analytics"),
    ("linkedin",  "in", "LinkedIn"),
    ("email",     "✉",  "Email Automation"),
    ("chatbot",   "◐",  "AI Sourcing Chatbot"),
]

# ─── Design tokens (matches ui/styles.py CSS variables) ─────────────────────────
class Colors:
    """Mirror of the CSS `--*` variables for places where Python needs them
    (e.g. matplotlib charts, plotly themes)."""

    BG_PRIMARY   = "#0a0e1a"
    BG_CARD      = "#141828"
    BG_ELEVATED  = "#1a1f2e"
    BG_NESTED    = "#0f1320"

    BORDER       = "rgba(255,255,255,0.08)"
    BORDER_STRONG= "rgba(255,255,255,0.16)"
    BORDER_GLOW  = "rgba(124,58,237,0.35)"

    TEXT         = "#ffffff"
    TEXT_DIM     = "#9ca3af"
    TEXT_FAINT   = "#6b7280"

    PURPLE       = "#7c3aed"
    PURPLE_LIGHT = "#a78bfa"
    PURPLE_GLOW  = "rgba(124,58,237,0.45)"
    CYAN         = "#22d3ee"
    GREEN        = "#10b981"
    AMBER        = "#f59e0b"
    RED          = "#f43f5e"
    LINKEDIN     = "#0a66c2"


# ─── Score thresholds ───────────────────────────────────────────────────────────
SCORE_HIGH_MIN = 70
SCORE_MID_MIN  = 45

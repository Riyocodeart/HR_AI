"""
services/config.py
───────────────────
Single source of truth for provider/model selection so a future Google
model rotation (they've been deprecating Flash models every few months in
2026) only needs a change here, not a hunt through every file that calls
the API.
"""

DEFAULT_PROVIDER = "gemini"
GEMINI_API_KEYS_ENV = "GEMINI_API_KEYS"
GEMINI_API_KEY_ENV = "GEMINI_API_KEY"
GEMINI_API_KEY_PREFIX = "GEMINI_API_KEY_"

# gemini-2.0-flash was shut down by Google on June 1, 2026 — DO NOT use it.
# gemini-2.5-flash is the current stable replacement (cheap, fast, good
# enough for structured extraction / scoring). It is scheduled to be
# deprecated around October 2026 — when that happens, update this one
# constant rather than hunting through the codebase.
GEMINI_MODEL = "gemini-2.5-flash"

# Max candidates sent to Gemini in a single scoring call. Keeps prompts
# small enough to stay fast and reliable; larger datasets are automatically
# chunked into batches of this size by core/scorer.py.
SCORING_BATCH_SIZE = 40

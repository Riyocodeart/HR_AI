"""
parser.json_validator
=====================
Robust JSON extraction, schema validation, and last-resort repair.

The LLM is *supposed* to emit clean JSON (we ask Ollama for
``format='json'``), but production code never trusts that — code fences
sneak in, balanced braces drift, trailing commas appear. This module
absorbs those failure modes.

Public API
----------
* ``extract_json(text)``           → dict
* ``validate(payload, schema)``    → raises ``jsonschema.ValidationError``
* ``repair_json(text)``            → dict | None  (heuristic last resort)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator, ValidationError

from .utils import get_logger

log = get_logger(__name__)


_CODE_FENCE = re.compile(r"```(?:json)?\s*|\s*```", re.IGNORECASE)


# ─────────────────────────────────────────────────────────────────────────────
# Extraction
# ─────────────────────────────────────────────────────────────────────────────
def extract_json(text: str) -> dict[str, Any]:
    """
    Best-effort JSON-from-text extractor.

    Strategy
    --------
    1. Strip markdown code fences.
    2. Try ``json.loads`` on the trimmed payload.
    3. Fall back to the substring between the first ``{`` and the last
       balanced ``}``.
    4. Raise ``ValueError`` if all attempts fail — callers decide whether
       to retry the LLM or hit :func:`repair_json`.
    """
    if not text or not text.strip():
        raise ValueError("Empty model response")

    cleaned = _CODE_FENCE.sub("", text).strip()

    # Fast path
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Slow path: find the outermost balanced object
    candidate = _find_balanced_object(cleaned)
    if candidate is None:
        raise ValueError("No JSON object found in model output")

    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Could not decode JSON object: {exc}") from exc


def _find_balanced_object(text: str) -> str | None:
    """Return the substring of the first balanced ``{...}`` block, or None."""
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────────────────────────────────────
def load_schema(path: str | Path) -> dict:
    """Read a JSON schema from disk."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate(payload: dict, schema: dict) -> None:
    """
    Validate ``payload`` against ``schema``. Aggregates all errors so the
    caller / repair prompt sees the full picture, not just the first one.
    """
    errors = sorted(Draft7Validator(schema).iter_errors(payload), key=lambda e: e.path)
    if not errors:
        return

    bullets = []
    for err in errors:
        loc = "/".join(str(p) for p in err.absolute_path) or "<root>"
        bullets.append(f"  • {loc}: {err.message}")
    msg = "Schema validation failed:\n" + "\n".join(bullets)
    log.warning(msg)
    raise ValidationError(msg)


# ─────────────────────────────────────────────────────────────────────────────
# Repair
# ─────────────────────────────────────────────────────────────────────────────
def repair_json(text: str) -> dict | None:
    """
    Heuristic last-resort repair for malformed JSON.

    Strips trailing commas, fixes naive single-quoted strings, retries.
    Returns ``None`` if nothing salvageable comes out — the caller should
    then either re-prompt the model or surface the failure.
    """
    if not text:
        return None

    candidate = _CODE_FENCE.sub("", text).strip()
    candidate = _find_balanced_object(candidate) or candidate

    # 1. Trailing commas before } or ]
    candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
    # 2. Single → double quotes (only when the string contains no double quotes)
    candidate = re.sub(
        r"'([^'\"]*?)'",
        lambda m: '"' + m.group(1).replace('"', '\\"') + '"',
        candidate,
    )
    # 3. Smart quotes → straight quotes
    candidate = candidate.replace("“", '"').replace("”", '"')
    candidate = candidate.replace("‘", "'").replace("’", "'")

    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        log.warning("repair_json gave up: %s", exc)
        return None

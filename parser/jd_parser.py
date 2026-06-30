"""
parser.jd_parser
================
Main orchestrator for the JD extraction pipeline.

    Raw JD ─► Cleaner ─► PromptBuilder ─► Ollama(model: str = "qwen2.5:1.5b-instruct",)
            ─► JSON Extract ─► Schema Validate ─► Normalize ─► dict

Public entry point
------------------
``parse_job_description(text: str) -> dict``

Object-oriented wrapper
-----------------------
``JDParser`` — instantiate once, call ``.parse()`` many times.
Useful in Streamlit so the schema / Ollama client aren't rebuilt on each rerun.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

from jsonschema import ValidationError
from pydantic import ValidationError as PydanticValidationError

from .cleaner import JDCleaner
from .json_validator import extract_json, load_schema, repair_json, validate
from .models import JobDescription
from .normalizer import JDNormalizer
from .prompt_builder import PromptBuilder
from .utils import get_logger

log = get_logger(__name__)


# Default location of the schema — adjust at runtime via JDParser(schema_path=...).
_DEFAULT_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "jd_schema.json"


class OllamaError(RuntimeError):
    """Raised when the local Ollama daemon is unreachable or rejects the call."""


class JDParser:
    """
    JD extraction pipeline.

    Parameters
    ----------
    model : str
        Ollama model tag. Default ``"model: str = "qwen2.5:1.5b-instruct",
"``.
    host : str
        Ollama server URL.
    schema_path : str | Path | None
        Path to ``jd_schema.json``. If ``None`` the bundled schema next to
        the package root is used. If that's also missing, schema validation
        is skipped (Pydantic still validates).
    temperature : float
    seed : int
        Together these pin deterministic output from Qwen.
    timeout : int
        Per-call timeout in seconds passed to Ollama.
    """

    def __init__(
        self,
        model: str = "qwen2.5:1.5b-instruct",
        host: str = "http://localhost:11434",
        schema_path: str | Path | None = None,
        temperature: float = 0.0,
        seed: int = 42,
        timeout: int = 120,
    ) -> None:
        self.model = model
        self.host = host.rstrip("/")
        self.temperature = temperature
        self.seed = seed
        self.timeout = timeout

        self.cleaner = JDCleaner()
        self.prompt_builder = PromptBuilder()
        self.normalizer = JDNormalizer()

        self.schema: dict | None = self._maybe_load_schema(schema_path)

        # Lazy-imported Ollama client (keeps requirements optional at import).
        self._client = self._init_client()

    # ─────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────
    def parse(self, text: str) -> dict[str, Any]:
        """
        Parse a raw JD string into a structured dict matching ``jd_schema.json``.

        Pipeline
        --------
        1. Clean.
        2. Call Qwen via Ollama (JSON mode).
        3. Extract + validate. On failure → retry once with repair prompt.
        4. If still invalid → heuristic repair.
        5. Pydantic-coerce, normalise, return.

        Raises
        ------
        OllamaError
            When the Ollama daemon is unreachable.
        ValueError
            When the model produced unrecoverable garbage twice in a row.
        """
        if not text or not text.strip():
            log.warning("Empty JD passed to parse(); returning empty skeleton")
            return JobDescription().to_dict()

        cleaned = self.cleaner.clean(text)
        messages = self.prompt_builder.build_messages(cleaned)

        raw = self._chat(messages)
        log.debug("First Qwen response: %d chars", len(raw))

        # Attempt 1 — straight extract + validate
        try:
            payload = extract_json(raw)
            self._validate(payload)
        except (ValueError, ValidationError) as first_err:
            log.warning("First-pass validation failed: %s", first_err)

            # Attempt 2 — show the model its mistake
            repair_msgs = messages + [
                {"role": "assistant", "content": raw},
                {"role": "user",
                 "content": self.prompt_builder.build_repair_prompt(raw, str(first_err))},
            ]
            raw2 = self._chat(repair_msgs)
            try:
                payload = extract_json(raw2)
                self._validate(payload)
            except (ValueError, ValidationError) as second_err:
                log.warning("Second-pass validation failed: %s", second_err)

                # Attempt 3 — local heuristic repair (no LLM round-trip)
                repaired = repair_json(raw2) or repair_json(raw)
                if repaired is None:
                    raise ValueError(
                        f"JD parser could not produce valid JSON after 2 LLM "
                        f"attempts and one heuristic repair. Last error: {second_err}"
                    ) from second_err
                payload = repaired
                # Soft-validate; don't crash on schema mismatches at this point
                try:
                    self._validate(payload)
                except ValidationError as exc:
                    log.warning("Repair returned a non-schema-compliant payload: %s", exc)

        return self._finalize(payload)

    def parse_stream(self, text: str) -> Iterator[tuple[str, Any]]:
        """
        Generator variant that yields ``(field_name, value)`` pairs as the
        Qwen call completes — convenient for the UI's typing animation.

        The Ollama call is not actually streamed token-by-token (that would
        give us partial JSON that's hard to render); instead we parse once
        and then yield each top-level field in a deterministic order so
        the UI can animate the reveal.
        """
        result = self.parse(text)
        # Stable, recruiter-friendly order
        ordered_keys = (
            "job_title", "company_name", "department", "industry", "domain",
            "location", "work_mode", "employment_type", "experience",
            "education", "skills", "programming_languages", "frameworks",
            "libraries", "cloud_platforms", "databases", "devops_tools",
            "tools", "responsibilities", "certifications", "soft_skills",
            "languages", "keywords", "salary", "notice_period",
            "travel_requirement", "shift",
        )
        for key in ordered_keys:
            if key in result:
                yield key, result[key]
        # Anything extra at the end (forward-compatibility)
        for key, value in result.items():
            if key not in ordered_keys:
                yield key, value

    # ─────────────────────────────────────────────────────────────────────
    # Internals
    # ─────────────────────────────────────────────────────────────────────
    def _init_client(self):
        """
        Instantiate an Ollama Python client.

        Falls back to the HTTP API via ``requests`` if the ``ollama`` package
        isn't installed — keeps the dependency optional in resource-limited
        sandboxes.
        """
        try:
            import ollama  # type: ignore

            return ollama.Client(host=self.host, timeout=self.timeout)
        except ImportError:
            log.info("`ollama` package not installed; falling back to HTTP requests")
            return None

    def _maybe_load_schema(self, schema_path: str | Path | None) -> dict | None:
        path = Path(schema_path) if schema_path else _DEFAULT_SCHEMA_PATH
        if not path.exists():
            log.warning("Schema not found at %s — schema validation disabled", path)
            return None
        try:
            return load_schema(path)
        except Exception as exc:  # noqa: BLE001
            log.warning("Could not load schema (%s) — schema validation disabled", exc)
            return None

    def _chat(self, messages: list[dict]) -> str:
        """
        Send ``messages`` to Ollama and return the assistant content.

        Uses JSON mode + temperature=0 + fixed seed for determinism.
        """
        options = {
            "temperature": self.temperature,
            "seed": self.seed,
            "top_p": 1.0,
            "num_ctx": 8192,
        }

        if self._client is not None:
            try:
                resp = self._client.chat(
                    model=self.model,
                    messages=messages,
                    format="json",
                    options=options,
                )
                return resp["message"]["content"]
            except Exception as exc:  # noqa: BLE001 — surface as OllamaError
                raise OllamaError(f"Ollama .chat() failed: {exc}") from exc

        # HTTP fallback
        return self._chat_http(messages, options)

    def _chat_http(self, messages: list[dict], options: dict) -> str:
        import requests  # local import keeps top-level light

        try:
            resp = requests.post(
                f"{self.host}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "format": "json",
                    "stream": False,
                    "options": options,
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise OllamaError(f"HTTP call to Ollama failed: {exc}") from exc

        data = resp.json()
        try:
            return data["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise OllamaError(f"Unexpected Ollama response shape: {data}") from exc

    def _validate(self, payload: dict) -> None:
        """Run jsonschema validation when a schema is loaded; otherwise no-op."""
        if self.schema is None:
            return
        validate(payload, self.schema)

    def _finalize(self, payload: dict) -> dict:
        """Pydantic-coerce → normalise → dict (the canonical output)."""
        try:
            model = JobDescription.model_validate(payload)
        except PydanticValidationError as exc:
            log.warning("Pydantic coercion warning: %s", exc)
            # Pydantic strict failures are rare here because the model is
            # extra=allow with all-Optional fields. Fall back to raw payload.
            return self.normalizer.normalize(payload)
        return self.normalizer.normalize(model.to_dict())


# ─────────────────────────────────────────────────────────────────────────────
# Module-level convenience (matches the spec in the brief)
# ─────────────────────────────────────────────────────────────────────────────
_default_parser: JDParser | None = None


def _get_default() -> JDParser:
    global _default_parser
    if _default_parser is None:
        _default_parser = JDParser()
    return _default_parser


def parse_job_description(text: str) -> dict:
    """
    Parse a JD into a structured dict matching ``jd_schema.json``.

    Lazy-instantiates a process-wide default :class:`JDParser` so the
    Ollama client / schema aren't reloaded on every call.
    """
    return _get_default().parse(text)

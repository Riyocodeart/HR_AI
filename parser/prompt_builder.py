"""
parser.prompt_builder
=====================
Builds the system + user prompt pair sent to Qwen 2.5 7B Instruct.

The system prompt is intentionally rigid — it pins down the schema,
the "no inference" rule, and the JSON-only output contract. The user
prompt is just the cleaned JD wrapped in delimiters.

Why the schema is embedded literally
------------------------------------
Qwen 2.5 follows JSON schemas better when they're shown in-prompt than
when described in prose. Determinism + recall both improve.
"""

from __future__ import annotations

import json
from typing import Iterable

# A compact JSON sketch of the target output. We intentionally keep it
# small and human-readable — the model copies its shape verbatim.
_SCHEMA_SKETCH: dict = {
    "job_title": "string | null",
    "company_name": "string | null",
    "department": "string | null",
    "employment_type": "string | null  // full-time / part-time / contract / internship",
    "work_mode": "string | null        // remote / hybrid / onsite",
    "location": "string | null",
    "experience": {
        "minimum_years": "number | null",
        "maximum_years": "number | null",
    },
    "education": ["string"],
    "skills": {
        "required": ["string"],
        "preferred": ["string"],
    },
    "responsibilities": ["string"],
    "tools": ["string"],
    "certifications": ["string"],
    "soft_skills": ["string"],
    "industry": "string | null",
    "domain": "string | null",
    "salary": "string | null",
    "notice_period": "string | null",
    "travel_requirement": "string | null",
    "shift": "string | null",
    "languages": ["string"],
    "keywords": ["string"],
    "programming_languages": ["string"],
    "frameworks": ["string"],
    "libraries": ["string"],
    "cloud_platforms": ["string"],
    "databases": ["string"],
    "devops_tools": ["string"],
}


_SYSTEM_PROMPT = """\
You are an expert Job Description (JD) parser inside a production
recruitment pipeline. Your only job is to extract structured data
from a JD and return it as a single valid JSON object.

═══ STRICT RULES ═══
1.  Output ONLY a JSON object. No prose, no markdown fences, no comments.
2.  Never fabricate or infer information that is not explicitly in the JD.
3.  If a scalar field is absent → return null. If an array is absent → [].
4.  Preserve the original casing of proper nouns (company names, technologies).
5.  Split skills into "required" (mandatory / must-have) and "preferred"
    (nice-to-have / optional / bonus).
6.  Experience: extract numeric years. "5+ years" → minimum_years=5,
    maximum_years=null. "3-5 years" → minimum_years=3, maximum_years=5.
7.  Be deterministic — same JD must always produce the same JSON.
8.  Do not add fields outside the schema below.

═══ OUTPUT SCHEMA (return all keys, use null / [] when absent) ═══
{schema}

═══ TAXONOMY HINTS (split tools into the right bucket) ═══
- programming_languages : Python, Java, Go, Rust, C++, TypeScript, Scala, ...
- frameworks            : Django, FastAPI, Spring, React, Next.js, TensorFlow, PyTorch, ...
- libraries             : pandas, NumPy, scikit-learn, Hugging Face Transformers, ...
- cloud_platforms       : AWS, GCP, Azure, OCI, ...
- databases             : PostgreSQL, MySQL, MongoDB, Redis, Snowflake, BigQuery, ...
- devops_tools          : Docker, Kubernetes, Jenkins, GitHub Actions, Terraform, Ansible, ...
- tools                 : everything else (Jira, Figma, Tableau, Postman, ...)

The same item should appear in only ONE bucket. If you are unsure, place
it in "tools".

═══ REMINDER ═══
Return ONLY the JSON object. Nothing before, nothing after.
"""


class PromptBuilder:
    """
    Construct prompts for the JD extraction call.

    The builder is stateless — instances are cheap and safe to share.
    """

    def __init__(self, schema_sketch: dict | None = None) -> None:
        self._schema = schema_sketch or _SCHEMA_SKETCH

    # ── Public API ───────────────────────────────────────────────────────
    def build_system_prompt(self) -> str:
        """Return the static system prompt with the schema embedded."""
        schema_str = json.dumps(self._schema, indent=2, ensure_ascii=False)
        return _SYSTEM_PROMPT.format(schema=schema_str)

    def build_user_prompt(self, jd_text: str) -> str:
        """
        Wrap the cleaned JD in delimiters and append the extraction cue.

        Delimiters discourage the model from quoting JD text verbatim
        inside the output JSON.
        """
        return (
            "Parse the following job description and return the JSON object.\n\n"
            "<JOB_DESCRIPTION>\n"
            f"{jd_text}\n"
            "</JOB_DESCRIPTION>\n\n"
            "Return the JSON object now."
        )

    def build_repair_prompt(self, broken_json: str, error: str) -> str:
        """
        Used when the first response fails JSON / schema validation.

        Shows the model its own output plus the validator error and asks
        for a corrected JSON object.
        """
        return (
            "Your previous output was not valid JSON for the required schema.\n\n"
            f"Validator error:\n{error}\n\n"
            "Your previous output:\n"
            f"{broken_json}\n\n"
            "Return ONLY a corrected JSON object matching the schema. "
            "No prose, no markdown fences."
        )

    def build_messages(self, jd_text: str) -> list[dict]:
        """Convenience: produce the Ollama-shape ``messages`` list."""
        return [
            {"role": "system", "content": self.build_system_prompt()},
            {"role": "user", "content": self.build_user_prompt(jd_text)},
        ]

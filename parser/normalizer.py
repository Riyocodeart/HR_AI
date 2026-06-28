"""
parser.normalizer
=================
Post-validation cleanup so downstream consumers (embedding generator,
FAISS indexer, ranking engine) see canonical, deduplicated, well-typed
values regardless of how the LLM phrased them.

Idempotent: ``normalize(normalize(x)) == normalize(x)``.
"""

from __future__ import annotations

import re
from typing import Any

from .utils import get_logger

log = get_logger(__name__)


# ── Canonical enum mappings ──────────────────────────────────────────────────
_WORK_MODE = {
    "remote": "remote",
    "work from home": "remote",
    "wfh": "remote",
    "fully remote": "remote",
    "hybrid": "hybrid",
    "flex": "hybrid",
    "flexible": "hybrid",
    "onsite": "onsite",
    "on-site": "onsite",
    "in-office": "onsite",
    "in office": "onsite",
    "office": "onsite",
}

_EMPLOYMENT_TYPE = {
    "full time": "full-time",
    "full-time": "full-time",
    "fulltime": "full-time",
    "permanent": "full-time",
    "part time": "part-time",
    "part-time": "part-time",
    "contract": "contract",
    "contractor": "contract",
    "contractual": "contract",
    "freelance": "contract",
    "internship": "internship",
    "intern": "internship",
    "temporary": "temporary",
    "temp": "temporary",
}


class JDNormalizer:
    """Apply deterministic post-processing to a parsed JD dict."""

    # ── Public API ───────────────────────────────────────────────────────
    def normalize(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Return a normalized copy of ``payload``."""
        out = dict(payload)  # shallow copy — list/dict children handled below

        out["work_mode"] = self._map_enum(out.get("work_mode"), _WORK_MODE)
        out["employment_type"] = self._map_enum(
            out.get("employment_type"), _EMPLOYMENT_TYPE
        )

        out["experience"] = self._normalize_experience(out.get("experience"))

        # All list fields → dedupe + trim
        for key in (
            "education", "responsibilities", "tools", "certifications",
            "soft_skills", "languages", "keywords", "programming_languages",
            "frameworks", "libraries", "cloud_platforms", "databases",
            "devops_tools",
        ):
            out[key] = self._clean_string_list(out.get(key))

        out["skills"] = self._normalize_skills(out.get("skills"))

        # Scalar trims
        for key in (
            "job_title", "company_name", "department", "location",
            "industry", "domain", "salary", "notice_period",
            "travel_requirement", "shift",
        ):
            out[key] = self._clean_string(out.get(key))

        return out

    # ── Field-level helpers ──────────────────────────────────────────────
    @staticmethod
    def _clean_string(value: Any) -> str | None:
        if value is None:
            return None
        s = str(value).strip()
        s = re.sub(r"\s+", " ", s)
        return s or None

    @classmethod
    def _clean_string_list(cls, value: Any) -> list[str]:
        if not value:
            return []
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            return []
        seen: set[str] = set()
        cleaned: list[str] = []
        for item in value:
            s = cls._clean_string(item)
            if not s:
                continue
            key = s.casefold()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(s)
        return cleaned

    @staticmethod
    def _map_enum(value: Any, lookup: dict[str, str]) -> str | None:
        if value is None:
            return None
        key = str(value).strip().lower()
        return lookup.get(key, str(value).strip() or None)

    @classmethod
    def _normalize_experience(cls, value: Any) -> dict[str, float | None]:
        default = {"minimum_years": None, "maximum_years": None}
        if not isinstance(value, dict):
            return default

        def _coerce(v: Any) -> float | None:
            if v is None or v == "":
                return None
            try:
                f = float(v)
                return f if f >= 0 else None
            except (TypeError, ValueError):
                return None

        out = {
            "minimum_years": _coerce(value.get("minimum_years")),
            "maximum_years": _coerce(value.get("maximum_years")),
        }
        # If only max is set, mirror it onto min so consumers always have a floor
        if out["minimum_years"] is None and out["maximum_years"] is not None:
            log.debug("Experience min missing; mirroring max onto min")
            out["minimum_years"] = 0.0
        return out

    @classmethod
    def _normalize_skills(cls, value: Any) -> dict[str, list[str]]:
        if not isinstance(value, dict):
            return {"required": [], "preferred": []}
        required = cls._clean_string_list(value.get("required"))
        preferred = cls._clean_string_list(value.get("preferred"))
        # Drop preferred items that are already required (dedup across buckets)
        required_set = {s.casefold() for s in required}
        preferred = [p for p in preferred if p.casefold() not in required_set]
        return {"required": required, "preferred": preferred}

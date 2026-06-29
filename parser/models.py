"""
parser.models
=============
Pydantic data models for the parsed Job Description.

The shape mirrors ``jd_schema.json`` exactly, plus a handful of opt-in tech
taxonomy buckets requested by the ranking pipeline (programming_languages,
frameworks, libraries, cloud_platforms, databases, devops_tools).

Design notes
------------
* `extra="allow"` so any **additional structured entity** the model
  legitimately surfaces is not dropped (forward-compatible with the
  ranker's feature extraction).
* All non-mandatory fields default to ``None`` / ``[]`` — never invent.
* Pydantic owns *value* validation; ``json_validator`` owns *schema*
  validation. Keep the responsibilities separate.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ─────────────────────────────────────────────────────────────────────────────
# Nested objects
# ─────────────────────────────────────────────────────────────────────────────
class Experience(BaseModel):
    """Experience range in years. Either bound may be null."""

    model_config = ConfigDict(extra="allow")

    minimum_years: Optional[float] = None
    maximum_years: Optional[float] = None


class Skills(BaseModel):
    """Required vs preferred skill split."""

    model_config = ConfigDict(extra="allow")

    required: List[str] = Field(default_factory=list)
    preferred: List[str] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Root model
# ─────────────────────────────────────────────────────────────────────────────
class JobDescription(BaseModel):
    """
    Canonical structured representation of a parsed Job Description.

    Field set is the union of `jd_schema.json` and the dynamic tech buckets
    used by the ranking engine. Missing scalars are ``None``; missing
    collections are empty lists.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    # ── Core identity ────────────────────────────────────────────────────
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    department: Optional[str] = None
    employment_type: Optional[str] = None        # full-time / contract / ...
    work_mode: Optional[str] = None              # remote / hybrid / onsite
    location: Optional[str] = None

    # ── Quantitative requirements ────────────────────────────────────────
    experience: Experience = Field(default_factory=Experience)

    # ── Qualifications ───────────────────────────────────────────────────
    education: List[str] = Field(default_factory=list)
    skills: Skills = Field(default_factory=Skills)
    certifications: List[str] = Field(default_factory=list)

    # ── Job content ──────────────────────────────────────────────────────
    responsibilities: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)

    # ── Context ──────────────────────────────────────────────────────────
    industry: Optional[str] = None
    domain: Optional[str] = None
    salary: Optional[str] = None
    notice_period: Optional[str] = None
    travel_requirement: Optional[str] = None
    shift: Optional[str] = None

    # ── Misc ─────────────────────────────────────────────────────────────
    languages: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)

    # ── Dynamic tech taxonomy (extends schema) ───────────────────────────
    programming_languages: List[str] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    libraries: List[str] = Field(default_factory=list)
    cloud_platforms: List[str] = Field(default_factory=list)
    databases: List[str] = Field(default_factory=list)
    devops_tools: List[str] = Field(default_factory=list)

    # ─────────────────────────────────────────────────────────────────────
    # Convenience
    # ─────────────────────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        """Return a plain dict suitable for JSON serialization."""
        return self.model_dump(mode="json", by_alias=True)

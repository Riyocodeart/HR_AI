"""
parser/jsonl_reader.py
======================
Aarya's Task — JSONL Reader (Candidate Parser module)

Implements the exact workflow from Parser_design.md:

    candidates.jsonl
          │
          ▼
    JSONL Reader (Line by Line)
          │
          ▼
    Parse JSON Object
          │
          ▼
    Validate Required Fields
          │
        ┌─┴────────────┐
        │              │
  Missing Field?   Valid Record
        │              │
        ▼              ▼
  Error Logger   Candidate Parser
                       │
         ┌─────────────┼──────────────┐
         ▼             ▼              ▼
  Profile Parser  Career Parser  Education Parser
         │             │              │
         └──────────┬──┴──────────────┘
                    ▼
              Skills Parser
                    │
                    ▼
          Redrob Signals Parser
                    │
                    ▼
         Candidate Object Builder
                    │
                    ▼
        Feature Engineering Pipeline

Usage:
    from parser.jsonl_reader import JSONLReader

    reader = JSONLReader("data/candidates.jsonl")
    for candidate in reader.read():
        print(candidate["candidate_id"])

    # Or load all at once
    candidates, errors = reader.read_all()
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Optional

# ── Logger setup ──────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# REQUIRED FIELDS  (per datacleaning.md Step 1)
# ══════════════════════════════════════════════════════════════════════════════

REQUIRED_ROOT_FIELDS = [
    "candidate_id",
    "profile",
    "career_history",
    "education",
    "skills",
    "redrob_signals",
]

REQUIRED_PROFILE_FIELDS = [
    "years_of_experience",
    "current_title",
    "location",
]


# ══════════════════════════════════════════════════════════════════════════════
# PARSED DATA STRUCTURES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ParsedProfile:
    anonymized_name:     str
    headline:            str
    summary:             str
    location:            str
    country:             str
    years_of_experience: float
    current_title:       str
    current_company:     str
    current_company_size: str
    current_industry:    str


@dataclass
class ParsedCareerEntry:
    company:         str
    title:           str
    start_date:      Optional[str]
    end_date:        Optional[str]
    duration_months: int
    is_current:      bool
    industry:        str
    company_size:    str
    description:     str


@dataclass
class ParsedEducation:
    institution:   str
    degree:        str
    field_of_study: str
    start_year:    Optional[int]
    end_year:      Optional[int]
    grade:         str
    tier:          str


@dataclass
class ParsedSkill:
    name:            str
    proficiency:     str
    endorsements:    int
    duration_months: int


@dataclass
class ParsedCertification:
    name:   str
    issuer: str
    year:   Optional[int]


@dataclass
class ParsedLanguage:
    language:    str
    proficiency: str


@dataclass
class ParsedRedrobSignals:
    profile_completeness_score: float
    signup_date:                Optional[str]
    last_active_date:           Optional[str]
    open_to_work_flag:          bool
    profile_views_received_30d: int
    applications_submitted_30d: int
    recruiter_response_rate:    float
    avg_response_time_hours:    Optional[float]
    skill_assessment_scores:    dict
    connection_count:           int
    endorsements_received:      int
    notice_period_days:         int
    expected_salary_range_inr_lpa: dict
    preferred_work_mode:        str
    willing_to_relocate:        bool
    github_activity_score:      float
    search_appearance_30d:      int
    saved_by_recruiters_30d:    int
    interview_completion_rate:  float
    offer_acceptance_rate:      float
    verified_email:             bool
    verified_phone:             bool
    linkedin_connected:         bool


@dataclass
class CandidateObject:
    """
    Final structured object produced by the Candidate Object Builder step.
    This is the direct input to the Feature Engineering Pipeline.
    """
    candidate_id:   str
    profile:        ParsedProfile
    career_history: list[ParsedCareerEntry]
    education:      list[ParsedEducation]
    skills:         list[ParsedSkill]
    certifications: list[ParsedCertification]
    languages:      list[ParsedLanguage]
    redrob_signals: ParsedRedrobSignals
    # Added by the reader — not in raw data
    _parse_warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert back to plain dict (for compatibility with ranking engine)."""
        return {
            "candidate_id": self.candidate_id,
            "profile": {
                "anonymized_name":     self.profile.anonymized_name,
                "headline":            self.profile.headline,
                "summary":             self.profile.summary,
                "location":            self.profile.location,
                "country":             self.profile.country,
                "years_of_experience": self.profile.years_of_experience,
                "current_title":       self.profile.current_title,
                "current_company":     self.profile.current_company,
                "current_company_size": self.profile.current_company_size,
                "current_industry":    self.profile.current_industry,
            },
            "career_history": [
                {
                    "company":         j.company,
                    "title":           j.title,
                    "start_date":      j.start_date,
                    "end_date":        j.end_date,
                    "duration_months": j.duration_months,
                    "is_current":      j.is_current,
                    "industry":        j.industry,
                    "company_size":    j.company_size,
                    "description":     j.description,
                }
                for j in self.career_history
            ],
            "education": [
                {
                    "institution":    e.institution,
                    "degree":         e.degree,
                    "field_of_study": e.field_of_study,
                    "start_year":     e.start_year,
                    "end_year":       e.end_year,
                    "grade":          e.grade,
                    "tier":           e.tier,
                }
                for e in self.education
            ],
            "skills": [
                {
                    "name":            s.name,
                    "proficiency":     s.proficiency,
                    "endorsements":    s.endorsements,
                    "duration_months": s.duration_months,
                }
                for s in self.skills
            ],
            "certifications": [
                {"name": c.name, "issuer": c.issuer, "year": c.year}
                for c in self.certifications
            ],
            "languages": [
                {"language": l.language, "proficiency": l.proficiency}
                for l in self.languages
            ],
            "redrob_signals": {
                "profile_completeness_score":    self.redrob_signals.profile_completeness_score,
                "signup_date":                   self.redrob_signals.signup_date,
                "last_active_date":              self.redrob_signals.last_active_date,
                "open_to_work_flag":             self.redrob_signals.open_to_work_flag,
                "profile_views_received_30d":    self.redrob_signals.profile_views_received_30d,
                "applications_submitted_30d":    self.redrob_signals.applications_submitted_30d,
                "recruiter_response_rate":       self.redrob_signals.recruiter_response_rate,
                "avg_response_time_hours":       self.redrob_signals.avg_response_time_hours,
                "skill_assessment_scores":       self.redrob_signals.skill_assessment_scores,
                "connection_count":              self.redrob_signals.connection_count,
                "endorsements_received":         self.redrob_signals.endorsements_received,
                "notice_period_days":            self.redrob_signals.notice_period_days,
                "expected_salary_range_inr_lpa": self.redrob_signals.expected_salary_range_inr_lpa,
                "preferred_work_mode":           self.redrob_signals.preferred_work_mode,
                "willing_to_relocate":           self.redrob_signals.willing_to_relocate,
                "github_activity_score":         self.redrob_signals.github_activity_score,
                "search_appearance_30d":         self.redrob_signals.search_appearance_30d,
                "saved_by_recruiters_30d":       self.redrob_signals.saved_by_recruiters_30d,
                "interview_completion_rate":     self.redrob_signals.interview_completion_rate,
                "offer_acceptance_rate":         self.redrob_signals.offer_acceptance_rate,
                "verified_email":                self.redrob_signals.verified_email,
                "verified_phone":                self.redrob_signals.verified_phone,
                "linkedin_connected":            self.redrob_signals.linkedin_connected,
            },
        }


# ══════════════════════════════════════════════════════════════════════════════
# PARSE ERROR
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ParseError:
    line_number:  int
    candidate_id: Optional[str]
    reason:       str
    raw_line:     str


# ══════════════════════════════════════════════════════════════════════════════
# SECTION PARSERS
# ══════════════════════════════════════════════════════════════════════════════

def _str(v, default: str = "") -> str:
    return str(v).strip() if v is not None else default

def _float(v, default: float = 0.0) -> float:
    try:
        return float(v) if v is not None else default
    except (TypeError, ValueError):
        return default

def _int(v, default: int = 0) -> int:
    try:
        return int(v) if v is not None else default
    except (TypeError, ValueError):
        return default

def _bool(v, default: bool = False) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.lower() in ("true", "yes", "1")
    return bool(v) if v is not None else default


class ProfileParser:
    """Extracts and normalizes the profile section."""

    def parse(self, raw: dict, warnings: list) -> ParsedProfile:
        yoe = raw.get("years_of_experience")
        if yoe is None:
            warnings.append("years_of_experience missing — defaulting to 0")
        if yoe is not None and (_float(yoe) < 0 or _float(yoe) > 60):
            warnings.append(f"years_of_experience={yoe} is outside realistic range 0-60")

        return ParsedProfile(
            anonymized_name=     _str(raw.get("anonymized_name")),
            headline=            _str(raw.get("headline")),
            summary=             _str(raw.get("summary")),
            location=            _str(raw.get("location")),
            country=             _str(raw.get("country")),
            years_of_experience= _float(raw.get("years_of_experience")),
            current_title=       _str(raw.get("current_title")),
            current_company=     _str(raw.get("current_company")),
            current_company_size=_str(raw.get("current_company_size")),
            current_industry=    _str(raw.get("current_industry")),
        )


class CareerParser:
    """Extracts and normalizes the career_history list."""

    def parse(self, raw_list: list, warnings: list) -> list[ParsedCareerEntry]:
        if not isinstance(raw_list, list):
            warnings.append("career_history is not a list — treating as empty")
            return []

        entries = []
        current_count = 0
        for i, job in enumerate(raw_list):
            if not isinstance(job, dict):
                warnings.append(f"career_history[{i}] is not a dict — skipping")
                continue

            # Validate start ≤ end date
            start = job.get("start_date")
            end   = job.get("end_date")
            if start and end and end != "null":
                if str(start) > str(end):
                    warnings.append(f"career_history[{i}]: start_date {start} > end_date {end}")

            is_current = _bool(job.get("is_current"))
            if is_current:
                current_count += 1
                if current_count > 1:
                    warnings.append(f"career_history[{i}]: multiple jobs marked is_current=True")

            entries.append(ParsedCareerEntry(
                company=         _str(job.get("company")),
                title=           _str(job.get("title")),
                start_date=      _str(job.get("start_date")) or None,
                end_date=        (_str(job.get("end_date")) or None) if job.get("end_date") not in (None, "null") else None,
                duration_months= _int(job.get("duration_months")),
                is_current=      is_current,
                industry=        _str(job.get("industry")),
                company_size=    _str(job.get("company_size")),
                description=     _str(job.get("description")),
            ))

        return entries


class EducationParser:
    """Extracts and normalizes the education list."""

    def parse(self, raw_list: list, warnings: list) -> list[ParsedEducation]:
        if not isinstance(raw_list, list):
            warnings.append("education is not a list — treating as empty")
            return []

        entries = []
        for i, edu in enumerate(raw_list):
            if not isinstance(edu, dict):
                warnings.append(f"education[{i}] is not a dict — skipping")
                continue

            start_yr = _int(edu.get("start_year")) or None
            end_yr   = _int(edu.get("end_year"))   or None

            if start_yr and end_yr and start_yr >= end_yr:
                warnings.append(f"education[{i}]: start_year {start_yr} >= end_year {end_yr}")

            entries.append(ParsedEducation(
                institution=   _str(edu.get("institution")),
                degree=        _str(edu.get("degree")),
                field_of_study=_str(edu.get("field_of_study")),
                start_year=    start_yr,
                end_year=      end_yr,
                grade=         _str(edu.get("grade")),
                tier=          _str(edu.get("tier"), default="unknown"),
            ))

        return entries


class SkillsParser:
    """Extracts and normalizes the skills list. Removes duplicates per datacleaning.md."""

    def parse(self, raw_list: list, warnings: list) -> list[ParsedSkill]:
        if not isinstance(raw_list, list):
            warnings.append("skills is not a list — treating as empty")
            return []

        seen_names = set()
        entries = []
        for i, skill in enumerate(raw_list):
            if not isinstance(skill, dict):
                warnings.append(f"skills[{i}] is not a dict — skipping")
                continue

            name = _str(skill.get("name"))
            if not name:
                warnings.append(f"skills[{i}]: empty skill name — skipping")
                continue

            # Remove duplicates (case-insensitive per datacleaning.md)
            name_lower = name.lower()
            if name_lower in seen_names:
                warnings.append(f"Duplicate skill '{name}' removed")
                continue
            seen_names.add(name_lower)

            valid_proficiencies = {"beginner", "intermediate", "advanced", "expert"}
            proficiency = _str(skill.get("proficiency"), "beginner")
            if proficiency not in valid_proficiencies:
                warnings.append(f"skills[{i}]: unknown proficiency '{proficiency}' — defaulting to beginner")
                proficiency = "beginner"

            entries.append(ParsedSkill(
                name=            name,
                proficiency=     proficiency,
                endorsements=    _int(skill.get("endorsements")),
                duration_months= _int(skill.get("duration_months")),
            ))

        return entries


class CertificationParser:
    """Extracts certifications (may be empty list)."""

    def parse(self, raw_list, warnings: list) -> list[ParsedCertification]:
        if not raw_list:
            return []
        if not isinstance(raw_list, list):
            warnings.append("certifications is not a list — treating as empty")
            return []

        entries = []
        for i, cert in enumerate(raw_list):
            if isinstance(cert, str):
                entries.append(ParsedCertification(name=cert, issuer="", year=None))
            elif isinstance(cert, dict):
                entries.append(ParsedCertification(
                    name=   _str(cert.get("name")),
                    issuer= _str(cert.get("issuer")),
                    year=   _int(cert.get("year")) or None,
                ))
        return entries


class LanguageParser:
    """Extracts languages."""

    def parse(self, raw_list, warnings: list) -> list[ParsedLanguage]:
        if not raw_list:
            return []
        if not isinstance(raw_list, list):
            warnings.append("languages is not a list — treating as empty")
            return []

        valid_proficiencies = {"basic", "conversational", "professional", "native"}
        entries = []
        for lang in raw_list:
            if not isinstance(lang, dict):
                continue
            proficiency = _str(lang.get("proficiency"), "basic")
            if proficiency not in valid_proficiencies:
                proficiency = "basic"
            entries.append(ParsedLanguage(
                language=    _str(lang.get("language")),
                proficiency= proficiency,
            ))
        return entries


class RedrobSignalsParser:
    """Extracts and normalizes all redrob_signals fields."""

    def parse(self, raw: dict, warnings: list) -> ParsedRedrobSignals:
        if not isinstance(raw, dict):
            warnings.append("redrob_signals is not a dict — using defaults")
            raw = {}

        # Validate numeric fields are numeric
        for field_name in ("recruiter_response_rate", "interview_completion_rate", "offer_acceptance_rate"):
            val = raw.get(field_name)
            if val is not None and not isinstance(val, (int, float)):
                warnings.append(f"redrob_signals.{field_name} is not numeric: {val}")

        # Validate boolean fields
        for field_name in ("open_to_work_flag", "willing_to_relocate", "verified_email",
                           "verified_phone", "linkedin_connected"):
            val = raw.get(field_name)
            if val is not None and not isinstance(val, bool):
                warnings.append(f"redrob_signals.{field_name} is not boolean: {val}")

        return ParsedRedrobSignals(
            profile_completeness_score=    _float(raw.get("profile_completeness_score")),
            signup_date=                   _str(raw.get("signup_date")) or None,
            last_active_date=              _str(raw.get("last_active_date")) or None,
            open_to_work_flag=             _bool(raw.get("open_to_work_flag")),
            profile_views_received_30d=    _int(raw.get("profile_views_received_30d")),
            applications_submitted_30d=    _int(raw.get("applications_submitted_30d")),
            recruiter_response_rate=       _float(raw.get("recruiter_response_rate")),
            avg_response_time_hours=       _float(raw.get("avg_response_time_hours")) or None,
            skill_assessment_scores=       raw.get("skill_assessment_scores") or {},
            connection_count=              _int(raw.get("connection_count")),
            endorsements_received=         _int(raw.get("endorsements_received")),
            notice_period_days=            _int(raw.get("notice_period_days"), default=90),
            expected_salary_range_inr_lpa= raw.get("expected_salary_range_inr_lpa") or {},
            preferred_work_mode=           _str(raw.get("preferred_work_mode")),
            willing_to_relocate=           _bool(raw.get("willing_to_relocate")),
            github_activity_score=         _float(raw.get("github_activity_score"), default=-1),
            search_appearance_30d=         _int(raw.get("search_appearance_30d")),
            saved_by_recruiters_30d=       _int(raw.get("saved_by_recruiters_30d")),
            interview_completion_rate=     _float(raw.get("interview_completion_rate")),
            offer_acceptance_rate=         _float(raw.get("offer_acceptance_rate"), default=-1),
            verified_email=                _bool(raw.get("verified_email")),
            verified_phone=                _bool(raw.get("verified_phone")),
            linkedin_connected=            _bool(raw.get("linkedin_connected")),
        )


# ══════════════════════════════════════════════════════════════════════════════
# CANDIDATE PARSER  (orchestrates all section parsers)
# ══════════════════════════════════════════════════════════════════════════════

class CandidateParser:
    """
    Orchestrates all section parsers and builds the final CandidateObject.
    Corresponds to the 'Candidate Parser' node in Parser_design.md.
    """

    def __init__(self):
        self._profile_parser  = ProfileParser()
        self._career_parser   = CareerParser()
        self._edu_parser      = EducationParser()
        self._skills_parser   = SkillsParser()
        self._cert_parser     = CertificationParser()
        self._lang_parser     = LanguageParser()
        self._signals_parser  = RedrobSignalsParser()

    def parse(self, raw: dict) -> CandidateObject:
        """
        Parse one raw JSON dict into a CandidateObject.
        Collects warnings along the way — does not raise on non-fatal issues.
        """
        warnings = []

        profile  = self._profile_parser.parse(raw.get("profile", {}), warnings)
        career   = self._career_parser.parse(raw.get("career_history", []), warnings)
        education= self._edu_parser.parse(raw.get("education", []), warnings)
        skills   = self._skills_parser.parse(raw.get("skills", []), warnings)
        certs    = self._cert_parser.parse(raw.get("certifications", []), warnings)
        langs    = self._lang_parser.parse(raw.get("languages", []), warnings)
        signals  = self._signals_parser.parse(raw.get("redrob_signals", {}), warnings)

        return CandidateObject(
            candidate_id=    str(raw["candidate_id"]),
            profile=         profile,
            career_history=  career,
            education=       education,
            skills=          skills,
            certifications=  certs,
            languages=       langs,
            redrob_signals=  signals,
            _parse_warnings= warnings,
        )


# ══════════════════════════════════════════════════════════════════════════════
# JSONL READER  (the main class — Aarya's deliverable)
# ══════════════════════════════════════════════════════════════════════════════

class JSONLReader:
    """
    Reads candidates.jsonl line by line following Parser_design.md workflow:

        Open candidates.jsonl
            │
            ▼
        Read one line
            │
            ▼
        json.loads(line)
            │
            ▼
        Validate JSON + Required Fields
            │
            ├── Invalid ──► Log Error
            │
            ▼
        Extract all sections via CandidateParser
            │
            ▼
        Create Candidate Object
            │
            ▼
        Repeat Until EOF

    Args:
        filepath:       Path to candidates.jsonl
        skip_invalid:   If True, silently skip records that fail validation
                        and log them. If False, raise on first error.
        log_warnings:   Whether to log per-field warnings to the logger.
    """

    def __init__(self, filepath: str, skip_invalid: bool = True, log_warnings: bool = False):
        self.filepath      = Path(filepath)
        self.skip_invalid  = skip_invalid
        self.log_warnings  = log_warnings
        self._parser       = CandidateParser()
        self.errors: list[ParseError] = []

    def _validate_required_fields(self, raw: dict, line_num: int) -> Optional[str]:
        """Returns an error message if required fields are missing, else None."""
        for field in REQUIRED_ROOT_FIELDS:
            if field not in raw or raw[field] is None:
                return f"Missing required field: '{field}'"
        if not isinstance(raw.get("profile"), dict):
            return "Field 'profile' must be an object"
        if not isinstance(raw.get("career_history"), list):
            return "Field 'career_history' must be an array"
        return None

    def read(self) -> Iterator[CandidateObject]:
        """
        Generator — yields one CandidateObject per valid line.
        Invalid lines are logged and skipped (or raise if skip_invalid=False).
        """
        if not self.filepath.exists():
            raise FileNotFoundError(f"candidates.jsonl not found: {self.filepath}")

        with open(self.filepath, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue  # skip blank lines

                # Step: json.loads(line)
                try:
                    raw = json.loads(line)
                except json.JSONDecodeError as e:
                    cid = None
                    err = ParseError(line_num, cid, f"Invalid JSON: {e}", line[:200])
                    self.errors.append(err)
                    logger.error(f"Line {line_num}: Invalid JSON — {e}")
                    if not self.skip_invalid:
                        raise
                    continue

                if not isinstance(raw, dict):
                    err = ParseError(line_num, None, "JSON root is not an object", line[:200])
                    self.errors.append(err)
                    logger.error(f"Line {line_num}: JSON root is not an object")
                    if not self.skip_invalid:
                        raise ValueError(err.reason)
                    continue

                cid = raw.get("candidate_id")

                # Step: Validate Required Fields
                validation_error = self._validate_required_fields(raw, line_num)
                if validation_error:
                    err = ParseError(line_num, cid, validation_error, line[:200])
                    self.errors.append(err)
                    logger.error(f"Line {line_num} ({cid}): {validation_error}")
                    if not self.skip_invalid:
                        raise ValueError(f"Validation failed at line {line_num}: {validation_error}")
                    continue

                # Step: Candidate Parser → all section parsers → Candidate Object Builder
                try:
                    candidate = self._parser.parse(raw)
                except Exception as e:
                    err = ParseError(line_num, cid, f"Parse error: {e}", line[:200])
                    self.errors.append(err)
                    logger.error(f"Line {line_num} ({cid}): Parse error — {e}")
                    if not self.skip_invalid:
                        raise
                    continue

                if self.log_warnings and candidate._parse_warnings:
                    for w in candidate._parse_warnings:
                        logger.warning(f"  ({cid}) {w}")

                yield candidate

    def read_all(self) -> tuple[list[CandidateObject], list[ParseError]]:
        """
        Read all candidates into memory at once.
        Returns (candidates, errors).
        """
        candidates = list(self.read())
        return candidates, self.errors

    def read_as_dicts(self) -> Iterator[dict]:
        """
        Yields raw-compatible dicts (compatible with ranking engine input format).
        """
        for candidate in self.read():
            yield candidate.to_dict()

    @property
    def error_count(self) -> int:
        return len(self.errors)


# ══════════════════════════════════════════════════════════════════════════════
# CLI — quick test / validation run
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    import time

    path = sys.argv[1] if len(sys.argv) > 1 else "data/candidates.jsonl"
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    print(f"Reading: {path}")
    reader = JSONLReader(path, skip_invalid=True, log_warnings=False)

    t0 = time.time()
    count = 0
    warning_count = 0
    for c in reader.read():
        count += 1
        warning_count += len(c._parse_warnings)
        if count <= 3:
            print(f"\n  [{count}] {c.candidate_id}")
            print(f"       Name:     {c.profile.anonymized_name}")
            print(f"       Title:    {c.profile.current_title}")
            print(f"       Exp:      {c.profile.years_of_experience}y")
            print(f"       Location: {c.profile.location}")
            print(f"       Skills:   {len(c.skills)}")
            print(f"       Career:   {len(c.career_history)} jobs")
            print(f"       Warnings: {len(c._parse_warnings)}")

    t1 = time.time()
    print(f"\n✓ Read {count:,} candidates in {t1-t0:.2f}s")
    print(f"  Parse errors:   {reader.error_count}")
    print(f"  Field warnings: {warning_count}")
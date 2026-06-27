"""
filter.py
─────────
Handles everything after the JD is parsed:
  1. load_candidates()     — reads a CSV and normalises column names
  2. score_candidates()    — filters & scores each candidate against the JD
  3. export_excel()        — produces a formatted, colour-coded .xlsx report
  4. export_csv()          — returns scored results as CSV bytes

Scoring formula
───────────────
  total_score (0–100) = skill_score (0–40)
                      + role_score  (0–30)
                      + exp_score   (0–30)

Skill score  : (# required skills found in candidate profile) / (# required) × 40
Role score   : keyword overlap between JD title and candidate title / JD words × 30
Exp score    : 30 if within [exp_min, exp_max]; reduced linearly for over/under-qualified
"""

import io
import re
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from services.key_rotation import load_gemini_api_keys

SKILL_ALIASES = {

    # Programming
    "python": ["python"],

    "r": [
        "r programming",
        "r language"
    ],

    # SQL & Databases
    "sql": [
        "sql",
        "mysql",
        "postgresql",
        "sqlite",
        "sql server"
    ],

    "mongodb": [
        "mongodb",
        "mongo"
    ],

    # Data Science
    "data science": [
        "data science"
    ],

    "statistics": [
        "statistics",
        "statistical analysis"
    ],

    "eda": [
        "eda",
        "exploratory data analysis"
    ],

    "feature engineering": [
        "feature engineering",
        "feature selection"
    ],

    # Machine Learning
    "machine learning": [
        "ml",
        "machine learning",
        "machine learning basics"
    ],

    "deep learning": [
        "deep learning",
        "neural networks"
    ],

    "nlp": [
        "nlp",
        "natural language processing"
    ],

    "computer vision": [
        "computer vision",
        "cv"
    ],

    "recommendation systems": [
        "recommendation systems",
        "recommender systems"
    ],

    # ML Libraries
    "pandas": [
        "pandas"
    ],

    "numpy": [
        "numpy"
    ],

    "matplotlib": [
        "matplotlib"
    ],

    "scikit-learn": [
        "scikit-learn",
        "sklearn"
    ],

    "tensorflow": [
        "tensorflow"
    ],

    "keras": [
        "keras"
    ],

    "pytorch": [
        "pytorch",
        "torch"
    ],

    "xgboost": [
        "xgboost"
    ],

    "lightgbm": [
        "lightgbm",
        "lgbm"
    ],

    # Data Engineering
    "spark": [
        "spark",
        "apache spark",
        "pyspark"
    ],

    "hadoop": [
        "hadoop",
        "apache hadoop"
    ],

    "kafka": [
        "kafka",
        "apache kafka"
    ],

    "airflow": [
        "airflow",
        "apache airflow"
    ],

    "etl": [
        "etl",
        "data pipeline",
        "data pipelines"
    ],

    "data engineering": [
        "data engineering",
        "data engineer"
    ],

    "data warehousing": [
        "data warehousing",
        "data warehouse"
    ],

    "databricks": [
        "databricks"
    ],

    "snowflake": [
        "snowflake"
    ],

    "big data": [
        "big data"
    ],

    # Cloud
    "aws": [
        "aws",
        "amazon web services"
    ],

    "cloud": [
        "cloud",
        "cloud computing",
        "cloud architecture"
    ],

    # BI Tools
    "power bi": [
        "power bi",
        "powerbi"
    ],

    "tableau": [
        "tableau"
    ],

    "excel": [
        "excel",
        "microsoft excel"
    ],

    # AI / GenAI
    "transformers": [
        "transformers",
        "huggingface",
        "hugging face"
    ],

    "llm": [
        "llm",
        "large language models"
    ],

    "genai": [
        "genai",
        "generative ai"
    ],

    "chatgpt": [
        "chatgpt"
    ],

    "prompt engineering": [
        "prompt engineering"
    ],

    "mlops": [
        "mlops",
        "machine learning operations"
    ],

    # Misc
    "research": [
        "research",
        "research publications",
        "publications"
    ],

    "git": [
        "git",
        "github",
        "version control"
    ],

    "linux": [
        "linux",
        "unix"
    ]
}

ALIAS_TO_CANONICAL = {}

for canonical, aliases in SKILL_ALIASES.items():
    for alias in aliases:
        ALIAS_TO_CANONICAL[alias.lower()] = canonical



ROLE_SIMILARITY = {

    "data scientist": [
        "machine learning engineer",
        "ai engineer",
        "research scientist"
    ],

    "machine learning engineer": [
        "data scientist",
        "ai engineer",
        "research scientist",
        "ml architect"
    ],

    "ai engineer": [
        "machine learning engineer",
        "data scientist",
        "ml architect"
    ],

    "research scientist": [
        "data scientist",
        "machine learning engineer"
    ],

    "ml architect": [
        "machine learning engineer",
        "ai engineer"
    ],

    "data analyst": [
        "business analyst"
    ],

    "business analyst": [
        "data analyst"
    ],

    "data engineer": [
        "big data engineer",
        "etl developer"
    ],

    "big data engineer": [
        "data engineer"
    ],

    "etl developer": [
        "data engineer"
    ]
}

def _role_match_score(jd_role: str, cand_role: str) -> int:

    jd_role = jd_role.lower().strip()
    cand_role = cand_role.lower().strip()

    # Exact match
    if jd_role == cand_role:
        return 30

    # Similar role family
    if cand_role in ROLE_SIMILARITY.get(jd_role, []):
        return 25

    # Fallback to existing overlap logic
    jd_words = set(jd_role.split())
    cand_words = set(cand_role.split())

    overlap = jd_words & cand_words

    return round(
        len(overlap) / max(len(jd_words), 1) * 25
    )

# ──────────────────────────────────────────────────────────────────────────────
# COLUMN NAME VARIANTS  (add aliases here if your CSV uses different headings)
# ──────────────────────────────────────────────────────────────────────────────
_COL_ALIASES: dict[str, list[str]] = {
    "name":       ["name", "candidate_name", "full_name", "applicant"],
    "role":       ["role", "job_title", "title", "position", "designation"],
    "location":   ["location", "city", "place", "loc", "region"],
    "experience": ["experience", "exp", "years_of_experience", "years", "yoe"],
    "skills":     ["skills", "skill", "tech_skills", "technical_skills", "technologies"],
    "company":    ["company", "current_company", "employer", "organisation", "organization"],
    "education":  ["education", "edu", "degree", "qualification"],
}


def _find_col(df: pd.DataFrame, field: str) -> str | None:
    """Return the first DataFrame column that matches any alias for `field`."""
    for alias in _COL_ALIASES.get(field, []):
        if alias in df.columns:
            return alias
    return None


def _parse_experience(raw) -> float:
    """Extract the first numeric value from an experience cell."""
    nums = re.findall(r"\d+\.?\d*", str(raw))
    return float(nums[0]) if nums else 0.0

def _skill_match(skill: str, candidate_text: str) -> bool:

    skill = skill.lower().strip()

    canonical = ALIAS_TO_CANONICAL.get(skill, skill)

    aliases = SKILL_ALIASES.get(canonical, [skill])

    for alias in aliases:

        pattern = r"\b" + re.escape(alias.lower()) + r"\b"

        if re.search(pattern, candidate_text):
            return True

    return False


# ──────────────────────────────────────────────────────────────────────────────
# LOAD
# ──────────────────────────────────────────────────────────────────────────────

def load_candidates(uploaded_file) -> pd.DataFrame:
    """
    Read a candidate file (CSV or Excel) and normalise all column names to
    lowercase_underscore. Accepts whatever raw columns the file has — no
    pre-formatting required; AI column mapping (see detect_columns) figures
    out what's what later.

    Returns:
        pd.DataFrame with normalised column names, original data untouched.

    Raises:
        ValueError: if the file extension isn't recognised.
    """
    name = getattr(uploaded_file, "name", "").lower()
    if name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(uploaded_file)
    elif name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        # Best-effort: try CSV first, then Excel, rather than hard-failing
        # on an unrecognised/missing extension.
        try:
            df = pd.read_csv(uploaded_file)
        except Exception:
            uploaded_file.seek(0)
            df = pd.read_excel(uploaded_file)

    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    return df


# ──────────────────────────────────────────────────────────────────────────────
# AI-ASSISTED COLUMN DETECTION
# ──────────────────────────────────────────────────────────────────────────────

def detect_columns(df: pd.DataFrame, jd: dict = None, api_key: str = None) -> dict:
    """
    Map canonical fields (name, role, location, experience, skills, email,
    company, education) to whatever columns actually exist in the uploaded
    file. Tries Gemini first (handles messy/unexpected headers — exactly the
    "I had to hand-build the Excel to match the app" problem); falls back to
    the static alias table below if no API key or the call fails.
    """
    keys = load_gemini_api_keys(api_key)
    mapping = {}

    if keys:
        try:
            from services.provider_factory import get_provider
            provider = get_provider("gemini", keys)
            sample_rows = df.head(3).to_dict(orient="records")
            mapping = provider.map_candidate_columns(list(df.columns), sample_rows) or {}
            # Keep only fields that actually exist as columns.
            mapping = {k: v for k, v in mapping.items() if v in df.columns}
        except Exception:
            mapping = {}

    # Fill in anything AI missed using the static alias table.
    for field in _COL_ALIASES:
        if field not in mapping:
            col = _find_col(df, field)
            if col:
                mapping[field] = col

    return mapping


# ──────────────────────────────────────────────────────────────────────────────
# SCORE — AI (primary path)
# ──────────────────────────────────────────────────────────────────────────────

def _score_candidates_ai(df: pd.DataFrame, jd: dict, api_key: str) -> pd.DataFrame:
    """Batch-scores every candidate via Gemini using the FULL row, not just
    the canonical fields, so any extra signal columns (activity, certs,
    endorsements, last_active, whatever the dataset happens to include) get
    weighed in. Raises on failure so the caller can fall back."""
    from services.provider_factory import get_provider
    provider = get_provider("gemini", load_gemini_api_keys(api_key))

    records = []
    for idx, row in df.iterrows():
        rec = {k: (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
        rec["_row_id"] = int(idx)
        records.append(rec)

    results = provider.score_candidates(jd, records)
    by_id = {int(r["_row_id"]): r for r in results if "_row_id" in r}

    rows_total, rows_skill, rows_role, rows_signal = [], [], [], []
    rows_matched, rows_missing, rows_rationale = [], [], []
    for idx in df.index:
        r = by_id.get(int(idx), {})
        skill_sc  = int(r.get("skill_score", 0) or 0)
        role_sc   = int(r.get("role_score", 0) or 0)
        signal_sc = int(r.get("signal_score", 0) or 0)
        total     = int(r.get("total_score", skill_sc + role_sc + signal_sc) or 0)
        rows_total.append(total)
        rows_skill.append(skill_sc)
        rows_role.append(role_sc)
        rows_signal.append(signal_sc)
        matched = r.get("matched_skills") or []
        missing = r.get("missing_skills") or []
        rows_matched.append(", ".join(matched) if matched else "None")
        rows_missing.append(", ".join(missing) if missing else "None")
        rows_rationale.append(r.get("rationale", ""))

    out = df.copy()
    out["total_score"]    = rows_total
    out["skill_score"]    = rows_skill
    out["role_score"]     = rows_role
    out["signal_score"]   = rows_signal
    out["matched_skills"] = rows_matched
    out["missing_skills"] = rows_missing
    out["rationale"]      = rows_rationale
    return out


# ──────────────────────────────────────────────────────────────────────────────
# SCORE — Offline rule-based (fallback, no API key needed)
# ──────────────────────────────────────────────────────────────────────────────

_LOCATION_ALIASES = {
    "bangalore": "bengaluru", "bengaluru": "bengaluru",
    "bombay": "mumbai", "mumbai": "mumbai",
    "gurgaon": "gurugram", "gurugram": "gurugram",
    "calcutta": "kolkata", "kolkata": "kolkata",
}


def _normalize_location(loc: str) -> str:
    loc = (loc or "").strip().lower()
    return _LOCATION_ALIASES.get(loc, loc)


def _score_candidates_offline(df: pd.DataFrame, jd: dict, col_map: dict) -> pd.DataFrame:
    """
    Deterministic keyword/rule scorer. Used when no Gemini key is available.
    Fixes the location bug from the original version: previously, if the JD
    location couldn't be parsed (jd_location == ""), `bool("" and ...)` is
    always False, so EVERY candidate was marked "No match" regardless of
    their actual city. Now a missing JD location is treated as "N/A / not
    specified" rather than a silent fail for every row.
    """
    df = df.copy()

    required_skills = [s.lower().strip() for s in jd.get("skills", []) if s]
    jd_role     = (jd.get("role") or "").lower()
    jd_location = _normalize_location(jd.get("location") or "")
    exp_min     = int(jd.get("experience_min") or 0)
    exp_max     = int(jd.get("experience_max") or 99)

    skills_col   = col_map.get("skills")
    role_col     = col_map.get("role")
    location_col = col_map.get("location")
    exp_col      = col_map.get("experience")

    rows_skill_sc, rows_role_sc, rows_signal_sc = [], [], []
    rows_loc, rows_matched, rows_missing, rows_total, rows_rationale = [], [], [], [], []

    for _, row in df.iterrows():
        cand_skills_raw = str(row[skills_col]).lower() if skills_col and pd.notna(row.get(skills_col)) else ""
        matched = [s for s in required_skills if _skill_match(s, cand_skills_raw)]
        missing = [s for s in required_skills if not _skill_match(s, cand_skills_raw)]
        skill_sc = round(len(matched) / max(len(required_skills), 1) * 40)

        cand_role = str(row[role_col]).lower() if role_col and pd.notna(row.get(role_col)) else ""
        role_sc = _role_match_score(jd_role, cand_role) if (jd_role and cand_role) else 0

        cand_exp = _parse_experience(row[exp_col]) if exp_col and pd.notna(row.get(exp_col)) else 0.0
        if exp_min <= cand_exp <= exp_max:
            exp_pts = 20
        elif cand_exp > exp_max:
            exp_pts = max(0, 20 - int((cand_exp - exp_max) * 2))
        else:
            exp_pts = max(0, 20 - int((exp_min - cand_exp) * 3))

        cand_loc = _normalize_location(str(row[location_col])) if location_col and pd.notna(row.get(location_col)) else ""
        if not jd_location:
            loc_label, loc_bonus = "— N/A", 5  # JD had no location: don't penalize anyone
        elif cand_loc and jd_location in cand_loc:
            loc_label, loc_bonus = "✅ Yes", 10
        else:
            loc_label, loc_bonus = "❌ No", 0

        signal_sc = exp_pts + loc_bonus
        total = skill_sc + role_sc + signal_sc

        rows_skill_sc.append(skill_sc)
        rows_role_sc.append(role_sc)
        rows_signal_sc.append(signal_sc)
        rows_loc.append(loc_label)
        rows_matched.append(", ".join(matched) if matched else "None")
        rows_missing.append(", ".join(missing) if missing else "None")
        rows_total.append(total)
        rows_rationale.append(
            f"Offline rule-based: {len(matched)}/{max(len(required_skills),1)} skills matched, "
            f"experience {cand_exp:g}y vs required {exp_min}-{exp_max}y."
        )

    df["total_score"]    = rows_total
    df["skill_score"]    = rows_skill_sc
    df["role_score"]     = rows_role_sc
    df["signal_score"]   = rows_signal_sc
    df["location_match"] = rows_loc
    df["matched_skills"] = rows_matched
    df["missing_skills"] = rows_missing
    df["rationale"]      = rows_rationale
    return df


# ──────────────────────────────────────────────────────────────────────────────
# SCORE — Unified public entry point
# ──────────────────────────────────────────────────────────────────────────────

def score_candidates(df: pd.DataFrame, jd: dict, api_key: str = None, mode: str = "auto"):
    """
    Score and rank every candidate against the parsed JD.

    Args:
        df:      Candidate DataFrame (normalised columns).
        jd:      Dict produced by core.parser.parse_jd_with_ai() / parse_jd().
        api_key: Gemini API key. If omitted, reads GEMINI_API_KEY from env.
        mode:    "auto" (Gemini if a key is available, else offline),
                 "ai" (force Gemini, raises if it fails),
                 "offline" (force the deterministic rule-based scorer).

    Returns:
        (scored_df, name_col, source)
        scored_df — original DataFrame + score columns, sorted by total_score
        name_col  — detected column name for candidate names (or None)
        source    — "gemini" or "offline-rule", whichever actually ran
    """
    keys = load_gemini_api_keys(api_key)
    col_map = detect_columns(df, jd, api_key=keys)
    name_col = col_map.get("name") or _find_col(df, "name")

    source = "offline-rule"
    scored = None

    if mode in ("auto", "ai") and keys:
        try:
            scored = _score_candidates_ai(df, jd, keys)
            source = "gemini"
        except Exception:
            if mode == "ai":
                raise
            scored = None

    if scored is None:
        scored = _score_candidates_offline(df, jd, col_map)
        source = "offline-rule"

    scored = scored.sort_values("total_score", ascending=False).reset_index(drop=True)
    scored.insert(0, "rank", range(1, len(scored) + 1))

    return scored, name_col, source

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
    Read a CSV UploadedFile and normalise all column names to lowercase_underscore.

    Returns:
        pd.DataFrame with normalised columns.

    Raises:
        ValueError: if the file cannot be parsed as CSV.
    """
    df = pd.read_csv(uploaded_file)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df


# ──────────────────────────────────────────────────────────────────────────────
# SCORE
# ──────────────────────────────────────────────────────────────────────────────

def score_candidates(df: pd.DataFrame, jd: dict) -> tuple[pd.DataFrame, str | None]:
    """
    Score and rank every candidate against the parsed JD.

    Args:
        df:  Candidate DataFrame (normalised columns).
        jd:  Dict produced by jd_parser.extract_jd_with_ai().

    Returns:
        (scored_df, name_col)
        scored_df  — original DataFrame + score columns, sorted descending by total_score
        name_col   — detected column name for candidate names (or None)
    """
    df = df.copy()

    # JD fields
    required_skills = [s.lower().strip() for s in jd.get("skills", [])]
    jd_role         = jd.get("role", "").lower()
    jd_location     = jd.get("location", "").lower()
    exp_min         = int(jd.get("experience_min", 0) or 0)
    exp_max         = int(jd.get("experience_max", 99) or 99)

    # Detect columns
    skills_col  = _find_col(df, "skills")
    role_col    = _find_col(df, "role")
    location_col= _find_col(df, "location")
    exp_col     = _find_col(df, "experience")
    name_col    = _find_col(df, "name")

    rows_skill_sc, rows_role_sc, rows_exp_sc = [], [], []
    rows_loc, rows_matched, rows_missing, rows_total = [], [], [], []

    for _, row in df.iterrows():

        # ── Skill Score (0–40) ────────────────────────────────────────────────
        cand_skills_raw = str(row[skills_col]).lower() if skills_col else ""
        matched = [
        skill
        for skill in required_skills
        if _skill_match(skill, cand_skills_raw)
        ]

        missing = [
        skill
        for skill in required_skills
        if not _skill_match(skill, cand_skills_raw)
        ]

        skill_sc = round(
            len(matched) / max(len(required_skills), 1) * 40
        )

        # ── Role Score (0–30) ─────────────────────────────────────────────────
        cand_role = str(row[role_col]).lower() if role_col else ""
        if jd_role and cand_role:
            role_sc    = _role_match_score(
                jd_role,
                cand_role
            )
        else:
            role_sc = 0

        # ── Experience Score (0–30) ───────────────────────────────────────────
        cand_exp = _parse_experience(row[exp_col]) if exp_col else 0.0
        if exp_min <= cand_exp <= exp_max:
            exp_sc = 30
        elif cand_exp > exp_max:
            exp_sc = max(0, 30 - int((cand_exp - exp_max) * 3))
        else:
            exp_sc = max(0, 30 - int((exp_min - cand_exp) * 5))

        # ── Location Match (boolean) ──────────────────────────────────────────
        cand_loc  = str(row[location_col]).lower() if location_col else ""
        loc_match = bool(jd_location and jd_location in cand_loc)

        total = skill_sc + role_sc + exp_sc

        rows_skill_sc.append(skill_sc)
        rows_role_sc.append(role_sc)
        rows_exp_sc.append(exp_sc)
        rows_loc.append("✅ Yes" if loc_match else "❌ No")
        rows_matched.append(", ".join(matched) if matched else "None")
        rows_missing.append(", ".join(missing) if missing else "None")
        rows_total.append(total)

    df["total_score"]      = rows_total
    df["skill_score"]      = rows_skill_sc
    df["role_score"]       = rows_role_sc
    df["experience_score"] = rows_exp_sc
    df["location_match"]   = rows_loc
    df["matched_skills"]   = rows_matched
    df["missing_skills"]   = rows_missing

    df = df.sort_values("total_score", ascending=False).reset_index(drop=True)
    df.insert(0, "rank", range(1, len(df) + 1))

    return df, name_col



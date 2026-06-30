"""
features/feature_dictionary.py
================================
Aarya's Task — Feature Dictionary (Feature Planning module)

Defines every feature used by the ranking engine as a structured Python
object. This is the single source of truth for:
    - What each feature is called
    - Where its raw data comes from (which JSON field)
    - What type of value it produces
    - How it gets normalized to 0-1 scale
    - What scoring component it belongs to
    - Whether higher or lower is better
    - Its description for documentation

All 10 feature categories from feature.md are covered:
    1. Profile Features
    2. Career Features
    3. Skill Features
    4. Education Features
    5. Certification Features
    6. Language Features
    7. Redrob Behavioral Signals
    8. Semantic Features
    9. Data Quality & Integrity Features
    10. Dynamic Job Features

Usage:
    from features.feature_dictionary import ALL_FEATURES, get_features_by_category

    for feature in get_features_by_category("skill"):
        print(feature.name, "→", feature.description)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════════════════════

class FeatureCategory(str, Enum):
    PROFILE      = "profile"
    CAREER       = "career"
    SKILL        = "skill"
    EDUCATION    = "education"
    CERTIFICATION = "certification"
    LANGUAGE     = "language"
    BEHAVIORAL   = "behavioral"
    SEMANTIC     = "semantic"
    INTEGRITY    = "integrity"
    DYNAMIC_JD   = "dynamic_jd"


class FeatureType(str, Enum):
    BOOLEAN    = "boolean"      # 0 or 1
    NUMERIC    = "numeric"      # continuous float
    RATIO      = "ratio"        # float between 0.0 and 1.0
    COUNT      = "count"        # non-negative integer
    SCORE      = "score"        # float, already 0-100 or 0-1
    SIMILARITY = "similarity"   # cosine similarity 0.0-1.0
    ORDINAL    = "ordinal"      # discrete ordered levels


class NormalizationMethod(str, Enum):
    NONE          = "none"           # already normalized
    MIN_MAX       = "min_max"        # (x - min) / (max - min)
    CLIP_RATIO    = "clip_ratio"     # min(x / max_val, 1.0)
    BOOLEAN_CAST  = "boolean_cast"   # 1 if truthy else 0
    ORDINAL_MAP   = "ordinal_map"    # map levels to [0, 0.33, 0.66, 1.0]
    LOG_SCALE     = "log_scale"      # log(1 + x) / log(1 + max_val)
    GAUSSIAN      = "gaussian"       # exp(-((x-ideal)^2) / (2*sigma^2))
    INVERSE       = "inverse"        # 1 / (1 + x) — lower is better


class Direction(str, Enum):
    HIGHER_BETTER = "higher_better"   # More = better score
    LOWER_BETTER  = "lower_better"    # Less = better score
    RANGE_IDEAL   = "range_ideal"     # Ideal value or range; outside is penalized
    NEUTRAL       = "neutral"         # Used as informational only


# ══════════════════════════════════════════════════════════════════════════════
# FEATURE DEFINITION
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class FeatureDefinition:
    """
    Defines a single feature used in the ranking pipeline.
    """
    name:               str                    # Unique feature identifier (snake_case)
    display_name:       str                    # Human-readable name
    category:           FeatureCategory        # Which scoring component this belongs to
    source_section:     str                    # Top-level JSON key (profile/career_history/etc.)
    source_field:       str                    # Specific field path within that section
    feature_type:       FeatureType            # Data type of raw value
    normalization:      NormalizationMethod    # How to convert to 0-1 scale
    direction:          Direction              # Whether higher/lower is better
    description:        str                    # Plain English description
    # Optional metadata
    normalization_params: dict = field(default_factory=dict)  # e.g. {"max_val": 50}
    ideal_value:        Optional[float] = None  # For RANGE_IDEAL features
    ideal_range:        Optional[tuple] = None  # (min, max) for range ideal
    weight_hint:        float = 1.0             # Relative importance within category
    is_required:        bool  = False           # If True, missing = hard penalty
    notes:              str   = ""              # Implementation notes


# ══════════════════════════════════════════════════════════════════════════════
# 1. PROFILE FEATURES
# ══════════════════════════════════════════════════════════════════════════════

PROFILE_FEATURES = [
    FeatureDefinition(
        name="headline_match",
        display_name="Headline Match",
        category=FeatureCategory.PROFILE,
        source_section="profile",
        source_field="headline",
        feature_type=FeatureType.SIMILARITY,
        normalization=NormalizationMethod.NONE,
        direction=Direction.HIGHER_BETTER,
        description="Semantic similarity between candidate's LinkedIn headline and JD title/role.",
        weight_hint=1.2,
        notes="Use TF-IDF or sentence-transformer cosine similarity with JD_TEXT.",
    ),
    FeatureDefinition(
        name="summary_match",
        display_name="Summary Match",
        category=FeatureCategory.PROFILE,
        source_section="profile",
        source_field="summary",
        feature_type=FeatureType.SIMILARITY,
        normalization=NormalizationMethod.NONE,
        direction=Direction.HIGHER_BETTER,
        description="Semantic similarity between profile summary and the full job description.",
        weight_hint=1.5,
        notes="Summary is the most concise self-description — high signal if aligned with JD.",
    ),
    FeatureDefinition(
        name="current_title_match",
        display_name="Current Title Match",
        category=FeatureCategory.PROFILE,
        source_section="profile",
        source_field="current_title",
        feature_type=FeatureType.SIMILARITY,
        normalization=NormalizationMethod.NONE,
        direction=Direction.HIGHER_BETTER,
        description="Match between candidate's current job title and the JD's target role.",
        weight_hint=2.0,
        is_required=True,
        notes="Use synonym mapping (e.g. 'ML Engineer' ≈ 'Machine Learning Engineer') before cosine sim.",
    ),
    FeatureDefinition(
        name="current_industry_match",
        display_name="Current Industry Match",
        category=FeatureCategory.PROFILE,
        source_section="profile",
        source_field="current_industry",
        feature_type=FeatureType.BOOLEAN,
        normalization=NormalizationMethod.BOOLEAN_CAST,
        direction=Direction.HIGHER_BETTER,
        description="Whether the candidate's current industry matches the JD's target industry.",
        weight_hint=0.8,
    ),
    FeatureDefinition(
        name="company_size_match",
        display_name="Current Company Size Match",
        category=FeatureCategory.PROFILE,
        source_section="profile",
        source_field="current_company_size",
        feature_type=FeatureType.ORDINAL,
        normalization=NormalizationMethod.ORDINAL_MAP,
        direction=Direction.HIGHER_BETTER,
        description="Match between candidate's current company size and JD's preferred company size.",
        weight_hint=0.5,
        notes="Size bands: 1-10, 11-50, 51-200, 201-500, 501-1000, 1001-5000, 5001-10000, 10001+",
    ),
    FeatureDefinition(
        name="location_match",
        display_name="Location Match",
        category=FeatureCategory.PROFILE,
        source_section="profile",
        source_field="location",
        feature_type=FeatureType.ORDINAL,
        normalization=NormalizationMethod.ORDINAL_MAP,
        direction=Direction.HIGHER_BETTER,
        description="Match between candidate location and JD's preferred work location.",
        weight_hint=1.0,
        normalization_params={"levels": {"preferred": 1.0, "acceptable": 0.6, "willing_to_relocate": 0.3, "no_match": 0.0}},
        notes="Preferred=Pune/Noida, Acceptable=Bangalore/Hyderabad/Mumbai/Delhi/Gurugram.",
    ),
    FeatureDefinition(
        name="country_match",
        display_name="Country Match",
        category=FeatureCategory.PROFILE,
        source_section="profile",
        source_field="country",
        feature_type=FeatureType.BOOLEAN,
        normalization=NormalizationMethod.BOOLEAN_CAST,
        direction=Direction.HIGHER_BETTER,
        description="Whether the candidate is based in the same country as the job.",
        weight_hint=0.7,
        notes="JD is India-based. Candidates in Canada/US/UK are down-weighted unless relocating.",
    ),
    FeatureDefinition(
        name="experience_match",
        display_name="Experience Match",
        category=FeatureCategory.PROFILE,
        source_section="profile",
        source_field="years_of_experience",
        feature_type=FeatureType.NUMERIC,
        normalization=NormalizationMethod.GAUSSIAN,
        direction=Direction.RANGE_IDEAL,
        description="How closely the candidate's total years of experience matches the JD's requirement.",
        ideal_range=(5, 9),
        ideal_value=7.0,
        weight_hint=1.8,
        normalization_params={"sigma": 2.0},
        notes="Gaussian centered at 7y, sigma=2. Score drops for <5y or >9y. 6-8y is sweet spot.",
    ),
]


# ══════════════════════════════════════════════════════════════════════════════
# 2. CAREER FEATURES
# ══════════════════════════════════════════════════════════════════════════════

CAREER_FEATURES = [
    FeatureDefinition(
        name="relevant_experience_years",
        display_name="Relevant Experience",
        category=FeatureCategory.CAREER,
        source_section="career_history",
        source_field="title + description",
        feature_type=FeatureType.NUMERIC,
        normalization=NormalizationMethod.CLIP_RATIO,
        direction=Direction.HIGHER_BETTER,
        description="Total months spent in AI/ML/NLP/search/ranking roles, converted to years.",
        normalization_params={"max_val": 8},
        weight_hint=2.0,
        notes="Sum duration_months where job title or description matches AI role keywords.",
    ),
    FeatureDefinition(
        name="current_role_relevance",
        display_name="Current Role Relevance",
        category=FeatureCategory.CAREER,
        source_section="career_history",
        source_field="title (is_current=True)",
        feature_type=FeatureType.SCORE,
        normalization=NormalizationMethod.NONE,
        direction=Direction.HIGHER_BETTER,
        description="Relevance of the candidate's current job title to the JD's target role.",
        weight_hint=2.5,
        notes="Higher weight because current role is the most predictive signal of fit.",
    ),
    FeatureDefinition(
        name="career_progression",
        display_name="Career Progression",
        category=FeatureCategory.CAREER,
        source_section="career_history",
        source_field="title (all)",
        feature_type=FeatureType.BOOLEAN,
        normalization=NormalizationMethod.BOOLEAN_CAST,
        direction=Direction.HIGHER_BETTER,
        description="Whether the candidate has shown seniority growth (junior → senior) over their career.",
        weight_hint=1.2,
        notes="Compare seniority levels of oldest vs newest roles using keyword mapping.",
    ),
    FeatureDefinition(
        name="leadership_experience",
        display_name="Leadership Experience",
        category=FeatureCategory.CAREER,
        source_section="career_history",
        source_field="description",
        feature_type=FeatureType.BOOLEAN,
        normalization=NormalizationMethod.BOOLEAN_CAST,
        direction=Direction.HIGHER_BETTER,
        description="Whether any career description mentions team management or leadership responsibilities.",
        weight_hint=0.8,
        notes="Keywords: 'managed', 'led', 'team of', 'mentored', 'head of', 'directed'.",
    ),
    FeatureDefinition(
        name="industry_experience",
        display_name="Industry Experience",
        category=FeatureCategory.CAREER,
        source_section="career_history",
        source_field="industry",
        feature_type=FeatureType.SCORE,
        normalization=NormalizationMethod.CLIP_RATIO,
        direction=Direction.HIGHER_BETTER,
        description="Proportion of career spent in AI/ML/tech product industries vs. services.",
        normalization_params={"max_val": 1.0},
        weight_hint=1.0,
    ),
    FeatureDefinition(
        name="company_diversity",
        display_name="Company Diversity",
        category=FeatureCategory.CAREER,
        source_section="career_history",
        source_field="company",
        feature_type=FeatureType.COUNT,
        normalization=NormalizationMethod.CLIP_RATIO,
        direction=Direction.HIGHER_BETTER,
        description="Number of distinct employers — indicates broad exposure vs. single-employer career.",
        normalization_params={"max_val": 6},
        weight_hint=0.6,
        notes="More than 6 employers without long tenures may indicate job hopping.",
    ),
    FeatureDefinition(
        name="company_size_experience",
        display_name="Company Size Experience",
        category=FeatureCategory.CAREER,
        source_section="career_history",
        source_field="company_size",
        feature_type=FeatureType.SCORE,
        normalization=NormalizationMethod.NONE,
        direction=Direction.HIGHER_BETTER,
        description="Experience working in company sizes similar to the JD company.",
        weight_hint=0.5,
        notes="Redrob AI is Series A — prefer startup/small company background.",
    ),
    FeatureDefinition(
        name="avg_job_tenure_months",
        display_name="Average Job Tenure",
        category=FeatureCategory.CAREER,
        source_section="career_history",
        source_field="duration_months",
        feature_type=FeatureType.NUMERIC,
        normalization=NormalizationMethod.GAUSSIAN,
        direction=Direction.RANGE_IDEAL,
        description="Average months per employer — measures career stability.",
        ideal_value=30.0,
        weight_hint=1.0,
        normalization_params={"sigma": 12.0},
        notes="Ideal is ~2.5 years per company. <12 months average = job hopper signal (JD warning).",
    ),
    FeatureDefinition(
        name="career_stability",
        display_name="Career Stability",
        category=FeatureCategory.CAREER,
        source_section="career_history",
        source_field="duration_months",
        feature_type=FeatureType.SCORE,
        normalization=NormalizationMethod.NONE,
        direction=Direction.HIGHER_BETTER,
        description="Inverse of job hopping — penalizes candidates with many short stints (<18 months).",
        weight_hint=1.0,
        notes="Count stints < 18 months. 0 stints = 1.0. Each short stint reduces score.",
    ),
    FeatureDefinition(
        name="project_relevance",
        display_name="Project Relevance",
        category=FeatureCategory.CAREER,
        source_section="career_history",
        source_field="description",
        feature_type=FeatureType.SCORE,
        normalization=NormalizationMethod.CLIP_RATIO,
        direction=Direction.HIGHER_BETTER,
        description="Relevance of work responsibilities in career descriptions to the JD.",
        normalization_params={"max_val": 15},
        weight_hint=2.0,
        notes="Count AI/ML concept hits in descriptions. JD hint: descriptions > skill tags.",
    ),
    FeatureDefinition(
        name="recent_experience_weight",
        display_name="Recent Experience Weight",
        category=FeatureCategory.CAREER,
        source_section="career_history",
        source_field="description + start_date",
        feature_type=FeatureType.SCORE,
        normalization=NormalizationMethod.NONE,
        direction=Direction.HIGHER_BETTER,
        description="Weighted relevance of recent roles (last 3 jobs weighted 50%/30%/20%).",
        weight_hint=1.5,
        notes="More recent work is a stronger predictor of current capability.",
    ),
    FeatureDefinition(
        name="career_description_similarity",
        display_name="Career Description Similarity",
        category=FeatureCategory.CAREER,
        source_section="career_history",
        source_field="description (all)",
        feature_type=FeatureType.SIMILARITY,
        normalization=NormalizationMethod.NONE,
        direction=Direction.HIGHER_BETTER,
        description="Semantic similarity of all career descriptions concatenated against the JD.",
        weight_hint=2.0,
        notes="Most important career feature. JD explicitly says descriptions carry more signal than tags.",
    ),
]


# ══════════════════════════════════════════════════════════════════════════════
# 3. SKILL FEATURES
# ══════════════════════════════════════════════════════════════════════════════

SKILL_FEATURES = [
    FeatureDefinition(
        name="required_skills_matched",
        display_name="Required Skills Matched",
        category=FeatureCategory.SKILL,
        source_section="skills + career_history",
        source_field="name + description",
        feature_type=FeatureType.COUNT,
        normalization=NormalizationMethod.CLIP_RATIO,
        direction=Direction.HIGHER_BETTER,
        description="Number of mandatory JD skills found in candidate's skills list or career descriptions.",
        weight_hint=3.0,
        is_required=True,
        notes="Search both skill tags AND career text. Use synonym expansion.",
    ),
    FeatureDefinition(
        name="preferred_skills_matched",
        display_name="Preferred Skills Matched",
        category=FeatureCategory.SKILL,
        source_section="skills + career_history",
        source_field="name + description",
        feature_type=FeatureType.COUNT,
        normalization=NormalizationMethod.CLIP_RATIO,
        direction=Direction.HIGHER_BETTER,
        description="Number of nice-to-have JD skills found in candidate profile.",
        normalization_params={"max_val": 10},
        weight_hint=1.5,
    ),
    FeatureDefinition(
        name="skill_coverage",
        display_name="Skill Coverage",
        category=FeatureCategory.SKILL,
        source_section="skills + career_history",
        source_field="name",
        feature_type=FeatureType.RATIO,
        normalization=NormalizationMethod.NONE,
        direction=Direction.HIGHER_BETTER,
        description="Percentage of required JD skills covered by the candidate. (matched / total_required)",
        weight_hint=2.5,
    ),
    FeatureDefinition(
        name="skill_proficiency_score",
        display_name="Skill Proficiency Score",
        category=FeatureCategory.SKILL,
        source_section="skills",
        source_field="proficiency",
        feature_type=FeatureType.SCORE,
        normalization=NormalizationMethod.NONE,
        direction=Direction.HIGHER_BETTER,
        description="Weighted average proficiency of relevant skills. Beginner=0.25, Intermediate=0.55, Advanced=0.80, Expert=1.0.",
        weight_hint=1.5,
        normalization_params={"levels": {"beginner": 0.25, "intermediate": 0.55, "advanced": 0.80, "expert": 1.0}},
    ),
    FeatureDefinition(
        name="skill_duration_score",
        display_name="Skill Duration Score",
        category=FeatureCategory.SKILL,
        source_section="skills",
        source_field="duration_months",
        feature_type=FeatureType.NUMERIC,
        normalization=NormalizationMethod.CLIP_RATIO,
        direction=Direction.HIGHER_BETTER,
        description="Average duration (months) of relevant skills, normalized to 0-1.",
        normalization_params={"max_val": 60},
        weight_hint=1.0,
        notes="Longer duration = deeper practical experience with the skill.",
    ),
    FeatureDefinition(
        name="skill_endorsement_score",
        display_name="Skill Endorsement Score",
        category=FeatureCategory.SKILL,
        source_section="skills",
        source_field="endorsements",
        feature_type=FeatureType.NUMERIC,
        normalization=NormalizationMethod.LOG_SCALE,
        direction=Direction.HIGHER_BETTER,
        description="Log-scaled total endorsements across all relevant skills.",
        normalization_params={"max_val": 100},
        weight_hint=0.8,
        notes="Endorsements are a social proof signal. Log-scaled to reduce outlier impact.",
    ),
    FeatureDefinition(
        name="expert_skill_count",
        display_name="Expert Skill Count",
        category=FeatureCategory.SKILL,
        source_section="skills",
        source_field="proficiency == 'expert'",
        feature_type=FeatureType.COUNT,
        normalization=NormalizationMethod.CLIP_RATIO,
        direction=Direction.HIGHER_BETTER,
        description="Number of skills where candidate has 'expert' proficiency.",
        normalization_params={"max_val": 5},
        weight_hint=1.2,
    ),
    FeatureDefinition(
        name="advanced_skill_count",
        display_name="Advanced Skill Count",
        category=FeatureCategory.SKILL,
        source_section="skills",
        source_field="proficiency == 'advanced'",
        feature_type=FeatureType.COUNT,
        normalization=NormalizationMethod.CLIP_RATIO,
        direction=Direction.HIGHER_BETTER,
        description="Number of skills where candidate has 'advanced' proficiency.",
        normalization_params={"max_val": 8},
        weight_hint=1.0,
    ),
    FeatureDefinition(
        name="ai_skill_count",
        display_name="AI Skill Count",
        category=FeatureCategory.SKILL,
        source_section="skills",
        source_field="name (AI/ML keywords)",
        feature_type=FeatureType.COUNT,
        normalization=NormalizationMethod.CLIP_RATIO,
        direction=Direction.HIGHER_BETTER,
        description="Count of AI/ML-related skills (embeddings, LLM, NLP, retrieval, ranking, etc.).",
        normalization_params={"max_val": 8},
        weight_hint=2.0,
        notes="Use SKILL_SYNONYMS to match. This is the primary category for this JD.",
    ),
    FeatureDefinition(
        name="backend_skill_count",
        display_name="Backend Skill Count",
        category=FeatureCategory.SKILL,
        source_section="skills",
        source_field="name (backend keywords)",
        feature_type=FeatureType.COUNT,
        normalization=NormalizationMethod.CLIP_RATIO,
        direction=Direction.HIGHER_BETTER,
        description="Count of backend engineering skills (Python, Go, Java, FastAPI, Flask, etc.).",
        normalization_params={"max_val": 5},
        weight_hint=0.8,
    ),
    FeatureDefinition(
        name="cloud_skill_count",
        display_name="Cloud Skill Count",
        category=FeatureCategory.SKILL,
        source_section="skills",
        source_field="name (AWS/GCP/Azure)",
        feature_type=FeatureType.COUNT,
        normalization=NormalizationMethod.CLIP_RATIO,
        direction=Direction.HIGHER_BETTER,
        description="Count of cloud platform skills (AWS, GCP, Azure, SageMaker, Vertex AI, etc.).",
        normalization_params={"max_val": 3},
        weight_hint=0.7,
    ),
    FeatureDefinition(
        name="database_skill_count",
        display_name="Database Skill Count",
        category=FeatureCategory.SKILL,
        source_section="skills",
        source_field="name (SQL/NoSQL/vector DB)",
        feature_type=FeatureType.COUNT,
        normalization=NormalizationMethod.CLIP_RATIO,
        direction=Direction.HIGHER_BETTER,
        description="Count of database skills — SQL, vector DBs (FAISS, Pinecone, etc.), NoSQL.",
        normalization_params={"max_val": 4},
        weight_hint=1.0,
        notes="Vector database skills are especially relevant for this JD.",
    ),
]


# ══════════════════════════════════════════════════════════════════════════════
# 4. EDUCATION FEATURES
# ══════════════════════════════════════════════════════════════════════════════

EDUCATION_FEATURES = [
    FeatureDefinition(
        name="highest_degree",
        display_name="Highest Degree",
        category=FeatureCategory.EDUCATION,
        source_section="education",
        source_field="degree",
        feature_type=FeatureType.ORDINAL,
        normalization=NormalizationMethod.ORDINAL_MAP,
        direction=Direction.HIGHER_BETTER,
        description="Highest academic degree attained. PhD > Masters > Bachelors > Diploma.",
        normalization_params={"levels": {"phd": 1.0, "masters": 0.75, "bachelors": 0.5, "diploma": 0.25, "unknown": 0.3}},
        weight_hint=1.0,
    ),
    FeatureDefinition(
        name="degree_match",
        display_name="Degree Match",
        category=FeatureCategory.EDUCATION,
        source_section="education",
        source_field="degree",
        feature_type=FeatureType.BOOLEAN,
        normalization=NormalizationMethod.BOOLEAN_CAST,
        direction=Direction.HIGHER_BETTER,
        description="Whether the degree meets the minimum qualification specified in the JD.",
        weight_hint=0.8,
    ),
    FeatureDefinition(
        name="field_match",
        display_name="Field of Study Match",
        category=FeatureCategory.EDUCATION,
        source_section="education",
        source_field="field_of_study",
        feature_type=FeatureType.SCORE,
        normalization=NormalizationMethod.NONE,
        direction=Direction.HIGHER_BETTER,
        description="Relevance of the field of study to the JD role.",
        weight_hint=1.2,
        normalization_params={"relevant_fields": ["computer science", "machine learning", "artificial intelligence",
                                                    "data science", "mathematics", "statistics",
                                                    "electrical engineering", "information technology"]},
    ),
    FeatureDefinition(
        name="institution_tier",
        display_name="Institution Tier",
        category=FeatureCategory.EDUCATION,
        source_section="education",
        source_field="tier",
        feature_type=FeatureType.ORDINAL,
        normalization=NormalizationMethod.ORDINAL_MAP,
        direction=Direction.HIGHER_BETTER,
        description="Prestige tier of the institution (tier_1 = IIT/NIT/top-intl, tier_4 = unranked).",
        normalization_params={"levels": {"tier_1": 1.0, "tier_2": 0.75, "tier_3": 0.5, "tier_4": 0.25, "unknown": 0.4}},
        weight_hint=1.5,
    ),
    FeatureDefinition(
        name="academic_score",
        display_name="Academic Score",
        category=FeatureCategory.EDUCATION,
        source_section="education",
        source_field="grade",
        feature_type=FeatureType.NUMERIC,
        normalization=NormalizationMethod.MIN_MAX,
        direction=Direction.HIGHER_BETTER,
        description="GPA or percentage grade normalized to 0-1 scale.",
        normalization_params={"min_val": 0, "max_val": 10, "gpa_max": 4.0, "percent_max": 100},
        weight_hint=0.7,
        notes="Handle multiple formats: CGPA/10, GPA/4, percentage/100.",
    ),
    FeatureDefinition(
        name="graduation_recency",
        display_name="Graduation Recency",
        category=FeatureCategory.EDUCATION,
        source_section="education",
        source_field="end_year",
        feature_type=FeatureType.NUMERIC,
        normalization=NormalizationMethod.INVERSE,
        direction=Direction.HIGHER_BETTER,
        description="Years since graduation — more recent = more current curriculum exposure.",
        weight_hint=0.5,
        notes="1 / (1 + years_since_graduation * 0.1). Recent grads score higher.",
    ),
    FeatureDefinition(
        name="academic_consistency",
        display_name="Academic Consistency",
        category=FeatureCategory.EDUCATION,
        source_section="education",
        source_field="start_year + end_year",
        feature_type=FeatureType.BOOLEAN,
        normalization=NormalizationMethod.BOOLEAN_CAST,
        direction=Direction.HIGHER_BETTER,
        description="Whether academic timeline is valid (start < end, no future dates, no overlaps).",
        weight_hint=0.5,
        notes="Part of Integrity validation but surfaced as an Education feature.",
    ),
]


# ══════════════════════════════════════════════════════════════════════════════
# 5. CERTIFICATION FEATURES
# ══════════════════════════════════════════════════════════════════════════════

CERTIFICATION_FEATURES = [
    FeatureDefinition(
        name="certification_count",
        display_name="Certification Count",
        category=FeatureCategory.CERTIFICATION,
        source_section="certifications",
        source_field="*",
        feature_type=FeatureType.COUNT,
        normalization=NormalizationMethod.CLIP_RATIO,
        direction=Direction.HIGHER_BETTER,
        description="Total number of certifications listed.",
        normalization_params={"max_val": 8},
        weight_hint=0.5,
    ),
    FeatureDefinition(
        name="relevant_certifications",
        display_name="Relevant Certifications",
        category=FeatureCategory.CERTIFICATION,
        source_section="certifications",
        source_field="name",
        feature_type=FeatureType.COUNT,
        normalization=NormalizationMethod.CLIP_RATIO,
        direction=Direction.HIGHER_BETTER,
        description="Number of certifications directly relevant to the JD role.",
        normalization_params={"max_val": 4},
        weight_hint=1.5,
        notes="Relevant: AWS ML Specialty, TF Developer, PyTorch, Google Cloud ML, DeepLearning.AI, etc.",
    ),
    FeatureDefinition(
        name="recent_certifications",
        display_name="Recent Certifications",
        category=FeatureCategory.CERTIFICATION,
        source_section="certifications",
        source_field="year",
        feature_type=FeatureType.SCORE,
        normalization=NormalizationMethod.NONE,
        direction=Direction.HIGHER_BETTER,
        description="Certifications earned in the last 3 years weighted more than older ones.",
        weight_hint=1.0,
        notes="Decay: year <= current-1: full, current-3: 0.7, current-5: 0.4, older: 0.1.",
    ),
    FeatureDefinition(
        name="premium_certifications",
        display_name="Premium Certifications",
        category=FeatureCategory.CERTIFICATION,
        source_section="certifications",
        source_field="issuer",
        feature_type=FeatureType.COUNT,
        normalization=NormalizationMethod.CLIP_RATIO,
        direction=Direction.HIGHER_BETTER,
        description="Certifications from top-tier issuers (Google, AWS, Microsoft, DeepLearning.AI, etc.).",
        normalization_params={"max_val": 3},
        weight_hint=1.2,
    ),
]


# ══════════════════════════════════════════════════════════════════════════════
# 6. LANGUAGE FEATURES
# ══════════════════════════════════════════════════════════════════════════════

LANGUAGE_FEATURES = [
    FeatureDefinition(
        name="required_language_match",
        display_name="Required Language Match",
        category=FeatureCategory.LANGUAGE,
        source_section="languages",
        source_field="language + proficiency",
        feature_type=FeatureType.SCORE,
        normalization=NormalizationMethod.ORDINAL_MAP,
        direction=Direction.HIGHER_BETTER,
        description="Whether the candidate has the required language (English) at sufficient proficiency.",
        normalization_params={"levels": {"native": 1.0, "professional": 0.85, "conversational": 0.5, "basic": 0.2}},
        weight_hint=2.0,
        is_required=True,
        notes="English is required. Proficiency of 'professional' or above preferred.",
    ),
    FeatureDefinition(
        name="professional_language_count",
        display_name="Professional Language Count",
        category=FeatureCategory.LANGUAGE,
        source_section="languages",
        source_field="proficiency in ['professional', 'native']",
        feature_type=FeatureType.COUNT,
        normalization=NormalizationMethod.CLIP_RATIO,
        direction=Direction.HIGHER_BETTER,
        description="Number of languages at professional or native proficiency.",
        normalization_params={"max_val": 3},
        weight_hint=0.5,
    ),
    FeatureDefinition(
        name="native_language_count",
        display_name="Native Language Count",
        category=FeatureCategory.LANGUAGE,
        source_section="languages",
        source_field="proficiency == 'native'",
        feature_type=FeatureType.COUNT,
        normalization=NormalizationMethod.CLIP_RATIO,
        direction=Direction.HIGHER_BETTER,
        description="Number of languages at native proficiency.",
        normalization_params={"max_val": 2},
        weight_hint=0.3,
    ),
]


# ══════════════════════════════════════════════════════════════════════════════
# 7. REDROB BEHAVIORAL SIGNALS
# ══════════════════════════════════════════════════════════════════════════════

BEHAVIORAL_FEATURES = [
    # --- Recruiter Interest ---
    FeatureDefinition(
        name="profile_completeness",
        display_name="Profile Completeness Score",
        category=FeatureCategory.BEHAVIORAL,
        source_section="redrob_signals",
        source_field="profile_completeness_score",
        feature_type=FeatureType.RATIO,
        normalization=NormalizationMethod.NONE,
        direction=Direction.HIGHER_BETTER,
        description="Platform-computed completeness of the candidate's profile (0-1).",
        weight_hint=1.0,
    ),
    FeatureDefinition(
        name="profile_views_30d",
        display_name="Profile Views (30 Days)",
        category=FeatureCategory.BEHAVIORAL,
        source_section="redrob_signals",
        source_field="profile_views_received_30d",
        feature_type=FeatureType.COUNT,
        normalization=NormalizationMethod.LOG_SCALE,
        direction=Direction.HIGHER_BETTER,
        description="Number of recruiter profile views in the last 30 days — indicates market interest.",
        normalization_params={"max_val": 100},
        weight_hint=0.8,
    ),
    FeatureDefinition(
        name="search_appearance_30d",
        display_name="Search Appearance (30 Days)",
        category=FeatureCategory.BEHAVIORAL,
        source_section="redrob_signals",
        source_field="search_appearance_30d",
        feature_type=FeatureType.COUNT,
        normalization=NormalizationMethod.LOG_SCALE,
        direction=Direction.HIGHER_BETTER,
        description="How many times the profile appeared in recruiter searches in 30 days.",
        normalization_params={"max_val": 500},
        weight_hint=0.7,
    ),
    FeatureDefinition(
        name="saved_by_recruiters_30d",
        display_name="Saved by Recruiters (30 Days)",
        category=FeatureCategory.BEHAVIORAL,
        source_section="redrob_signals",
        source_field="saved_by_recruiters_30d",
        feature_type=FeatureType.COUNT,
        normalization=NormalizationMethod.CLIP_RATIO,
        direction=Direction.HIGHER_BETTER,
        description="Number of recruiters who saved this profile in 30 days — strong interest signal.",
        normalization_params={"max_val": 15},
        weight_hint=1.2,
    ),
    # --- Candidate Availability ---
    FeatureDefinition(
        name="open_to_work",
        display_name="Open to Work",
        category=FeatureCategory.BEHAVIORAL,
        source_section="redrob_signals",
        source_field="open_to_work_flag",
        feature_type=FeatureType.BOOLEAN,
        normalization=NormalizationMethod.BOOLEAN_CAST,
        direction=Direction.HIGHER_BETTER,
        description="Whether the candidate has actively signaled they are looking for a job.",
        weight_hint=2.5,
        is_required=False,
        notes="Used as availability multiplier — not in work = 0.75x final score.",
    ),
    FeatureDefinition(
        name="notice_period",
        display_name="Notice Period",
        category=FeatureCategory.BEHAVIORAL,
        source_section="redrob_signals",
        source_field="notice_period_days",
        feature_type=FeatureType.NUMERIC,
        normalization=NormalizationMethod.INVERSE,
        direction=Direction.LOWER_BETTER,
        description="Notice period in days. Shorter = better. JD prefers ≤30 days.",
        ideal_value=30,
        weight_hint=1.5,
        notes="≤30d: 1.0, ≤60d: 0.6, ≤90d: 0.3, >90d: 0.0 (or use smooth decay).",
    ),
    FeatureDefinition(
        name="preferred_work_mode",
        display_name="Preferred Work Mode",
        category=FeatureCategory.BEHAVIORAL,
        source_section="redrob_signals",
        source_field="preferred_work_mode",
        feature_type=FeatureType.BOOLEAN,
        normalization=NormalizationMethod.BOOLEAN_CAST,
        direction=Direction.HIGHER_BETTER,
        description="Whether candidate's preferred work mode matches JD (onsite / hybrid / flexible).",
        weight_hint=0.6,
    ),
    FeatureDefinition(
        name="willing_to_relocate",
        display_name="Willing to Relocate",
        category=FeatureCategory.BEHAVIORAL,
        source_section="redrob_signals",
        source_field="willing_to_relocate",
        feature_type=FeatureType.BOOLEAN,
        normalization=NormalizationMethod.BOOLEAN_CAST,
        direction=Direction.HIGHER_BETTER,
        description="Whether the candidate is open to relocating to the job's location.",
        weight_hint=0.8,
        notes="Bonus if candidate is not already in preferred location but willing to relocate.",
    ),
    # --- Recruiter Responsiveness ---
    FeatureDefinition(
        name="recruiter_response_rate",
        display_name="Recruiter Response Rate",
        category=FeatureCategory.BEHAVIORAL,
        source_section="redrob_signals",
        source_field="recruiter_response_rate",
        feature_type=FeatureType.RATIO,
        normalization=NormalizationMethod.NONE,
        direction=Direction.HIGHER_BETTER,
        description="Fraction of recruiter messages the candidate responded to (0.0-1.0).",
        weight_hint=2.0,
        notes="JD explicitly mentions this: 5% response rate = candidate not actually available.",
    ),
    FeatureDefinition(
        name="avg_response_time",
        display_name="Average Response Time",
        category=FeatureCategory.BEHAVIORAL,
        source_section="redrob_signals",
        source_field="avg_response_time_hours",
        feature_type=FeatureType.NUMERIC,
        normalization=NormalizationMethod.INVERSE,
        direction=Direction.LOWER_BETTER,
        description="Average hours to respond to recruiter messages. Faster = more engaged.",
        weight_hint=1.0,
        notes="≤4h: 1.0, ≤24h: 0.7, ≤72h: 0.4, >72h: 0.1. None = neutral 0.3.",
    ),
    # --- Platform Trust ---
    FeatureDefinition(
        name="verified_email",
        display_name="Verified Email",
        category=FeatureCategory.BEHAVIORAL,
        source_section="redrob_signals",
        source_field="verified_email",
        feature_type=FeatureType.BOOLEAN,
        normalization=NormalizationMethod.BOOLEAN_CAST,
        direction=Direction.HIGHER_BETTER,
        description="Whether the candidate's email address has been verified.",
        weight_hint=0.7,
    ),
    FeatureDefinition(
        name="verified_phone",
        display_name="Verified Phone",
        category=FeatureCategory.BEHAVIORAL,
        source_section="redrob_signals",
        source_field="verified_phone",
        feature_type=FeatureType.BOOLEAN,
        normalization=NormalizationMethod.BOOLEAN_CAST,
        direction=Direction.HIGHER_BETTER,
        description="Whether the candidate's phone number has been verified.",
        weight_hint=0.7,
    ),
    FeatureDefinition(
        name="linkedin_connected",
        display_name="LinkedIn Connected",
        category=FeatureCategory.BEHAVIORAL,
        source_section="redrob_signals",
        source_field="linkedin_connected",
        feature_type=FeatureType.BOOLEAN,
        normalization=NormalizationMethod.BOOLEAN_CAST,
        direction=Direction.HIGHER_BETTER,
        description="Whether the candidate has connected their LinkedIn profile.",
        weight_hint=0.8,
    ),
    # --- Interview Performance ---
    FeatureDefinition(
        name="interview_completion_rate",
        display_name="Interview Completion Rate",
        category=FeatureCategory.BEHAVIORAL,
        source_section="redrob_signals",
        source_field="interview_completion_rate",
        feature_type=FeatureType.RATIO,
        normalization=NormalizationMethod.NONE,
        direction=Direction.HIGHER_BETTER,
        description="Fraction of scheduled interviews the candidate completed.",
        weight_hint=1.5,
        notes="No-show rate is a strong signal of unreliability.",
    ),
    FeatureDefinition(
        name="offer_acceptance_rate",
        display_name="Offer Acceptance Rate",
        category=FeatureCategory.BEHAVIORAL,
        source_section="redrob_signals",
        source_field="offer_acceptance_rate",
        feature_type=FeatureType.RATIO,
        normalization=NormalizationMethod.NONE,
        direction=Direction.HIGHER_BETTER,
        description="Fraction of job offers the candidate accepted. -1 means no history.",
        weight_hint=0.8,
        notes="Candidates who consistently decline offers may not be serious about moving.",
    ),
    # --- Technical Activity ---
    FeatureDefinition(
        name="github_activity_score",
        display_name="GitHub Activity Score",
        category=FeatureCategory.BEHAVIORAL,
        source_section="redrob_signals",
        source_field="github_activity_score",
        feature_type=FeatureType.SCORE,
        normalization=NormalizationMethod.CLIP_RATIO,
        direction=Direction.HIGHER_BETTER,
        description="Platform-computed GitHub activity score (0-100). -1 means no GitHub linked.",
        normalization_params={"max_val": 100},
        weight_hint=1.5,
        notes="JD mentions open-source contributions as a positive signal.",
    ),
    FeatureDefinition(
        name="skill_assessment_scores",
        display_name="Skill Assessment Scores",
        category=FeatureCategory.BEHAVIORAL,
        source_section="redrob_signals",
        source_field="skill_assessment_scores",
        feature_type=FeatureType.SCORE,
        normalization=NormalizationMethod.NONE,
        direction=Direction.HIGHER_BETTER,
        description="Average of platform skill assessment scores for relevant skills (0-100).",
        weight_hint=1.2,
        notes="Only include assessments for skills relevant to this JD.",
    ),
    # --- Platform Engagement ---
    FeatureDefinition(
        name="last_active_recency",
        display_name="Last Active Date",
        category=FeatureCategory.BEHAVIORAL,
        source_section="redrob_signals",
        source_field="last_active_date",
        feature_type=FeatureType.NUMERIC,
        normalization=NormalizationMethod.INVERSE,
        direction=Direction.LOWER_BETTER,
        description="Days since last platform activity. Lower = more recently active = more available.",
        weight_hint=2.5,
        notes="JD explicit: 6+ months inactive = multiply final score by 0.5.",
    ),
    FeatureDefinition(
        name="applications_submitted_30d",
        display_name="Applications Submitted (30 Days)",
        category=FeatureCategory.BEHAVIORAL,
        source_section="redrob_signals",
        source_field="applications_submitted_30d",
        feature_type=FeatureType.COUNT,
        normalization=NormalizationMethod.CLIP_RATIO,
        direction=Direction.HIGHER_BETTER,
        description="Number of job applications submitted in last 30 days — indicates active search.",
        normalization_params={"max_val": 10},
        weight_hint=0.8,
    ),
    FeatureDefinition(
        name="connection_count",
        display_name="Connection Count",
        category=FeatureCategory.BEHAVIORAL,
        source_section="redrob_signals",
        source_field="connection_count",
        feature_type=FeatureType.COUNT,
        normalization=NormalizationMethod.LOG_SCALE,
        direction=Direction.HIGHER_BETTER,
        description="Number of professional connections on the platform.",
        normalization_params={"max_val": 1000},
        weight_hint=0.4,
    ),
    # --- Compensation ---
    FeatureDefinition(
        name="salary_match",
        display_name="Expected Salary Match",
        category=FeatureCategory.BEHAVIORAL,
        source_section="redrob_signals",
        source_field="expected_salary_range_inr_lpa",
        feature_type=FeatureType.SCORE,
        normalization=NormalizationMethod.NONE,
        direction=Direction.HIGHER_BETTER,
        description="Whether the candidate's expected salary is within the JD's budget range.",
        weight_hint=1.0,
        notes="expected_salary_range_inr_lpa contains {min, max}. Compare with JD salary band.",
    ),
]


# ══════════════════════════════════════════════════════════════════════════════
# 8. SEMANTIC FEATURES
# ══════════════════════════════════════════════════════════════════════════════

SEMANTIC_FEATURES = [
    FeatureDefinition(
        name="jd_overall_similarity",
        display_name="JD Overall Embedding Similarity",
        category=FeatureCategory.SEMANTIC,
        source_section="all",
        source_field="full_text",
        feature_type=FeatureType.SIMILARITY,
        normalization=NormalizationMethod.NONE,
        direction=Direction.HIGHER_BETTER,
        description="Cosine similarity between the full candidate text embedding and JD embedding.",
        weight_hint=2.0,
        notes="Generated by semantic retrieval stage. Used for initial top-K shortlisting.",
    ),
    FeatureDefinition(
        name="headline_jd_similarity",
        display_name="Headline Similarity",
        category=FeatureCategory.SEMANTIC,
        source_section="profile",
        source_field="headline",
        feature_type=FeatureType.SIMILARITY,
        normalization=NormalizationMethod.NONE,
        direction=Direction.HIGHER_BETTER,
        description="Cosine similarity between candidate headline and JD title.",
        weight_hint=1.2,
    ),
    FeatureDefinition(
        name="summary_jd_similarity",
        display_name="Summary Similarity",
        category=FeatureCategory.SEMANTIC,
        source_section="profile",
        source_field="summary",
        feature_type=FeatureType.SIMILARITY,
        normalization=NormalizationMethod.NONE,
        direction=Direction.HIGHER_BETTER,
        description="Cosine similarity between profile summary and full JD text.",
        weight_hint=1.5,
    ),
    FeatureDefinition(
        name="career_jd_similarity",
        display_name="Career Description Similarity",
        category=FeatureCategory.SEMANTIC,
        source_section="career_history",
        source_field="description (concatenated)",
        feature_type=FeatureType.SIMILARITY,
        normalization=NormalizationMethod.NONE,
        direction=Direction.HIGHER_BETTER,
        description="Cosine similarity between all career descriptions and JD.",
        weight_hint=2.0,
        notes="Highest-weight semantic feature. JD says descriptions carry more signal than skill tags.",
    ),
    FeatureDefinition(
        name="skill_jd_similarity",
        display_name="Skill Embeddings Similarity",
        category=FeatureCategory.SEMANTIC,
        source_section="skills",
        source_field="name (concatenated)",
        feature_type=FeatureType.SIMILARITY,
        normalization=NormalizationMethod.NONE,
        direction=Direction.HIGHER_BETTER,
        description="Cosine similarity between skill names and JD required skills.",
        weight_hint=1.5,
    ),
    FeatureDefinition(
        name="education_jd_similarity",
        display_name="Education Similarity",
        category=FeatureCategory.SEMANTIC,
        source_section="education",
        source_field="field_of_study + degree",
        feature_type=FeatureType.SIMILARITY,
        normalization=NormalizationMethod.NONE,
        direction=Direction.HIGHER_BETTER,
        description="Semantic similarity of education background to JD educational requirements.",
        weight_hint=0.8,
    ),
    FeatureDefinition(
        name="industry_jd_similarity",
        display_name="Industry Similarity",
        category=FeatureCategory.SEMANTIC,
        source_section="career_history + profile",
        source_field="industry",
        feature_type=FeatureType.SIMILARITY,
        normalization=NormalizationMethod.NONE,
        direction=Direction.HIGHER_BETTER,
        description="Embedding similarity between candidate's industry background and JD industry.",
        weight_hint=0.7,
    ),
]


# ══════════════════════════════════════════════════════════════════════════════
# 9. DATA QUALITY & INTEGRITY FEATURES  (Aarya's design, Tanishq's implementation)
# ══════════════════════════════════════════════════════════════════════════════

INTEGRITY_FEATURES = [
    FeatureDefinition(
        name="has_headline",
        display_name="Missing Headline",
        category=FeatureCategory.INTEGRITY,
        source_section="profile",
        source_field="headline",
        feature_type=FeatureType.BOOLEAN,
        normalization=NormalizationMethod.BOOLEAN_CAST,
        direction=Direction.HIGHER_BETTER,
        description="Profile has a non-empty headline. Missing = integrity penalty.",
        weight_hint=1.0,
        normalization_params={"penalty_if_missing": 5},
    ),
    FeatureDefinition(
        name="has_summary",
        display_name="Missing Summary",
        category=FeatureCategory.INTEGRITY,
        source_section="profile",
        source_field="summary",
        feature_type=FeatureType.BOOLEAN,
        normalization=NormalizationMethod.BOOLEAN_CAST,
        direction=Direction.HIGHER_BETTER,
        description="Profile has a non-empty summary. Missing = integrity penalty.",
        weight_hint=1.0,
        normalization_params={"penalty_if_missing": 5},
    ),
    FeatureDefinition(
        name="has_skills",
        display_name="Missing Skills",
        category=FeatureCategory.INTEGRITY,
        source_section="skills",
        source_field="*",
        feature_type=FeatureType.BOOLEAN,
        normalization=NormalizationMethod.BOOLEAN_CAST,
        direction=Direction.HIGHER_BETTER,
        description="Skills list is non-empty. Missing = integrity penalty.",
        weight_hint=2.0,
        normalization_params={"penalty_if_missing": 25},
    ),
    FeatureDefinition(
        name="has_career_descriptions",
        display_name="Missing Career Descriptions",
        category=FeatureCategory.INTEGRITY,
        source_section="career_history",
        source_field="description",
        feature_type=FeatureType.BOOLEAN,
        normalization=NormalizationMethod.BOOLEAN_CAST,
        direction=Direction.HIGHER_BETTER,
        description="At least one career history entry has a description >30 chars.",
        weight_hint=1.5,
        normalization_params={"penalty_if_missing": 10},
    ),
    FeatureDefinition(
        name="no_duplicate_skills",
        display_name="Duplicate Skills",
        category=FeatureCategory.INTEGRITY,
        source_section="skills",
        source_field="name",
        feature_type=FeatureType.BOOLEAN,
        normalization=NormalizationMethod.BOOLEAN_CAST,
        direction=Direction.HIGHER_BETTER,
        description="Skills list has no duplicate entries (case-insensitive).",
        weight_hint=0.5,
        normalization_params={"penalty_if_failing": 5},
    ),
    FeatureDefinition(
        name="no_duplicate_companies",
        display_name="Duplicate Companies",
        category=FeatureCategory.INTEGRITY,
        source_section="career_history",
        source_field="company + title + start_date",
        feature_type=FeatureType.BOOLEAN,
        normalization=NormalizationMethod.BOOLEAN_CAST,
        direction=Direction.HIGHER_BETTER,
        description="Career history has no duplicate job records.",
        weight_hint=0.5,
        normalization_params={"penalty_if_failing": 5},
    ),
    FeatureDefinition(
        name="career_timeline_valid",
        display_name="Career Timeline Consistency",
        category=FeatureCategory.INTEGRITY,
        source_section="career_history",
        source_field="start_date + end_date",
        feature_type=FeatureType.BOOLEAN,
        normalization=NormalizationMethod.BOOLEAN_CAST,
        direction=Direction.HIGHER_BETTER,
        description="All career dates are chronologically valid (start < end, no future dates).",
        weight_hint=1.5,
        normalization_params={"penalty_if_failing": 20},
    ),
    FeatureDefinition(
        name="experience_consistency",
        display_name="Experience Consistency",
        category=FeatureCategory.INTEGRITY,
        source_section="profile + career_history",
        source_field="years_of_experience vs sum(duration_months)",
        feature_type=FeatureType.BOOLEAN,
        normalization=NormalizationMethod.BOOLEAN_CAST,
        direction=Direction.HIGHER_BETTER,
        description="Profile's stated years_of_experience is consistent with sum of career history durations.",
        weight_hint=1.5,
        normalization_params={"tolerance_years": 3, "penalty_if_failing": 8},
    ),
    FeatureDefinition(
        name="education_timeline_valid",
        display_name="Education Timeline Consistency",
        category=FeatureCategory.INTEGRITY,
        source_section="education",
        source_field="start_year + end_year",
        feature_type=FeatureType.BOOLEAN,
        normalization=NormalizationMethod.BOOLEAN_CAST,
        direction=Direction.HIGHER_BETTER,
        description="Education dates are valid (start < end, not in the future, reasonable duration).",
        weight_hint=0.8,
        normalization_params={"penalty_if_failing": 5},
    ),
    FeatureDefinition(
        name="no_career_gaps",
        display_name="Career Gap Score",
        category=FeatureCategory.INTEGRITY,
        source_section="career_history",
        source_field="start_date + end_date",
        feature_type=FeatureType.SCORE,
        normalization=NormalizationMethod.NONE,
        direction=Direction.HIGHER_BETTER,
        description="Penalizes unexplained employment gaps > 12 months.",
        weight_hint=0.8,
        normalization_params={"gap_threshold_days": 365, "penalty_per_gap": 5},
    ),
    FeatureDefinition(
        name="skill_experience_consistency",
        display_name="Skill–Experience Consistency",
        category=FeatureCategory.INTEGRITY,
        source_section="skills + career_history",
        source_field="duration_months vs total career",
        feature_type=FeatureType.BOOLEAN,
        normalization=NormalizationMethod.BOOLEAN_CAST,
        direction=Direction.HIGHER_BETTER,
        description="Skill duration_months are not larger than total career duration.",
        weight_hint=0.8,
        normalization_params={"tolerance_months": 12, "penalty_if_failing": 3},
    ),
    FeatureDefinition(
        name="no_future_dates",
        display_name="Invalid Dates",
        category=FeatureCategory.INTEGRITY,
        source_section="career_history + education",
        source_field="start_date + end_date + end_year",
        feature_type=FeatureType.BOOLEAN,
        normalization=NormalizationMethod.BOOLEAN_CAST,
        direction=Direction.HIGHER_BETTER,
        description="No future or impossible dates in career or education records.",
        weight_hint=1.5,
        normalization_params={"penalty_if_failing": 8},
    ),
    FeatureDefinition(
        name="no_excessive_expert_skills",
        display_name="Unrealistic Skill Claims",
        category=FeatureCategory.INTEGRITY,
        source_section="skills",
        source_field="proficiency == 'expert'",
        feature_type=FeatureType.BOOLEAN,
        normalization=NormalizationMethod.BOOLEAN_CAST,
        direction=Direction.HIGHER_BETTER,
        description="Candidate does not claim expert proficiency in an unrealistic number of skills (>10).",
        weight_hint=0.8,
        normalization_params={"max_expert_skills": 10, "penalty_if_failing": 5},
    ),
]


# ══════════════════════════════════════════════════════════════════════════════
# 10. DYNAMIC JOB FEATURES
# ══════════════════════════════════════════════════════════════════════════════

DYNAMIC_JD_FEATURES = [
    FeatureDefinition(
        name="jd_title_match",
        display_name="Title Match",
        category=FeatureCategory.DYNAMIC_JD,
        source_section="profile",
        source_field="current_title",
        feature_type=FeatureType.SIMILARITY,
        normalization=NormalizationMethod.NONE,
        direction=Direction.HIGHER_BETTER,
        description="Semantic similarity between candidate's current title and JD job title.",
        weight_hint=2.0,
    ),
    FeatureDefinition(
        name="jd_required_skill_match",
        display_name="Required Skill Match",
        category=FeatureCategory.DYNAMIC_JD,
        source_section="skills + career_history",
        source_field="name + description",
        feature_type=FeatureType.RATIO,
        normalization=NormalizationMethod.NONE,
        direction=Direction.HIGHER_BETTER,
        description="Coverage ratio of JD mandatory skills by candidate.",
        weight_hint=3.0,
        is_required=True,
    ),
    FeatureDefinition(
        name="jd_preferred_skill_match",
        display_name="Preferred Skill Match",
        category=FeatureCategory.DYNAMIC_JD,
        source_section="skills + career_history",
        source_field="name + description",
        feature_type=FeatureType.RATIO,
        normalization=NormalizationMethod.NONE,
        direction=Direction.HIGHER_BETTER,
        description="Coverage ratio of JD nice-to-have skills by candidate.",
        weight_hint=1.5,
    ),
    FeatureDefinition(
        name="jd_experience_match",
        display_name="Experience Match",
        category=FeatureCategory.DYNAMIC_JD,
        source_section="profile",
        source_field="years_of_experience",
        feature_type=FeatureType.SCORE,
        normalization=NormalizationMethod.GAUSSIAN,
        direction=Direction.RANGE_IDEAL,
        description="Gaussian-scored match between candidate experience and JD requirement.",
        ideal_range=(5, 9),
        weight_hint=1.8,
    ),
    FeatureDefinition(
        name="jd_industry_match",
        display_name="Industry Match",
        category=FeatureCategory.DYNAMIC_JD,
        source_section="career_history + profile",
        source_field="industry",
        feature_type=FeatureType.BOOLEAN,
        normalization=NormalizationMethod.BOOLEAN_CAST,
        direction=Direction.HIGHER_BETTER,
        description="Whether the candidate's industry background aligns with the JD's industry.",
        weight_hint=0.8,
    ),
    FeatureDefinition(
        name="jd_education_match",
        display_name="Education Match",
        category=FeatureCategory.DYNAMIC_JD,
        source_section="education",
        source_field="degree",
        feature_type=FeatureType.BOOLEAN,
        normalization=NormalizationMethod.BOOLEAN_CAST,
        direction=Direction.HIGHER_BETTER,
        description="Whether candidate meets the JD's minimum education requirement.",
        weight_hint=0.7,
    ),
    FeatureDefinition(
        name="jd_certification_match",
        display_name="Certification Match",
        category=FeatureCategory.DYNAMIC_JD,
        source_section="certifications",
        source_field="name",
        feature_type=FeatureType.SCORE,
        normalization=NormalizationMethod.CLIP_RATIO,
        direction=Direction.HIGHER_BETTER,
        description="Number of JD-specified certifications held by the candidate.",
        normalization_params={"max_val": 3},
        weight_hint=0.8,
    ),
    FeatureDefinition(
        name="jd_location_match",
        display_name="Location Match",
        category=FeatureCategory.DYNAMIC_JD,
        source_section="profile + redrob_signals",
        source_field="location + willing_to_relocate",
        feature_type=FeatureType.SCORE,
        normalization=NormalizationMethod.ORDINAL_MAP,
        direction=Direction.HIGHER_BETTER,
        description="Location compatibility: preferred city / acceptable city / relocation / mismatch.",
        weight_hint=1.0,
    ),
    FeatureDefinition(
        name="jd_work_mode_match",
        display_name="Work Mode Match",
        category=FeatureCategory.DYNAMIC_JD,
        source_section="redrob_signals",
        source_field="preferred_work_mode",
        feature_type=FeatureType.BOOLEAN,
        normalization=NormalizationMethod.BOOLEAN_CAST,
        direction=Direction.HIGHER_BETTER,
        description="Whether candidate's preferred work mode matches JD (hybrid/onsite/flexible).",
        weight_hint=0.6,
    ),
    FeatureDefinition(
        name="jd_salary_match",
        display_name="Salary Match",
        category=FeatureCategory.DYNAMIC_JD,
        source_section="redrob_signals",
        source_field="expected_salary_range_inr_lpa",
        feature_type=FeatureType.BOOLEAN,
        normalization=NormalizationMethod.BOOLEAN_CAST,
        direction=Direction.HIGHER_BETTER,
        description="Whether candidate's expected salary is within the JD's compensation range.",
        weight_hint=1.0,
    ),
    FeatureDefinition(
        name="jd_company_size_match",
        display_name="Company Size Match",
        category=FeatureCategory.DYNAMIC_JD,
        source_section="career_history",
        source_field="company_size",
        feature_type=FeatureType.SCORE,
        normalization=NormalizationMethod.ORDINAL_MAP,
        direction=Direction.HIGHER_BETTER,
        description="Whether candidate has experience at companies of similar size to the hiring company.",
        weight_hint=0.5,
    ),
    FeatureDefinition(
        name="jd_domain_match",
        display_name="Domain Match",
        category=FeatureCategory.DYNAMIC_JD,
        source_section="career_history + skills",
        source_field="description + name",
        feature_type=FeatureType.SCORE,
        normalization=NormalizationMethod.NONE,
        direction=Direction.HIGHER_BETTER,
        description="Depth of experience in the JD's specific domain (AI search/ranking/retrieval).",
        weight_hint=2.0,
        notes="Highest-weight dynamic feature for this JD. Counts domain-specific concept hits.",
    ),
]


# ══════════════════════════════════════════════════════════════════════════════
# MASTER FEATURE REGISTRY
# ══════════════════════════════════════════════════════════════════════════════

ALL_FEATURES: list[FeatureDefinition] = (
    PROFILE_FEATURES +
    CAREER_FEATURES +
    SKILL_FEATURES +
    EDUCATION_FEATURES +
    CERTIFICATION_FEATURES +
    LANGUAGE_FEATURES +
    BEHAVIORAL_FEATURES +
    SEMANTIC_FEATURES +
    INTEGRITY_FEATURES +
    DYNAMIC_JD_FEATURES
)

# Name → FeatureDefinition lookup
FEATURE_MAP: dict[str, FeatureDefinition] = {f.name: f for f in ALL_FEATURES}


# ══════════════════════════════════════════════════════════════════════════════
# QUERY HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def get_features_by_category(category: str) -> list[FeatureDefinition]:
    """Return all features belonging to a given category name."""
    return [f for f in ALL_FEATURES if f.category.value == category]


def get_required_features() -> list[FeatureDefinition]:
    """Return features marked is_required=True."""
    return [f for f in ALL_FEATURES if f.is_required]


def get_features_by_source(section: str) -> list[FeatureDefinition]:
    """Return features that read from a given JSON section."""
    return [f for f in ALL_FEATURES if section in f.source_section]


def get_feature(name: str) -> FeatureDefinition:
    """Look up a feature by name. Raises KeyError if not found."""
    if name not in FEATURE_MAP:
        raise KeyError(f"Feature '{name}' not found. Available: {list(FEATURE_MAP.keys())}")
    return FEATURE_MAP[name]


def print_feature_summary():
    """Print a human-readable summary of all features by category."""
    from collections import Counter
    counts = Counter(f.category.value for f in ALL_FEATURES)
    print(f"\n{'─'*60}")
    print(f"  FEATURE DICTIONARY SUMMARY  ({len(ALL_FEATURES)} total features)")
    print(f"{'─'*60}")
    for cat, n in sorted(counts.items()):
        feats = get_features_by_category(cat)
        print(f"  {cat:<20} {n:>3} features")
        for feat in feats:
            req_flag = " [REQUIRED]" if feat.is_required else ""
            print(f"    • {feat.name:<40} {feat.feature_type.value:<12} {feat.direction.value}{req_flag}")
    print(f"{'─'*60}\n")


# ══════════════════════════════════════════════════════════════════════════════
# CLI — print summary
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print_feature_summary()
    print(f"Total features: {len(ALL_FEATURES)}")
    print(f"Required features: {len(get_required_features())}")
    print(f"\nSample feature lookup:")
    f = get_feature("career_description_similarity")
    print(f"  Name:        {f.name}")
    print(f"  Category:    {f.category.value}")
    print(f"  Source:      {f.source_section} → {f.source_field}")
    print(f"  Type:        {f.feature_type.value}")
    print(f"  Norm:        {f.normalization.value}")
    print(f"  Direction:   {f.direction.value}")
    print(f"  Weight hint: {f.weight_hint}")
    print(f"  Description: {f.description}")
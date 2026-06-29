# Candidate Schema

Candidate
│
├── candidate_id : str
│
├── profile
│   ├── full_name : str
│   ├── headline : str
│   ├── location : str
│   ├── total_experience : float
│   ├── current_company : str
│   ├── current_designation : str
│
├── career_history : List[Job]
│   ├── company : str
│   ├── designation : str
│   ├── start_date : str
│   ├── end_date : str
│   ├── duration_months : int
│   ├── responsibilities : str
│   └── technologies : List[str]
│
├── education : List[Education]
│   ├── degree : str
│   ├── specialization : str
│   ├── institute : str
│   └── graduation_year : int
│
├── skills : List[str]
├── certifications : List[str]
├── projects : List[str]
├── languages : List[str]
│
├── redrob_signals
│   ├── profile_score : float
│   ├── profile_completeness : float
│   ├── activity_score : float
│   └── availability : str
│
└── metadata
    ├── source
    ├── last_updated
    └── parser_version
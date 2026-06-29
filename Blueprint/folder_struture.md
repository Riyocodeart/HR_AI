project/

│
├── data/
│   ├── candidates.jsonl
│   ├── train.csv
│   └── sample_submission.csv
│
├── schemas/
│   └── candidate_schema.py
│
├── parser/
│   ├── jsonl_reader.py
│   ├── validator.py
│   ├── candidate_parser.py
│   ├── profile_parser.py
│   ├── career_parser.py
│   ├── education_parser.py
│   ├── skills_parser.py
│   └── signals_parser.py
│
├── features/
│   ├── experience_features.py
│   ├── skills_features.py
│   ├── education_features.py
│   ├── title_features.py
│   └── embedding_features.py
│
├── ranking/
│   ├── model.py
│   ├── inference.py
│   └── scorer.py
│
├── utils/
│   ├── constants.py
│   ├── logger.py
│   └── helpers.py
│
└── app.py


After parser was introduced ----- 

your-project/
├── app.py                    ← REPLACED
├── jd_schema.json            ← (your existing file — keep it here so the parser finds it)
├── parser/                   ← NEW (the offline JD parser module)
│   ├── __init__.py
│   ├── cleaner.py
│   ├── jd_parser.py
│   ├── json_validator.py
│   ├── models.py
│   ├── normalizer.py
│   ├── prompt_builder.py
│   ├── utils.py
│   ├── requirements.txt
│   └── README.md
└── ui/                       ← NEW (small UI glue, kept out of app.py)
    ├── jd_parser_animation.py
    └── linkedin_tab.py
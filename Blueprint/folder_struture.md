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
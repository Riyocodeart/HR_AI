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
              ┌──────────────────┴──────────────────┐
              │                                     │
        Missing Field?                         Valid Record
              │                                     │
              ▼                                     ▼
        Error Logger                        Candidate Parser
                                                    │
         ┌──────────────────────────────────────────┼──────────────────────────────┐
         │                                          │                              │
         ▼                                          ▼                              ▼
   Profile Parser                           Career Parser               Education Parser
         │                                          │                             │
         └───────────────────────┬──────────────────┴─────────────────────────────┘
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
                                 │
                                 ▼
                       Ranking Model Input
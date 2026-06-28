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

                       

                       WORKFLOW
START

   │
   ▼

Open candidates.jsonl

   │
   ▼

Read one line

   │
   ▼

json.loads(line)

   │
   ▼

Validate JSON

   │
   ├──────── Invalid
   │            │
   │            ▼
   │      Log Error
   │
   ▼

Extract Profile

   │
   ▼

Extract Career History

   │
   ▼

Extract Education

   │
   ▼

Extract Skills

   │
   ▼

Extract Redrob Signals

   │
   ▼

Create Candidate Object

   │
   ▼

Return Candidate

   │
   ▼

Repeat Until EOF

   │
   ▼

END
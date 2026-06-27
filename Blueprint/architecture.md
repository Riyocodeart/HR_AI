AI Recruiter Ranking System

Goal:
Rank the top 100 candidates for any uploaded JD.

Pipeline

Job Description
        │
        ▼
JD Parser (Local LLM) 
        │
        ▼
Structured JD
        │
        ▼
Candidate Parser
        │
        ▼
Candidate Validation
        │
        ▼
Feature Engineering
        │
        ▼
Semantic Retrieval (FAISS)
        │
        ▼
Ranking Engine
        │
        ▼
Reasoning Generator
        │
        ▼
Submission CSV
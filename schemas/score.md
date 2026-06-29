# Candidate Scoring Strategy

## Objective

The goal of the scoring engine is to rank candidates based on their overall suitability for a given Job Description (JD). Instead of relying only on keyword matching, the system combines semantic understanding, structured profile information, behavioral signals, and profile quality to produce a final ranking score.

The scoring pipeline is fully offline and deterministic.

---

# Overall Pipeline

Job Description
        │
        ▼
JD Parser
        │
        ▼
Structured Requirements
        │
        ▼
Candidate Feature Extraction
        │
        ▼
Semantic Similarity
        │
        ▼
Behavior & Quality Scoring
        │
        ▼
Weighted Score Calculation
        │
        ▼
Integrity Penalties
        │
        ▼
Final Candidate Score

---

# Candidate Score Formula

Final Score

=

Semantic Score
+

Skill Score
+

Career Score
+

Experience Score
+

Behavior Score
+

Education Score
+

Certification Score
+

Language Score
+

Integrity Score

Each component is normalized before combining.

---

# Scoring Categories

## 1. Semantic Score

Purpose

Measure contextual similarity between the Job Description and the candidate profile.

Possible Inputs

- Headline similarity
- Summary similarity
- Career description similarity
- Skills similarity

Produces

Semantic Score

---

## 2. Skill Score

Purpose

Measure technical fit.

Evaluates

- Required skills matched
- Preferred skills matched
- Skill proficiency
- Skill duration
- Endorsements
- AI/ML skills
- Backend skills
- Cloud skills

Produces

Skill Score

---

## 3. Career Score

Purpose

Measure professional relevance.

Evaluates

- Relevant experience
- Career progression
- Leadership
- Industry relevance
- Current role relevance
- Company experience
- Job stability

Produces

Career Score

---

## 4. Experience Score

Purpose

Compare candidate experience against JD requirements.

Evaluates

- Total years
- Relevant years
- Seniority level
- Recent experience

Produces

Experience Score

---

## 5. Education Score

Purpose

Evaluate educational relevance.

Evaluates

- Degree
- Field
- Institute Tier
- Academic score

Produces

Education Score

---

## 6. Certification Score

Purpose

Reward relevant certifications.

Evaluates

- Certification relevance
- Certification count
- Certification recency

Produces

Certification Score

---

## 7. Language Score

Purpose

Evaluate language compatibility.

Evaluates

- Required languages
- Professional proficiency

Produces

Language Score

---

## 8. Behavioral Score

Purpose

Estimate recruiter friendliness and candidate engagement.

Evaluates

Recruiter Interest

- Profile completeness
- Search appearance
- Saved by recruiters
- Profile views

Candidate Availability

- Open to work
- Notice period
- Relocation
- Work mode

Responsiveness

- Recruiter response rate
- Response time

Platform Trust

- Verified email
- Verified phone
- LinkedIn connected

Interview Signals

- Interview completion
- Offer acceptance

Technical Activity

- GitHub score
- Skill assessment scores

Platform Activity

- Last active
- Applications submitted
- Connection count

Produces

Behavior Score

---

## 9. Integrity Score

Purpose

Penalize inconsistent or suspicious profiles.

Checks include

- Invalid dates
- Impossible timelines
- Experience mismatch
- Duplicate skills
- Duplicate jobs
- Missing information
- Career gaps
- Education inconsistency
- Unrealistic skill claims

Produces

Integrity Score

---

# Dynamic Weighting

The ranking engine should not use fixed weights for every job.

Instead, weights are adjusted depending on the parsed Job Description.

Example

Technical AI Engineer

Higher importance

- Skills
- Semantic similarity
- Experience

Lower importance

- Education
- Languages

--------------------------------------------

Engineering Manager

Higher importance

- Leadership
- Career progression
- Team management

Lower importance

- Individual technical skills

--------------------------------------------

AI Product Manager

Higher importance

- Product ownership
- Communication
- AI exposure
- Business understanding

Lower importance

- Deep technical implementation

---

# Score Normalization

Every feature should be normalized before scoring.

Examples

Boolean Features

No = 0

Yes = 1

--------------------------------

Years of Experience

Normalize against JD requirement.

--------------------------------

Skill Proficiency

Beginner

Intermediate

Advanced

Expert

Mapped into numerical values.

--------------------------------

Behavior Scores

Scaled between 0 and 1.

---

# Candidate Ranking

The final ranking process

1. Parse Job Description
2. Generate structured requirements
3. Extract candidate features
4. Compute semantic similarity
5. Calculate category scores
6. Apply dynamic weights
7. Apply integrity penalties
8. Compute Final Score
9. Sort candidates
10. Select Top 100

---

# Reasoning Generation

Each ranked candidate should include a concise explanation generated from computed features.

Example

"Backend Engineer with 6.9 years of experience. Strong semantic match on data engineering, Spark, SQL and Airflow. High recruiter responsiveness and profile completeness. Minor penalty for limited cloud experience."

Reasoning should only use computed feature values and should not introduce unsupported information.

---

# Future Improvements

Potential enhancements include

- Learning feature weights from recruiter feedback
- Better skill synonym detection
- Company reputation scoring
- Industry trend adjustment
- Salary market benchmarking
- Temporal weighting of recent experience
- Multi-stage reranking
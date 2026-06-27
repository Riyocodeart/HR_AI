# Feature Engineering Plan

## Purpose

This document defines all candidate features that will be extracted and used by the ranking engine. Features are grouped into logical categories and later converted into numerical scores for candidate ranking.

---

# 1. Profile Features

Source: `profile`

| Feature                    | Description                                                     |
| -------------------------- | --------------------------------------------------------------- |
| Headline Match             | Semantic similarity between candidate headline and JD title     |
| Summary Match              | Semantic similarity between profile summary and JD              |
| Current Title Match        | Match between current designation and target role               |
| Current Industry Match     | Match between candidate industry and JD industry                |
| Current Company Size Match | Match between company size and preferred company size           |
| Location Match             | Match between candidate location and JD location                |
| Country Match              | Match between candidate country and job country                 |
| Experience Match           | Difference between candidate experience and required experience |

---

# 2. Career Features

Source: `career_history`

| Feature                       | Description                                      |
| ----------------------------- | ------------------------------------------------ |
| Relevant Experience           | Years spent in relevant roles                    |
| Current Role Relevance        | Relevance of current designation                 |
| Career Progression            | Growth from junior to senior positions           |
| Leadership Experience         | Team management or leadership responsibilities   |
| Industry Experience           | Experience in relevant industries                |
| Company Diversity             | Number and variety of employers                  |
| Company Size Experience       | Experience working in similar company sizes      |
| Average Job Tenure            | Average duration per company                     |
| Career Stability              | Job hopping vs stable employment                 |
| Project Relevance             | Relevance of work responsibilities to JD         |
| Recent Experience Weight      | More weight to recent experience                 |
| Career Description Similarity | Semantic similarity of work descriptions with JD |

---

# 3. Skill Features

Source: `skills`

| Feature                  | Description                           |
| ------------------------ | ------------------------------------- |
| Required Skills Matched  | Number of mandatory skills matched    |
| Preferred Skills Matched | Number of optional skills matched     |
| Skill Coverage           | Percentage of required skills covered |
| Skill Proficiency Score  | Beginner → Expert weighted score      |
| Skill Duration Score     | Experience duration for each skill    |
| Skill Endorsement Score  | Total endorsements received           |
| Expert Skill Count       | Number of expert-level skills         |
| Advanced Skill Count     | Number of advanced-level skills       |
| AI Skill Count           | Count of AI/ML related skills         |
| Backend Skill Count      | Count of backend engineering skills   |
| Cloud Skill Count        | Count of cloud platform skills        |
| Database Skill Count     | Count of SQL/NoSQL/database skills    |

---

# 4. Education Features

Source: `education`

| Feature              | Description                     |
| -------------------- | ------------------------------- |
| Highest Degree       | Bachelor's / Master's / PhD     |
| Degree Match         | Degree relevance to JD          |
| Field Match          | Field of study relevance        |
| Institution Tier     | Tier 1–4 score                  |
| Academic Score       | GPA / Percentage (if available) |
| Graduation Recency   | Years since graduation          |
| Academic Consistency | Valid academic timeline         |

---

# 5. Certification Features

Source: `certifications`

| Feature                 | Description                          |
| ----------------------- | ------------------------------------ |
| Certification Count     | Total certifications                 |
| Relevant Certifications | Certifications relevant to JD        |
| Recent Certifications   | Newer certifications weighted higher |
| Premium Certifications  | Industry-recognized certifications   |

---

# 6. Language Features

Source: `languages`

| Feature                     | Description                            |
| --------------------------- | -------------------------------------- |
| Required Language Match     | Match with JD language requirement     |
| Professional Language Count | Number of professional-level languages |
| Native Language Count       | Number of native languages             |

---

# 7. Redrob Behavioral Signals

Source: `redrob_signals`

## Recruiter Interest

* Profile Completeness Score
* Profile Views (30 Days)
* Search Appearance (30 Days)
* Saved by Recruiters (30 Days)

## Candidate Availability

* Open to Work
* Notice Period
* Preferred Work Mode
* Willing to Relocate

## Recruiter Responsiveness

* Recruiter Response Rate
* Average Response Time

## Platform Trust

* Verified Email
* Verified Phone
* LinkedIn Connected

## Interview Performance

* Interview Completion Rate
* Offer Acceptance Rate

## Technical Activity

* GitHub Activity Score
* Skill Assessment Scores

## Platform Engagement

* Applications Submitted
* Connection Count
* Account Age
* Last Active Date

## Compensation

* Expected Minimum Salary
* Expected Maximum Salary

---

# 8. Semantic Features

Generated after JD parsing.

| Feature                 | Description                   |
| ----------------------- | ----------------------------- |
| JD Embedding Similarity | Overall semantic similarity   |
| Headline Similarity     | Headline vs JD                |
| Summary Similarity      | Summary vs JD                 |
| Career Similarity       | Career descriptions vs JD     |
| Skill Similarity        | Skill embeddings vs JD        |
| Education Similarity    | Education relevance           |
| Industry Similarity     | Industry embedding similarity |

---

# 9. Data Quality & Integrity Features

Derived from candidate profile.

| Feature                        | Description                          |
| ------------------------------ | ------------------------------------ |
| Missing Headline               | Missing profile headline             |
| Missing Summary                | Missing summary                      |
| Missing Skills                 | Empty skills list                    |
| Missing Career Description     | Empty work descriptions              |
| Duplicate Skills               | Duplicate skill entries              |
| Duplicate Companies            | Duplicate employment records         |
| Career Timeline Consistency    | Chronological validation             |
| Experience Consistency         | Profile experience vs career history |
| Education Timeline Consistency | Valid education years                |
| Career Gap Score               | Long unexplained employment gaps     |
| Skill–Experience Consistency   | Skill duration vs career duration    |
| Role–Summary Consistency       | Current role aligns with summary     |
| Invalid Dates                  | Future or impossible dates           |
| Incomplete Profile Penalty     | Missing critical information         |

---

# 10. Dynamic Job Features

Generated after parsing the uploaded Job Description.

| Feature               | Description                     |
| --------------------- | ------------------------------- |
| Title Match           | Job title similarity            |
| Required Skill Match  | Mandatory skill coverage        |
| Preferred Skill Match | Nice-to-have skill coverage     |
| Experience Match      | Experience difference           |
| Industry Match        | Industry alignment              |
| Education Match       | Degree requirement match        |
| Certification Match   | Required certifications         |
| Location Match        | Work location compatibility     |
| Work Mode Match       | Remote/Hybrid/Onsite preference |
| Salary Match          | Expected salary within budget   |
| Company Size Match    | Preferred company size          |
| Domain Match          | Domain-specific experience      |

---

# Feature Groups Used for Final Ranking

| Category                   | Purpose                                          |
| -------------------------- | ------------------------------------------------ |
| Semantic Features          | Understand contextual fit beyond keywords        |
| Skills                     | Evaluate technical capability                    |
| Career History             | Measure role relevance and growth                |
| Experience                 | Match required experience                        |
| Education & Certifications | Validate academic and professional background    |
| Behavioral Signals         | Estimate recruiter responsiveness and engagement |
| Data Integrity             | Penalize inconsistent or low-quality profiles    |
| Dynamic JD Features        | Adapt ranking to every uploaded job description  |

---

**Note:** Feature weights will not be fixed. The ranking engine will dynamically adjust category importance based on the parsed Job Description. For example, technical roles will prioritize skills and semantic similarity, while leadership roles may place greater emphasis on career progression and management experience.

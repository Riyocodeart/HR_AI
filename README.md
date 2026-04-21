# HR_AI
# 🎯 AI Recruiter — Intelligent Candidate Screening

A full-stack AI-powered recruiter tool built with Streamlit + OpenAI.

## Pipeline
1. **Upload JD** (PDF or paste text)
2. **AI Extraction** — GPT-4o-mini extracts Role, Skills, Location, Experience
3. **Upload Candidates CSV** (30–50 rows)
4. **Filter & Score** — Skill (40pts) + Role (30pts) + Experience (30pts)
5. **Export** — Color-coded Excel + CSV

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
npm install linkedin-profile-scraper
node scrape_linkedin.js
```

## CSV Format
Your candidates CSV should have these columns (names are auto-detected):
| name | role | location | experience | skills |
|------|------|----------|------------|--------|
| Priya Sharma | Data Scientist | Mumbai | 4 | Python ML SQL |

A sample file `sample_candidates.csv` is included with 30 candidates.

## API Key
Enter your OpenAI API key in the sidebar. The app uses `gpt-4o-mini` for cost efficiency.

## Scoring Logic
```
total_score = skill_score (0-40) + role_score (0-30) + experience_score (0-30)
```
- **Skill Score**: % of required skills found in candidate profile × 40
- **Role Score**: keyword overlap between JD role and candidate role × 30  
- **Experience Score**: 30 if within range, reduced for over/under-qualified
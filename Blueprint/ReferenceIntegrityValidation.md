This module compares candidate data against trusted offline reference datasets.

Checks could include:
| Check                                   | Needs External Data? |
| --------------------------------------- | -------------------- |
| Company founded before employment start | ✅ Yes                |
| University exists                       | ✅ Yes                |
| City belongs to country                 | ✅ Yes                |
| Company name alias normalization        | ✅ Yes                |
| Degree is valid                         | Optional             |
| Job title taxonomy                      | Optional             |
| Skill taxonomy                          | Optional             |

Since the rules prohibit external API calls, you cannot query the internet during execution.
However, you can include offline reference files in your project, for example:

data/
│
├── company_reference.csv
├── university_reference.csv
├── city_country_mapping.csv
├── job_title_mapping.json
├── skill_taxonomy.json


Candidate JSON
       │
       ▼
Company = ABC AI
       │
       ▼
company_reference.csv
       │
       ▼
Founded = 2023
       │
       ▼
Employment Start = 2017
       │
       ▼
Validation Failure


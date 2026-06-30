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

New struture 
# Refactor Map · `app.py` → modular architecture

> Following the rules from your prompt: nothing is rewritten, only relocated. The
> app stays runnable after every wave.

## Wave 1 — Foundation + UI (this delivery)

These move out of `app.py` because they are pure presentation / config, with
zero coupling to business logic. Safe to extract first.

| Current location in `app.py`     | Lines (~)   | Moves to                  | Reason                                 |
| -------------------------------- | ----------- | ------------------------- | -------------------------------------- |
| `<style>` CSS block              | 88–315      | `ui/styles.py`            | Pure CSS — no Python coupling          |
| `_score_badge()`                 | 425         | `ui/components.py`        | Reusable view helper                   |
| `_gemini_keys()`                 | 408–423     | `core/helpers.py`         | Config reader, used everywhere         |
| `tabs_cfg`, sidebar render block | 510–620     | `ui/sidebar.py`           | Pure UI                                |
| `defaults` session-state dict    | 478–491     | `core/session.py`         | One-shot initializer                   |
| `st.set_page_config(...)`        | 80–85       | `core/config.py`          | Boot-time config                       |
| Model / host / seed constants    | (inline)    | `core/constants.py`       | Shared by parser + UI                  |
| Logger setup (none yet)          | —           | `core/logger.py`          | New file, used by services next wave   |
| Existing typing animation        | (in ui/)    | `ui/animations.py`        | Just re-export — no rewrite            |
| New Overview/Command Center page | —           | `pages/overview.py`       | Matches reference image 1              |

## Wave 2 — Services (next delivery)

These are business logic. They get wrapped so the three engines (Gemini / Qwen /
Regex) all expose the same `.parse(text) -> dict` interface.

| Current location                     | Moves to                    | Public surface              |
| ------------------------------------ | --------------------------- | --------------------------- |
| `_parse_jd_chain()` (app.py ~456)    | `services/jd_service.py`    | `parse_jd(text) -> dict`    |
| `parse_jd_with_ai` (core/parser)     | `services/gemini_service.py`| `GeminiJDClient.parse(...)` |
| `JDParser` (parser/)                 | `services/ollama_service.py`| Thin wrapper around parser/ |
| `parse_jd` regex (core/parser)       | `services/regex_service.py` | Fallback adapter            |
| `score_candidates` (core/scorer)     | `services/scoring_service.py`| keep as-is, just relocate  |
| `generate_*_url` (core/linkedin)     | `services/linkedin_service.py`| keep as-is                |
| `export_excel/csv` (core/exporter)   | `services/export_service.py`| keep as-is                  |
| Gmail integration                    | `services/gmail_service.py` | new module                  |

## Wave 3 — Pages (final delivery)

Each tab becomes its own file with one entry point: `render(state)`.

| Current `elif active_tab == "..."`   | Moves to                    | Notes                       |
| ------------------------------------ | --------------------------- | --------------------------- |
| `"overview"` (NEW)                   | `pages/overview.py`         | Built in Wave 1             |
| `"recruiter"` (lines 656–950)        | `pages/recruiter.py`        | Steps 01–04                 |
| `"linkedin"` (line 970)              | `pages/linkedin.py`         | Already in `ui/linkedin_tab`, just rename |
| `"analytics"` (lines 975–1080)       | `pages/analytics.py`        |                             |
| `"chatbot"` (lines 1083–1175)        | `pages/chatbot.py`          | Match reference image 3     |
| `"email"` (lines 1180–1280)          | `pages/email.py`            |                             |

After Wave 3, `app.py` is **~150 lines** doing only:
1. `core.config.setup()`
2. `core.session.init()`
3. `ui.styles.apply()`
4. `ui.sidebar.render()` → returns active tab
5. Dispatch to `pages.<tab>.render()`

---

## Dependency graph (post-refactor)

```
                       app.py
                         │
        ┌────────────────┼─────────────────┐
        ▼                ▼                 ▼
      core/            ui/              pages/
        │            (depends on        (depends on
        │             core only)         core + ui + services)
        ▼
   constants/config/session/logger/helpers
        ▲
        │
     services/
   (depends on core only)
        ▲
        │
     parser/  (already standalone)
```

No circular imports. `pages/` is the only layer that touches `services/`. `ui/`
never touches `services/`.

## Migration checklist

- [x] **Wave 1**: ui/styles, ui/sidebar, ui/components, ui/animations, core/*,  pages/overview, slim app.py
- [ ] **Wave 2**: services/* (jd, gemini, ollama, regex, scoring, linkedin, export, gmail)
- [ ] **Wave 3**: pages/recruiter, pages/linkedin, pages/analytics, pages/chatbot, pages/email

After Wave 1: app drops from **1279 → ~700 lines** and visually matches the reference. Existing pages stay in `app.py` as-is (they keep working) but use the new theme. Wave 2 doesn't change behaviour — it just relocates logic. Wave 3 reduces app.py to a router.


# NexRecruit AI · Final Architecture

> Post-Wave-3 reference. Everything below is the **target state** that
> exists after copying the Wave 3 bundle.

## File tree

```
HR_AI/
│
├── app.py                        ← 58 lines · pure router
├── jd_schema.json                ← your existing schema
├── test_ollama.py                ← integration check (run when changing models)
├── REFACTOR_PLAN.md              ← Wave-by-wave map (Wave 1)
├── FINAL_ARCHITECTURE.md         ← this file (Wave 3)
│
├── core/                         ← config, session, helpers — touched everywhere
│   ├── __init__.py
│   ├── config.py                 ← setup_page() + PROJECT_ROOT / SCHEMA_PATH
│   ├── constants.py              ← Colors, TABS, model names, score bands
│   ├── session.py                ← init() + log_activity() + defaults dict
│   ├── logger.py                 ← re-export of parser.utils.get_logger
│   └── helpers.py                ← gemini_keys, score_band, humanise_count
│
├── parser/                       ← Wave 0 · offline Qwen JD parser
│   ├── __init__.py               ← exposes JDParser, parse_job_description, OllamaError
│   ├── jd_parser.py              ← orchestrator
│   ├── cleaner.py
│   ├── prompt_builder.py
│   ├── json_validator.py
│   ├── normalizer.py
│   ├── models.py                 ← Pydantic JobDescription
│   └── utils.py
│
├── services/                     ← business logic · stable public surface
│   ├── __init__.py
│   ├── jd_service.py             ← THE 3-tier orchestrator: Gemini → Qwen → Regex
│   ├── gemini_service.py         ← wraps core.parser Gemini calls
│   ├── ollama_service.py         ← cached JDParser + is_reachable()/has_model()
│   ├── regex_service.py          ← wraps core.parser regex fallback
│   ├── scoring_service.py        ← re-exports core.scorer
│   ├── linkedin_service.py       ← URLs + build_queries()
│   ├── export_service.py         ← re-exports core.exporter
│   ├── gmail_service.py          ← OAuth + send + 5 email templates
│   ├── analytics_service.py      ← pure-Python KPI / funnel helpers
│   ├── chatbot_service.py        ← Gemini-backed Q&A with JD grounding
│   └── key_rotation.py           ← (your existing file — untouched)
│
├── ui/                           ← presentation primitives · zero biz logic
│   ├── __init__.py
│   ├── styles.py                 ← THE dark theme (one source of truth)
│   ├── sidebar.py                ← left rail · matches reference screenshots
│   ├── components.py             ← metric_card, dash_card, candidate_row, …
│   ├── animations.py             ← canonical import for animation helpers
│   ├── jd_parser_animation.py    ← typing-reveal effect + shape adapters
│   └── linkedin_tab.py           ← LinkedIn tab implementation
│
├── pages/                        ← one file per tab · single render() entry
│   ├── __init__.py
│   ├── overview.py               ← Command Center dashboard (image 1)
│   ├── recruiter.py              ← Steps 01-04 pipeline (Wave 3)
│   ├── linkedin.py               ← thin wrapper around ui.linkedin_tab
│   ├── analytics.py              ← scored-candidate analytics
│   ├── chatbot.py                ← AI Sourcing Chatbot (image 3)
│   └── email.py                  ← outreach automation
│
└── core/  ← your existing files (untouched)
    ├── parser.py                 ← parse_jd_with_ai, parse_jd, …
    ├── scorer.py                 ← score_candidates, detect_columns, …
    ├── linkedin.py               ← generate_linkedin_url, …
    ├── exporter.py               ← export_excel, export_csv
    └── cleaner.py                ← DataCleaner
```

## Layer rules

```
       ┌──────────────────────────────────────────────────────┐
       │                       app.py                         │
       │       (boot · sidebar · dispatch · nothing else)     │
       └────────────────┬─────────────────────────────────────┘
                        │
            ┌───────────┼───────────┐
            ▼           ▼           ▼
        ┌────────┐ ┌────────┐  ┌──────────┐
        │ pages/ │ │  ui/   │  │ services/│
        │        │ │        │  │          │
        │ render │ │ render │  │ compute  │
        │ tab    │ │ comps  │  │ logic    │
        └───┬────┘ └───┬────┘  └────┬─────┘
            │          │            │
            │          ▼            │
            │      ┌──────┐         │
            └─────►│ core/├◄────────┘
                   │      │
                   │ glue │
                   └───┬──┘
                       │
                       ▼
                   ┌────────┐  ┌──────────┐
                   │parser/ │  │ existing │
                   │  (Qwen)│  │ core/*.py│
                   └────────┘  └──────────┘
```

**Allowed imports** (verified — no cycles):

| Layer       | May import from                                  |
| ----------- | ------------------------------------------------ |
| `app.py`    | `core`, `ui`, `pages`                            |
| `pages/`    | `services`, `ui`, `core`                         |
| `services/` | `core`, `parser`, and the user's existing `core/*` |
| `ui/`       | `core` only                                      |
| `core/`     | `parser` only (one-way)                          |

**Forbidden:** anything importing `app.py` (it would create a cycle).
Anything in `ui/` reaching into `services/`. Anything circular.

## Line counts — before vs. after

| File                     | Before  | After  | Change |
| ------------------------ | ------- | ------ | ------ |
| `app.py`                 | 1280    | **58** | **−95.5 %** |
| Largest extracted page   | —       | 336 (`recruiter.py`) | (matches original) |
| Total project (.py)      | ~1280   | ~3200  | +growth from proper docstrings + services layer |

Each new file is < 350 lines. No file does more than one thing.

## How to add a new tab

1. Append `("mytab", "icon", "My Tab")` to `TABS` in `core/constants.py`.
2. Create `pages/mytab.py` with `def render(): ...`.
3. Add one line to `PAGE_DISPATCH` in `app.py`.

Three edits, total. No CSS, no sidebar code, no router wiring.

## How to swap the parser model

Change one line in `core/constants.py`:

```python
QWEN_MODEL = "qwen2.5:3b-instruct"   # was 1.5b
```

`services/ollama_service.py` reads from there. Restart Streamlit and the
new model is used everywhere.

## How to verify everything works

```bash
python test_ollama.py                                  # one-shot integration test
python -c "import ast; ast.parse(open('app.py').read())"  # syntax sanity
streamlit run app.py                                   # actually launch
```
# Project Rules & Development Guidelines
## AI Powered Water Recharge

| | |
|---|---|
| **Document Version** | 1.0 |
| **Companion Documents** | AI_Powered_Water_Recharge_PRD.md, AI_Powered_Water_Recharge_Architecture.md |
| **Applies To** | All code, data, models, and documentation produced for this project — including AI coding assistants (Claude Code, Copilot, etc.) used during development |
| **Status** | Draft for Panel Review |

---

## 1. Purpose of This Document

This document defines the non-negotiable rules and conventions for building AI Powered Water Recharge, so that the project stays consistent, reproducible, explainable, and deliverable within the 12-month academic timeline defined in the PRD. These rules apply equally whether code is written by hand or generated with the help of an AI coding assistant — if an AI assistant is used, it must be pointed at this file (and the PRD/Architecture docs) before generating code, so its output stays consistent with the rest of the project.

**Guiding rule above all others:** if a decision in this document ever conflicts with the PRD or Architecture document, the PRD/Architecture documents win — this file governs *how* we build, not *what* we build.

---

## 2. Core Non-Negotiable Rules (Read First)

1. **No hardware. No IoT. No exceptions.** Every data need is met by satellite platforms or existing government sensor networks (Section 10 of the PRD). Do not introduce any physical sensor, device driver, or hardware dependency at any point in development.
2. **No model ships without an explanation.** Any code path that returns a Module 1 (Recommendation) or Module 4 (Risk) prediction to the API layer MUST also return a SHAP/LIME-derived explanation. A prediction without an explanation is treated as a bug, not a missing feature.
3. **No paid infrastructure.** Every service, library, and hosting choice must operate within a documented free tier. If a free tier is at risk of being exceeded, the fix is to change the usage pattern (see Section 6), never to introduce a paid plan.
4. **No secrets in source control.** API keys, service account credentials, and database passwords are never hardcoded or committed — see Section 8.
5. **No silent failures in data pipelines.** Every ingestion script must log success/failure to the `data_refresh_log` table (per Architecture doc Section 7) — a failed fetch must be visible, not swallowed.
6. **No unlabelled ground truth.** Any dataset used to train or validate a model must come from an identifiable, documented source (CGWB/India-WRIS, Bhuvan, etc.) — no synthetic or scraped-without-attribution data in the training set for reported results.

---

## 3. Coding Standards

### 3.1 Python (Backend, ML, Ingestion)
- Follow **PEP 8** for all Python code; enforce with `black` (formatter) and `flake8` or `ruff` (linter) before every commit.
- Use **type hints** on all function signatures — this matters especially in the ML modules, where a mistyped tensor/array shape is a common source of silent bugs.
- Use **Pydantic models** for all FastAPI request/response schemas — never accept or return raw untyped dictionaries at the API boundary.
- Every function longer than ~30 lines should be split, unless it is a single cohesive model-training loop.
- Docstrings (Google-style) are required on every public function/class — one-line summary minimum, full Args/Returns block for anything ML-related.
- Naming: `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants.

### 3.2 JavaScript/React (Frontend)
- Use **functional components with Hooks** — no class components.
- Use **ESLint + Prettier** with a shared config file committed to the repo, so formatting is never a matter of personal preference.
- Component naming: `PascalCase` for component files (`SiteDetailPanel.jsx`), `camelCase` for functions/variables.
- No inline styles for anything beyond a one-off layout tweak — use a consistent styling approach (CSS modules or Tailwind, pick one and stay consistent project-wide).

### 3.3 SQL / Database
- All schema changes go through migration files (e.g., Alembic for SQLAlchemy) — never edit the production schema by hand.
- Table and column names: `snake_case`, plural table names (`sites`, `well_readings`), matching the Architecture document's ER diagram exactly. If a field is added that isn't in the ER diagram, update the Architecture doc in the same pull request.

---

## 4. Git & Version Control Rules

| Rule | Detail |
|---|---|
| Branching | `main` is always deployable. All work happens on `feature/<short-description>` or `fix/<short-description>` branches. |
| Commit messages | Follow Conventional Commits format: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:` prefix + short imperative summary. Example: `feat: add SHAP explanation endpoint for site recommendations` |
| Pull requests | Every change to `main` goes through a PR, even in a solo-developer project — this creates a reviewable history for your panel and for your own future reference. |
| Commit size | Prefer small, focused commits over large multi-feature commits — makes it possible to trace *when* a specific model choice or bug was introduced. |
| Notebooks | Jupyter notebooks used for experimentation are committed to `notebooks/` but are **never** the source of production code — working logic must be extracted into `backend/app/ml/` as proper Python modules before being used by the API. |
| `.gitignore` | Must exclude: `.env`, `*.pyc`, `__pycache__/`, `node_modules/`, trained model binaries above a reasonable size (use Git LFS or external storage instead), and any downloaded raw satellite/well data dumps. |

---

## 5. Machine Learning Development Rules

1. **Spatial train/test split, never random split.** Random splitting on geospatial data leaks information between neighboring points. Split by region/district instead, per the PRD's Section 12 requirement.
2. **Every model must be reproducible.** Set and document random seeds; log the exact training data snapshot (date range, region, source version) alongside the trained model artifact.
3. **Baseline before complexity.** Before shipping XGBoost/LSTM as the "final" model for a module, a simpler baseline (Logistic Regression / plain Random Forest) must be trained and its metric recorded, so improvement is demonstrable — this is also exactly what your panel will ask for.
4. **Explainability is computed at training time, not bolted on later.** When a new model version is trained, SHAP value computation on the validation set is part of the same training script/notebook, not a separate afterthought task.
5. **No metric without a threshold check.** Don't just report AUC/F1/RMSE — compare against the target thresholds defined in PRD Section 15 (Success Metrics) and explicitly state pass/fail.
6. **Model versioning.** Every trained model artifact is saved with a filename convention: `module_name_vX.Y_YYYYMMDD.pkl` (or `.pt` for PyTorch), alongside a small JSON metadata file recording training data range, hyperparameters, and evaluation metrics.
7. **Retraining is a deliberate action, not automatic-by-default in MVP.** Per PRD Section 4, auto-retraining is a stretch goal — until it's explicitly implemented and tested, model updates happen via a manually run, logged script.

---

## 6. Data & Free-Tier Quota Rules

1. **Prototype small, scale deliberately.** All new pipeline logic is tested on a single district before being run on a state or national scale — this is both a compute-quota rule and a debugging-sanity rule.
2. **Cache before you recompute.** Any GEE-derived layer that will be reused (slope, NDVI composite, etc.) must be exported once as a GEE Asset or stored in PostGIS, not recomputed on every script run.
3. **Respect the GEE Contributor Tier budget (1,000 EECU-hours/month).** Before running a new large-scale export, estimate its cost using a small-region test run first. If a task is discovered to be unexpectedly expensive, it must be redesigned (smaller area, seasonal composite instead of daily time series) rather than simply re-run and accepted as a cost.
4. **Poll government portals conservatively.** India-WRIS/WIMS fetch jobs run at most once daily. No script should poll these portals more frequently "just in case" — this is both good etiquette toward a public server and avoids unnecessary risk of being rate-limited or blocked.
5. **Document every data source's access method.** Any new external data source introduced must be added to the Architecture document's Section 10 table (source, purpose, access method, quota constraint) in the same PR that introduces it.

---

## 7. API Design Rules

- All endpoints are versioned under `/api/v1/` — breaking changes get `/api/v2/`, never a silent breaking change to `v1`.
- All responses follow a consistent envelope: `{ "data": ..., "error": null }` on success, `{ "data": null, "error": { "message": ..., "code": ... } }` on failure.
- No endpoint returns a raw model prediction without the corresponding explanation object attached (see Rule 2, Section 2).
- Long-running operations (large-region site recommendation) must be asynchronous (`job_id` + polling), never a blocking request that risks timing out — per Architecture doc Section 5.
- Input validation happens at the Pydantic model level, not deep inside business logic — invalid input should be rejected before it reaches any ML module.

---

## 8. Security & Secrets Management

- All credentials (GEE service account key, NASA Earthdata login, database password) live in a `.env` file that is **never committed** — a `.env.example` with placeholder values is committed instead, documenting what's required.
- In deployed environments, secrets are set via the hosting platform's environment variable settings (Render/GitHub Actions secrets), never hardcoded into Dockerfiles or source.
- No personally identifiable information is ever collected, stored, or logged — this project only processes public geospatial and groundwater data.
- Any script that touches an external API must implement basic error handling for authentication failures (expired token, invalid key) with a clear log message, not a raw stack trace.

---

## 9. Documentation Rules

- Every module (`module1_recommendation/`, `module2_explainability/`, etc.) has its own `README.md` explaining: what it does, its inputs/outputs, and how to run it standalone for testing.
- The root `README.md` must always contain: project one-line description, setup instructions, and links to the PRD, Architecture, and this Rules document — this is the first thing your panel or any new contributor should see.
- Any architectural decision that deviates from the Architecture document must be recorded as a short **Architecture Decision Record (ADR)** in `docs/adr/NNNN-short-title.md`, explaining what changed and why — this protects you from "why did you do it this way?" questions in your defense by giving you a written answer already prepared.

---

## 10. Testing Rules

| Layer | Minimum Testing Requirement |
|---|---|
| ML modules | Unit test that a trained model, given a known fixed input, produces output within an expected range (sanity check, not full accuracy validation) |
| API endpoints | Test that each endpoint returns the correct response shape and status code for both valid and invalid input |
| Data ingestion scripts | Test the change-detection logic (does it correctly skip already-ingested data?) using a mocked/sample response |
| Frontend | At minimum, manual test checklist per feature before merging; automated component tests are a stretch goal, not a hard requirement given the timeline |

---

## 11. Rules for AI Coding Assistants (Claude Code, Copilot, etc.)

If an AI coding assistant is used to help build this project, it must be given this file plus the PRD and Architecture documents as context before generating code, and must follow these additional constraints:

1. **Never introduce a hardware/IoT dependency**, even if asked to "make monitoring more real-time" — real-time monitoring in this project means faster/more frequent *polling of existing data sources*, not new sensors.
2. **Never suggest a paid API or paid tier** as a solution to a quota or rate-limit problem — the correct fix is always a usage-pattern change (caching, smaller scope, scheduling), per Section 6.
3. **Never generate a model-serving code path that skips the explainability step** — if asked to "quickly get a prediction working," the explanation call is not something to defer "for later."
4. **Always match existing schema/API conventions** defined in the Architecture document rather than inventing new table names, endpoint patterns, or response shapes.
5. **Flag, don't silently fix, spatial data leakage risks** — if generated code performs a random train/test split on geospatial data, this is a rule violation (Section 5.1) and must be called out, not quietly shipped.
6. **When uncertain about a project-specific decision** (e.g., which satellite band to use, which threshold to set), state the assumption explicitly in a code comment rather than picking silently — this keeps the human developer able to review and correct it.

---

## 12. Definition of Done (Per Feature)

A feature/module is considered "done" only when all of the following are true:

- [ ] Code follows the standards in Section 3
- [ ] Any new/changed data source is documented per Section 6.5
- [ ] Any new/changed model includes a recorded baseline comparison (Section 5.3)
- [ ] Any new/changed model includes explainability output (Section 5.4)
- [ ] Any new/changed API endpoint includes input validation and the standard response envelope (Section 7)
- [ ] No secrets or credentials introduced into source control (Section 8)
- [ ] Module-level README updated if behavior changed (Section 9)
- [ ] Basic tests pass per Section 10
- [ ] Change is merged via PR, not a direct push to `main` (Section 4)

---

## 13. Escalation / Deviation Process

If a rule in this document genuinely cannot be followed for a specific technical reason (e.g., a free-tier limit turns out to be too restrictive for a specific analysis), the correct process is:

1. Document the conflict and proposed alternative in an ADR (Section 9).
2. Update the PRD/Architecture document if the change affects scope or system design.
3. Only then implement the deviation — rules are not to be silently bypassed under time pressure, since that's exactly what causes inconsistent, hard-to-defend project work by the time of panel submission.

---

*End of Document*

# Sprint 32A — Calibrated AI Fit Scoring Audit + Scope Lock

## 1. Sprint 32 Goal

Sprint 32 will prepare a **calibrated AI-assisted fit scoring layer** that can complement—not replace—the repository’s existing **rule-based** job-fit and tailoring logic.

**Sprint 32A is audit and scope-lock only.** No OpenAI client, no new dependencies, no API keys, no settings changes, and no scoring implementation occur in this sub-sprint.

### Principles locked in Sprint 32A

| Principle | Requirement |
|---|---|
| Rule-based scoring remains intact | `calculate_job_fit_score`, `analyze_job_posting`, and related constants stay the primary implemented system until a later sub-sprint is validated |
| AI scoring is advisory only | AI output must not auto-save, auto-apply, or overwrite stored application fields |
| User approval required | Any AI-derived recommendation shown to the user must be reviewed before external use or persistence |
| Forbidden automation | No auto-save, auto-apply, recruiter automation, scraping, Gmail, Calendar, OAuth, or background application submission |

---

## 2. Current Rule-Based Scoring Baseline

The following paths are the **documented baseline** for fit scoring and related UI at the start of Sprint 32. All are **rule-based and local** today.

| Path | Role |
|---|---|
| `apps/job_intelligence/constants.py` | Canonical lists: target titles, seniority signals, locations, skills, deal-breakers, learning targets |
| `apps/job_intelligence/services.py` | `calculate_job_fit_score`, `build_smart_review`, locked CV `Aminul_Islam_Data_Analyst_CV`, project recommendations, readiness |
| `apps/ai_agents/services.py` | `analyze_job_posting`, `analyze_cv_gap`, `build_cv_tailoring_advisor`, CV gap and posting analysis |
| `apps/ai_agents/views.py` | Job Posting Analyzer, Application AI Pack, CV Tailoring Advisor context |
| `apps/ai_agents/tests.py` | Service and view tests for analyzer, tailoring advisor, and related flows |
| `templates/ai_agents/job_posting_analyzer.html` | Fit score, risks, deal-breakers, pre-fill bridge, CV Tailoring Advisor (Sprint 31C) |
| `templates/job_intelligence/application_smart_review.html` | Full Smart Review for saved applications |

### Existing capabilities (implemented today)

- **Job fit scoring** — numeric 0–100 from keyword/title/location/seniority/deal-breaker rules
- **Fit labels** — e.g. Strong / Good / Weak / Skip style recommendations from score bands
- **Recommended locked CV** — `Aminul_Islam_Data_Analyst_CV` (no alternate CV filenames in advisor path)
- **Recommended projects** — finance/risk, operations/KPI, ETL/API, or general analytics buckets
- **Matched skills** — from `GOOD_SKILLS` and CV gap extraction
- **Risks** — seniority, location, stretch targets, learning-target tools, unclear title
- **Deal-breakers** — clearance, qualifications, seniority phrases from `DEAL_BREAKERS`
- **Learning targets / missing tools** — e.g. dbt, Snowflake, Airflow flagged as gaps, not invented experience
- **Manual pre-fill workflow** — Job Posting Analyzer → Review & Pre-fill Application (user submits form)
- **Saved application Smart Review** — Application Detail fit summary + full Smart Review page
- **CV Tailoring Advisor (Sprint 31)** — advisory angles, projects, gaps, cover-letter themes, interview points

No external AI/LLM API is called in these code paths at the Sprint 32A baseline.

---

## 3. Existing Scoring Inputs

Sprint 32 should **reuse existing fields** before adding new model fields or migrations.

| Input | Source | Used by (examples) |
|---|---|---|
| `company_name` | Job Posting Analyzer form; `JobApplication` | `analyze_job_posting`, tailoring advisor |
| `job_title` | Form; application record | Fit score text, title matching |
| `location` | Form; application | Location / remote scoring |
| `required_skills` | Application | `_text()` / smart review, agent pack JD bundle |
| `job_description` | Form `job_posting`; application | Posting analysis, CV gap, tailoring |
| `notes` | Application | Smart review text, agent pack |
| `cv_version` | Application | Readiness, tailoring `cv_evidence` |
| `cover_letter_version` | Application | Readiness, tailoring `cv_evidence` |
| `role_fit` | Application (`RoleFit` choices) | Score boost when title match weak |
| `status` | Application | Next-action logic |
| `pipeline_stage` | Application | Queue / workflow context (not primary score input today) |
| `work_type` | Application (`WorkType`) | Location/work pattern scoring in smart review |
| `experience_level` | Application | Junior-friendly signals in `_text()` |

Optional future AI prompts may also reference **portfolio evidence text** supplied by the user in forms (e.g. CV gap `cv_evidence`) without sending private inbox or Gmail data.

---

## 4. Existing Rule-Based Outputs

| Output | Producer | Notes |
|---|---|---|
| Fit score (0–100) | `calculate_job_fit_score`, `analyze_job_posting` | Primary numeric signal |
| Fit label / recommendation | `fit_label`, `JobPostingAnalysis.recommendation` | Human-readable band |
| Explanation / reasons | `job_fit_reasons`, `JobPostingAnalysis.explanation` | Traceable rule hits |
| Matched skills | Posting analysis, CV gap, tailoring advisor | Keyword-based |
| Risks | Posting analysis, tailoring advisor | Advisory list |
| Deal-breakers | `DEAL_BREAKERS` detection | May reduce score |
| Recommended CV | Locked filename + angle copy | Smart review / advisor |
| Recommended projects | `recommend_projects*` helpers | Portfolio names only |
| Next actions | `JobPostingAnalysis.next_actions`, `determine_next_action` | Operational guidance |
| Readiness score | `calculate_readiness` | % complete checklist |
| Missing readiness items | `readiness_missing_items` | Field-level gaps |
| CV Tailoring Advisor bundle | `CVTailoringAdvisorResult` | Sprint 31 advisory outputs |

These outputs remain the **only implemented scoring system** until Sprint 32B+ is completed and validated.

---

## 5. Proposed Sprint 32 AI Scoring Contract

Future AI integration (32B onward) should return **structured JSON only**, validated before display. Example contract:

```json
{
  "ai_fit_score": 0,
  "ai_fit_label": "string",
  "confidence": "low | medium | high",
  "evidence_matches": ["string"],
  "gaps": ["string"],
  "deal_breakers": ["string"],
  "reasoning_summary": "short string",
  "recommended_cv_angle": "string",
  "recommended_projects": ["string"],
  "manual_review_required": true,
  "claim_safety_notes": ["string"]
}
```

### Contract rules

| Rule | Detail |
|---|---|
| `ai_fit_score` | Integer 0–100; must not silently replace stored rule-based score |
| `manual_review_required` | Default **true** for apply/skip decisions until user explicitly accepts |
| Side-by-side display | UI should show **rule-based score** and **AI score** together (planned 32D) |
| No auto-overwrite | AI output must **never** automatically overwrite `role_fit`, `fit_score` on save, or application status |
| Advisory framing | Labels and reasoning are suggestions; user approves external actions |

---

## 6. Calibration Rules

Calibration means **comparing** AI output to rule-based output, not trusting AI alone.

| Rule | Application |
|---|---|
| Compare scores | Show rule-based fit score and `ai_fit_score` side by side |
| Highlight disagreement | Flag when scores differ by more than an agreed threshold (e.g. 15 points) for manual review |
| Manual approval before save | Do not persist AI recommendations to `JobApplication` without explicit user action in a later sprint |
| Seniority risk | Senior/lead/3+/5+ year signals reduce confidence; do not inflate AI score |
| Location risk | Non-target locations reduce confidence unless remote UK is clear |
| Clearance / qualifications | SC/DV clearance, ACCA/ACA/CIMA, etc. → deal-breaker or `manual_review_required` |
| Hard-tool gaps | dbt, Snowflake, Airflow, Spark, etc. → gaps list; not invented portfolio experience |
| No evidence inflation | Missing CV evidence or skills must not increase score |
| No invented claims | No invented skills, employers, dates, clients, production users, metrics, or SaaS usage |

Locked CV policy from Sprint 31 remains: recommended filename stays **`Aminul_Islam_Data_Analyst_CV`**; AI may only suggest **angles**, not alternate CV files.

---

## 7. OpenAI Implementation Boundary For Later Sprint

**Sprint 32A does not implement OpenAI.**

A future sub-sprint (e.g. 32C) may add an OpenAI client **only after** this audit is merged, tagged, and approved. Preconditions:

| Requirement | Detail |
|---|---|
| Configuration | Environment variable only (e.g. `OPENAI_API_KEY`); **no hard-coded API key** |
| Repository | **No key committed** to git; `.env` stays gitignored |
| Resilience | Timeout handling; **graceful fallback** to rule-based scoring on failure |
| Validation | Structured output parsing with schema validation |
| Tests | **Mocked responses only**; no real API calls in CI or default test suite |
| Local dev | Test suite must pass **without** API key present |
| Automation | No automatic application save, submit, or recruiter outreach |
| Data sources | No scraping; no job-board API; user-provided text only |

Claude or other providers are **out of scope** unless separately audited; Sprint 32A locks OpenAI as the hypothetical first external provider only in planning terms, not as implemented.

---

## 8. Security / Secrets Boundary

| Rule | State in Sprint 32A |
|---|---|
| Do not print `.env` contents | Required for all validation and documentation |
| Do not commit API keys | No keys in repo, examples, or screenshots |
| Do not add real credentials to examples | Use placeholders such as `OPENAI_API_KEY=<set locally>` |
| User data to external services | No design approved yet to send application DB rows to a model without explicit 32B+ spec and approval |
| Gmail / Calendar / contacts / inbox | **Must not** be sent to any model |
| Recruiter email bodies | **Must not** be sent to any model in initial OpenAI design |

---

## 9. Claim-Safety Boundary

| Claim | Sprint 32A state |
|---|---|
| Sprint 32A scope | **Audit and scope-lock only** |
| OpenAI implemented | **No** |
| Claude implemented | **No** |
| External AI / LLM API active | **No** |
| Gmail integration | **No** (manual recruiter email import only; Sprint 29) |
| Calendar integration | **No** |
| Scraping | **No** |
| Auto-apply | **No** |
| Recruiter automation | **No** |
| Final CV generation | **No** |
| Implemented scoring | **Rule-based only** until later Sprint 32 sub-phases are validated and documented |

Portfolio and README claims must continue to state **rule-based, local, manual** workflows until evidence exists for a tagged AI integration sub-sprint.

---

## 10. Recommended Sprint 32 Breakdown

| Sub-sprint | Focus | Implementation in 32A? |
|---|---|---|
| **32A** | Calibrated AI Fit Scoring Audit + Scope Lock | **This document only** |
| **32B** | AI scoring service contract + mocked tests | **Not started** — JSON contract, parsers, fixtures |
| **32C** | OpenAI client wrapper + safe fallback (mocked first) | **Not started** — env-based key, no real calls in tests |
| **32D** | UI integration: rule-based vs AI score comparison | **Not started** — side-by-side, disagreement highlight |
| **32E** | Evidence + closure | **Not started** — closure doc and index |

**Gate:** Sprint **32B must not begin** until Sprint **32A** is committed, merged to `main`, tagged (e.g. `sprint-32a-calibrated-ai-fit-scoring-audit-complete`), pushed, **CI green**, and the `sprint-32a-calibrated-ai-fit-scoring-audit` branch is cleaned up.

---

## 11. Sprint 32A Final Decision Gate

Sprint **32A** is **complete** only when:

1. This audit document is validated (project Sprint 32A validation routine).
2. Changes are committed and merged to `main`.
3. Sprint 32A tag is created and pushed.
4. GitHub Actions / Django CI is green on `main`.
5. The `sprint-32a-calibrated-ai-fit-scoring-audit` branch is cleaned up.

Until then, **no OpenAI dependency, no API integration, and no calibrated AI scoring** should be described as delivered in the repository.

---

## Audit Metadata

| Item | Value |
|---|---|
| Sprint | 32A — Calibrated AI Fit Scoring Audit + Scope Lock |
| Branch | `sprint-32a-calibrated-ai-fit-scoring-audit` |
| Baseline after Sprint 31 | Rule-based fit + CV Tailoring Advisor; **330 tests** on main after Sprint 31C (`2132095`) |
| Primary output | This file + `docs/evidence/evidence_index.md` entry |
| Next planned step | Sprint 32B (not implemented in 32A) |

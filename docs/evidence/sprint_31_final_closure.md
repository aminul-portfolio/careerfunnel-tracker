# Sprint 31 — CV Tailoring Advisor Final Closure

## 1. Sprint Goal

Sprint 31 added a **rule-based CV Tailoring Advisor** workflow that suggests job-specific CV and portfolio evidence while preserving **manual approval** and **claim accuracy**.

The advisor helps users decide how to position an application—recommended CV filename, CV angle, role family, experience angles, portfolio projects, skill gaps, risks, cover-letter themes, and interview talking points—without generating a final CV, finalizing a cover letter, submitting applications, or connecting to external services.

Sprint 31 was delivered in four sub-phases: evidence audit (31A), service logic (31B), UI integration (31C), and evidence closure (31D).

---

## 2. Completed Sprint Breakdown

| Sub-sprint | Focus | Outcome |
|---|---|---|
| **Sprint 31A** | CV Evidence Source Audit | Documented safe evidence sources and claim boundaries before implementation |
| **Sprint 31B** | CV Tailoring Advisor Logic | `CVTailoringAdvisorResult` and `build_cv_tailoring_advisor()` with tests |
| **Sprint 31C** | Application Detail / Job Analyzer Integration | Advisor surfaced in Job Posting Analyzer, Application AI Pack, and Application Detail link |
| **Sprint 31D** | Evidence + Closure | This closure document and evidence index update (documentation only) |

---

## 3. Sprint 31A Evidence

| Item | Detail |
|---|---|
| Document | `docs/evidence/sprint_31a_cv_evidence_source_audit.md` |
| Tag | `sprint-31a-cv-evidence-source-audit-complete` |

### What Sprint 31A delivered

- Audited claim-safe documentation sources (README, Sprint 29–30 evidence, Career Evidence, assisted intake, portfolio wording) before building advisor logic.
- Defined candidate evidence categories for Sprint 31B, manual approval rules, and unsafe/future-only claims.
- Recorded a readiness gate: review audit, pass validation, and obtain explicit user approval before implementation.

### Scope

Documentation and audit only. No product code changes in Sprint 31A.

---

## 4. Sprint 31B Evidence

| Item | Detail |
|---|---|
| Service | `apps/ai_agents/services.py` |
| Tests | `apps/ai_agents/tests.py` (`CVTailoringAdvisorLogicTests`) |
| Tag | `sprint-31b-cv-tailoring-advisor-logic-complete` |

### What Sprint 31B delivered

- **`CVTailoringAdvisorResult`** — frozen dataclass for advisory tailoring output.
- **`build_cv_tailoring_advisor()`** — rule-based function composing `analyze_job_posting`, `analyze_cv_gap`, `recommend_projects_from_text`, and job-intelligence constants.
- **Locked CV recommendation** — always `Aminul_Islam_Data_Analyst_CV` (no alternate CV filenames invented).
- **Role-family-specific CV angle** — Finance/FinTech, BI/Reporting, Analytics Engineering stretch, Data Analyst, or Review Carefully.
- **Strongest experience suggestions** — claim-safe angles only (no invented employers, dates, or metrics).
- **Strongest project suggestions** — reuses existing project recommendation logic.
- **Matched skills / partial matches / missing skills** — from `analyze_cv_gap`.
- **Risks and deal-breakers** — seniority, location, hard-tool gaps, unclear fit, and `DEAL_BREAKERS` signals.
- **Cover-letter themes only** — not a finalized cover letter.
- **Interview evidence points** — talking-point suggestions only.
- **Claim-safety notes** and **manual approval reminder** — advisory boundaries on every result.

### Scope

Logic and tests only. No templates, views, or forms in Sprint 31B.

---

## 5. Sprint 31C Evidence

| Item | Detail |
|---|---|
| Views | `apps/ai_agents/views.py` |
| Templates | `templates/ai_agents/job_posting_analyzer.html`, `templates/ai_agents/application_agent_pack.html`, `templates/applications/application_detail.html` |
| Tests | `apps/ai_agents/tests.py` (view integration assertions) |
| Tag | `sprint-31c-cv-tailoring-advisor-integration-complete` |

### What Sprint 31C delivered

- **Job Posting Analyzer** — after valid POST, calls `build_cv_tailoring_advisor` and renders a **CV Tailoring Advisor** section with claim-safe advisory copy alongside existing fit score output.
- **Application AI Pack** — builds tailoring advisor from saved application fields (company, title, location, skills/JD/notes, CV/cover-letter versions) for manual review before external tailoring.
- **Application Detail** — link **Open AI Pack / CV Tailoring Advisor** to `ai_agents:application_agent_pack` (navigation only; no new business logic on detail page).

### Scope

Integration only. No models, migrations, external APIs, or automation added.

---

## 6. Current User Workflow

After Sprint 31C, the intended manual workflow is:

1. User pastes a job posting into **Job Posting Analyzer**.
2. System shows **fit review** (existing analyzer) and **CV Tailoring Advisor** suggestions (rule-based, advisory).
3. User reviews recommended CV (`Aminul_Islam_Data_Analyst_CV`), CV angle, role family, strongest experience angles, strongest projects, matched/partial/missing skills, risks, deal-breakers, cover-letter themes, and interview evidence points.
4. User may open **Review & Pre-fill Application** and manually save a record—nothing is auto-submitted.
5. On saved application records, user opens **AI Pack / CV Tailoring Advisor** from Application Detail or the Application AI Pack page.
6. User **manually decides** what wording to use in CV, cover letter, recruiter messages, or submissions outside the app.

CareerFunnel Tracker **assists and suggests**; the user **reviews and approves** all final external actions.

---

## 7. Claim-Safety Boundary

Sprint 31 does **not** implement or claim:

| Boundary | State |
|---|---|
| Rule-based logic only | **Yes** — deterministic services; no external AI/LLM |
| Final CV generated | **No** |
| Cover letter finalized | **No** — themes only |
| Application submitted automatically | **No** |
| Gmail integration | **No** |
| Calendar integration | **No** |
| OAuth | **No** |
| Scraping | **No** |
| External AI / LLM API | **No** |
| Recruiter automation | **No** |
| Auto-apply / auto-save | **No** |
| Invented skills, experience, employers, dates, clients, users, or metrics | **No** |
| Production SaaS / customer claims | **No** |

**User must manually approve** all suggested wording before using it in a CV, cover letter, recruiter message, or application sent outside the repository.

---

## 8. Validation Evidence

Latest proven validation state after Sprint 31C integration (per project validation routine):

| Check | Result |
|---|---|
| `ruff check` | Passed |
| `python manage.py check` | Passed |
| `python manage.py makemigrations --check --dry-run` | Passed |
| `python manage.py test` | Passed |
| Test count after Sprint 31C | **330 tests** |
| GitHub Actions / Django CI | Passed for Sprint 31C on `main` |
| Latest Sprint 31C main commit | `2132095` |
| Sprint 31C tag | `sprint-31c-cv-tailoring-advisor-integration-complete` |

Sprint 31D adds this closure document and evidence index entry only. Full Sprint 31 closure still requires 31D validation, merge to `main`, tag, push, green CI, and branch cleanup per Section 10.

---

## 9. Implemented vs Not Implemented

| Area | Status | Notes |
|---|---|---|
| CV evidence audit | Implemented | `docs/evidence/sprint_31a_cv_evidence_source_audit.md` |
| CV Tailoring Advisor service logic | Implemented | `build_cv_tailoring_advisor` in `apps/ai_agents/services.py` |
| Job Posting Analyzer integration | Implemented | POST shows advisor section with advisory copy |
| Application AI Pack integration | Implemented | Saved-application tailoring on agent pack page |
| Application Detail link | Implemented | Link to AI Pack; no automatic tailoring |
| Final CV generation | Not implemented | Locked filename + angles only |
| Cover letter auto-generation/finalization | Not implemented | Themes only |
| Auto-submit / auto-apply | Not implemented | Manual pre-fill and save unchanged |
| Gmail / Calendar / OAuth | Not implemented | Out of scope |
| External AI / LLM API | Not implemented | Rule-based only |
| Scraping | Not implemented | User-pasted job text only |
| Recruiter automation | Not implemented | Sprint 29 manual workflow unchanged |

---

## 10. Sprint 31 Final Decision

Sprint 31 is **complete** when:

1. This closure document (`docs/evidence/sprint_31_final_closure.md`) is validated.
2. Changes are merged to `main`.
3. Sprint 31 family work is tagged and pushed as appropriate (31A–31C tags already recorded; 31D closure merge follows project checklist).
4. GitHub Actions / Django CI is green on `main`.
5. The `sprint-31d-evidence-and-closure` branch is cleaned up after merge.

Until those steps finish, treat Sprint 31D as **documentation closure in progress** on the closure branch—not as a claim that all merge/tag steps are already done on `main`.

---

## Evidence package (Sprint 31)

| Path | Role |
|---|---|
| `docs/evidence/sprint_31a_cv_evidence_source_audit.md` | Source audit and 31B readiness gate (31A) |
| `apps/ai_agents/services.py` | `CVTailoringAdvisorResult`, `build_cv_tailoring_advisor` (31B) |
| `apps/ai_agents/tests.py` | Logic and view integration tests (31B–31C) |
| `apps/ai_agents/views.py` | Analyzer and agent pack context (31C) |
| `templates/ai_agents/job_posting_analyzer.html` | Job Posting Analyzer UI (31C) |
| `templates/ai_agents/application_agent_pack.html` | Application AI Pack UI (31C) |
| `templates/applications/application_detail.html` | AI Pack link (31C) |
| `docs/evidence/sprint_31_final_closure.md` | This Sprint 31 closure document (31D) |
| `docs/evidence/evidence_index.md` | Evidence map entry |

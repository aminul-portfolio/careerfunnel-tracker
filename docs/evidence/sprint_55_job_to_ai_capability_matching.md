# Sprint 55 - Job-to-AI Capability Matching Evidence

## Sprint 55 Phase 1

Sprint 55 Phase 1 adds a deterministic service-layer foundation for matching job description text to AI capability framework categories.

It does not add external AI calls, scraping, auto-apply, recommendations, persistence, or UI automation.

## Service

- **Module:** `apps/skills/services/job_ai_capability_matching.py`
- **Entry point:** `match_job_description_to_ai_capabilities(job_description: str)`
- **Inputs:** Raw job description text (manual paste or saved application text in later phases)
- **Outputs:** Matched capabilities, missing capabilities, detected terms, match score, match label, explanation points, claim-safety notes

## Matching model

```text
Job description text
-> AI capability keyword detection
-> matched AI capability categories
-> missing / weak AI capability signals
-> claim-safe matching summary
```

Keyword groups map to Sprint 53 capability slugs. Match score is the percentage of framework categories with at least one keyword hit.

## Match labels

| Score | Label |
| --- | --- |
| 0-24 | Limited AI signal |
| 25-49 | Moderate AI signal |
| 50-74 | Strong AI signal |
| 75-100 | High AI-workflow alignment |

## Phase 1 tests

- **File:** `apps/skills/tests/test_job_ai_capability_matching.py`
- **12** service tests covering empty text, no AI signal, single-domain matches, multi-match scoring, label bands, determinism, and claim-safety wording.

## Phase 1 boundaries

- No UI, forms, dashboard widgets, models, or migrations
- No external AI provider calls
- No job application workflow changes

---

## Sprint 55 Phase 2

Sprint 55 Phase 2 exposes the deterministic job-to-AI capability matching service in a read-only review surface.

It uses demo/sample text only.

It does not persist results, connect to saved applications, call external AI providers, scrape jobs, or automate applications.

### Report page

- **Route:** `/skills/job-ai-capability-match/`
- **View:** `job_ai_capability_match_report`
- **Template:** `templates/skills/job_ai_capability_match_report.html`
- **Navigation:** Intelligence sidebar link - Job AI Capability Match
- **Demo text:** Static sample job description in view (clearly labelled, not a real application)

### Phase 2 display

- Match score and match label
- Detected terms
- Matched capability categories with matched terms
- Missing / weak capability signals
- Explanation points and claim-safety notes

### Phase 2 tests

- **File:** `apps/skills/tests/test_job_ai_capability_match_report_view.py`
- **10** view tests for login, render, score/label/terms, claim safety, and service context

### Combined apps.skills tests after Phase 2

- **58** tests (48 Phase 1 baseline + 10 Phase 2 view tests)

### Phase 2 boundaries

- No forms, saved application wiring, persistence, models, or migrations
- No external AI provider calls or automation

## Phase 3 (not started)

- Connect matching to saved job application text or manual paste form

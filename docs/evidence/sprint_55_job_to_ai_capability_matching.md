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

## Tests

- **File:** `apps/skills/tests/test_job_ai_capability_matching.py`
- Covers empty text, no AI signal, single-domain matches, multi-match scoring, label bands, determinism, and claim-safety wording.

## Phase 1 boundaries

- No UI, forms, dashboard widgets, models, or migrations
- No external AI provider calls
- No job application workflow changes

## Phase 2 (not started)

- Platform surface to display matching results on relevant job-intelligence pages

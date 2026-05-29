# Sprint 59 - Final Career Intelligence Workflow Evidence

## Sprint 59 Phase 1

Sprint 59 Phase 1 adds a deterministic service-layer foundation for the Final Career Intelligence Workflow.

It integrates Sprint 53-58 outputs into workflow stages, action sequence items, evidence targets, and claim-safe summary data.

It does not add UI, persistence, external AI calls, scraping, auto-apply, background jobs, or saved application integration.

## Service

- **Module:** `apps/skills/services/final_career_intelligence_workflow.py`
- **Entry point:** `build_final_career_intelligence_workflow()`
- **Inputs:** Sprint 53-58 service outputs (portfolio baseline defaults)
- **Outputs:** Workflow label, overall status, readiness and job-match scores, strategy status, workflow stages, action sequence, integration summary, evidence targets, claim-safety notes

## Workflow model

```text
AI capability framework
+ AI readiness score
+ job-to-AI capability match
+ learning recommendations
+ career readiness dashboard
+ career strategy action plan
-> final career intelligence workflow
-> workflow stages
-> end-to-end readiness summary
-> next action sequence
-> claim-safe final integration data
```

## Workflow stages

1. Capability Framework
2. AI Readiness Scoring
3. Job-to-AI Capability Matching
4. Learning Recommendations
5. Career Readiness Dashboard
6. Career Strategy Action Plan
7. Manual Review Gate

## Stage status labels

- Ready
- Review
- Manual check
- Developing

## Overall status labels

- Integrated workflow ready for manual use
- Needs evidence strengthening
- Manual review required
- Developing intelligence workflow

## Action sequence priority labels

- High
- Medium
- Low

## Action sequence status labels

- Ready
- Review
- Manual check
- Developing

## Rule summary

| Signal | Workflow behaviour |
| --- | --- |
| Action plan needs focused improvement | Overall status highlights evidence strengthening |
| Readiness >= 70 and job match >= 50 | Integrated workflow ready for manual use when strategy is ready |
| Action plan manual review required | Overall status is manual review required |
| High-priority action plan items | High-priority action sequence items preserved |
| Always | Manual Review Gate stage and claim-safety notes |

## Tests

- **File:** `apps/skills/tests/test_final_career_intelligence_workflow.py`
- **14** service tests covering structure, stages, action sequence, scores, determinism, and claim safety.

## Phase 1 boundaries

- No UI, templates, navigation, charts, forms, models, or migrations
- No external AI provider calls or persistence

## Phase 2 (not started)

- Read-only final career intelligence workflow page surface

---

## Sprint 59 Phase 2

Sprint 59 Phase 2 exposes the deterministic Final Career Intelligence Workflow service in a read-only platform surface.

It integrates Sprint 53-58 outputs into workflow stages, action sequence items, evidence targets, and claim-safe summary data for manual review.

It does not persist results, connect to saved applications, call external AI providers, scrape jobs, automate applications, or replace human judgement.

### Report page

- **Route:** `/skills/final-career-intelligence-workflow/`
- **View:** `final_career_intelligence_workflow`
- **Template:** `templates/skills/final_career_intelligence_workflow.html`
- **Navigation:** Intelligence sidebar link - Final Career Intelligence Workflow
- **Service:** `build_final_career_intelligence_workflow()`

### Phase 2 display

- Workflow label and overall status
- Readiness score and job-match score
- Strategy status and next best action
- Workflow stages table (stage number, title, source, status, summary, output reference)
- Action sequence table (step, title, priority, status, reason, manual next step, source stage, evidence target)
- Integration summary, evidence targets, and claim-safety notes

### Phase 2 tests

- **File:** `apps/skills/tests/test_final_career_intelligence_workflow_view.py`
- **15** view tests for login, render, workflow content, claim safety, and service context

### Combined apps.skills tests after Phase 2

- **162** tests (147 Phase 1 baseline + 15 Phase 2 view tests)

### Phase 2 boundaries

- No forms, saved application wiring, persistence, models, or migrations
- No external AI provider calls or automation

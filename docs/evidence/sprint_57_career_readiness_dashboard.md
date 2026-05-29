# Sprint 57 - Career Readiness Dashboard Evidence

## Sprint 57 Phase 1

Sprint 57 Phase 1 adds a deterministic service-layer foundation for a Career Readiness Dashboard.

It combines existing AI readiness, job-to-AI capability matching, and learning recommendation outputs.

It does not add UI, persistence, external AI calls, scraping, auto-apply, background jobs, or saved application integration.

## Service

- **Module:** `apps/skills/services/career_readiness_dashboard.py`
- **Entry point:** `build_career_readiness_dashboard()`
- **Inputs:** Sprint 54 readiness, Sprint 55 job-match, Sprint 56 recommendations (portfolio baseline defaults)
- **Outputs:** KPI cards, summary points, dashboard sections, counts, next best action, claim-safety notes

## Dashboard model

```text
AI capability framework
+ AI readiness score
+ job-to-AI capability match
+ learning recommendations
-> career readiness KPIs
-> readiness summary
-> next best action
-> claim-safe dashboard data
```

## Dashboard sections

- AI Readiness
- Job AI Capability Match
- Learning Recommendations
- Manual Review

## KPI status labels

- Review
- Developing
- Strong
- Manual check

## Rule summary

| Signal | Dashboard behaviour |
| --- | --- |
| Readiness below 50 | Foundation improvement highlighted in summary |
| Job match high, readiness lower | Evidence strengthening highlighted |
| Overall priority High | Next best action emphasised |
| Always | Manual review section and claim-safety notes |

## Tests

- **File:** `apps/skills/tests/test_career_readiness_dashboard.py`
- **15** service tests covering structure, KPIs, summaries, determinism, and claim safety.

## Phase 1 boundaries

- No UI, templates, navigation, charts, forms, models, or migrations
- No external AI provider calls or persistence

## Phase 2 (not started)

- Read-only dashboard page surface

---

## Sprint 57 Phase 2

Sprint 57 Phase 2 exposes the deterministic Career Readiness Dashboard service in a read-only platform surface.

It uses portfolio baseline readiness, sample job-match, and recommendation outputs.

It does not persist results, connect to saved applications, call external AI providers, scrape jobs, automate applications, or replace human judgement.

### Dashboard page

- **Route:** `/skills/career-readiness-dashboard/`
- **View:** `career_readiness_dashboard`
- **Template:** `templates/skills/career_readiness_dashboard.html`
- **Navigation:** Intelligence sidebar link - Career Readiness Dashboard
- **Service:** `build_career_readiness_dashboard()`

### Phase 2 display

- Readiness score and label
- Job-match score and label
- Overall priority and next best action
- Capability, matched, missing, and recommendation counts
- KPI cards with status labels
- Summary points and dashboard sections
- Claim-safety notes

### Phase 2 tests

- **File:** `apps/skills/tests/test_career_readiness_dashboard_view.py`
- **12** view tests for login, render, KPIs, summaries, sections, claim safety, and service context

### Combined apps.skills tests after Phase 2

- **107** tests (95 Phase 1 baseline + 12 Phase 2 view tests)

### Phase 2 boundaries

- No forms, saved application wiring, persistence, models, or migrations
- No external AI provider calls or automation

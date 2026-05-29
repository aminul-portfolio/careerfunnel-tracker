# Sprint 58 - Career Strategy Action Plan / Progress Tracking Evidence

## Sprint 58 Phase 1

Sprint 58 Phase 1 adds a deterministic service-layer foundation for Career Strategy Action Plan and Progress Tracking.

It uses the Sprint 57 Career Readiness Dashboard output to generate manual action items, progress indicators, and evidence targets.

It does not add UI, persistence, external AI calls, scraping, auto-apply, background jobs, or saved application integration.

## Service

- **Module:** `apps/skills/services/career_strategy_action_plan.py`
- **Entry point:** `build_career_strategy_action_plan()`
- **Input:** Sprint 57 `CareerReadinessDashboardResult` (portfolio baseline default)
- **Outputs:** Strategy label, overall status, action items, progress indicators, evidence targets, summary points, claim-safety notes

## Action plan model

```text
career readiness dashboard
+ next best action
+ recommendations
+ capability gaps
+ manual review boundaries
-> strategy action plan
-> action items
-> progress indicators
-> evidence targets
-> claim-safe progress tracking data
```

## Action categories

- Learning
- Evidence strengthening
- Project improvement
- CV / interview preparation
- Manual review

## Priority labels

- High
- Medium
- Low

## Action status labels

- Not started
- In progress
- Ready for review
- Manual check

## Overall status labels

- Needs focused improvement
- Developing readiness
- Ready for targeted applications
- Manual review required

## Rule summary

| Signal | Action plan behaviour |
| --- | --- |
| Dashboard overall priority High | High-priority action from next best action |
| High-priority recommendation count > 0 | Evidence strengthening and project improvement actions |
| Readiness below 50 | Foundation learning action |
| Job match >= 50 with missing capabilities | Capability gap review action |
| Strong readiness and job match | CV / interview preparation action |
| Always | Manual review action item and claim-safety notes |

## Progress indicators

- AI readiness score current/target
- Job match score current/target
- High-priority recommendation count current/target
- Capability evidence coverage current/target

## Tests

- **File:** `apps/skills/tests/test_career_strategy_action_plan.py`
- **14** service tests covering structure, action rules, progress indicators, determinism, and claim safety.

## Phase 1 boundaries

- No UI, templates, navigation, charts, forms, models, or migrations
- No external AI provider calls or persistence

## Phase 2 (not started)

- Read-only action plan / progress page surface

---

## Sprint 58 Phase 2

Sprint 58 Phase 2 exposes the deterministic Career Strategy Action Plan service in a read-only platform surface.

It uses the Sprint 57 Career Readiness Dashboard output to show manual action items, progress indicators, and evidence targets.

It does not persist results, connect to saved applications, call external AI providers, scrape jobs, automate applications, or replace human judgement.

### Report page

- **Route:** `/skills/career-strategy-action-plan/`
- **View:** `career_strategy_action_plan`
- **Template:** `templates/skills/career_strategy_action_plan.html`
- **Navigation:** Intelligence sidebar link - Career Strategy Action Plan
- **Service:** `build_career_strategy_action_plan()`

### Phase 2 display

- Strategy label and overall status
- Next best action
- Action items table (category, priority, status, reason, suggested next step, evidence target, dashboard section)
- Progress indicators table (current, target, status, supporting text)
- Evidence targets list
- Summary points and claim-safety notes

### Phase 2 tests

- **File:** `apps/skills/tests/test_career_strategy_action_plan_view.py`
- **12** view tests for login, render, action items, progress indicators, claim safety, and service context

### Combined apps.skills tests after Phase 2

- **133** tests (121 Phase 1 baseline + 12 Phase 2 view tests)

### Phase 2 boundaries

- No forms, saved application wiring, persistence, models, or migrations
- No external AI provider calls or automation

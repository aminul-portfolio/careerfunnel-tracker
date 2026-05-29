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

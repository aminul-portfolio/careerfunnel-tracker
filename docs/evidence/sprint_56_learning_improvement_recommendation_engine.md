# Sprint 56 - Learning and Improvement Recommendation Engine Evidence

## Sprint 56 Phase 1

Sprint 56 Phase 1 adds a deterministic service-layer foundation for learning and improvement recommendations.

It uses existing readiness and job-to-AI capability outputs.

It does not add external AI calls, scraping, auto-apply, persistence, UI automation, or background jobs.

## Service

- **Module:** `apps/skills/services/learning_recommendations.py`
- **Entry point:** `build_learning_recommendations(readiness, job_match)`
- **Portfolio helper:** `build_portfolio_baseline_learning_recommendations()`
- **Inputs:** Sprint 54 `AIReadinessScoringResult` and Sprint 55 `JobAICapabilityMatchResult`
- **Outputs:** Overall priority, next best action, recommendations, readiness summary, job-match summary, claim-safety notes

## Recommendation model

```text
AI readiness score
+ job-to-AI capability match result
+ missing / weak capability signals
-> safe learning recommendations
-> project improvement suggestions
-> CV / interview evidence suggestions
-> next best action summary
```

## Recommendation categories

- Learning
- Project improvement
- CV evidence
- Interview preparation
- Manual review

## Priority labels

- High
- Medium
- Low

## Rule summary

| Signal | Recommendation type |
| --- | --- |
| Low readiness score | Foundation learning actions |
| Missing job capability keywords | Capability-specific learning review |
| Job matched but weak readiness evidence | Project improvement or CV evidence |
| Strong readiness + strong job match | Interview story preparation |
| Always | Manual review reminder |

## Tests

- **File:** `apps/skills/tests/test_learning_recommendations.py`
- **12** service tests covering low/strong readiness, missing capabilities, evidence gaps, priorities, determinism, and claim safety.

## Phase 1 boundaries

- No UI, forms, dashboard widgets, models, or migrations
- No external AI provider calls or persistence

## Phase 2 (not started)

- Read-only platform surface to display recommendations

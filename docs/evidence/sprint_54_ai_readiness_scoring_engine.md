# Sprint 54 - AI Readiness Scoring Engine Evidence

## 1. Sprint Objective

Sprint 54 builds a rule-based AI Readiness Scoring Engine on top of the Sprint 53 PPTX AI Capability Framework and exposes the result in a reviewable platform surface.

**Branch:** `sprint-54-ai-readiness-scoring-engine`

**Phase commits:**

| Phase | Commit | Scope |
| --- | --- | --- |
| Phase 1 | `57af48c` | Scoring service and service tests |
| Phase 2 | (this document) | Readiness report page, view tests, evidence |

---

## 2. What Sprint 54 Added

### Phase 1 - Scoring foundation

- Service: `apps/skills/services/ai_readiness_scoring.py`
- Rule-based scoring from manual evidence strength inputs mapped to Sprint 53 capability slugs
- Evidence strengths: `none`, `gap_learning`, `partial`, `strong` (aligned with evidence-bank tier concepts)
- Readiness label bands from Foundation needed through Agent / portfolio-ready
- Portfolio baseline helper: `build_portfolio_baseline_ai_readiness_score()`
- **12** service tests in `apps/skills/tests/test_ai_readiness_scoring.py`

### Phase 2 - Readiness report UI

- Login-required GET page at `/skills/ai-readiness-report/`
- View calls `build_portfolio_baseline_ai_readiness_score()` only (no duplicated scoring logic)
- Template shows score, label, coverage counts, explanation points, claim-safety notes, and per-capability lines
- Intelligence sidebar link: **AI Readiness Report**
- **8** view tests in `apps/skills/tests/test_ai_readiness_report_view.py`

Sprint 54 Phase 2 exposes the rule-based AI readiness score in a reviewable platform surface.
It does not add autonomous AI, external AI provider calls, scraping, auto-apply, or background automation.

---

## 3. Review Flow

```text
AI Capability Framework
-> Evidence Strength
-> AI Readiness Score
-> Readiness Label
-> Explanation Points
-> Claim-Safety Notes
```

### How to review

1. Log in locally.
2. Open **Intelligence -> AI Readiness Report** or navigate to `/skills/ai-readiness-report/`.
3. Confirm KPI cards show score, label, and coverage counts from the service.
4. Confirm explanation points and claim-safety notes are visible.
5. Confirm per-capability readiness lines match the portfolio baseline output.
6. Open **AI Capability Framework** via the on-page link to compare framework categories.

---

## 4. Main Implementation Evidence

| Layer | Path | Role |
| --- | --- | --- |
| Scoring service | `apps/skills/services/ai_readiness_scoring.py` | Phase 1 rule-based engine |
| View | `apps/skills/views.py` | `ai_readiness_report` |
| URLs | `apps/skills/urls.py` | Route `ai-readiness-report/` |
| Template | `templates/skills/ai_readiness_report.html` | Readiness report display |
| Navigation | `templates/partials/sidebar.html` | Intelligence group link |
| Framework page | `/skills/ai-capability-framework/` | Sprint 53 reference (unchanged scoring scope on that page) |

**Not added:** models, migrations, external AI calls, job matching, recommendations, automation.

---

## 5. Test Coverage Summary

| File | Tests | Focus |
| --- | ---: | --- |
| `test_ai_readiness_scoring.py` | 12 | Scoring service logic and claim safety |
| `test_ai_readiness_report_view.py` | 8 | Page render, score/label, claim safety, service context |
| Other `apps.skills` tests | 16 | Sprint 53 framework service and page |

**Combined `apps.skills` total after Phase 2:** 36 tests.

---

## 6. Claim-Safety Boundaries

| Boundary | Sprint 54 behaviour |
| --- | --- |
| Rule-based only | Deterministic score from static/manual evidence inputs |
| Manual review | Page copy states advisory, non-predictive purpose |
| No external AI | Scoring service and page do not call providers |
| No automation | GET-only report; no workflows triggered |
| No job matching | No application or JD comparison in Phase 2 |
| No recommendations | No ranked next actions on this page |
| Portfolio baseline | Static CareerFunnel evidence map; verify manually before external claims |

---

## 7. Intentionally Not Implemented Yet

- User-editable evidence inputs on the page
- Database persistence of readiness scores
- Dashboard widgets or funnel metrics integration
- Job matching or recommendation engine
- External AI provider integration
- Sprint 55+ scope

---

## 8. ASCII / Encoding Note

Sprint 54 copy uses ASCII hyphens and straight apostrophes in new template and evidence text.

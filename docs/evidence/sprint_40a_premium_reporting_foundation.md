# Sprint 40A - Premium Reporting Foundation Evidence

## 1. Sprint Objective

Sprint 40A upgrades the metrics reporting page into a **Premium Reporting Foundation** focused on:

1. Funnel Performance
2. Data Quality
3. Application Quality
4. Shared reporting components (header, KPI strip, confidence badge, empty state, manual action links, advisory copy)

This sprint is **reporting-only**. It does not redesign the dashboard, forms, models, migrations, or Sprint 40B/40C report areas.

**Branch:** `sprint-40a-premium-reporting-foundation`

---

## 2. Funnel Performance Report Summary

**Service:** `build_funnel_performance_report(user)` in `apps/metrics/services.py`

| Element | Description |
| --- | --- |
| Applications / responses / interviews / offers | Counts and conversion rates from `build_funnel_metrics` |
| Stage breakdown | Reuses `build_funnel_stage_rows` |
| Advisory interpretation | Plain-English diagnosis from `diagnose_funnel` |
| Recommended manual action | Diagnosis recommended action (no automation) |
| Confidence badge | Volume-based funnel confidence label |
| Manual workflow links | Application create, application list, weekly review list |
| Empty state | Reviewer-friendly copy when no applications exist |

---

## 3. Data Quality Report Summary

**Service:** `build_data_quality_foundation_report(user)` in `apps/metrics/services.py`

| Element | Description |
| --- | --- |
| Missing CV version | Count from existing `build_data_quality_report` |
| Missing job description | Count from existing data quality checks |
| Missing required skills | Count from existing data quality checks |
| Missing follow-up data | Count from existing data quality checks |
| Confidence / data-readiness badge | Derived from analytics-ready rate |
| Data quality checks table | Existing check rows with severity and recommendations |
| Reviewer-friendly empty state | Guidance for new users with zero applications |
| Manual workflow links | Application list and evaluation queue |

---

## 4. Application Quality Report Summary

**Service:** `build_application_quality_foundation_report(user)` in `apps/metrics/services.py`

| Element | Description |
| --- | --- |
| Application completeness | Label derived from quality issue rate |
| Evidence strength | Label derived from analytics-ready rate |
| Decision readiness | Label combining issue rate and follow-up gaps |
| Quality status labels | Strong / Needs review / Weak per flagged application |
| Manual review links | Per-application detail URLs |
| Issue table | Flagged applications with advisory issue lists |
| Manual workflow links | Application list and evaluation queue |

---

## 5. Shared Reporting Components Added

**Templates:** `templates/metrics/partials/`

| Partial | Purpose |
| --- | --- |
| `report_header.html` | Report title, subtitle, trust note |
| `report_kpi_strip.html` | Reusable KPI card strip |
| `confidence_badge.html` | Data-readiness / reporting confidence badge |
| `report_empty_state.html` | Reviewer-friendly empty state with optional manual links |
| `manual_action_link.html` | Consistent manual workflow link pattern |
| `advisory_note.html` | Claim-safe advisory copy block |
| `funnel_performance_report.html` | Sprint 40A funnel performance section |
| `data_quality_foundation_report.html` | Sprint 40A data quality section |
| `application_quality_foundation_report.html` | Sprint 40A application quality section |

**CSS:** minimal `.cf-report-*` styles in `static/css/components.css`

**Context assembly:** `build_reporting_foundation_context(user)` returns foundation reports plus legacy metrics context for backward compatibility.

---

## 6. Manual Workflow / Action-Link Safety

- All action links route to existing manual pages (application create/list/detail, evaluation queue, weekly review list).
- Reporting GET requests are read-only via `build_reporting_foundation_context`.
- No automatic status updates, submissions, email sending, or background polling.
- Extended analytics sections (weekly trend, source ROI, CV performance, rejections) remain in a dashed legacy block marked **Sprint 40B/C not in scope**.

---

## 7. Claim-Safety Confirmation

Sprint 40A reporting copy confirms CareerFunnel Tracker:

- Does not auto-apply or submit applications
- Does **not** change statuses automatically when reports are viewed
- Does **not** claim live SaaS deployment or external AI decisions
- Presents **advisory, evidence-based** guidance from stored records only

---

## 8. What Was Deliberately Not Changed

- Models, migrations, and database schema
- Dashboard templates and dashboard services
- Forms and export centre implementation (except existing manual links reused)
- Recruiter email workflow logic
- Interview prep workflow logic
- README public claims
- GitHub workflow files
- Sprint 40B source/CV/search reports (not expanded)
- Sprint 40C rejection pattern / weekly trend premium reports (not expanded)

---

## 9. Test Coverage Summary

**File:** `apps/metrics/tests.py`

| Test class | New tests | Focus |
| --- | ---: | --- |
| `PremiumReportingFoundationTests` | 10 | Foundation renders, shared components, claim safety, mutation safety, empty state, confidence badges, manual links, 40B/40C scope guard |

Key tests:

- `test_funnel_performance_report_renders`
- `test_data_quality_report_renders`
- `test_application_quality_report_renders`
- `test_reporting_foundation_uses_shared_report_components`
- `test_reporting_pages_are_claim_safe`
- `test_reporting_get_does_not_mutate_records`
- `test_reporting_empty_state_for_new_user`
- `test_reporting_confidence_badges_render`
- `test_reporting_links_remain_manual`
- `test_no_sprint_40b_or_40c_scope_leak`

Existing `MetricsViewTests` and service tests remain passing.

---

## 10. Validation Commands

```powershell
ruff check .
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test apps.metrics.tests
```

---

## Files Changed (Sprint 40A)

- `apps/metrics/services.py`
- `apps/metrics/views.py`
- `apps/metrics/tests.py`
- `templates/metrics/funnel_metrics.html`
- `templates/metrics/partials/*.html` (new)
- `static/css/components.css`
- `docs/evidence/sprint_40a_premium_reporting_foundation.md`
- `docs/evidence/evidence_index.md`

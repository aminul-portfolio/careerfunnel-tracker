# Sprint 40C - Rejection, Weekly Trend, Visual Evidence, and Export Centre Polish Evidence

## 1. Sprint Objective

Sprint 40C completes the Sprint 40 Premium Reporting Suite polish after Sprint 40A (foundation) and Sprint 40B (source/CV search/filter/pagination):

1. Rejection Patterns clarity and manual next actions
2. Weekly Trend advisory copy, sparse-data messaging, and chart evidence
3. Visual Analytics Evidence for reviewer interpretation
4. Export Centre manual-download polish
5. Sprint 40 reporting-suite evidence documentation

**Branch:** `sprint-40c-rejection-weekly-visual-export-polish`

---

## 2. Rejection Pattern Polish Summary

**Services:** `build_rejection_patterns_report(user)`, existing `build_rejection_pattern_report(user)`

| Improvement | Description |
| --- | --- |
| Sample-size note | Clearer low-volume warning (directional only, not predictions) |
| Advisory interpretation | Plain-English summary without automated decision language |
| Manual next action | Prominent recommended manual step per report state |
| Manual review actions | Existing recommendation list retained |
| Source/CV breakdown tables | Unchanged aggregates; copy clarifies manual review |
| Manual workflow links | Application list and evaluation queue |

Template: `templates/metrics/partials/rejection_patterns_report.html`

---

## 3. Weekly Trend Polish Summary

**Service:** `build_weekly_trend_report(user)`

| Improvement | Description |
| --- | --- |
| Advisory interpretation | Week-level context; warns against over-reading sparse data |
| Sparse-data message | Shown when fewer than two active weeks have applications |
| Chart evidence note | Chart.js from stored dates; no external BI platform |
| Rolling chart | Ten-week window always rendered; zero lines until data exists |
| Manual next action | Log across weeks, then compare table and chart manually |
| Manual workflow links | Application create and daily log list |

Template: `templates/metrics/partials/weekly_trend_report.html`

---

## 4. Visual Analytics Evidence Summary

**Service:** `build_visual_analytics_evidence()` (static claim-safe copy)

| Element | Description |
| --- | --- |
| Interpretation points | How to read funnel, weekly, and rejection visuals |
| Limitations | SQLite-only charts; no Tableau/Power BI/live SaaS dashboards |
| Data source note | Local database for signed-in user; refresh after logging |
| Manual links | Metrics reporting and Export Centre |

Template: `templates/metrics/partials/visual_analytics_evidence.html`

Does **not** claim Tableau, Power BI, live dashboards, production analytics, or SaaS customers as integrated features.

---

## 5. Export Centre Polish Summary

**Service:** `build_export_centre_context()` in `apps/exports/services.py`

| Improvement | Description |
| --- | --- |
| Manual notice | Each download is user-initiated; no schedule or background jobs |
| Button copy | "Download manually" / "Download full tracker (manual)" |
| Trust panel | On-demand exports from authenticated records only |
| Limitations list | No Gmail, OAuth, external BI, or scheduled delivery |
| Reporting link | Return to metrics reporting |

Template: `templates/exports/export_center.html`

Exports remain synchronous GET downloads of Excel workbooks - no fake automation.

---

## 6. Manual Workflow Safety

- Reporting GET requests remain read-only (no record mutation on page view).
- Export Centre downloads require explicit user clicks.
- No automatic status updates, submissions, email sending, or background polling.
- Rejection and weekly sections use manual workflow links only.
- Sprint 40A and 40B reporting behaviour preserved.

---

## 7. Claim-Safety Confirmation

Sprint 40C copy confirms CareerFunnel Tracker:

- Does **not** predict outcomes or make automatic screening decisions
- Does **not** integrate Tableau, Power BI, or live SaaS analytics
- Does **not** schedule exports or run background export jobs
- Does **not** auto-apply, OAuth, Gmail, calendar, or production deployment claims
- Presents **advisory, evidence-based** guidance from stored records

---

## 8. What Was Deliberately Not Changed

- Models, migrations, and database schema
- Dashboard templates and dashboard services
- Application forms
- Recruiter email and interview prep workflow logic
- Sprint 41 scope (not started)
- Skill Intelligence Engine
- GitHub workflow files and README public claims

---

## 9. Test Coverage Summary

| Test class | Focus |
| --- | --- |
| `PremiumReportingSprint40cTests` (7) | Rejection/weekly/visual copy, mutation safety, Sprint 41 guard, claim safety |
| `ExportCentrePolishTests` (4) | Manual export copy, GET downloads, no mutation on centre view |
| Updated `MetricsViewTests` | Weekly sparse-data message alignment |
| Updated `RejectionPatternReportTests` | Sample-warning text alignment |
| Updated shell audit | Metrics page title copy |
| Existing Sprint 40A/40B tests | Continue passing |

**Combined run:** metrics + exports polish + shell audit tests passing.

---

## 10. Validation Commands

```powershell
ruff check .
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test apps.metrics.tests apps.exports.tests tests.test_sprint_37a_shell_foundation_audit
```

---

## Files Changed (Sprint 40C)

- `apps/metrics/services.py`
- `apps/metrics/tests.py`
- `apps/exports/services.py`
- `apps/exports/views.py`
- `apps/exports/tests.py`
- `templates/metrics/funnel_metrics.html`
- `templates/metrics/partials/rejection_patterns_report.html` (new)
- `templates/metrics/partials/weekly_trend_report.html` (new)
- `templates/metrics/partials/visual_analytics_evidence.html` (new)
- `templates/exports/export_center.html`
- `static/css/components.css`
- `tests/test_sprint_37a_shell_foundation_audit.py`
- `docs/evidence/sprint_40c_rejection_weekly_visual_export_polish.md`
- `docs/evidence/evidence_index.md`

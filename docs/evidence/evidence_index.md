# CareerFunnel Tracker - Evidence Index

## Purpose

This document is the evidence index for CareerFunnel Tracker.

It gives reviewers, recruiters, and future maintainers a clear path through the project evidence: sprint checkpoints, screenshot proof, Git tags, test progression, analytics documentation, and what each artefact demonstrates.

CareerFunnel Tracker is positioned as a Django-based job-search intelligence and analytics platform. The evidence below proves that the project was built through controlled, tested, evidence-first sprints rather than one-off UI changes.

---

## Current Project Checkpoint

| Item | Current State |
|---|---|
| Current stable branch | `main` |
| Latest completed sprint | Sprint 14 — Weekly Trend Analytics + Documentation Integrity |
| Latest completed sprint tag | `sprint-14-complete` |
| Current verified test count | 176 tests passing |
| Main evidence folder | `docs/evidence/screenshots/` |
| Analytics documentation folder | `docs/analytics/` |

---

## Evidence Principles

CareerFunnel Tracker evidence follows these rules:

- Every major sprint should produce either code evidence, documentation evidence, screenshot evidence, or all three.
- UI screenshots must show real implemented pages, not mockups.
- Tests must pass before sprint commits are merged.
- Metrics and recommendations must be rule-based and evidence-based.
- No fake users, fake customers, fake AI claims, or hardcoded analytics values should be used.
- Documentation should explain what the project does, why it matters, and what limitations still exist.

---

# Sprint Evidence Summary

## Sprint 1 - Foundation + Dashboard Trust

### Status

Completed and tagged.

### Git Tag

```text
sprint-1-complete
```

### Main Evidence Screenshot

```text
docs/evidence/screenshots/sprint-1b-dashboard-trust-surfaces.png
```

### What This Screenshot Proves

- Dashboard page exists.
- Dashboard layout was upgraded from a basic interface into a more credible product surface.
- Real-data KPI cards are visible.
- Trust notes are visible.
- Dashboard content is based on stored tracker data.
- The project avoids fake dashboard metrics.

### Key Features Proven

- Foundation safety improvements.
- Application source choices improved.
- Job-fit scoring logic stabilised.
- Dashboard trust surfaces added.
- Real-data presentation approach established.

### Reviewer Value

This sprint proves the project has a stable base and a credible first impression.

---

## Sprint 2A - Source ROI + CV Version Performance

### Status

Completed and tagged.

### Git Tag

```text
sprint-2a-complete
```

### Main Evidence Screenshot

```text
docs/evidence/screenshots/sprint-2a-metrics-source-roi-cv-performance.png
```

### What This Screenshot Proves

- Metrics page includes Source ROI.
- Metrics page includes CV Version Performance.
- The platform groups outcomes by source.
- The platform groups outcomes by CV version.
- The UI explains performance tracking without pretending to be scientific A/B testing.
- Analytics are built from existing `JobApplication` records.

### Key Features Proven

- `build_source_roi(user)`
- `build_cv_version_performance(user)`
- Source-level response, interview, and offer metrics.
- CV-version-level response, interview, offer, and rejection metrics.
- Metrics UI tables.
- Service-layer tests.

### Reviewer Value

This sprint proves the project can turn raw application records into BI-style performance analysis.

---

## Sprint 2B - Rejection Pattern Analysis

### Status

Completed and tagged.

### Git Tag

```text
sprint-2b-complete
```

### Main Evidence Screenshot

```text
docs/evidence/screenshots/sprint-2b-rejection-pattern-analysis.png
```

### What This Screenshot Proves

- Metrics page includes Rejection Pattern Analysis.
- Total rejections and auto-rejections are visible.
- Rejection rates are calculated.
- Rejections are grouped by source.
- Rejections are grouped by CV version.
- Seniority or stretch-role risk is counted.
- Low-sample-size warning is shown where appropriate.
- Recommended actions are evidence-based.

### Key Features Proven

- `build_rejection_pattern_report(user)`
- Rejection status grouping.
- Auto-rejection analysis.
- Source-level rejection grouping.
- CV-version rejection grouping.
- Seniority-risk keyword detection.
- Evidence-based recommendation logic.

### Reviewer Value

This sprint proves the platform supports decision-making, not just passive reporting.

---

## Sprint 3 - Application Quality Intelligence

### Status

Completed and tagged.

### Git Tag

```text
sprint-3-complete
```

### Main Evidence Screenshot

```text
docs/evidence/screenshots/sprint-3-application-quality-report.png
```

### What This Screenshot Proves

- Metrics page includes Application Quality.
- The platform identifies applications with incomplete evidence.
- Missing CV version is tracked.
- Missing precise source is tracked.
- Missing job description is tracked.
- Missing required skills are tracked.
- Missing follow-up dates are tracked.
- Seniority or stretch-role risk is tracked.
- Applications needing action are shown.

### Key Features Proven

- `build_application_quality_report(user)`
- `ApplicationQualityIssue`
- `ApplicationQualityReport`
- Missing-field detection.
- Active-status follow-up detection.
- Seniority-risk detection.
- Recommended actions for application cleanup.

### Reviewer Value

This sprint proves the platform improves operational discipline and application-record quality.

---

## Sprint 4 - Data Quality + Analytics Governance

### Status

Completed and tagged.

### Git Tag

```text
sprint-4-complete
```

### Main Evidence Screenshot

```text
docs/evidence/screenshots/sprint-4-data-quality-analytics-governance.png
```

### Documentation Evidence

```text
docs/analytics/metric_definitions.md
docs/analytics/analytics_lineage.md
```

### What This Screenshot Proves

- Metrics page includes Data Quality.
- Analytics-ready application count is visible.
- Analytics-ready rate is visible.
- Data Quality Score is visible.
- Missing source and generic source counts are visible.
- Missing CV version, job description, required skills, and follow-up counts are visible.
- Data quality checks table is visible.
- Recommended cleanup actions are visible.

### What the Documentation Proves

`metric_definitions.md` proves:

- Metrics are governed and explainable.
- Each core metric has a business question, calculation, source field, value, and limitation.
- The project avoids black-box reporting.

`analytics_lineage.md` proves:

- The project follows Bronze -> Silver -> Gold analytics thinking.
- Raw records are transformed into cleaned logic and then business-ready outputs.
- The platform demonstrates Analytics Engineering principles.

### Key Features Proven

- `build_data_quality_report(user)`
- `DataQualityCheck`
- `DataQualityReport`
- Analytics-ready application logic.
- Data Quality Score.
- Completion-rate severity logic.
- Metric governance documentation.
- Analytics lineage documentation.

### Reviewer Value

This sprint proves the project is more than a Django CRUD app. It demonstrates data quality, metric governance, lineage, and reporting trust.

---

## Sprint 5 - Export + Evidence Centre

### Status

Completed and tagged.

### Git Tag

```text
sprint-5-complete
```

### Main Evidence Screenshot

```text
docs/evidence/screenshots/sprint-5-export-evidence-centre.png
```

### Documentation Evidence

```text
docs/evidence/evidence_index.md
README.md
```

### Sprint 5A Evidence

Commit:

```text
1818124 Sprint 5A: stabilise export routes and tests
```

What it proves:

- Existing export routes were reviewed.
- Missing `build_interviews_workbook` import was fixed.
- `export_notes` was protected with `@login_required`.
- Export-route tests were strengthened.
- Authenticated export access is tested.
- XLSX response content type and filename behaviour are tested.
- Unauthenticated redirects are tested.

### Sprint 5B Evidence

Commit:

```text
c0d878f Sprint 5B: upgrade export centre UI
```

What it proves:

- Export Centre page was upgraded.
- Template was reformatted from compressed markup into maintainable Django template structure.
- Full Tracker workbook export remains visible.
- Applications, Daily Logs, Weekly Reviews, Interview Prep, and Notes exports are visible.
- Trust and evidence note was added.
- Export links were preserved.

### Sprint 5C Evidence

This file:

```text
docs/evidence/evidence_index.md
```

What it proves:

- Evidence is organised.
- Sprint screenshots and tags are easy to review.
- Reviewer walkthrough path is documented.
- Project proof is traceable.

### Sprint 5D Evidence

README upgrade:

```text
README.md
```

What it proves:

- Project purpose is clear.
- Feature list is current.
- Analytics modules are explained.
- Screenshots and evidence are linked.
- Test status is visible.
- Known limitations are honest.
- Portfolio value is clear.

---

## Sprint 6 - UI Polish + Portfolio Presentation

### Status

Completed and tagged.

### Git Tag

```text
sprint-6-complete
```

### Main Evidence Screenshots

```text
docs/evidence/screenshots/sprint-6-dashboard-final-polish.png
docs/evidence/screenshots/sprint-6-metrics-final-polish.png
docs/evidence/screenshots/sprint-6-export-centre-final-polish.png
```

### Documentation Evidence

```text
docs/evidence/ui_polish_audit.md
docs/evidence/portfolio_presentation_notes.md
```

### What This Screenshot Set Proves

- Dashboard presentation was polished without changing analytics logic.
- Metrics page readability was improved while preserving rule-based calculations.
- Export Centre presentation remained reviewer-ready.
- Sprint 6 stayed within UI polish, screenshot evidence, and portfolio presentation scope.
- No fake users, fake customers, fake AI claims, or production deployment claims were introduced.

### Reviewer Value

This sprint proves the project can be polished for portfolio presentation while keeping claims honest and repository behaviour stable.

---

## Sprint 7 - Documentation Alignment + Deployment Preparation

### Status

Completed and tagged.

### Git Tag

```text
sprint-7-complete
```

### Main Evidence

```text
README.md
```

### What This Sprint Proves

- Project status documentation was aligned with the repository state.
- Optional deployment preparation notes were added without claiming live production hosting.

### Reviewer Value

This sprint proves documentation stays current as the project matures beyond early analytics sprints.

---

## Sprint 8 - Ruff Code Quality Cleanup

### Status

Completed and tagged.

### Git Tag

```text
sprint-8-complete
```

### Main Evidence

- Ruff-clean modules across applications, metrics, exports, AI agents, dashboard, and related apps.
- CI-style local verification remains passing.

### What This Sprint Proves

- Code quality tooling was applied repository-wide.
- Lint issues were resolved without changing analytics behaviour.

### Reviewer Value

This sprint proves the codebase is maintainable and review-ready for recruiters and technical interviewers.

---

## Sprint 9 - Today Action Panel

### Status

Completed and tagged.

### Git Tag

```text
sprint-9-complete
```

### What This Sprint Proves

- Dashboard includes a Today Action panel driven by stored records.
- Action logic is service-based and tested.

### Reviewer Value

This sprint proves the platform supports daily execution, not only retrospective reporting.

---

## Sprint 10 - Manual Follow-Up Email Draft

### Status

Completed and tagged.

### Git Tag

```text
sprint-10-complete
```

### What This Sprint Proves

- Manual follow-up email draft service and UI were added.
- Workflow remains user-controlled; no inbox automation is claimed.

### Reviewer Value

This sprint proves operational follow-up support without fake AI or email integration claims.

---

## Sprint 11 - Mark Follow-Up Sent Workflow

### Status

Completed and tagged.

### Git Tag

```text
sprint-11-complete
```

### What This Sprint Proves

- Users can mark follow-ups as sent through a manual workflow.
- UI copy clarifies the manual nature of the process.

### Reviewer Value

This sprint proves follow-up tracking stays honest and auditable.

---

## Sprint 12 - Status-Aware Follow-Up Action

### Status

Completed and tagged.

### Git Tag

```text
sprint-12-complete
```

### What This Sprint Proves

- Follow-up actions respect application pipeline status.
- Recommendations and actions avoid inappropriate stages.

### Reviewer Value

This sprint proves workflow logic is context-aware, not generic messaging only.

---

## Sprint 13 - Application Evidence Readiness

### Status

Completed and tagged.

### Git Tag

```text
sprint-13-complete
```

### What This Sprint Proves

- Application evidence readiness logic identifies whether records are strong enough for review.
- UI surfaces readiness on the application detail flow.

### Reviewer Value

This sprint proves the platform helps users improve record quality before analytics and exports rely on it.

---

## Sprint 14 - Weekly Trend Analytics + Documentation Integrity

### Status

Completed and tagged.

### Git Tag

```text
sprint-14-complete
```

### Commits

```text
6a9bb6d Sprint 14A: add weekly trend analytics service
3bd891c Sprint 14B: display weekly trend on funnel metrics
af2d9e7 Sprint 14C: optimize daily log aggregation
```

### Main Evidence Screenshot

```text
docs/evidence/screenshots/sprint-14-weekly-trend-analytics.png
```

Capture this screenshot manually from the Funnel Metrics Weekly Trend section before final Sprint 14 acceptance if the file is not yet in the repository.

### Documentation Evidence

```text
README.md
docs/analytics/metric_definitions.md
docs/evidence/evidence_index.md
```

### What This Sprint Proves

- `build_weekly_trend(user)` groups `JobApplication` records into Monday-starting weekly buckets (default 10 weeks).
- Zero-application weeks are included so the table shows a full lookback window.
- Response counts use existing `_RESPONSE_STATUSES`; response rate uses `safe_percentage()`.
- Funnel Metrics displays a Weekly Trend table (no chart in Sprint 14).
- `build_funnel_metrics()` aggregates `DailyLog` fields in one ORM `aggregate()` call instead of Python iteration.
- Metric definitions and evidence index reflect Sprints 7–14.

### Key Features Proven

- `WeeklyTrendRow` and `build_weekly_trend(user, weeks=10)`
- Funnel Metrics context: `weekly_trend_rows`, `weekly_trend_has_data`
- Weekly Trend section `id="weekly-trend"` with not-enough-data message when fewer than two active weeks exist
- DailyLog ORM aggregation with safe empty defaults
- Service and view tests for weekly trend and funnel metrics

### Reviewer Value

This sprint proves the project can add time-based funnel analytics with governed metrics, efficient aggregation, and reviewer-ready documentation—without charts, fake AI, or undeployed production claims.

---

# Screenshot Evidence Register

| Sprint | Screenshot File | Main Proof |
|---|---|---|
| Sprint 1B | `docs/evidence/screenshots/sprint-1b-dashboard-trust-surfaces.png` | Dashboard trust surfaces and real-data KPI presentation |
| Sprint 2A | `docs/evidence/screenshots/sprint-2a-metrics-source-roi-cv-performance.png` | Source ROI and CV Version Performance |
| Sprint 2B | `docs/evidence/screenshots/sprint-2b-rejection-pattern-analysis.png` | Rejection Pattern Analysis and recommendations |
| Sprint 3 | `docs/evidence/screenshots/sprint-3-application-quality-report.png` | Application Quality Report and applications needing action |
| Sprint 4 | `docs/evidence/screenshots/sprint-4-data-quality-analytics-governance.png` | Data Quality Score, checks, and analytics governance |
| Sprint 5 | `docs/evidence/screenshots/sprint-5-export-evidence-centre.png` | Export Centre and reviewer evidence flow |
| Sprint 6 | `docs/evidence/screenshots/sprint-6-dashboard-final-polish.png` | Dashboard final polish |
| Sprint 6 | `docs/evidence/screenshots/sprint-6-metrics-final-polish.png` | Metrics page final polish |
| Sprint 6 | `docs/evidence/screenshots/sprint-6-export-centre-final-polish.png` | Export Centre final polish |
| Sprint 14 | `docs/evidence/screenshots/sprint-14-weekly-trend-analytics.png` | Weekly Trend table on Funnel Metrics |

---

# Git Tag Register

| Tag | Meaning |
|---|---|
| `sprint-1-complete` | Foundation and dashboard trust checkpoint |
| `sprint-2a-complete` | Source ROI and CV Version Performance checkpoint |
| `sprint-2b-complete` | Rejection Pattern Analysis checkpoint |
| `sprint-3-complete` | Application Quality Intelligence checkpoint |
| `sprint-4-complete` | Data Quality and Analytics Governance checkpoint |
| `sprint-5-complete` | Export and Evidence Centre checkpoint |
| `sprint-6-complete` | UI polish and portfolio presentation checkpoint |
| `sprint-7-complete` | Documentation alignment and deployment preparation checkpoint |
| `sprint-8-complete` | Ruff code-quality cleanup checkpoint |
| `sprint-9-complete` | Today action panel checkpoint |
| `sprint-10-complete` | Manual follow-up email draft checkpoint |
| `sprint-11-complete` | Mark follow-up sent workflow checkpoint |
| `sprint-12-complete` | Status-aware follow-up action checkpoint |
| `sprint-13-complete` | Application evidence readiness checkpoint |
| `sprint-14-complete` | Weekly Trend analytics, Funnel Metrics table, DailyLog aggregation, and documentation checkpoint |

---

# Test Count Progression

| Checkpoint | Test Count | Notes |
|---|---:|---|
| Sprint 1 complete | 81 | Foundation safety, dashboard trust, early regression coverage |
| Sprint 2A complete | 96 | Source ROI and CV Version Performance tests added |
| Sprint 2B complete | 107 | Rejection Pattern Analysis tests added |
| Sprint 3 complete | 119 | Application Quality Report tests added |
| Sprint 4 complete | 134 | Data Quality Report tests added |
| Sprint 5 complete | 133 | Export tests consolidated into broader route coverage using subtests |
| Sprint 6 complete | 133 | UI polish and documentation work preserved existing test coverage |
| Sprint 13 complete | 161 | Application evidence readiness and follow-up workflow tests |
| Sprint 14 complete | 176 | Weekly trend service, funnel metrics UI, and DailyLog aggregation tests |

## Test Count Note

A lower test count does not always mean weaker coverage.

In Sprint 5A, export tests were consolidated into loop-based `subTest` coverage. This reduced the raw number of Django test methods while improving route coverage across export endpoints.

---

# Reviewer Walkthrough Path

Use this order when reviewing the project.

## 1. Start With README

```text
README.md
```

Purpose:

- Understand the project problem.
- Review the feature list.
- See the tech stack.
- Follow setup instructions.
- Find screenshots and evidence links.

## 2. Review Dashboard Screenshot

```text
docs/evidence/screenshots/sprint-1b-dashboard-trust-surfaces.png
```

Purpose:

- Confirm the project has a credible dashboard surface.
- See real-data KPI presentation.

## 3. Review Metrics Screenshots

```text
docs/evidence/screenshots/sprint-2a-metrics-source-roi-cv-performance.png
docs/evidence/screenshots/sprint-2b-rejection-pattern-analysis.png
docs/evidence/screenshots/sprint-3-application-quality-report.png
docs/evidence/screenshots/sprint-4-data-quality-analytics-governance.png
docs/evidence/screenshots/sprint-6-metrics-final-polish.png
docs/evidence/screenshots/sprint-14-weekly-trend-analytics.png
```

Purpose:

- Follow the analytics depth progression.
- Confirm metrics, decision support, data quality logic, and weekly trend table.

## 4. Review Analytics Documentation

```text
docs/analytics/metric_definitions.md
docs/analytics/analytics_lineage.md
```

Purpose:

- Understand how metrics are calculated.
- Understand the Bronze -> Silver -> Gold lineage.
- Confirm governance and limitations.

## 5. Review Export Centre

```text
/export/
docs/evidence/screenshots/sprint-6-export-centre-final-polish.png
```

Purpose:

- Confirm workbook exports are available.
- Confirm tracker data can be reviewed or backed up.
- Confirm no fake export data is used.

## 6. Review Tests

```powershell
python manage.py test
```

Purpose:

- Confirm service-layer analytics logic is tested.
- Confirm export routes are protected and functional.
- Confirm the repository is stable.

---

# Feature-to-Evidence Map

| Feature | Evidence Type | Evidence Location |
|---|---|---|
| Dashboard trust surface | Screenshot | `docs/evidence/screenshots/sprint-1b-dashboard-trust-surfaces.png` |
| Source ROI | Screenshot + tests | Sprint 2A screenshot, `apps/metrics/tests.py` |
| CV Version Performance | Screenshot + tests | Sprint 2A screenshot, `apps/metrics/tests.py` |
| Rejection Pattern Analysis | Screenshot + tests | Sprint 2B screenshot, `apps/metrics/tests.py` |
| Application Quality Report | Screenshot + tests | Sprint 3 screenshot, `apps/metrics/tests.py` |
| Data Quality Report | Screenshot + tests + docs | Sprint 4 screenshot, `apps/metrics/tests.py`, `docs/analytics/` |
| Weekly Trend | Screenshot + tests + docs | Sprint 14 screenshot, `apps/metrics/services.py`, `apps/metrics/tests.py`, `docs/analytics/metric_definitions.md` |
| Metric governance | Documentation | `docs/analytics/metric_definitions.md` |
| Analytics lineage | Documentation | `docs/analytics/analytics_lineage.md` |
| Export Centre | UI + tests | `/export/`, `apps/exports/tests.py` |
| Export route protection | Tests | `apps/exports/tests.py` |

---

# What This Project Demonstrates

CareerFunnel Tracker demonstrates:

- Django application development.
- Service-layer analytics design.
- BI-style reporting logic.
- Data quality checks.
- Metric governance.
- Analytics lineage.
- Export workflows.
- Evidence-first sprint delivery.
- Test-driven stability.
- Recruiter-friendly documentation.

---

# What This Project Does Not Claim

The project does not claim:

- Real paying customers.
- Production SaaS scale.
- Live AI automation.
- Gmail inbox automation.
- Scientific CV A/B testing.
- Financial ROI calculation.
- Enterprise data warehouse architecture.
- Fully deployed commercial platform unless deployment is added later.

These limitations are intentional and documented to keep the portfolio honest.

---

# Current Known Limitations

- Status history is not tracked yet.
- Stage transition events are not modelled yet.
- Rejection reasons are not independently verified.
- Seniority-risk detection is keyword-based.
- CV Version Performance is directional, not scientific A/B testing.
- Source ROI means channel outcome performance, not financial ROI.
- Weekly Trend uses `date_applied`, not response date.
- Export files are workbook exports, not automated BI pipelines.
- No live LLM or AI integration is active.
- No Gmail / Smart Inbox integration is active.
- No Celery / Redis background processing is active.

---

# Evidence Quality Checklist

Before considering a sprint complete, confirm:

- [ ] `python manage.py check` passes
- [ ] `python manage.py makemigrations --check --dry-run` passes
- [ ] `python manage.py test` passes
- [ ] `git status` is clean
- [ ] screenshot evidence is saved if UI changed
- [ ] screenshot file name is clear
- [ ] commit message is specific
- [ ] sprint tag is created after merge
- [ ] Notion is updated
- [ ] evidence index is updated if needed

---

# Final Reviewer Summary

CareerFunnel Tracker is a job-search analytics platform built with Django.

Its evidence shows a progression from a stable tracker into a more complete analytics product:

```text
Sprint 1:
Foundation and dashboard trust

Sprint 2:
Source ROI, CV Version Performance, and Rejection Pattern Analysis

Sprint 3:
Application Quality Intelligence

Sprint 4:
Data Quality, Metric Definitions, and Analytics Lineage

Sprint 5:
Exports, Evidence Centre, and reviewer handoff

Sprint 6:
UI polish, final screenshot evidence, and portfolio presentation notes

Sprint 7–13:
Documentation alignment, code quality, dashboard actions, manual follow-up workflows, and application evidence readiness

Sprint 14:
Weekly trend analytics, Funnel Metrics table display, DailyLog aggregation optimization, and documentation integrity
```

The strongest portfolio signal is that the project does not only display data. It explains where the data comes from, how it is transformed, what each metric means, what limitations exist, and what action the user should take next.

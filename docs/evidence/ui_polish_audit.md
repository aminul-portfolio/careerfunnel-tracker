# CareerFunnel Tracker - UI Polish Audit

## Purpose

This document defines the Sprint 6 UI polish scope for CareerFunnel Tracker.

The goal is to improve reviewer first impression, readability, and portfolio presentation without changing backend logic, analytics calculations, models, migrations, or core product behaviour.

Sprint 6 should polish what already exists. It should not become a redesign sprint or a new feature sprint.

---

## Current Baseline

| Area | Current State |
|---|---|
| Stable branch before Sprint 6 | `main` |
| Sprint 6 branch | `sprint-6-ui-polish-portfolio-presentation` |
| Latest completed tag | `sprint-5-complete` |
| Current verified tests before Sprint 6 | 133 passing |
| Current product stage | Analytics, export, evidence, and documentation foundation complete |
| Main risk | Over-polishing, accidental redesign, or touching backend logic unnecessarily |

---

## Sprint 6 Principle

Sprint 6 should follow this rule:

```text
Improve presentation without changing product logic.
```

Allowed improvement types:

- Copy clarity
- Section hierarchy
- Table readability
- Empty-state clarity
- Screenshot readiness
- Minor layout consistency
- Documentation for portfolio presentation

Avoid:

- New analytics services
- New models
- Migrations
- New routes
- Chart.js
- JavaScript features
- LLM / AI integration
- Full redesign
- Fake data or fake claims

---

# Page-by-Page UI Audit

| Page / Area | Current Observation | Priority | Risk | Proposed Action |
|---|---|---:|---:|---|
| Dashboard | Strong first impression already exists. KPI cards, diagnosis, recent records, and trust notes are visible. | Medium | Low | Light copy/spacing polish only. Preserve current layout. |
| Metrics | Most powerful page but very long. Contains Funnel Metrics, Source ROI, CV Performance, Rejection Patterns, Application Quality, and Data Quality. | High | Medium | Improve readability, section hierarchy, and table scanning. Do not change calculations. |
| Export Centre | Improved in Sprint 5. Clear export cards and trust note are present. | Medium | Low | Light polish only. Ensure final screenshot looks clean. |
| Applications | Core data-entry/review area. Important but not the highest Sprint 6 priority unless obvious visual issues appear. | Medium | Medium | Inspect after Metrics/Dashboard. Avoid form redesign unless needed. |
| Follow-ups | Operational workflow area. Useful for job-search discipline. | Low | Low | Keep as-is unless an obvious empty-state/copy issue appears. |
| Interview Prep | Supports interview-readiness story. | Low | Low | Keep as-is unless final portfolio screenshots need it. |
| Daily Logs | Supports activity tracking and daily discipline. | Low | Low | Keep as-is unless obvious readability issues appear. |
| Weekly Reviews | Supports review workflow and diagnosis. | Low | Low | Keep as-is unless obvious table/readability issue appears. |
| Notes | Supports decisions, lessons, and strategy. | Low | Low | Keep as-is unless empty state or list readability needs a minor improvement. |
| AI Agents / Deterministic Assistance | Needs careful wording to avoid exaggerated AI claims. | Medium | Medium | Use “deterministic assistance” or “rule-based assistant” wording where relevant. Avoid live AI claims. |

---

# Priority Definitions

| Priority | Meaning |
|---|---|
| High | Important for recruiter/reviewer first impression or central product value |
| Medium | Useful polish but not required before screenshots |
| Low | Safe to leave unchanged unless time allows |

---

# Risk Definitions

| Risk | Meaning |
|---|---|
| Low | Copy/template-only change with minimal breakage risk |
| Medium | Template or layout change that could affect readability or responsiveness |
| High | Backend, model, migration, URL, or feature behaviour change; avoid in Sprint 6 |

---

# Sprint 6 Recommended Actions

## Sprint 6A - UI Polish Audit + Encoding Cleanup

Status: In progress.

Scope:

- Create this audit document.
- Fix visible encoding issue in `templates/metrics/funnel_metrics.html`.
- Keep all product logic unchanged.

Allowed files:

```text
docs/evidence/ui_polish_audit.md
templates/metrics/funnel_metrics.html
```

Acceptance:

- Audit document exists.
- Encoding issue is fixed.
- No Python files changed.
- No CSS changed.
- Tests still pass.

---

## Sprint 6B - Metrics Page Readability Polish

Recommended focus:

- Add clearer section grouping.
- Improve long-page scanning.
- Strengthen short explanatory notes.
- Make table sections easier to review.
- Keep all existing metrics and context variables.
- Avoid any backend or service changes.

Likely allowed files:

```text
templates/metrics/funnel_metrics.html
static/css/components.css
```

Acceptance:

- Metrics page remains functionally identical.
- Existing analytics sections remain visible.
- No service logic changes.
- Tests pass.
- Browser check completed.

---

## Sprint 6C - Dashboard + Export Centre Light Presentation Polish

Recommended focus:

- Dashboard hero and trust/evidence copy.
- Export Centre reviewer journey copy.
- Consistent card language.
- No new export logic.
- No dashboard backend changes.

Likely allowed files:

```text
templates/dashboard/overview.html
templates/exports/export_center.html
static/css/components.css
```

Acceptance:

- Dashboard and Export Centre look more portfolio-ready.
- Existing links and data remain unchanged.
- Tests pass.
- Browser check completed.

---

## Sprint 6D - Final Screenshot Set

Recommended screenshot files:

```text
docs/evidence/screenshots/sprint-6-dashboard-final-polish.png
docs/evidence/screenshots/sprint-6-metrics-final-polish.png
docs/evidence/screenshots/sprint-6-export-centre-final-polish.png
```

Optional if useful:

```text
docs/evidence/screenshots/sprint-6-application-quality-final-polish.png
docs/evidence/screenshots/sprint-6-data-quality-final-polish.png
```

Acceptance:

- Screenshots are saved in `docs/evidence/screenshots/`.
- Screenshots show real implemented pages.
- No fake data or fake customer claims are introduced.

---

## Sprint 6E - Portfolio Presentation Notes

Create:

```text
docs/evidence/portfolio_presentation_notes.md
```

Recommended sections:

- 30-second recruiter summary
- 2-minute walkthrough
- Top 5 features
- Strongest technical proof
- Strongest analytics proof
- Known limitations
- How the project maps to Data Analyst / BI / Analytics Engineer roles

Acceptance:

- Document is concise and recruiter-ready.
- No exaggerated claims.
- Limitations remain honest.

---

## Sprint 6F - Merge + Tag

Final completion steps:

```text
git status
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Then:

```text
merge into main
tag sprint-6-complete
update Notion
```

---

# Out of Scope for Sprint 6

Do not add:

- Gmail / Smart Inbox
- LLM integration
- StageEvent model
- Celery / Redis
- Chart.js-heavy dashboards
- PDF export
- Excel export redesign
- New database models
- Migrations
- Deployment work
- Billing or SaaS commercial features
- Fake customers
- Fake users
- Fake AI claims
- Major product redesign

---

# Final Sprint 6 Success Criteria

Sprint 6 is successful when:

- UI polish audit exists.
- Metrics page readability is improved.
- Dashboard and Export Centre presentation are lightly polished.
- Final screenshot set is saved.
- Portfolio presentation notes exist.
- All tests pass.
- No migrations are created.
- No analytics logic is broken.
- Sprint is merged into `main`.
- Tag `sprint-6-complete` is created.
- Notion is updated.

---

# Reviewer Interpretation

After Sprint 6, CareerFunnel Tracker should feel like a polished, evidence-based analytics portfolio product.

The reviewer should quickly understand:

```text
What the app does
What analytics it provides
How the data is governed
What evidence proves the work
Why the project is relevant to DA / BI / AE roles
```

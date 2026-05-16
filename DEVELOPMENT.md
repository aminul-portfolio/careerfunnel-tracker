# CareerFunnel Tracker

CareerFunnel Tracker is a Django-based job-search intelligence and analytics platform.

It helps track job applications, daily activity, weekly reviews, follow-ups, interview preparation, notes, metrics, data quality, and exportable evidence. The project is designed as a realistic portfolio data product for Data Analyst, BI Analyst, Reporting Analyst, Analytics Engineer, Junior Data Engineer, and FinTech analytics roles.

It is more than a basic job tracker. It turns job-search records into explainable analytics, quality checks, recommendations, and reviewer-ready evidence.

---

## Project Purpose

CareerFunnel Tracker answers practical job-search questions such as:

- Which application sources are producing better outcomes?
- Which CV versions are linked to stronger or weaker results?
- Where are applications being rejected?
- Which records are incomplete or weak for analysis?
- Is the dataset complete enough for reliable reporting?
- What actions should happen next?

The platform is intentionally evidence-based. It uses deterministic service-layer logic and stored records. It does not rely on external AI APIs, fake users, fake customers, or hardcoded analytics numbers.

---

## Current Status

| Item | Status |
|---|---|
| Current stable branch | `main` |
| Latest completed sprint | Sprint 16 — Analytics-Critical Field Warnings + Data Quality Impact Reporting |
| Latest completed sprint tag | `sprint-16-complete` |
| Current verified tests | 233 passing |
| Main analytics documentation | `docs/analytics/` |
| Evidence documentation | `docs/evidence/` |
| Screenshot evidence folder | `docs/evidence/screenshots/` |

Note: Sprint 5 consolidated several export-route tests into broader `subTest` coverage, so the raw test count reduced from 134 to 133 while export route coverage improved. Sprint 14 adds weekly trend service, UI, and DailyLog aggregation tests (176 total at Sprint 14 completion). Sprint 15 adds shared role-fit constants, intake-to-application prefill, Evaluation Queue, and Application Detail Fit Review tests (204 total at Sprint 15 completion). Sprint 16 adds save-quality warning service, post-save advisory warnings, and Data Quality Report analytics impact notes (233 total at Sprint 16 completion).

---

## Key Features

### Core Tracking

- Application tracker with company, role, source, status, CV version, job description, required skills, role fit, and follow-up date
- Daily target vs actual activity logging
- Weekly review and diagnostic reflection workflow
- Follow-up tracking
- Interview preparation records
- Notes and decision log
- User-specific authenticated records

### Analytics and Decision Support

- Funnel Metrics
- Weekly Trend (Monday-starting weekly buckets on Funnel Metrics)
- Source ROI
- CV Version Performance
- Rejection Pattern Analysis
- Application Quality Report
- Data Quality Report
- Evidence-based recommended actions
- Low-sample-size warnings where appropriate

### Export and Evidence

- Export Centre for workbook downloads
- Applications export
- Daily Logs export
- Weekly Reviews export
- Interview Prep export
- Notes export
- Full Tracker workbook export
- Evidence index documentation
- Screenshot evidence by sprint

### Documentation

- Metric definitions
- Analytics lineage
- Evidence index
- Sprint-based project operating record

---

## Analytics Modules

### Funnel Metrics

Shows the core job-search funnel:

- Total Applications
- Response Rate
- Interview Rate
- Offer Rate
- Stage-by-stage funnel breakdown
- Daily target vs actual activity
- Weekly Trend table (applications, responses, and response rate by Monday-starting week)

### Source ROI

Groups applications by source and calculates:

- Applications
- Responses
- Response Rate
- Interviews
- Interview Rate
- Offers
- Offer Rate

This helps compare channels such as LinkedIn, Reed.co.uk, Indeed, company websites, recruiters, and referrals.

### CV Version Performance

Groups applications by CV version and calculates:

- Applications
- Responses
- Response Rate
- Interviews
- Interview Rate
- Offers
- Offer Rate
- Rejections
- Rejection Rate

This is performance tracking, not scientific A/B testing.

### Rejection Pattern Analysis

Analyses rejection outcomes using:

- Total Rejections
- Auto-Rejections
- Rejection Rate
- Auto-Rejection Rate
- Rejections by Source
- Rejections by CV Version
- Seniority or stretch-role risk count
- Evidence-based recommended actions

### Application Quality Report

Flags incomplete or weak application records, including:

- Missing CV version
- Missing precise source
- Missing or thin job description
- Missing required skills
- Missing follow-up date
- Seniority or stretch-role risk

### Data Quality Report

Summarises analytics readiness and data trust:

- Analytics-ready applications
- Analytics-ready rate
- Data Quality Score
- Missing source count
- Generic source count
- Missing CV version count
- Missing job description count
- Missing required skills count
- Missing follow-up date count
- Data quality checks
- Recommended cleanup actions

---

## Export Centre

The Export Centre provides workbook downloads for review, backup, and BI-style analysis.

Available exports:

- Full Tracker Workbook
- Applications Export
- Daily Logs Export
- Weekly Reviews Export
- Interview Prep Export
- Notes and Decisions Export

Exports are generated from authenticated user records. No fake export data is used.

---

## Evidence and Documentation

### Screenshot Evidence

| Sprint | Evidence File | Proof |
|---|---|---|
| Sprint 1B | `docs/evidence/screenshots/sprint-1b-dashboard-trust-surfaces.png` | Dashboard trust surfaces |
| Sprint 2A | `docs/evidence/screenshots/sprint-2a-metrics-source-roi-cv-performance.png` | Source ROI and CV Version Performance |
| Sprint 2B | `docs/evidence/screenshots/sprint-2b-rejection-pattern-analysis.png` | Rejection Pattern Analysis |
| Sprint 3 | `docs/evidence/screenshots/sprint-3-application-quality-report.png` | Application Quality Report |
| Sprint 4 | `docs/evidence/screenshots/sprint-4-data-quality-analytics-governance.png` | Data Quality and Analytics Governance |
| Sprint 5 | `docs/evidence/screenshots/sprint-5-export-evidence-centre.png` | Export and Evidence Centre |
| Sprint 6 | `docs/evidence/screenshots/sprint-6-dashboard-final-polish.png` | Dashboard final polish |
| Sprint 6 | `docs/evidence/screenshots/sprint-6-metrics-final-polish.png` | Metrics final polish |
| Sprint 6 | `docs/evidence/screenshots/sprint-6-export-centre-final-polish.png` | Export Centre final polish |
| Sprint 14 | `docs/evidence/screenshots/sprint-14-weekly-trend-analytics.png` | Weekly Trend on Funnel Metrics |
| Sprint 15 | `docs/evidence/screenshots/sprint-15-conversion-bridge.png` | Job Posting Analyzer Save as Application prefill bridge |
| Sprint 15 | `docs/evidence/screenshots/sprint-15-evaluation-queue.png` | Evaluation Queue for Job Found / Fit Checked roles |
| Sprint 16 | `docs/evidence/screenshots/sprint-16-quality-warnings.png` | Post-save advisory quality warnings on application create/update |
| Sprint 16 | `docs/evidence/screenshots/sprint-16-data-quality-impact-report.png` | Data Quality Report Analytics Impact notes |

### Documentation Files

| File | Purpose |
|---|---|
| `docs/analytics/metric_definitions.md` | Defines metrics, calculations, source fields, business questions, and limitations |
| `docs/analytics/analytics_lineage.md` | Explains Bronze -> Silver -> Gold analytics lineage |
| `docs/evidence/evidence_index.md` | Lists screenshot proof, sprint tags, test progression, and reviewer walkthrough path |

---

## Sprint History

| Sprint | Status | Tag / Branch | Main Outcome |
|---|---|---|---|
| Sprint 1 | Completed | `sprint-1-complete` | Foundation safety and dashboard trust surfaces |
| Sprint 2A | Completed | `sprint-2a-complete` | Source ROI and CV Version Performance |
| Sprint 2B | Completed | `sprint-2b-complete` | Rejection Pattern Analysis |
| Sprint 3 | Completed | `sprint-3-complete` | Application Quality Intelligence |
| Sprint 4 | Completed | `sprint-4-complete` | Data Quality and Analytics Governance |
| Sprint 5 | Completed | `sprint-5-complete` | Export Centre and evidence handoff |
| Sprint 6 | Completed | `sprint-6-complete` | UI polish and portfolio presentation |
| Sprint 7 | Completed | `sprint-7-complete` | Documentation alignment and optional deployment preparation |
| Sprint 8 | Completed | `sprint-8-complete` | Ruff code-quality cleanup across modules |
| Sprint 9 | Completed | `sprint-9-complete` | Today action panel on dashboard |
| Sprint 10 | Completed | `sprint-10-complete` | Manual follow-up email draft service and UI |
| Sprint 11 | Completed | `sprint-11-complete` | Manual mark follow-up sent workflow |
| Sprint 12 | Completed | `sprint-12-complete` | Status-aware follow-up action |
| Sprint 13 | Completed | `sprint-13-complete` | Application evidence readiness |
| Sprint 14 | Completed | `sprint-14-complete` | Weekly Trend analytics, Funnel Metrics weekly trend table, DailyLog ORM aggregation optimization, documentation updates, and screenshot evidence |
| Sprint 15 | Completed | `sprint-15-complete` | Shared role-fit constants, Job Posting Analyzer to Add Application prefill bridge, Evaluation Queue, Application Detail Fit Review, and screenshot evidence |
| Sprint 16 | Completed | `sprint-16-complete` | Save-quality warnings service, post-save advisory warnings, accurate Source ROI wording, Data Quality Report Analytics Impact notes, and screenshot evidence |

**Sprint 14 detail:** `build_weekly_trend()` groups applications into Monday-starting weeks; the Funnel Metrics page shows a weekly trend table (no chart); `build_funnel_metrics()` uses one ORM `aggregate()` call for DailyLog totals; metric definitions and evidence index were updated; screenshot evidence is stored at `docs/evidence/screenshots/sprint-14-weekly-trend-analytics.png`.

**Sprint 15 detail:** Role-fit scoring lists are unified in `apps/job_intelligence/constants.py` for Job Posting Analyzer and Smart Review; the analyzer can open a pre-filled Add Application form via GET parameters (the user must review and submit before anything is saved); Evaluation Queue lists opportunities at Job Found or Fit Checked; Application Detail shows a compact rule-based Fit Review summary; screenshot evidence paths are documented in `docs/evidence/evidence_index.md`.

**Sprint 16 detail:** `SaveQualityWarning` and `build_save_quality_warnings()` flag analytics-critical gaps on saved applications; create and update views show advisory Django warning messages after a successful save (non-blocking, no `form.add_error()`); Source warnings use accurate “cannot attribute / grouped under Other” wording; the Data Quality Report adds quantified Analytics Impact notes explaining which reports are affected by current gaps; screenshot evidence paths are documented in `docs/evidence/evidence_index.md`.

---

## Tech Stack

- Python
- Django
- SQLite for local development
- Django Templates
- HTML / CSS / JavaScript
- OpenPyXL
- WhiteNoise
- Git
- GitHub Actions CI, if enabled in repository

---

## Project Structure

```text
apps/
  accounts/
  dashboard/
  applications/
  ai_agents/
  followups/
  interviews/
  daily_log/
  weekly_review/
  metrics/
  job_intelligence/
  notes/
  exports/

docs/
  analytics/
    metric_definitions.md
    analytics_lineage.md
  evidence/
    evidence_index.md
    screenshots/
```

---

## Local Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run migrations:

```bash
python manage.py migrate
```

Seed demo data, if the command is available:

```bash
python manage.py seed_demo_data
```

Start the server:

```bash
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

---

## Optional Deployment Preparation

Deployment is optional and would require environment-specific setup. The project already includes `gunicorn` and `whitenoise` in `requirements.txt`, and WhiteNoise static-file settings are configured.

Before any hosted deployment, set `SECRET_KEY`, `DEBUG=False`, and `ALLOWED_HOSTS` for the target environment. SQLite is used for local development, so a real hosted deployment would also need a production database configuration. Run `python manage.py collectstatic` during deployment preparation.

---

## Demo Login

```text
Username: demo
Password: DemoPass12345
```

If demo credentials are changed later, update this section before sharing the project publicly.

---

## Run Tests

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Current stable verification:

```text
python manage.py check - passing
python manage.py makemigrations --check --dry-run - no changes detected
python manage.py test - 233 tests passing
```

---

## Deterministic Assistance Layer

The project includes a local deterministic assistance layer under `apps/ai_agents/`.

These features use rule-based logic and run without external API keys. They demonstrate decision-support workflows without making live AI or LLM claims.

Examples include:

- Job Posting Analyzer
- Next Best Action logic
- Follow-Up Message Writer
- Interview Prep Generator
- Weekly Coach
- CV Gap-style checks
- Cover Letter Quality checks
- Smart Notifications Centre

These should be understood as local rule-based assistants, not external AI agents.

---

## Portfolio Value

CareerFunnel Tracker demonstrates:

- Django application architecture
- Authenticated user-specific data
- Service-layer analytics design
- BI-style KPI reporting
- Data quality checks
- Metric governance
- Analytics lineage
- Export workflows
- Evidence-first sprint delivery
- Automated testing
- Reviewer-friendly documentation

The project is relevant to:

- Data Analyst roles
- BI Analyst roles
- Reporting Analyst roles
- Analytics Engineer roles
- Junior Data Engineer roles
- FinTech analytics roles

---

## Known Limitations

The current version is intentionally realistic and scoped.

Known limitations:

- Status history is not tracked yet.
- Stage transition events are not modelled yet.
- Rejection reasons are not independently verified.
- Seniority-risk detection is keyword-based.
- CV Version Performance is directional, not scientific A/B testing.
- Source ROI means channel outcome performance, not financial ROI.
- Weekly Trend uses application date (`date_applied`), not response date.
- Export files are workbook exports, not automated BI pipelines.
- No live LLM integration is active.
- Fit Review and Job Posting Analyzer scoring are rule-based and local, not live AI/API integrations.
- Job Posting Analyzer pre-fills the Add Application form only; it does not save or submit applications automatically.
- No Gmail / Smart Inbox integration is active.
- No Celery / Redis background processing is active.
- No production SaaS billing or multi-tenant commercial layer is active.

---

## Reviewer Walkthrough

Recommended review order:

1. Read this README.
2. Open the dashboard.
3. Open the Metrics page.
4. Review Weekly Trend, Source ROI, CV Version Performance, Rejection Pattern Analysis, Application Quality, and Data Quality.
5. Open the Export Centre.
6. Review `docs/analytics/metric_definitions.md`.
7. Review `docs/analytics/analytics_lineage.md`.
8. Review `docs/evidence/evidence_index.md`.
9. Run the test suite.

---

## Recruiter-Friendly Summary

CareerFunnel Tracker is a Django-based job-search intelligence platform that turns application activity into analytics, evidence, and decision support. It tracks applications, daily targets, weekly reviews, follow-ups, interview preparation, notes, and exports. It also provides funnel metrics, source performance, CV version performance, rejection patterns, application quality checks, data quality governance, and reviewer-ready documentation.

The project demonstrates Django development, analytics engineering thinking, BI-style reporting, data quality logic, export workflows, and evidence-based portfolio delivery.

---

## Sprint 17 Note

This file preserves the previous internal/development-focused README content after Sprint 17A moved the repository front door to a recruiter-facing case study.

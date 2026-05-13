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
| Current sprint branch | `sprint-5-export-evidence-centre` |
| Latest completed sprint tag | `sprint-4-complete` |
| Current verified tests | 133 passing on Sprint 5 branch |
| Main analytics documentation | `docs/analytics/` |
| Evidence documentation | `docs/evidence/` |
| Screenshot evidence folder | `docs/evidence/screenshots/` |

Note: Sprint 5 consolidated several export-route tests into broader `subTest` coverage, so the raw test count reduced from 134 to 133 while export route coverage improved.

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
| Sprint 5 | `docs/evidence/screenshots/sprint-5-export-evidence-centre.png` | Export and Evidence Centre, to be added after Sprint 5 UI evidence |

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
| Sprint 5 | In progress | `sprint-5-export-evidence-centre` | Export Centre and evidence handoff |

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
├── accounts/
├── dashboard/
├── applications/
├── ai_agents/
├── followups/
├── interviews/
├── daily_log/
├── weekly_review/
├── metrics/
├── notes/
└── exports/

docs/
├── analytics/
│   ├── metric_definitions.md
│   └── analytics_lineage.md
└── evidence/
    ├── evidence_index.md
    └── screenshots/
```

If your terminal displays box characters incorrectly, the same structure is:

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

Current Sprint 5 branch verification:

```text
python manage.py check - passing
python manage.py makemigrations --check --dry-run - no changes detected
python manage.py test - 133 tests passing
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
- Export files are workbook exports, not automated BI pipelines.
- No live LLM integration is active.
- No Gmail / Smart Inbox integration is active.
- No Celery / Redis background processing is active.
- No production SaaS billing or multi-tenant commercial layer is active.

---

## Reviewer Walkthrough

Recommended review order:

1. Read this README.
2. Open the dashboard.
3. Open the Metrics page.
4. Review Source ROI, CV Version Performance, Rejection Pattern Analysis, Application Quality, and Data Quality.
5. Open the Export Centre.
6. Review `docs/analytics/metric_definitions.md`.
7. Review `docs/analytics/analytics_lineage.md`.
8. Review `docs/evidence/evidence_index.md`.
9. Run the test suite.

---

## Recruiter-Friendly Summary

CareerFunnel Tracker is a Django-based job-search intelligence platform that turns application activity into analytics, evidence, and decision support. It tracks applications, daily targets, weekly reviews, follow-ups, interview preparation, notes, and exports. It also provides funnel metrics, source performance, CV version performance, rejection patterns, application quality checks, data quality governance, and reviewer-ready documentation.

The project demonstrates Django development, analytics engineering thinking, BI-style reporting, data quality logic, export workflows, and evidence-based portfolio delivery.

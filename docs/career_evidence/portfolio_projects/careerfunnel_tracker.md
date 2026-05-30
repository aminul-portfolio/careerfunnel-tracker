# Project Evidence Review -- CareerFunnel Tracker

## Project Identity

| Field | Value |
|---|---|
| Project name | CareerFunnel Tracker |
| GitHub URL | https://github.com/aminul-portfolio/careerfunnel-tracker |
| Latest visible tag/release | sprint-29d-evidence-documentation-complete |
| Latest visible commit | 1189a2c -- Merge sprint-29d evidence documentation |
| Current branch | main |
| Evidence checked date | 22 May 2026 |
| Evidence source | Current repository + terminal validation proof |
| Local validation | Complete |

## Project Goal

Django-based job-search intelligence and analytics platform that turns application activity into explainable funnel metrics, source/CV performance reporting, data-quality signals, workbook exports, interview evidence, and recruiter-ready portfolio proof.

## Target Roles

- Data Analyst
- BI Analyst
- Reporting Analyst
- Analytics Engineer
- Junior Data Engineer
- Python/Django data-product roles
- FinTech analytics roles

## Implemented Features

- Application tracking
- Daily logs
- Weekly reviews
- Follow-up tracking
- Interview preparation records
- Funnel metrics
- Source performance reporting
- CV version performance
- Rejection pattern analysis
- Application quality checks
- Data quality reporting
- Workbook export centre
- Evaluation queue
- Rule-based job-posting fit review
- Manual follow-up support
- Manual recruiter email import (Sprint 28A foundation)
- Recruiter Email Actions, Recruiter Communication Context, and Interview Prep Recommended prompt (Sprint 29A-29C; rule-based, advisory only)
- Interview Evidence Workspace
- Career Evidence OS V1-V6
- Playwright screenshot automation
- Optional Notion metadata/status sync
- 771 automated tests documented
- GitHub Actions Django CI

## Planned / Not Implemented / Not Proven

- V7 OpenAI API
- V8 Claude API
- V9 Gmail API
- V10 Google Calendar API
- Live SaaS deployment
- Real users/customers
- Auto-apply automation

## Key Evidence Paths

| Evidence Area | Path / Location | What It Proves |
|---|---|---|
| Product overview | `README.md` | Scope, reviewer path, verification commands |
| Application workflows | `apps/applications/` | Tracking, quality warnings, follow-up support, Application Detail recruiter-email context |
| Sprint 29 recruiter email evidence | `docs/evidence/sprint_29_recruiter_email_workflow_enhancements.md` | Manual recruiter-email workflow enhancements (29A-29C) with claim-safe boundaries |
| Metrics and reporting | `apps/metrics/` | Funnel, source, CV, rejection, data-quality logic |
| Career Evidence V1-V3 | `docs/career_evidence/01_project_evidence_report.md`, `02_job_fit_matrix.md`, `03_recruiter_evidence_pack.md` | Repository-derived evidence packs |
| Career Evidence tools | `tools/career_evidence_audit.py`, `tools/career_job_fit_matrix.py`, `tools/career_recruiter_pack.py` | Evidence generation from repo paths |
| Dashboard UI | `/dashboard/career-evidence/` | V4 browser review surfaces |
| Reviewer-verifiable outputs | `docs/evidence/`, sprint closure docs | Documented sprint-based delivery |
| Notion sync (optional) | `docs/notion/README.md` | V6 metadata-only sync boundary |
| Automated tests | `tests/` | 771 automated tests (verified locally) |
| CI | `.github/workflows/` | Django CI workflow configuration |

## Signature Evidence

Career Evidence OS V1-V6 plus Sprint 29 recruiter-email workflow evidence on Application Detail: repository-derived project evidence, job-fit mapping, recruiter pack, manual rule-based recruiter action context, dashboard review, documented sprint-based delivery, and optional metadata-only Notion sync -- all traceable to local files and tests without external AI, inbox automation, or live deployment claims.

## Validation Proof Needed

Local validation is **complete** for this repository. Re-run when evidence changes materially:

```bash
git status --short
python -m ruff check .
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

## Safe Claims

- Built a Django job-search analytics platform with governed metrics, quality checks, evidence reports, exports, and recruiter-facing documentation.
- Implemented Career Evidence OS V1-V6 with repository-derived evidence, job-fit mapping, recruiter evidence, dashboard review, documented sprint-based delivery, and optional metadata-only Notion sync.

## Claims To Avoid

- Live SaaS product
- Production users
- Real recruiters/employers using it
- External AI integration
- Gmail/Calendar automation
- Auto-apply
- Guaranteed interviews/offers

## CV Bullets

- Built a job-search analytics tracker with structured application records, funnel-stage metrics, source-performance reporting, and data-quality warnings.
- Delivered manual intake workflow with rule-based review, field audit, decision-evidence logging, skill-gap tracking, and application readiness checks.
- Validated with 771 automated tests, Ruff checks, Django system checks, migration dry-run discipline, and documented sprint-based delivery.

## LinkedIn Wording

CareerFunnel Tracker - Django | Python | analytics workflow | test discipline. Portfolio job-search analytics with funnel metrics, source-performance reporting, data-quality warnings, skill-gap tracking, and manual intake workflow evidence. Validated with 771 automated tests. Not a live SaaS product; no external AI or email/calendar automation.

## Interview Talking Points

### 60-second explanation

CareerFunnel Tracker treats job search as a small analytics domain. I track applications and related activity, then surface funnel metrics, source and CV performance, rejection patterns, and data-quality warnings so reporting stays explainable. I also built a Career Evidence layer that turns the repository itself into reviewer-ready documentation.

### Business value

Hiring managers care whether you can turn messy operational records into trustworthy metrics. This project shows requirement-to-metric thinking, quality gates before analysis, and exports a BI reviewer can inspect.

### Technical value

Django apps for applications and metrics, rule-based fit review, evidence-generation tooling from real paths, Playwright screenshots, optional Notion metadata sync, and a full test suite with CI.

### Limitation answer

It is a portfolio analytics product, not a deployed SaaS with real users. External AI, Gmail, Calendar, and auto-apply are planned boundaries only -- not implemented.

## Next Recommended Sprint

Sprint name: Portfolio readiness alignment (Sprint 30)
Goal: Keep README, portfolio project review, and pinned-repo strategy aligned with the Sprint 29 baseline without overstating product maturity.
Allowed scope: `README.md`, `docs/career_evidence/portfolio_*`, `docs/evidence/` cross-links
Do not add: Fake deployment, Gmail/OAuth/inbox sync, automatic sending, automatic status mutation, automatic interview prep creation, or external AI claims
Validation plan: Re-run full `python manage.py test` (771 automated tests) and `ruff check .` after material repo changes

# Project Evidence Review -- CareerFunnel Tracker

## Project Identity

| Field | Value |
|---|---|
| Project name | CareerFunnel Tracker |
| GitHub URL | https://github.com/aminul-portfolio/careerfunnel-tracker |
| Latest visible tag/release | sprint-24a-complete |
| Latest visible commit | 79e4116 -- Merge sprint 24A portfolio front door |
| Current branch | main |
| Evidence checked date | 19 May 2026 |
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
- Interview Evidence Workspace
- Career Evidence OS V1-V6
- Playwright screenshot automation
- Optional Notion metadata/status sync
- 249 documented passing tests
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
| Application workflows | `apps/applications/` | Tracking, quality warnings, follow-up support |
| Metrics and reporting | `apps/metrics/` | Funnel, source, CV, rejection, data-quality logic |
| Career Evidence V1-V3 | `docs/career_evidence/01_project_evidence_report.md`, `02_job_fit_matrix.md`, `03_recruiter_evidence_pack.md` | Repository-derived evidence packs |
| Career Evidence tools | `tools/career_evidence_audit.py`, `tools/career_job_fit_matrix.py`, `tools/career_recruiter_pack.py` | Evidence generation from repo paths |
| Dashboard UI | `/dashboard/career-evidence/` | V4 browser review surfaces |
| Screenshot evidence | `docs/screenshots/career_evidence/` | V5 Playwright captures |
| Notion sync (optional) | `docs/notion/README.md` | V6 metadata-only sync boundary |
| Automated tests | `tests/` | 249 passing tests (verified locally) |
| CI | `.github/workflows/` | Django CI workflow configuration |

## Signature Evidence

Career Evidence OS V1-V6: repository-derived project evidence, job-fit mapping, recruiter pack, dashboard review, screenshot evidence, and optional metadata-only Notion sync -- all traceable to local files and tests without external AI or live deployment claims.

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
- Implemented Career Evidence OS V1-V6 with repository-derived evidence, job-fit mapping, recruiter evidence, dashboard review, screenshot evidence, and optional metadata-only Notion sync.

## Claims To Avoid

- Live SaaS product
- Production users
- Real recruiters/employers using it
- External AI integration
- Gmail/Calendar automation
- Auto-apply
- Guaranteed interviews/offers

## CV Bullets

- Built a Django job-search analytics platform converting application activity into funnel metrics, source/CV performance reporting, and data-quality signals.
- Delivered governed reporting, workbook exports, and a Career Evidence OS (V1-V6) with repository-derived recruiter documentation and optional Notion metadata sync.
- Verified 249 automated tests and GitHub Actions CI for a portfolio-grade data-product codebase.

## LinkedIn Wording

Portfolio project: Django job-search intelligence platform with explainable funnel metrics, source and CV performance reporting, data-quality checks, workbook exports, and a Career Evidence OS for recruiter-ready proof -- validated locally with 249 passing tests. Not a live SaaS product; no external AI or email/calendar automation.

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

Sprint name: Portfolio project evidence maintenance
Goal: Keep portfolio index and project review aligned with repository changes; do not mix other projects into CareerFunnel V1 report generation.
Allowed scope: `docs/career_evidence/portfolio_*`, portfolio project review files, README cross-links
Do not add: Changes to generated V1/V2/V3 CareerFunnel evidence content unless regenerating from tools; no fake deployment or integration claims
Validation plan: Re-run full `python manage.py test` and evidence tool tests after material repo changes

# Project Evidence Review -- TradeIntel 360

## Project Identity

| Field | Value |
|---|---|
| Project name | TradeIntel 360 |
| GitHub URL | https://github.com/aminul-portfolio/tradeintel-360 |
| Latest visible tag/release | No public release visible at review time |
| Latest visible commit | Not confirmed from uploaded ZIP. Public GitHub page showed main branch and 16 commits at review time. |
| Current branch | main |
| Evidence checked date | 19 May 2026 |
| Evidence source | GitHub URL + uploaded ZIP review |
| Local validation | Pending |

## Project Goal

Django-based post-trade performance analytics project that lets a user upload CSV or Excel trade history, clean and normalise the data, compute a 17-metric KPI suite, and review results through an interactive dashboard, structured KPI report, PDF export, configurable Excel export, and cleaned CSV output.

## Target Roles

- Data Analyst
- BI Analyst
- Reporting Analyst
- Analytics Engineer
- Junior Data Engineer
- FinTech analytics roles
- Python/Django data-product roles

## Implemented Features

- CSV/XLSX trade-history upload
- File cleaning and normalisation
- Pandas-based KPI computation
- 17-metric KPI suite
- Session-backed analysis workflow
- Date and symbol filtering
- Dashboard KPI summary
- Plotly equity curve
- Profit-per-trade bars
- P&L distribution histogram
- Monthly P&L breakdown
- KPI report page
- Paginated trade review table
- Configurable Excel export
- Optional KPI sheet and metadata sheet in Excel export
- Cleaned CSV export
- PDF report generation
- Reviewer-safe sample data files
- Screenshot evidence
- Login-gated Django views

## Planned / Not Implemented / Not Proven

- Live trading platform
- Broker integration
- Trade execution
- Trading automation
- Production deployment
- Real trader/customer usage
- Live integration with other FinTech projects
- Institutional annualised Sharpe
- Strong automated test coverage (ZIP shows placeholder tests only)
- Local validation

## Key Evidence Paths

| Evidence Area | Path / Location | What It Proves |
|---|---|---|
| Upload/cleaning | CSV/XLSX upload and normalisation workflow | Data intake and quality step |
| KPI engine | Pandas-based 17-metric suite | Post-trade analytics core |
| Dashboard | Plotly charts (equity, bars, histogram, monthly P&L) | Interactive review |
| Exports | Excel (configurable sheets), PDF, cleaned CSV | Reporting deliverables |
| Auth | Login-gated views | Access boundary |
| Sample data | Reviewer-safe sample files | Reproducible demo path |
| Tests | Test directory in ZIP | **Concern:** placeholder tests only -- do not claim strong coverage |
| Screenshots | Screenshot evidence folder | Visual portfolio proof |

## Signature Evidence

Session-backed workflow from trade-history upload through Pandas KPI computation to dashboard, KPI report, and multi-format exports (Excel with optional KPI/metadata sheets, PDF, cleaned CSV).

## Validation Proof Needed

- `git status --short`
- `python manage.py check`
- `python manage.py test` (after replacing placeholder tests)
- End-to-end upload with reviewer-safe sample file
- Add real unit/integration tests before claiming test coverage

## Safe Claims

- Built a Django post-trade analytics tool with CSV/Excel upload, Pandas-based 17-metric KPI computation, and Plotly dashboard visualisations.
- Delivers KPI report, configurable Excel export, PDF report, and cleaned CSV export behind login-gated views.
- Includes reviewer-safe sample data and screenshot evidence (GitHub/ZIP review; local validation and real tests pending).

## Claims To Avoid

- Live trading platform
- Broker integration
- Trade execution
- Trading automation
- Production deployment
- Real trader/customer usage
- Live integration with other FinTech projects
- Institutional annualised Sharpe
- Automated test coverage until real tests are added

## CV Bullets

- Developed a Django post-trade analytics application with CSV/Excel upload, data cleaning, and a 17-metric Pandas KPI suite.
- Built Plotly dashboards, structured KPI reports, and Excel/PDF/CSV export workflows for trade performance review.
- Portfolio evidence from GitHub/ZIP review; automated tests are placeholders -- real tests and local validation still needed.

## LinkedIn Wording

Portfolio project: Django post-trade performance analytics -- upload trade history, compute 17 KPIs with Pandas, explore Plotly dashboards, and export Excel/PDF/CSV reports. Portfolio/demo scope only; not a live trading platform; test coverage improvement in progress.

## Interview Talking Points

### 60-second explanation

TradeIntel 360 ingests trade history files, cleans and normalises them, computes seventeen KPIs with Pandas, and presents results on a dashboard with exports for Excel, PDF, and CSV.

### Business value

Shows post-trade reporting and export patterns relevant to trading desks and performance analysts -- without claiming execution or live brokerage.

### Technical value

Pandas analytics, session workflow, Plotly visualisations, multi-format exports, and login-gated Django views.

### Limitation answer

Placeholder tests in the reviewed ZIP -- I do not claim strong automated coverage yet. No broker integration or live suite links. Local validation pending.

## Next Recommended Sprint

Sprint name: TradeIntel real tests + validation
Goal: Replace placeholder tests with real coverage; run full local validation.
Allowed scope: `tests/`, sample-data fixtures, validation notes in TradeIntel repo
Do not add: Broker, execution, live integration, or institutional metric claims without proof
Validation plan: Implement tests for upload, KPI computation, and export paths -> `python manage.py test`

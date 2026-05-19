# Project Evidence Review -- CineScope Analytics

## Project Identity

| Field | Value |
|---|---|
| Project name | CineScope Analytics |
| GitHub URL | https://github.com/aminul-portfolio/cinescope-analytics |
| Latest visible tag/release | No public release visible at review time |
| Latest visible commit | d77a2ca -- Final README: corrected paths, ranking, author, role fit |
| Current branch | main |
| Evidence checked date | 19 May 2026 |
| Evidence source | GitHub URL + uploaded ZIP review |
| Local validation | Pending |

## Project Goal

Django-based movie engagement analytics project that captures raw user activity, transforms it through a daily ETL command into a gold-layer DailyMetric table, and surfaces KPI reporting, funnel analysis, CSV exports, ranked content tables, and pipeline observability through a staff analytics dashboard.

## Target Roles

- Data Analyst
- BI Analyst
- Reporting Analyst
- Analytics Engineer
- Junior Data Engineer
- Python/Django data-product roles

## Implemented Features

- Movie discovery and catalogue pages
- Search and filtering
- Movie detail pages
- User rating workflow
- Comment workflow
- Raw event tracking model
- Watch history and favourites tracking
- Daily ETL command: `build_daily_metrics`
- Gold-layer DailyMetric model
- ETL observability through ETLRunLog
- Staff analytics dashboard
- KPI cards
- Funnel tracking
- Ranked movie tables
- Data-quality checks
- CSV exports
- Screenshot evidence
- 7 real test functions found in ZIP

## Planned / Not Implemented / Not Proven

- Production streaming platform
- Real users/customers
- Live production deployment
- Netflix/IMDb-scale analytics
- External API integration
- CI passed (no CI workflow found)
- Strong test coverage
- Full documentation pack
- dbt/Airflow/warehouse implementation
- Correct README setup path (concern noted)
- Clean `requirements.txt` (encoding/null-byte concern noted)
- Repository cleanup for `.DS_Store` files
- Local validation

## Key Evidence Paths

| Evidence Area | Path / Location | What It Proves |
|---|---|---|
| Engagement capture | Raw event, watch history, favourites models | Source activity layer |
| ETL | `build_daily_metrics` command | Daily transformation workflow |
| Gold layer | `DailyMetric` model | Aggregated reporting table |
| Observability | `ETLRunLog` | Pipeline run audit trail |
| Analytics UI | Staff analytics dashboard, KPI cards, funnel | Reporting surfaces |
| Exports | CSV export surfaces | Analyst handoff |
| Tests | Test module (7 functions in ZIP) | Limited but real tests |
| README | Setup instructions | **Concern:** setup path may be wrong |
| CI | Not found | Do not claim CI |
| requirements.txt | Dependency file | **Concern:** possible encoding/null-byte issue |

## Signature Evidence

Daily ETL from raw engagement events to gold-layer `DailyMetric` with `ETLRunLog` observability, plus staff dashboard KPIs, funnel tracking, and ranked content tables.

## Validation Proof Needed

- Fix README setup path if incorrect
- Remove `.DS_Store` and other cleanup items from repo
- Fix `requirements.txt` encoding if needed
- `python manage.py check`
- `python manage.py test` (7 tests)
- `python manage.py build_daily_metrics` (or per README)
- Add CI workflow before claiming CI

## Safe Claims

- Built a Django movie engagement analytics project with raw event capture, daily ETL to a gold-layer `DailyMetric` table, and `ETLRunLog` observability.
- Surfaces KPI cards, funnel tracking, ranked tables, data-quality checks, and CSV exports on a staff analytics dashboard.
- Seven test functions visible in repository (GitHub/ZIP review; README/setup and CI cleanup pending).

## Claims To Avoid

- Production streaming platform
- Real users/customers
- Live production deployment
- Netflix/IMDb-scale analytics
- External API integration
- CI passed
- Strong test coverage
- Full documentation pack
- dbt/Airflow/warehouse implementation

## CV Bullets

- Developed a Django engagement analytics platform with raw event tracking, daily ETL (`build_daily_metrics`), and gold-layer `DailyMetric` reporting.
- Implemented ETL run logging, staff KPI/funnel dashboard, ranked content tables, and CSV exports.
- Supporting portfolio project with cleanup needs (README setup path, requirements encoding, CI, `.DS_Store`); local validation pending.

## LinkedIn Wording

Portfolio project: Django movie engagement analytics -- raw activity capture, daily ETL to gold-layer metrics, pipeline observability, and staff KPI/funnel dashboard. Supporting analytics evidence; not a production streaming platform; validation and repo cleanup in progress.

## Interview Talking Points

### 60-second explanation

CineScope captures movie engagement events, runs a daily ETL into a gold metrics table with run logs, and exposes KPIs, funnels, and ranked content on a staff dashboard with CSV exports.

### Business value

Classic analytics-engineering pattern: raw -> transformed metrics -> dashboard -- suitable for content and engagement analyst narratives.

### Technical value

Django app with ETL command, gold model, ETLRunLog, funnel and ranking reports, and seven unit tests in the repo.

### Limitation answer

Not a streaming platform at Netflix scale. README setup may be wrong; no CI; limited tests; requirements and `.DS_Store` cleanup needed. Local validation not yet run from CareerFunnel workspace.

## Next Recommended Sprint

Sprint name: CineScope README/setup/CI/test cleanup
Goal: Fix README paths and requirements encoding; remove `.DS_Store`; add CI; validate ETL command locally.
Allowed scope: README, requirements, `.gitignore`, tests, `.github/workflows/` in CineScope repo
Do not add: Streaming platform, external API, dbt/Airflow, or scale claims
Validation plan: Cleanup commit -> `manage.py test` -> `build_daily_metrics` with log capture -> add CI

# Project Evidence Review -- DataBridge Market API

## Project Identity

| Field | Value |
|---|---|
| Project name | DataBridge Market API |
| GitHub URL | https://github.com/aminul-portfolio/databridge-market-api |
| Latest visible tag/release | No public release visible at review time |
| Latest visible commit | e329983 -- Polish README and portfolio screenshots for DataBridge Market API |
| Current branch | main |
| Evidence checked date | 19 May 2026 |
| Evidence source | GitHub URL + uploaded ZIP review |
| Local validation | Pending |

## Project Goal

Django-based market data ingestion and analytics platform that demonstrates multi-source data ingestion, normalized OHLCV storage, ETL run tracking, metric snapshot generation, operational monitoring, read-only JSON API endpoints, and analyst-facing Streamlit output.

## Target Roles

- Data Analyst
- BI Analyst
- Reporting Analyst
- Analytics Engineer
- Junior Data Engineer
- FinTech analytics roles
- Python/Django data-product roles

## Implemented Features

- Django market data ingestion platform
- yfinance provider client
- ccxt provider client
- TwelveData provider client structure
- Normalized MarketBar / OHLCV storage
- IngestionRun execution tracking
- MetricSnapshot computation
- Trade journal import workflow
- Django management commands for ingestion, journal import, and metric computation
- Operational dashboard/UI
- ETL run history surface
- Metric snapshot surface
- Market bar surface
- Read-only JSON API endpoints
- Human-readable API reference page
- Public portfolio landing page
- Streamlit analytics file
- Screenshot evidence
- Proof index and status documentation
- GitHub Actions workflow configuration
- Test coverage visible in `market_ingestion/tests.py`

## Planned / Not Implemented / Not Proven

- Production deployment
- Real-time streaming architecture
- Broker execution
- Trading bot
- Live connection to MarketVista/RiskWise/TradeIntel
- Production PostgreSQL deployment
- Real customer/user usage
- CI success (unless verified locally)
- TwelveData live ingestion without API-key proof
- Local validation

## Key Evidence Paths

| Evidence Area | Path / Location | What It Proves |
|---|---|---|
| Ingestion models | `MarketBar`, `IngestionRun`, `MetricSnapshot` (ZIP/GitHub review) | Normalized storage and ETL tracking |
| Provider clients | yfinance, ccxt, TwelveData structure | Multi-source ingestion design |
| Management commands | Ingestion, journal import, metric computation commands | Operational ETL workflow |
| JSON API | Read-only API endpoints + reference page | Analyst/consumption boundary |
| Streamlit | Streamlit analytics file | Secondary analyst-facing output |
| Tests | `market_ingestion/tests.py` | Ingestion test coverage (not locally verified here) |
| CI | `.github/workflows/` | Workflow configuration (success not verified) |
| Documentation | Proof index, status docs, screenshots | Portfolio evidence packaging |

## Signature Evidence

Multi-provider ingestion into normalized OHLCV bars with `IngestionRun` audit trail and `MetricSnapshot` computation -- demonstrating ETL observability and read-only API exposure for downstream analytics.

## Validation Proof Needed

- `git status --short`
- `python -m ruff check .` (if configured)
- `python manage.py check`
- `python manage.py makemigrations --check --dry-run`
- `python manage.py test`
- Ingestion and metric management commands (per project README)
- Streamlit file runs locally (if dependencies available)

## Safe Claims

- Built a Django market data ingestion platform with multi-provider clients, normalized OHLCV storage, ETL run tracking, and metric snapshots.
- Exposed read-only JSON API endpoints and an analyst-facing Streamlit file for portfolio review.
- Demonstrates ingestion observability and trade journal import workflow (GitHub/ZIP review; local validation pending).

## Claims To Avoid

- Production deployment
- Real-time streaming architecture
- Broker execution
- Trading bot
- Live connection to MarketVista/RiskWise/TradeIntel
- Production PostgreSQL deployment
- Real customer/user usage
- CI success unless verified
- TwelveData live ingestion without API-key proof

## CV Bullets

- Built a Django market data ingestion platform with yfinance and ccxt clients, normalized OHLCV storage, and ETL run tracking.
- Implemented metric snapshot computation, trade journal import, operational monitoring UI, and read-only JSON API endpoints.
- Packaged Streamlit analytics and proof documentation for portfolio review (local validation pending).

## LinkedIn Wording

Portfolio project: Django market data ingestion with multi-source providers, normalized OHLCV bars, ETL run history, metric snapshots, read-only JSON API, and Streamlit analytics -- reviewed from GitHub/archive; not production-deployed; local validation pending.

## Interview Talking Points

### 60-second explanation

DataBridge ingests market data from multiple providers, stores normalized OHLCV bars, tracks each ingestion run, computes metric snapshots, and exposes read-only JSON endpoints plus a Streamlit view for analysts.

### Business value

Shows end-to-end ingestion design: provider boundary, normalized storage, run auditability, and consumption APIs -- relevant to FinTech and analytics engineering roles.

### Technical value

Django models for bars and runs, management commands for ETL, provider client abstraction, tests in `market_ingestion`, and operational UI surfaces.

### Limitation answer

No production deployment, broker execution, or live suite integration with other portfolio apps. TwelveData structure exists but live key-based ingestion needs separate proof. CI and local runs not verified from this repo.

## Next Recommended Sprint

Sprint name: DataBridge local validation
Goal: Clone repo, run checks/tests, execute ingestion and metric commands with documented output.
Allowed scope: Validation notes in DataBridge repo; optional release tag after proof
Do not add: Production, streaming, broker, or cross-project live integration claims
Validation plan: Full Django test run + sample ingestion command with terminal capture

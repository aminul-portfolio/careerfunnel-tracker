# Project Evidence Review -- MarketVista Dashboard

## Project Identity

| Field | Value |
|---|---|
| Project name | MarketVista Dashboard |
| GitHub URL | https://github.com/aminul-portfolio/marketvista-dashboard |
| Latest visible tag/release | No public release visible at review time |
| Latest visible commit | 3d2d235 -- chore: strengthen All Rights Reserved license with full ownership clauses |
| Current branch | main |
| Evidence checked date | 19 May 2026 |
| Evidence source | GitHub URL + uploaded ZIP review |
| Local validation | Pending |

## Project Goal

Django-based FinTech monitoring and analyst-visibility dashboard that turns reviewer-ready seeded market data into severity-ranked signals, watchlist prioritisation, user-defined threshold alerts, asset inspection, and honest sparse-data handling.

## Target Roles

- Data Analyst
- BI Analyst
- Reporting Analyst
- Analytics Engineer
- Junior Data Engineer
- FinTech analytics roles
- Python/Django data-product roles

## Implemented Features

- Django monitoring dashboard
- Reviewer-ready seeded market data
- Stored price snapshots
- Stored OHLC history
- Severity-ranked market signals
- Signal methodology context
- Watchlist workflow
- User-defined threshold alerts
- Asset-level inspection
- Plotly-backed charts
- Sparse intraday data handling
- Dashboard, signals, watchlist, alerts, asset browser, and asset detail pages
- Django admin inspectability
- Screenshot gallery
- Reviewer walkthrough
- Interview talking points
- Proof packaging checklist
- GitHub Actions workflow configuration

## Planned / Not Implemented / Not Proven

- Live DataBridge ingestion
- Live RiskWise handoff
- Live TradeIntel handoff
- Broker integration
- Trading bot
- Real-time market infrastructure
- Production deployment
- Real users/customers
- Automated trading workflow
- Public release tag
- Local validation

## Key Evidence Paths

| Evidence Area | Path / Location | What It Proves |
|---|---|---|
| Seeded data | Reviewer-ready market seed (ZIP/GitHub review) | Demonstration dataset boundary |
| Signals | Severity-ranked signals + methodology context | Analyst monitoring logic |
| Watchlist / alerts | Watchlist and threshold alert workflows | User-driven monitoring |
| Charts | Plotly-backed asset views | Visual analytics with sparse-data handling |
| UI surfaces | Dashboard, signals, watchlist, alerts, asset pages | End-to-end reviewer path |
| Admin | Django admin | Operational inspectability |
| Documentation | Walkthrough, interview points, proof checklist | Portfolio packaging |
| CI | `.github/workflows/` | Workflow configuration (success not verified) |

## Signature Evidence

Severity-ranked market signals with methodology context, watchlist prioritisation, and threshold alerts on seeded data -- including explicit sparse intraday data handling rather than pretending continuous live feeds.

## Validation Proof Needed

- `git status --short`
- `python manage.py check`
- `python manage.py makemigrations --check --dry-run`
- `python manage.py test` (if tests present)
- Seed/load demo data per README
- Create public release tag after local proof

## Safe Claims

- Built a Django FinTech monitoring dashboard with severity-ranked signals, watchlists, threshold alerts, and Plotly asset inspection on seeded market data.
- Documents signal methodology and honest sparse-data handling for portfolio review.
- Includes reviewer walkthrough, screenshot gallery, and proof packaging checklist (GitHub/ZIP review; local validation pending).

## Claims To Avoid

- Live DataBridge ingestion
- Live RiskWise handoff
- Live TradeIntel handoff
- Broker integration
- Trading bot
- Real-time market infrastructure
- Production deployment
- Real users/customers
- Automated trading workflow

## CV Bullets

- Developed a Django FinTech monitoring dashboard with severity-ranked market signals, watchlists, and user-defined threshold alerts on seeded data.
- Implemented Plotly-backed asset inspection with explicit sparse intraday data handling and signal methodology documentation.
- Packaged reviewer walkthrough and screenshot evidence for portfolio proof (local validation and release tag pending).

## LinkedIn Wording

Portfolio project: Django FinTech monitoring dashboard with severity-ranked signals, watchlists, threshold alerts, and Plotly charts on seeded market data -- portfolio evidence only; not live market infrastructure or cross-project ingestion; local validation pending.

## Interview Talking Points

### 60-second explanation

MarketVista is a monitoring dashboard for seeded market data: ranked signals, watchlists, alerts, and asset drill-down with charts. It explains how signals are derived and handles sparse intraday data honestly.

### Business value

Shows analyst-facing monitoring UX and alert design without claiming a live trading stack.

### Technical value

Django multi-page app, Plotly integration, admin inspectability, seeded snapshots/OHLC, and documentation for reviewers.

### Limitation answer

No live feeds from DataBridge or handoffs to RiskWise/TradeIntel. Not deployed for real users. Local validation and a release tag are still outstanding.

## Next Recommended Sprint

Sprint name: MarketVista validation and release tag
Goal: Local Django validation; add visible release tag after proof.
Allowed scope: Validation runbook, tag, README status in MarketVista repo
Do not add: Live ingestion, broker, or suite integration claims
Validation plan: `manage.py check` + test run + seed walkthrough with terminal log

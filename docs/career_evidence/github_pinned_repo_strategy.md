# GitHub Pinned Repository Strategy

Defines which repositories to pin on GitHub and how to describe them. Based on [portfolio_project_index.md](portfolio_project_index.md). Pin up to six repositories.

## Primary pinned repo order (default)

| Pin | Repository | GitHub URL |
|---:|---|---|
| 1 | CareerFunnel Tracker | https://github.com/aminul-portfolio/careerfunnel-tracker |
| 2 | BakeOps Intelligence | https://github.com/aminul-portfolio/bakeops-intelligence |
| 3 | DataBridge Market API | https://github.com/aminul-portfolio/databridge-market-api |
| 4 | RiskWise Planner | https://github.com/aminul-portfolio/riskwise-planner |
| 5 | MarketVista Dashboard | https://github.com/aminul-portfolio/marketvista-dashboard |
| 6 | PureLaka Commerce Platform | https://github.com/aminul-portfolio/purelaka-commerce-platform |

## Alternative order: BI / Data Analyst applications

| Pin | Repository | Rationale |
|---:|---|---|
| 1 | CareerFunnel Tracker | Governed metrics, exports, evidence OS |
| 2 | BakeOps Intelligence | KPI dashboards, BI CSV exports |
| 3 | GoalTracker KPI Reporting | Snapshots, Power BI-ready exports *(swap in if pin slot available; otherwise link from README)* |
| 4 | MarketVista Dashboard | Monitoring and alerts |
| 5 | DataBridge Market API | Analyst-facing ingestion and API |
| 6 | PureLaka Commerce Platform | Commerce KPI and reporting breadth |

*Note: GoalTracker is not in the default six-pin set because of validation/CI gaps; mention it in CV/LinkedIn instead unless pins are reorganised.*

## Alternative order: Analytics Engineer / Junior Data Engineer

| Pin | Repository | Rationale |
|---:|---|---|
| 1 | DataBridge Market API | Ingestion, ETL runs, normalized OHLCV |
| 2 | CareerFunnel Tracker | Lineage, quality, evidence discipline |
| 3 | BakeOps Intelligence | Gold-layer metric build pipeline |
| 4 | CineScope Analytics | Daily ETL + ETLRunLog *(if cleanup done; else keep unpinned)* |
| 5 | RiskWise Planner | Simulation services, audit trail |
| 6 | PureLaka Commerce Platform | Multi-app data boundaries |

## Alternative order: FinTech analytics applications

| Pin | Repository | Rationale |
|---:|---|---|
| 1 | DataBridge Market API | Market data ingestion and API |
| 2 | RiskWise Planner | Pre-trade risk and Monte Carlo |
| 3 | MarketVista Dashboard | Signals and monitoring |
| 4 | CareerFunnel Tracker | Analytical rigour and test evidence |
| 5 | TradeIntel 360 | Post-trade KPIs *(after real tests; else omit)* |
| 6 | BakeOps Intelligence | Strong secondary analytics product |

## Short GitHub pinned descriptions

Use these as repository descriptions or pin summaries. Keep under ~350 characters where possible.

### CareerFunnel Tracker

Django job-search analytics: funnel metrics, source/CV performance, data-quality reporting, workbook exports, and Career Evidence OS (V1-V6). Portfolio project with 249 passing tests -- not a live SaaS.

### BakeOps Intelligence

Django bakery operations analytics: KPI dashboards, profitability, waste-adjusted margins, gold-layer snapshots, and BI CSV exports. Seeded demo data -- not a commercial POS product.

### DataBridge Market API

Django market data ingestion: multi-provider clients, normalized OHLCV storage, ETL run tracking, metric snapshots, read-only JSON API, and Streamlit analytics. Portfolio ETL demo -- not production trading infrastructure.

### RiskWise Planner

Django pre-trade risk planning: Monte Carlo simulation, stress tests, scenario comparison, and capital preservation dashboards from uploaded trade history. No broker integration or live execution.

### MarketVista Dashboard

Django FinTech monitoring: severity-ranked signals, watchlists, threshold alerts, and Plotly asset views on seeded market data. Portfolio evidence -- not real-time market infrastructure.

### PureLaka Commerce Platform

Django commerce analytics: catalogue-to-order workflows, Stripe-ready payment boundary, subscription/MRR surfaces, and KPI dashboards. Portfolio proof-oriented build -- confirm public access before featuring.

## Projects not pinned yet (and why)

| Project | Reason to defer pinning |
|---|---|
| TradeIntel 360 | Good FinTech analytics demo; uploaded ZIP showed placeholder tests only. Pin after real automated tests and local validation. |
| GoalTracker KPI Reporting | Good supporting BI/reporting project; limited tests, no CI workflow found, requirements encoding concern. Feature in CV/LinkedIn before pinning. |
| CineScope Analytics | Supporting engagement analytics; README setup path, CI, and repo cleanup still needed. Pin after cleanup and validation. |

## Claims to avoid in GitHub repo descriptions

- "Live SaaS", "production-ready platform", "real users/customers"
- "AI-powered", "Gmail/Calendar integration", "auto-apply"
- "CI passing" unless you have verified the latest workflow run
- "Integrated suite" or "connected to [other repo]" unless built and tested
- "Deployed at [URL]" unless deployment is verified and documented
- "Enterprise-grade", "institutional trading", "real-time streaming" without proof
- For PureLaka: do not imply public repo access until confirmed

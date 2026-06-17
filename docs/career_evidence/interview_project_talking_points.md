# Interview Project Talking Points

Interview preparation derived from [portfolio_projects/](portfolio_projects/) and [portfolio_presentation_pack.md](portfolio_presentation_pack.md). Use evidence-backed language; state limitations when asked.

## 60-second portfolio overview

"I have nine Django portfolio projects that show different sides of analytics work: governed job-search metrics in CareerFunnel, operational KPIs in BakeOps, market ingestion in DataBridge, FinTech monitoring in MarketVista, pre-trade risk in RiskWise, and supporting work in commerce, post-trade KPIs, BI reporting, and engagement ETL. CareerFunnel is my anchor -- I validated it locally with 900+ validated tests. The others are strong GitHub and archive evidence; I am completing local validation runs so I can speak to terminal proof, not just code review. Everything is portfolio scope -- no fake users, no live SaaS, and no claims about connected production platforms unless I have run and tested the integration."

## 2-minute Analytics Engineer explanation

"My analytics engineering story centres on **DataBridge** and **CineScope**. DataBridge ingests market data through provider clients, stores normalized OHLCV bars, tracks each ingestion in an `IngestionRun` table, and computes metric snapshots -- that is the raw-to-trusted-metrics path with observability. CineScope does something similar for engagement: raw events, a daily `build_daily_metrics` ETL command, gold-layer `DailyMetric`, and `ETLRunLog` for pipeline visibility. **BakeOps** adds a gold-layer snapshot build for operational KPIs. **CareerFunnel** shows metric governance, lineage docs, and data-quality gates -- how I think about definitions before dashboards. I would not claim production orchestration with Airflow or dbt; these are Django management-command ETL patterns at portfolio scale. Next improvement: local validation runs and saved logs for DataBridge and CineScope."

## 2-minute Data / BI Analyst explanation

"For analyst roles I lead with **CareerFunnel** and **BakeOps**. CareerFunnel answers reporting questions recruiters care about: which sources and CV versions perform better, where applications stall, and which records fail data-quality checks before they skew metrics. It exports workbook evidence for review. BakeOps shows operational BI: KPI dashboards, waste-adjusted margin -- for example a product can rank first on revenue but lower on margin after waste -- and BI-ready CSV exports with documented metric definitions. **GoalTracker** is my BI export story: quality-weighted effective minutes, day and week snapshots, and Power BI-oriented fact/dimension CSVs plus a `.pbix` proof file. **MarketVista** shows monitoring and alerts for FinTech analyst workflows. I separate implemented features from roadmap items and I do not claim live customers or enterprise BI deployments."

---

## Project-by-project talking points

### CareerFunnel Tracker

| Topic | Points |
|---|---|
| Business problem | Job-search data is fragmented; hard to see funnel performance, source/CV effectiveness, and data quality. |
| Technical implementation | Django apps for applications and metrics; rule-based fit review; Career Evidence OS V1-V6; optional Notion metadata sync; Playwright screenshots. |
| Analytics/reporting value | Funnel metrics, source/CV performance, rejection patterns, data-quality report, workbook export centre. |
| Evidence/validation status | Verified from current repository; 900+ validated tests; local validation complete. |
| Limitation answer | Portfolio product, not live SaaS; no external AI, Gmail, Calendar, or auto-apply. |
| Improve next | Keep evidence packs aligned when repo changes; maintain test and CI discipline. |

### BakeOps Intelligence

| Topic | Points |
|---|---|
| Business problem | Bakery operations need profitability and waste visibility, not revenue alone. |
| Technical implementation | Django operational models; `build_bakery_metrics`; gold-layer snapshots; BI CSV export command. |
| Analytics/reporting value | KPI dashboard, waste-adjusted margin, ingredient risk, data-quality review. |
| Evidence/validation status | Strong; GitHub + ZIP review; local validation pending. |
| Limitation answer | Seeded data only; no real customers, POS integration, or production deployment. |
| Improve next | Run full local validation; capture terminal proof for seed, build, export. |

### DataBridge Market API

| Topic | Points |
|---|---|
| Business problem | Market data from multiple sources needs normalized storage and auditable ETL. |
| Technical implementation | yfinance/ccxt clients; MarketBar OHLCV; IngestionRun; MetricSnapshot; read-only JSON API; Streamlit file. |
| Analytics/reporting value | ETL history UI, metric snapshots, trade journal import, analyst API and Streamlit. |
| Evidence/validation status | Strong; GitHub + ZIP review; local validation pending. |
| Limitation answer | No production deployment, broker execution, or live links to other FinTech repos. |
| Improve next | Local test run; sample ingestion with logged output; optional release tag. |

### RiskWise Planner

| Topic | Points |
|---|---|
| Business problem | Traders need pre-trade planning and scenario comparison before risking capital. |
| Technical implementation | Upload workflow; service-layer Monte Carlo and stress logic; saved runs; login and ownership isolation. |
| Analytics/reporting value | Capital preservation dashboard, scenario comparison, sizing and risk calculators. |
| Evidence/validation status | Strong; 64 test functions in repo; local run pending; README/model alignment needed. |
| Limitation answer | No broker feeds, execution, or guaranteed outcomes. |
| Improve next | Align README with `riskwise/models.py`; run full test suite locally. |

### MarketVista Dashboard

| Topic | Points |
|---|---|
| Business problem | Analysts need ranked signals, watchlists, and alerts without pretending continuous live feeds. |
| Technical implementation | Seeded snapshots/OHLC; severity-ranked signals; Plotly charts; sparse intraday handling. |
| Analytics/reporting value | Dashboard, signals, watchlist, alerts, asset drill-down with methodology context. |
| Evidence/validation status | Strong; GitHub + ZIP review; local validation and release tag pending. |
| Limitation answer | No live DataBridge ingestion or cross-app handoffs; not production market infra. |
| Improve next | Local validation; public release tag after proof. |

### PureLaka Commerce Platform

| Topic | Points |
|---|---|
| Business problem | E-commerce needs transactional workflows tied to KPI and subscription reporting. |
| Technical implementation | Multi-app Django; cart/checkout/orders; Stripe-ready PaymentIntent; StripeEvent idempotency; MRR surfaces. |
| Analytics/reporting value | Analytics dashboard, KPI reporting, monitoring, data-quality model, CSV exports. |
| Evidence/validation status | Strong supporting; ZIP review; public GitHub and local validation pending. |
| Limitation answer | Not live SaaS; no real Stripe production volume; confirm public repo before interviews. |
| Improve next | Confirm GitHub access; local validation smoke test. |

### TradeIntel 360

| Topic | Points |
|---|---|
| Business problem | Post-trade history needs cleaning, KPI computation, and exportable reports. |
| Technical implementation | Pandas 17-metric suite; session workflow; Plotly charts; Excel/PDF/CSV exports. |
| Analytics/reporting value | Dashboard, KPI report, filtered trade table, multi-format exports. |
| Evidence/validation status | Good FinTech demo; placeholder tests in reviewed ZIP; validation pending. |
| Limitation answer | Not a trading platform; do not claim strong automated test coverage yet. |
| Improve next | Replace placeholder tests; end-to-end local validation. |

### GoalTracker KPI Reporting

| Topic | Points |
|---|---|
| Business problem | Personal/productivity KPIs need weighted time, snapshots, and BI-ready exports. |
| Technical implementation | Session capture; quality-weighted minutes; DaySnapshot/WeekSnapshot; v2 fact/dimension exports. |
| Analytics/reporting value | Target-vs-actual; export hub; `.pbix` proof asset. |
| Evidence/validation status | Good supporting BI; 2 test functions; no CI found; validation pending. |
| Limitation answer | Not enterprise BI or Power BI Service deployment. |
| Improve next | Fix requirements encoding; add CI; expand tests. |

### CineScope Analytics

| Topic | Points |
|---|---|
| Business problem | Content engagement needs ETL from raw events to trustworthy daily metrics. |
| Technical implementation | Raw events; `build_daily_metrics`; DailyMetric gold layer; ETLRunLog. |
| Analytics/reporting value | Staff dashboard, funnel, ranked tables, CSV exports. |
| Evidence/validation status | Supporting; 7 tests in ZIP; README/setup and cleanup pending. |
| Limitation answer | Not Netflix-scale; no dbt/Airflow; not production streaming. |
| Improve next | README fix, CI, repo cleanup, local ETL validation. |

---

## Best STAR examples

### CareerFunnel Tracker

- **Situation:** Job-search data was spread across boards and notes with no consistent metrics.
- **Task:** Build a Django analytics product with explainable funnel and quality reporting for portfolio proof.
- **Action:** Modelled applications and metrics in Django; added data-quality checks, workbook exports, and Career Evidence OS with repository-derived V1-V6 documentation; ran 900+ validated tests.
- **Result:** Recruiters can follow a documented evidence path from metrics to screenshots and generated packs; validated locally in this repository.

### BakeOps Intelligence

- **Situation:** Revenue ranking alone hid waste impact on product profitability.
- **Task:** Show operational KPIs and margin-after-waste for bakery-style data.
- **Action:** Built Django operational models, gold-layer metric snapshots, dashboards, and BI CSV export with governance docs.
- **Result:** Signature insight (e.g. Birthday Classic #1 revenue, #4 waste-adjusted margin) demonstrates analyst-grade questioning of headline KPIs.

### DataBridge Market API

- **Situation:** Multiple market data sources need a consistent OHLCV store and audit trail.
- **Task:** Demonstrate ingestion engineering for portfolio FinTech roles.
- **Action:** Implemented provider clients, normalized bars, IngestionRun tracking, metric snapshots, JSON API, and Streamlit view.
- **Result:** End-to-end ingestion story with observability; ready for local validation to strengthen interview proof.

### RiskWise Planner

- **Situation:** Pre-trade decisions need scenario and stress visibility before capital is risked.
- **Task:** Build planning analytics without claiming live trading.
- **Action:** Upload workflow, Monte Carlo and stress services, calculators, saved-run audit views, login isolation.
- **Result:** Decision-support platform with substantial test code in repository; README alignment and local runs remain next steps.

### MarketVista Dashboard

- **Situation:** Analysts need signal prioritisation and alerts without fake real-time infrastructure.
- **Task:** FinTech monitoring UX on seeded data with honest methodology.
- **Action:** Severity-ranked signals, watchlists, threshold alerts, Plotly asset views, sparse-data documentation.
- **Result:** Credible monitoring demo for FinTech analyst interviews; validation and release tag to follow.

---

## Which project for which role?

| Role | Lead with | Second | Third | Avoid leading with |
|---|---|---|---|---|
| Data Analyst | CareerFunnel | BakeOps | MarketVista | CineScope (until cleanup) |
| BI Analyst | CareerFunnel | BakeOps | GoalTracker | TradeIntel (test gaps) |
| Reporting Analyst | CareerFunnel | GoalTracker | TradeIntel | CineScope |
| Analytics Engineer | DataBridge | CareerFunnel | CineScope | PureLaka (access unconfirmed) |
| Junior Data Engineer | DataBridge | CineScope | BakeOps | TradeIntel |
| FinTech analytics | DataBridge | RiskWise | MarketVista | GoalTracker |
| Python/Django data product | CareerFunnel | PureLaka | BakeOps | TradeIntel |

---

## Claims I should not say in interviews

- "I have a live SaaS with real users/customers."
- "All nine projects are integrated in production."
- "CI is green across the portfolio" (unless you verified each repo recently).
- "I validated everything locally" (only CareerFunnel is complete today).
- "CareerFunnel uses OpenAI / Gmail / Calendar / auto-apply" (planned only).
- "RiskWise guarantees capital protection or profitability."
- "DataBridge streams real-time market data in production."
- "TradeIntel has strong automated test coverage" (placeholders found in review).
- "PureLaka is publicly on GitHub" (confirm access first).
- "GoalTracker / CineScope are enterprise BI / streaming platforms."
- "BakeOps connects to Shopify/Square" or "has paying bakery clients."

When unsure, say: **"That is portfolio evidence from the repository; I can walk you through the code paths and what I have validated locally."**

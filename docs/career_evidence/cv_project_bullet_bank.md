# CV Project Bullet Bank

Evidence-backed bullets derived from [portfolio_projects/](portfolio_projects/). Use in a **Projects** or **Portfolio** section. Final CV bullets should not mention "validation pending" -- that belongs in internal notes only.

## Core CV project section recommendation

- **Heading:** `Selected Portfolio Projects (Python / Django / Analytics)`
- **Lead line (optional):** Nine Django portfolio projects covering job-search analytics, operational KPIs, market ingestion, FinTech monitoring, risk planning, commerce reporting, and BI exports. Evidence available on GitHub.
- **Format:** Project name | 2-3 bullets | GitHub URL
- **Lead with BakeOps Intelligence, then CareerFunnel Tracker** for recruiter-facing packs (verified tests in this repository).

## 4-project short CV version

Use for one-page CVs or early-career applications.

1. BakeOps Intelligence (2 bullets)
2. CareerFunnel Tracker
3. RiskWise Planner OR MarketVista Dashboard (pick for FinTech)
4. One supporting project only if space allows (PureLaka or GoalTracker for BI)

## 6-project extended CV version

1. BakeOps Intelligence
2. CareerFunnel Tracker
3. TradeIntel 360
4. DataBridge Market API
4. RiskWise Planner
5. MarketVista Dashboard
6. PureLaka Commerce Platform OR GoalTracker KPI Reporting (BI roles)

Omit TradeIntel and CineScope from the main six until tests/cleanup are complete unless the role specifically needs post-trade KPIs or ETL narrative.

---

## CareerFunnel Tracker

**GitHub:** https://github.com/aminul-portfolio/careerfunnel-tracker

- Built a job-search analytics tracker with structured application records, funnel-stage metrics, source-performance reporting, and data-quality warnings.
- Delivered manual intake workflow with rule-based review, field audit, decision-evidence logging, skill-gap tracking, and application readiness checks.
- Validated with 771 automated tests, Ruff checks, Django system checks, migration dry-run discipline, and documented sprint-based delivery.

*Internal note: local validation complete in this repository.*

---

## BakeOps Intelligence

**GitHub:** https://github.com/aminul-portfolio/bakeops-intelligence

- Developed a Django bakery operations analytics platform with KPI dashboards, product profitability, waste-adjusted margins, and ingredient risk visibility from seeded operational data.
- Implemented gold-layer metric snapshots, a metric build command, and BI-ready CSV exports for analyst review.
- Documented metric governance and data lineage with reviewer walkthrough and screenshot evidence.

*Internal note: GitHub/ZIP review; run local validation before interviews.*

---

## DataBridge Market API

**GitHub:** https://github.com/aminul-portfolio/databridge-market-api

- Built a Django market data ingestion platform with yfinance and ccxt clients, normalized OHLCV storage, and ETL run tracking.
- Implemented metric snapshot computation, trade journal import, operational monitoring UI, and read-only JSON API endpoints.
- Packaged Streamlit analytics and proof documentation for portfolio review.

*Internal note: local validation pending.*

---

## RiskWise Planner

**GitHub:** https://github.com/aminul-portfolio/riskwise-planner

- Developed a Django pre-trade risk planning platform with Monte Carlo simulation, stress-test review, and scenario comparison from uploaded trade history.
- Implemented capital preservation dashboards, position sizing and risk control calculators, and saved-run audit views with service-layer simulation logic.
- Built substantial automated test coverage in the repository for risk and simulation workflows.

*Internal note: 64 test functions visible in repo; align README with models; local run pending.*

---

## MarketVista Dashboard

**GitHub:** https://github.com/aminul-portfolio/marketvista-dashboard

- Developed a Django FinTech monitoring dashboard with severity-ranked market signals, watchlists, and user-defined threshold alerts on seeded data.
- Implemented Plotly-backed asset inspection with explicit sparse intraday data handling and signal methodology documentation.
- Packaged reviewer walkthrough and screenshot evidence for portfolio proof.

*Internal note: local validation and release tag pending.*

---

## PureLaka Commerce Platform

**GitHub:** https://github.com/aminul-portfolio/purelaka-commerce-platform *(confirm public access)*

- Developed a Django e-commerce data product spanning catalogue, cart, checkout, orders, and role-based access control.
- Designed Stripe-ready payment flows with webhook idempotency and subscription/MRR analytics surfaces.
- Produced KPI reporting, monitoring, data-quality checks, and operational runbooks for portfolio proof.

*Internal note: ZIP-reviewed; public GitHub not confirmed at review time.*

---

## TradeIntel 360

**GitHub:** https://github.com/aminul-portfolio/tradeintel-360

- Developed a Django post-trade analytics application with CSV/Excel upload, data cleaning, and a 17-metric Pandas KPI suite.
- Built Plotly dashboards, structured KPI reports, and Excel/PDF/CSV export workflows for trade performance review.

*Internal note: do not claim strong test coverage; placeholders in reviewed ZIP. Use as secondary FinTech bullet only.*

---

## GoalTracker KPI Reporting

**GitHub:** https://github.com/aminul-portfolio/goaltracker-kpi-reporting

- Developed a Django KPI tracking platform with quality-weighted effective minutes, day/week snapshots, and target-vs-actual reporting.
- Delivered an export hub with Power BI-oriented fact/dimension CSV contracts and a desktop `.pbix` portfolio proof file.

*Internal note: supporting BI project; limited tests, no CI found. Good for Reporting/BI CV variant.*

---

## CineScope Analytics

**GitHub:** https://github.com/aminul-portfolio/cinescope-analytics

- Developed a Django engagement analytics platform with raw event tracking, daily ETL (`build_daily_metrics`), and gold-layer `DailyMetric` reporting.
- Implemented ETL run logging, staff KPI/funnel dashboard, ranked content tables, and CSV exports.

*Internal note: supporting project; cleanup and validation pending. Use for Analytics Engineer CV variant.*

---

## Best 6 CV bullets to use first

Copy-ready bullets (mix across projects or use top three from CareerFunnel + one each from next three projects):

1. Built a Django job-search analytics platform converting application activity into funnel metrics, source/CV performance reporting, and data-quality signals. *(CareerFunnel)*
2. Delivered governed reporting, workbook exports, and a Career Evidence OS (V1-V6) with repository-derived recruiter documentation. *(CareerFunnel)*
3. Developed a Django bakery operations analytics platform with KPI dashboards, waste-adjusted margins, and BI-ready CSV exports from seeded operational data. *(BakeOps)*
4. Built a Django market data ingestion platform with multi-provider clients, normalized OHLCV storage, and ETL run tracking. *(DataBridge)*
5. Developed a Django pre-trade risk planning platform with Monte Carlo simulation, stress tests, and scenario comparison from uploaded trade history. *(RiskWise)*
6. Developed a Django FinTech monitoring dashboard with severity-ranked signals, watchlists, and threshold alerts on seeded market data. *(MarketVista)*

Add a seventh only when needed: PureLaka (commerce breadth) or GoalTracker (Power BI exports) for BI-focused roles.

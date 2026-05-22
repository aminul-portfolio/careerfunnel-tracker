# Sprint 30 - Recruiter-Facing Project Summary

## Purpose

This document packages CareerFunnel Tracker into recruiter-facing wording for GitHub, LinkedIn preparation, CV project notes, recruiter messages, and interviews.

**Draft/reference only.** It does not mean LinkedIn has been published, a profile has been updated, or any external channel has been posted.

Use the sections below as reusable language. Always keep claims aligned with repository evidence and the boundaries in **What is not claimed**.

---

## Current verified baseline

| Item | State |
|---|---|
| Latest stable main | `284e040` |
| Latest completed Sprint 30 tag | `sprint-30a-portfolio-readiness-alignment-complete` |
| Sprint 29 | Complete (29A-29D recruiter email workflow and evidence) |
| Sprint 30A | Complete (portfolio readiness documentation alignment) |
| Validation baseline | **320 tests passing** |
| GitHub Actions / Django CI | Passed for Sprint 30A |
| Project scope | Local, portfolio-scale, rule-based, and manual |

---

## One-line project summary

Django job-search analytics platform that turns application activity into explainable funnel metrics, data-quality signals, and recruiter-ready evidence tracking.

---

## Recruiter-facing project paragraph

CareerFunnel Tracker is a Django portfolio project that structures job-search activity into an analytics-ready dataset. It tracks applications, sources, CV versions, follow-ups, interviews, notes, daily logs, and weekly reviews; then surfaces funnel metrics, source and CV performance, rejection patterns, data-quality warnings, and workbook exports. A Career Evidence OS (V1-V6) turns repository paths, tests, and documentation into reviewer-ready proof. Sprint 29 added a manual, rule-based recruiter-email workflow on Application Detail (action alerts, communication context, and an interview-prep recommendation prompt) without inbox automation. The codebase is validated with **320 passing tests** and Django CI. It is a local portfolio product, not a live SaaS deployment or customer-facing service.

---

## Technical explanation

CareerFunnel Tracker is organized as Django apps with authenticated, user-scoped records and service-layer logic for reporting and recommendations. Fit review, follow-up drafts, recruiter-email classification summaries, quality warnings, and metric calculations use **rule-based** Python services rather than external AI APIs. Management commands support seeding and operational tasks; the Export Centre produces workbook outputs for review. Evidence lives in `docs/evidence/`, `docs/analytics/`, and `docs/career_evidence/`, with sprint checkpoints and screenshot proof. **Ruff**, `manage.py check`, migration checks, and **320 automated tests** run in local validation and GitHub Actions. SQLite supports portfolio-scale local review; production hosting and multi-user database design are out of scope for current claims.

---

## Analytics Engineering explanation

The project treats job search as a small analytics domain with explicit **metric definitions** and **analytics lineage**. Operational fields are captured once, then propagated into funnel metrics, source/CV performance, rejection analysis, and data-quality readiness checks. The same readiness rule informs save-time warnings and impact reporting, which mirrors a lightweight analytics-engineering pattern: define the rule, expose it at the point of use, and document downstream impact. Workbook exports provide analyst-ready tables without claiming a live warehouse or orchestration platform. Sprint evidence and Career Evidence tooling keep outputs traceable to repository paths and tests.

---

## Data Analyst / BI explanation

Reviewers can inspect **funnel metrics** (applications, responses, interviews, offers), **source performance**, **CV version performance**, **weekly activity trends**, and **rejection patterns** from stored application records. The Data Quality Report and Application Quality views explain which fields are missing and how gaps affect reporting trust. Chart.js weekly trend evidence and curated screenshots support BI-style storytelling; Tableau workbook evidence is local and documented, not a verified public deployment. The Export Centre supports Excel-style review and backup. Recruiter-email context on Application Detail helps prioritize manual follow-up and interview prep without automating decisions.

---

## FinTech / operational reporting angle

The project reflects a reconciliation-minded approach: track what happened, when it happened, which channel or document version was involved, and whether the record is complete enough to trust in reporting. Follow-up status, last-contact dates, and manual recruiter-email history support **operational controls** and audit-friendly evidence rather than black-box recommendations. That aligns with FinTech and operations reporting habits: disciplined capture, explainable metrics, explicit limitations, and decision support the user still owns. It does not claim trade execution, market data production, or institutional-scale infrastructure.

---

## What this project proves

- Can design a business workflow as structured data with clear statuses and timestamps.
- Can build Django data-product interfaces for tracking, review queues, and reporting pages.
- Can create explainable metrics, quality checks, and impact notes from shared rules.
- Can write validation-backed documentation and sprint evidence across releases.
- Can keep portfolio claims evidence-based with tests, CI, and explicit boundaries.
- Can extend a manual recruiter-email workflow with rule-based summaries without overstating automation.

---

## What is not claimed

- No live SaaS deployment
- No production users
- No real customers
- No Gmail API implementation
- No OAuth implementation
- No inbox sync
- No scraping
- No auto-apply
- No automatic email sending
- No automatic application status mutation
- No automatic interview prep creation
- No external AI / LLM integration
- No production database architecture claim

---

## CV project bullet options

1. Built a Django job-search analytics platform with funnel metrics, source/CV performance reporting, and data-quality checks backed by 320 automated tests.
2. Delivered governed reporting, workbook exports, and a Career Evidence OS that maps repository evidence to recruiter-ready documentation.
3. Implemented rule-based fit review, follow-up support, and manual recruiter-email workflow context on Application Detail without inbox automation.
4. Documented metric definitions and analytics lineage so reporting logic stays explainable for analyst and BI reviewer interviews.
5. Maintained evidence-first sprint delivery with CI, local validation, and explicit claim boundaries for a portfolio data product.

---

## LinkedIn post draft for later

**Draft only - not published yet.**

I have been refining my Django portfolio project, CareerFunnel Tracker, as a job-search analytics product rather than a simple application list. It tracks applications, sources, CV versions, follow-ups, and interview prep, then turns that activity into funnel metrics, source and CV performance views, and data-quality warnings. Recent work added a manual, rule-based recruiter-email workflow on Application Detail so imported emails surface action context and interview-prep recommendations without claiming inbox sync or automation. The repository includes workbook exports, analytics documentation, Career Evidence OS materials, and 320 passing tests with Django CI. It is a local portfolio build for Data Analyst, BI, and analytics-engineering style roles - not a live SaaS product. GitHub: https://github.com/aminul-portfolio/careerfunnel-tracker

---

## Recruiter message version

CareerFunnel Tracker is my Django portfolio project for job-search analytics. It structures applications, sources, CV versions, follow-ups, and interview prep into explainable funnel and performance reporting, with data-quality checks and workbook exports. I document metrics and evidence in the repository (including a manual recruiter-email workflow added in Sprint 29) and validate the build with 320 automated tests. It is portfolio work for analyst and BI-style roles, not a commercial product or live deployment. Happy to walk through the README, evidence index, and a short demo on a local run if useful.

---

## Interview explanation

**Problem:** Job-search data spreads across boards, spreadsheets, CV versions, and follow-up notes, so it is hard to answer which sources perform better, which CV versions correlate with outcomes, and which records are too incomplete to trust in reporting.

**Solution:** CareerFunnel Tracker captures applications and related activity in Django, then exposes funnel metrics, source and CV performance, rejection patterns, quality warnings, exports, and reviewer-ready evidence documentation.

**Technical approach:** Django apps with service-layer rule-based logic, SQLite for local portfolio scale, automated tests and CI, and sprint evidence under `docs/evidence/`.

**Analytics value:** Metric definitions, lineage notes, and a single analytics-readiness rule propagated into warnings and impact reporting show how I think about governed metrics, not just charts.

**What I learned:** How to keep portfolio claims honest while still demonstrating workflow design, reporting, and documentation discipline across many sprints.

**Claim-safe limitation:** It is not deployed as a SaaS, has no production users, and does not use Gmail, OAuth, scraping, auto-apply, or external AI. Recruiter-email and follow-up features are manual and advisory only.

---

## Best portfolio positioning

Position CareerFunnel Tracker as:

- A **Django analytics portfolio project**
- A **job-search intelligence / application-quality tracker**
- An **evidence-first data product** with tests, documentation, and screenshots
- Relevant to **Data Analyst**, **BI Analyst**, **Reporting Analyst**, **Analytics Engineer**, and **junior Data Engineer** roles

Lead with metrics, quality governance, and evidence discipline; mention recruiter-email workflow as a recent manual, rule-based enhancement.

---

## Evidence links

| Path | Use |
|---|---|
| `README.md` | Product scope, reviewer path, verification commands, claim boundaries |
| `docs/evidence/sprint_29_recruiter_email_workflow_enhancements.md` | Sprint 29 recruiter-email workflow proof |
| `docs/evidence/evidence_index.md` | Sprint evidence map and reviewer navigation |
| `docs/career_evidence/portfolio_projects/careerfunnel_tracker.md` | Portfolio project review, CV/LinkedIn bullets, validation notes |
| `docs/career_evidence/github_pinned_repo_strategy.md` | Concise GitHub pin description |

---

## Sprint 30B conclusion

Sprint 30B prepares recruiter-facing project language while keeping the project claim-safe and evidence-based. It does not publish LinkedIn or introduce new product features. Use this document alongside repository evidence before updating external profiles or messages.

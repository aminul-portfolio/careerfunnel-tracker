# Sprint 30C - LinkedIn Update Draft / Readiness Gate

## Purpose

This document prepares LinkedIn-ready wording for CareerFunnel Tracker and a manual publish checklist. It does **not** publish anything.

State exactly:

- **Draft only - not published yet.**
- **No LinkedIn profile update has been made.**
- **No external publication has been made.**

Copy text from this document only after the **Publish readiness checklist** and **Do-not-publish conditions** are satisfied and you confirm the decision manually.

---

## Current verified baseline

| Item | State |
|---|---|
| Latest stable main | `ddddd23` |
| Latest completed Sprint 30 tag | `sprint-30b-recruiter-facing-summary-complete` |
| Sprint 30A | Complete (portfolio readiness documentation alignment) |
| Sprint 30B | Complete (recruiter-facing project summary) |
| Validation baseline | **320 tests passing** |
| GitHub Actions / Django CI | Passed for Sprint 30B |
| Project scope | Local, portfolio-scale, rule-based, manual, and evidence-based |

---

## LinkedIn positioning decision

Present **CareerFunnel Tracker** as a **Django analytics portfolio project** and **job-search intelligence tracker**, not as a SaaS product, commercial platform, or live customer-facing service.

Target relevance:

- Data Analyst
- BI Analyst
- Reporting Analyst
- Analytics Engineer
- Junior Data Engineer
- FinTech / operational reporting roles

Lead with explainable metrics, data-quality discipline, exports, and evidence documentation. Mention recruiter-email workflow as a **manual, rule-based** enhancement from Sprint 29.

---

## Recommended LinkedIn project title

1. **CareerFunnel Tracker - Django Job-Search Analytics Platform** (recommended)
2. CareerFunnel Tracker - Evidence-First Application Analytics
3. CareerFunnel Tracker - Job-Search Intelligence and Reporting Dashboard

**Recommendation:** Use option **1**. It is clear, role-relevant, and does not imply SaaS or deployment.

---

## LinkedIn project description

CareerFunnel Tracker is a Django portfolio project that turns job-search activity into structured analytics. It tracks applications, sources, CV versions, follow-ups, interviews, notes, and weekly activity; then reports funnel metrics, source and CV performance, rejection patterns, and data-quality warnings. Workbook exports support review and BI-style analysis. A Career Evidence OS (V1-V6) packages repository evidence for portfolio review. Sprint 29 added a manual, rule-based recruiter-email workflow on Application Detail (action alerts, communication context, interview-prep recommendation) without inbox sync or automation. Validated with **320 passing tests** and Django CI. Local portfolio build only - not a deployed SaaS, not a customer product, and not claiming Gmail, OAuth, external AI, or auto-apply.

**Associated with:** https://github.com/aminul-portfolio/careerfunnel-tracker

---

## LinkedIn post draft

**Draft only - not published yet.**

I have been building CareerFunnel Tracker as a Django portfolio project for job-search analytics, not as a simple application spreadsheet.

The problem it addresses: application data, CV versions, sources, and follow-ups scatter quickly, which makes it hard to see which channels perform better and which records are too incomplete to trust in reporting.

What is implemented today:

- Application tracking with funnel metrics, source/CV performance, and data-quality checks
- Workbook exports and analytics documentation (metric definitions, lineage)
- Career Evidence OS for reviewer-ready repository evidence
- Manual, rule-based recruiter-email workflow on Application Detail (Sprint 29): action context, follow-up guidance, and interview-prep recommendations without inbox automation

The repository is validated with **320 passing tests** and Django CI. It is evidence-first, local, and portfolio-scale - **not a live SaaS product** and not claiming production users, Gmail integration, or external AI.

If you are hiring for Data Analyst, BI, Reporting, or junior analytics-engineering style roles, the README and evidence index give a fast, honest review path: https://github.com/aminul-portfolio/careerfunnel-tracker

---

## Short LinkedIn post version

**Draft only - not published yet.**

CareerFunnel Tracker is my Django portfolio project for job-search analytics: funnel metrics, source/CV performance, data-quality warnings, workbook exports, and Career Evidence OS documentation. Sprint 29 added a manual recruiter-email workflow on Application Detail (rule-based, no inbox sync). **320 passing tests**, Django CI, evidence-first delivery. Portfolio project only - not a live SaaS. https://github.com/aminul-portfolio/careerfunnel-tracker

---

## LinkedIn About/Profile support wording

Short paragraph for later adaptation (About/Profile), aligned with **Data Analyst | BI Analyst | Python, SQL, Excel, Django | FX & FinTech Operations**:

I build portfolio analytics projects that show how operational data becomes explainable reporting. CareerFunnel Tracker is my Django job-search intelligence project: funnel metrics, source/CV performance, data-quality checks, exports, and evidence-backed documentation, validated with 320 automated tests. My background includes FX and FinTech operations, so I focus on disciplined tracking, reconciliation-minded data capture, and claim-safe portfolio evidence rather than hype. Open to Data Analyst, BI Analyst, Reporting Analyst, and analytics-engineering style roles.

---

## GitHub pinned repo description

Django job-search analytics: funnel metrics, source/CV performance, data-quality reporting, manual recruiter-email workflow (rule-based), exports, Career Evidence OS. **320 passing tests** - portfolio project, not live SaaS.

---

## Screenshot / media checklist before publishing

- [ ] README visible on GitHub and aligned with current sprint baseline
- [ ] GitHub Actions workflow shows green for latest main
- [ ] Latest completion tag visible on GitHub (`sprint-30b-recruiter-facing-summary-complete` or newer when applicable)
- [ ] `docs/evidence/evidence_index.md` includes Sprint 30 evidence entries
- [ ] `docs/evidence/sprint_30_recruiter_facing_project_summary.md` available for wording consistency
- [ ] Curated screenshots selected only if they show safe, non-private demo data
- [ ] No private emails, names, or employer-sensitive data visible in images
- [ ] No localhost URL presented as a verified live deployment
- [ ] No `.env`, `db.sqlite3`, credentials, or private paths in shared ZIPs or images

---

## Publish readiness checklist

- [ ] Project wording reviewed against this document and `sprint_30_recruiter_facing_project_summary.md`
- [ ] Claim-safety reviewed (no SaaS, customers, Gmail, OAuth, AI, scraping, auto-apply as implemented)
- [ ] GitHub repository public and accessible for reviewers
- [ ] README current for sprint baseline and test count (320)
- [ ] CI green on latest main intended for promotion
- [ ] Latest sprint tag pushed to GitHub when publishing sprint-specific updates
- [ ] LinkedIn post copied from this document only after final personal review
- [ ] No deployment, customer, production-user, or automation claims added at publish time
- [ ] User manually confirms publish decision (this gate does not auto-publish)

---

## Do-not-publish conditions

Do **not** publish LinkedIn content if any of the following is true:

- CI is failing on the commit you are promoting
- README is outdated relative to repository evidence (test count, sprint status, boundaries)
- Wording mentions SaaS, paying customers, production users, Gmail, OAuth, external AI, scraping, or auto-apply as **implemented**
- Screenshots or attachments reveal private or employer-sensitive data
- GitHub repository is not ready for public review (missing README, broken default branch, or inaccessible repo)
- You have not re-read **What is not claimed** below

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

## Evidence links

| Path | Use |
|---|---|
| `README.md` | Product scope, reviewer path, verification commands |
| `docs/evidence/sprint_30_recruiter_facing_project_summary.md` | Recruiter-facing bullets, paragraphs, interview wording |
| `docs/evidence/sprint_29_recruiter_email_workflow_enhancements.md` | Sprint 29 recruiter-email workflow proof |
| `docs/evidence/evidence_index.md` | Sprint evidence map |
| `docs/career_evidence/portfolio_projects/careerfunnel_tracker.md` | Portfolio project review and validation notes |
| `docs/career_evidence/github_pinned_repo_strategy.md` | Pin order and short repo descriptions |

---

## Sprint 30C conclusion

Sprint 30C prepares LinkedIn-ready wording and a manual publish gate. It does **not** publish LinkedIn content, edit a profile, or introduce new product features. Publishing remains a deliberate, user-controlled step after checklist review.

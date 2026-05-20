# Portfolio / CV Wording Pack

## Sprint Metadata

| Item | Value |
|---|---|
| Sprint | 26B |
| Scope type | Portfolio / CV / LinkedIn wording only |
| Implementation boundary | No README edit, no code changes, no model changes, no migrations, no screenshots, no AI/API integration, no Gmail, no Calendar, no scraping, no auto-apply |

## Purpose

Sprint 26B turns completed Sprint 25 (Assisted Intake evidence chain and README links) and Sprint 26 (GitHub/portfolio presentation review) into practical, claim-safe wording for CVs, LinkedIn, GitHub pins, interviews, and recruiter outreach.

Sprint 26B does not change the product or repository presentation. It creates wording options grounded in existing evidence for manual use outside the repo. Copy, adapt, or shorten sections as needed for each application.

## Source Evidence Reviewed

### Public project entry point

- README.md

### Sprint 25 assisted-intake evidence

- docs/evidence/assisted_job_intake_workflow.md
- docs/evidence/assisted_job_intake_field_audit.md
- docs/evidence/assisted_intake_field_decision_plan.md
- docs/evidence/assisted_intake_reviewer_path.md
- docs/evidence/assisted_intake_readme_link_plan.md

### Sprint 26 review

- docs/evidence/post_sprint_25_github_portfolio_review.md

### Portfolio wording sources

- docs/career_evidence/portfolio_project_index.md
- docs/career_evidence/portfolio_presentation_pack.md
- docs/career_evidence/cv_project_bullet_bank.md
- docs/career_evidence/interview_project_talking_points.md

## Positioning Summary

CareerFunnel Tracker is a Django-based analytics and evidence-tracking portfolio project that turns job-search activity into structured application records, funnel metrics, data-quality warnings, reviewer-ready documentation, and manual assisted-intake evidence.

Claim-safe emphasis:

- manual user review and approval at each step
- approval-based workflow from job-posting review to saved application records
- rule-based fit review and decision support (not external AI)
- evidence-backed field audit and field-decision documentation
- Django analytics surfaces, workbook exports, and curated screenshot proof
- reviewer-ready README and evidence chain for GitHub inspection
- no claims of production users, live SaaS, scraping, auto-apply, Gmail, Calendar, or background automation

## CV Project Bullet Options

### Short CV bullets

- Built a Django job-search analytics tracker with funnel metrics, source/CV performance views, and data-quality warnings from structured application records.
- Documented a manual, approval-based assisted-intake workflow with rule-based job-posting review and tracker-ready field pre-fill for user confirmation.
- Delivered reviewer-ready evidence: sprint documentation, curated screenshots, metric definitions, and 249 passing automated tests.
- Designed analytics governance so one readiness rule drives save-time warnings and downstream report impact notes.

### Stronger CV bullets

- Developed CareerFunnel Tracker, a Django application that converts job-search activity into funnel metrics, Evaluation Queue workflows, and governed data-quality reporting.
- Implemented a manual assisted-intake path: rule-based Job Posting Analyzer review, conversion bridge pre-fill, user approval before save, and evidence docs linked from README (Sprint 25A-F).
- Produced Assisted Intake Evidence including field audit and field-decision plan showing which tracker fields exist vs rule-based suggestions, without unnecessary model expansion.
- Built Career Evidence OS tooling (V1-V6) and portfolio evidence packs with repository-derived recruiter documentation, workbook exports, and validation discipline (Ruff, Django checks, migration checks, 249 tests).

### Technical CV bullets

- Structured Django apps with service-layer analytics for funnel metrics, rejection patterns, source/CV performance, and data-quality impact reporting.
- Implemented rule-based decision support for job-posting fit review, smart review summaries, and post-save quality warnings using shared readiness logic.
- Documented field governance through assisted-intake field audit and decision-plan evidence aligned to models, forms, and rule-based outputs in `apps/applications/` and related services.
- Maintained evidence-first delivery with curated UI screenshots, sprint evidence index, metric lineage docs, and full test/lint/check validation on the portfolio codebase.

## LinkedIn Project Wording

### LinkedIn Featured project description

CareerFunnel Tracker is a Django portfolio project I built to treat job search like a small analytics domain: structured application records, funnel and source/CV metrics, data-quality warnings, and reviewer-ready evidence on GitHub. After Sprint 25 and 26, the repo documents a manual, approval-based assisted-intake workflow with rule-based job-posting review, field audit, and field-decision planning -- not scraping, auto-apply, or external AI. The README links workflow evidence, screenshots, and validation commands so recruiters and technical reviewers can inspect the work quickly. Relevant for Data Analyst, BI Analyst, Reporting Analyst, and Analytics Engineer roles where governed metrics and honest delivery matter.

### LinkedIn post draft

I have updated my CareerFunnel Tracker portfolio repo with clearer GitHub presentation after Sprint 25 and 26. The project is a Django analytics tracker for job-search activity: funnel metrics, Evaluation Queue, data-quality warnings, and workbook exports. Sprint 25 documented a manual, approval-based assisted-intake workflow with rule-based job-posting review, a field audit, a field-decision plan, and a reviewer path -- all linked from README under Assisted Intake Evidence. Sprint 26 reviewed presentation quality and claim safety; the repo does not claim live SaaS, production users, external AI, scraping, or auto-apply. If you hire for Data Analyst, BI Analyst, or Analytics Engineer roles, the README, evidence docs, and curated screenshots are meant for a fast, honest review. GitHub: https://github.com/aminul-portfolio/careerfunnel-tracker

## GitHub Pinned Repo Description

### Short pinned description

Django job-search analytics tracker with governed metrics, manual assisted intake, and reviewer-ready evidence.

### Longer GitHub description

CareerFunnel Tracker is a Django portfolio project for structured job-search tracking, funnel analytics, data-quality warnings, and evidence-backed documentation. It uses rule-based fit review and a manual, approval-based assisted-intake workflow. README includes curated screenshots, Assisted Intake evidence links, and 249 passing tests. Portfolio scope only -- not a live SaaS product.

## Interview Explanation

### 30-second explanation

CareerFunnel Tracker is my Django portfolio project for job-search analytics. It tracks applications and turns them into funnel metrics, source and CV performance views, and data-quality warnings. I documented a manual assisted-intake workflow where rule-based job-posting review can pre-fill fields, but I always review and approve before saving. The repo is built for reviewer inspection: screenshots, evidence docs, and tests, without claiming external AI or a live product.

### 60-second explanation

I built CareerFunnel Tracker to show how operational job-search data can become governed analytics. It is a Django app with application tracking, an Evaluation Queue, funnel and quality reporting, and workbook exports. The assisted-intake path is manual and approval-based: I paste a job description, get rule-based fit guidance, decide apply or skip, and only then convert to a tracker record after reviewing pre-filled fields. Sprint 25 added evidence for workflow, field audit, and field decisions; Sprint 26 reviewed GitHub presentation and claim safety. I emphasize honest scope: rule-based logic, not external AI, and portfolio validation with 249 tests. It is strongest evidence for analyst and analytics-engineering roles where data quality and explainability matter.

### Technical reviewer explanation

On the technical side, CareerFunnel uses Django with a service layer for metrics, job intelligence, and rule-based assistants. Job-posting analysis and smart review use deterministic logic, shared constants, and tests -- not external LLM APIs. Sprint 25B/C evidence maps intake concepts to existing model fields vs generated suggestions, which is why no rushed migrations were needed. Data quality uses one analytics-readiness rule propagated to save warnings and impact notes. Evidence lives in README, `docs/evidence/`, `docs/analytics/`, curated screenshots, and Career Evidence tooling. I validate with Ruff, `manage.py check`, migration dry-run, and the full test suite. UI labels may say "AI" in places, but README and evidence docs define the behavior as rule-based local assistance unless a future sprint adds real API integration.

## Recruiter Message

Hello,

I would like to share CareerFunnel Tracker, a Django portfolio project that demonstrates job-search analytics, data-quality governance, and evidence-backed delivery. The repo includes funnel metrics, Evaluation Queue workflows, manual assisted-intake documentation, field audit evidence, curated screenshots, and 249 passing tests. It is designed for honest portfolio review rather than live SaaS claims. I believe it is relevant for Data Analyst, BI Analyst, and Analytics Engineer roles where structured data, reporting trust, and clear documentation matter. GitHub: https://github.com/aminul-portfolio/careerfunnel-tracker

Thank you for your time.

## Claim-Safe Wording Rules

### Use these phrases

- manual assisted-intake workflow
- approval-based workflow
- rule-based job-posting review
- tracker-ready application evidence
- reviewer-ready documentation
- Django analytics tracker
- data-quality warnings
- evidence-backed portfolio project
- curated screenshot evidence
- field audit and decision plan
- Evaluation Queue for apply/skip decisions
- governed metrics and analytics lineage
- portfolio-scale local validation

### Avoid these phrases

- AI-powered automation
- OpenAI integration
- Claude integration
- LinkedIn scraping
- Indeed scraping
- auto-apply
- automatic application submission
- Gmail integration
- Calendar automation
- live SaaS
- production users
- customer-ready platform
- background workflow automation
- fully automated job search

## Best Final CV Project Section

**CareerFunnel Tracker -- Django Analytics & Evidence Workflow**

Portfolio Django project turning job-search activity into governed funnel metrics, manual assisted-intake evidence, and reviewer-ready documentation.

- Built a Django job-search analytics tracker with funnel metrics, source/CV performance reporting, Evaluation Queue, and data-quality warnings tied to structured application records.
- Documented a manual, approval-based assisted-intake workflow with rule-based job-posting review, conversion-bridge pre-fill, field audit, and field-decision plan linked from README.
- Delivered evidence-first portfolio delivery: sprint evidence docs, metric definitions, curated screenshots, Career Evidence OS outputs, and workbook exports.
- Validated the codebase with 249 automated tests plus Ruff, Django system checks, and migration dry-run discipline.

**Tech:** Python, Django, Django ORM, HTML/CSS, JavaScript, Chart.js, SQLite, OpenPyXL, Ruff, Git

## Best Final LinkedIn Featured Text

CareerFunnel Tracker is my Django portfolio project for job-search analytics: structured applications, funnel and source/CV metrics, data-quality warnings, and reviewer-ready GitHub evidence. Sprint 25-26 added a claim-safe assisted-intake story -- manual, approval-based, rule-based review with field audit and decision documentation, not scraping or external AI. Curated screenshots and 249 tests support quick recruiter and technical review. Relevant for Data Analyst, BI Analyst, and Analytics Engineer roles.

## Best Final Interview Answer

I built CareerFunnel Tracker to demonstrate analytics thinking on real operational data: Django tracking, governed metrics, and honest limitations. The assisted-intake workflow is manual -- I review rule-based fit guidance, decide apply or skip in the Evaluation Queue, and approve pre-filled fields before saving. Sprint 25 produced workflow, field audit, and decision-plan evidence; Sprint 26 confirmed the GitHub presentation is claim-safe. I can walk reviewers through README, screenshots, and tests. I do not present it as a live SaaS or AI product; it is portfolio evidence for analyst and analytics-engineering roles where data quality, traceability, and explainable logic matter.

## Do Not Claim Checklist

- [ ] Do not claim external AI/API implementation.
- [ ] Do not claim OpenAI or Claude integration.
- [ ] Do not claim LinkedIn or Indeed scraping.
- [ ] Do not claim auto-apply.
- [ ] Do not claim Gmail or Calendar integration.
- [ ] Do not claim production SaaS users.
- [ ] Do not claim deployment unless verified elsewhere.
- [ ] Do not claim V7-V10 API work as implemented.

## Final Sprint 26B Recommendation

Sprint 26B should remain wording-only.

Recommended next step after Sprint 26B:

Either apply selected wording manually to CV, LinkedIn, and GitHub profile fields, or create a later documentation sprint for a dedicated job-application pack (cover letter inserts, role-specific variants).

Do not recommend V7-V10 API implementation yet unless explicitly approved later.

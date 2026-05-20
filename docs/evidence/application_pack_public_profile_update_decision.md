# Application Pack / Public Profile Update Decision

## Sprint Metadata

| Item | Value |
|---|---|
| Sprint | 26C |
| Scope type | Application-pack and public-profile wording decision only |
| Implementation boundary | No README edit, no CV edit, no LinkedIn edit, no GitHub profile edit, no code changes, no model changes, no migrations, no screenshots, no AI/API integration, no Gmail, no Calendar, no scraping, no auto-apply |

## Purpose

Sprint 26C selects which Sprint 26B wording from `docs/evidence/portfolio_cv_wording_pack.md` should be used manually in future public and job-application assets: CV project section, LinkedIn Featured project text, GitHub pinned repository description, recruiter messages, and interview answers.

Sprint 26C does not apply changes to CV, LinkedIn, GitHub profile, README, or application materials. It records recommended wording choices, claim boundaries, update order, and copy/paste-ready blocks for human review outside the repository.

## Source Evidence Reviewed

- README.md
- docs/evidence/portfolio_cv_wording_pack.md
- docs/evidence/post_sprint_25_github_portfolio_review.md
- docs/evidence/assisted_job_intake_workflow.md
- docs/evidence/assisted_job_intake_field_audit.md
- docs/evidence/assisted_intake_field_decision_plan.md
- docs/evidence/assisted_intake_reviewer_path.md
- docs/evidence/assisted_intake_readme_link_plan.md

## Executive Decision Summary

1. Use the Sprint 26B final CV project section as the primary CV wording source.
2. Use the Sprint 26B LinkedIn Featured text as the primary LinkedIn project wording source.
3. Use the Sprint 26B short pinned description for GitHub pinned repo text, with the longer GitHub description for the repository About/summary field if space allows.
4. Use the Sprint 26B recruiter message as a reusable recruiter-introduction draft.
5. Use the Sprint 26B final interview answer as the default interview explanation.
6. Keep all wording manual, approval-based, rule-based, evidence-backed, and Django-focused.
7. Do not claim external AI/API integrations, scraping, auto-apply, Gmail, Calendar, live SaaS, production users, background automation, or V7-V10 implementation.
8. Apply wording manually outside the repo after final human review on each platform.

## Selected Wording For Immediate Use

### CV Project Section

**CareerFunnel Tracker -- Django Analytics & Evidence Workflow**

Portfolio Django project turning job-search activity into governed funnel metrics, manual assisted-intake evidence, and reviewer-ready documentation.

- Built a Django job-search analytics tracker with funnel metrics, source/CV performance reporting, Evaluation Queue, and data-quality warnings tied to structured application records.
- Documented a manual, approval-based assisted-intake workflow with rule-based job-posting review, conversion-bridge pre-fill, field audit, and field-decision plan linked from README.
- Delivered evidence-first portfolio delivery: sprint evidence docs, metric definitions, curated screenshots, Career Evidence OS outputs, and workbook exports.
- Validated the codebase with 249 automated tests plus Ruff, Django system checks, and migration dry-run discipline.

**Tech:** Python, Django, Django ORM, HTML/CSS, JavaScript, Chart.js, SQLite, OpenPyXL, Ruff, Git

*Source: Sprint 26B "Best Final CV Project Section" in `docs/evidence/portfolio_cv_wording_pack.md`.*

### LinkedIn Featured Project Text

CareerFunnel Tracker is my Django portfolio project for job-search analytics: structured applications, funnel and source/CV metrics, data-quality warnings, and reviewer-ready GitHub evidence. Sprint 25-26 added a claim-safe assisted-intake story -- manual, approval-based, rule-based review with field audit and decision documentation, not scraping or external AI. Curated screenshots and 249 tests support quick recruiter and technical review. Relevant for Data Analyst, BI Analyst, and Analytics Engineer roles.

*Source: Sprint 26B "Best Final LinkedIn Featured Text" (~95 words).*

### GitHub Pinned Repo Description

**Short pinned description (use for pin / tagline):**

Django job-search analytics tracker with governed metrics, manual assisted intake, and reviewer-ready evidence.

**Longer GitHub description (use for repo About or profile summary if space allows):**

CareerFunnel Tracker is a Django portfolio project for structured job-search tracking, funnel analytics, data-quality warnings, and evidence-backed documentation. It uses rule-based fit review and a manual, approval-based assisted-intake workflow. README includes curated screenshots, Assisted Intake evidence links, and 249 passing tests. Portfolio scope only -- not a live SaaS product.

*Source: Sprint 26B "GitHub Pinned Repo Description" sections.*

### Recruiter Message

Hello,

I would like to share CareerFunnel Tracker, a Django portfolio project that demonstrates job-search analytics, data-quality governance, and evidence-backed delivery. The repo includes funnel metrics, Evaluation Queue workflows, manual assisted-intake documentation, field audit evidence, curated screenshots, and 249 passing tests. It is designed for honest portfolio review rather than live SaaS claims. I believe it is relevant for Data Analyst, BI Analyst, and Analytics Engineer roles where structured data, reporting trust, and clear documentation matter. GitHub: https://github.com/aminul-portfolio/careerfunnel-tracker

Thank you for your time.

*Source: Sprint 26B "Recruiter Message" (~105 words). Tailor role titles and opening line per application.*

### Interview Answer

I built CareerFunnel Tracker to demonstrate analytics thinking on real operational data: Django tracking, governed metrics, and honest limitations. The assisted-intake workflow is manual -- I review rule-based fit guidance, decide apply or skip in the Evaluation Queue, and approve pre-filled fields before saving. Sprint 25 produced workflow, field audit, and decision-plan evidence; Sprint 26 confirmed the GitHub presentation is claim-safe. I can walk reviewers through README, screenshots, and tests. I do not present it as a live SaaS or AI product; it is portfolio evidence for analyst and analytics-engineering roles where data quality, traceability, and explainable logic matter.

*Source: Sprint 26B "Best Final Interview Answer" (~115 words).*

## Use Now vs Save For Later

| Asset | Use Now? | Recommended Source | Notes |
|---|---|---|---|
| CV project section | Yes | Sprint 26B Best Final CV Project Section | Paste into CV Projects after human review; keep tech line accurate |
| LinkedIn Featured project | Yes | Sprint 26B Best Final LinkedIn Featured Text | Add project link to GitHub repo |
| GitHub pinned repo description | Yes | Sprint 26B short + longer descriptions | Short text for pin; longer for About field |
| Recruiter message | Yes, tailor per role | Sprint 26B Recruiter Message | Adjust role focus (DA vs BI vs AE) per outreach |
| Interview answer | Yes | Sprint 26B Best Final Interview Answer | Store in interview prep notes; extend with 60s version if needed |
| Full LinkedIn post | Save for later | Sprint 26B LinkedIn post draft | Use when announcing repo update; not required for applications |
| Technical reviewer explanation | Save for interviews / portfolio review | Sprint 26B Technical reviewer explanation | Use for engineering interviews or deep GitHub walkthroughs |

## Public Profile Update Order

1. Update CV project section first (stable wording for all applications).
2. Update GitHub pinned repository description (recruiters often check GitHub before LinkedIn).
3. Update LinkedIn Featured project text (align with GitHub and CV).
4. Save recruiter message as reusable template (edit per company/role).
5. Save interview answer in interview preparation notes (practice aloud once).
6. Publish LinkedIn post later only if timing is appropriate (optional visibility, not required for job search).

## Claim Boundaries For Public Use

### Safe public wording

- Django analytics tracker
- manual assisted-intake workflow
- approval-based workflow
- rule-based job-posting review
- reviewer-ready evidence
- data-quality warnings
- evidence-backed portfolio project
- field audit and decision plan
- curated screenshot evidence
- governed funnel metrics
- Evaluation Queue
- portfolio-scale validation (249 tests)

### Do not claim publicly

- External AI/API implementation
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
- background workflow automation
- V7-V10 API work as implemented
- AI-powered automation (without rule-based qualification)

## Final Recommended Public Wording Pack

Copy/paste-ready blocks for manual use after review.

### CV Entry

**CareerFunnel Tracker -- Django Analytics & Evidence Workflow**

Portfolio Django project turning job-search activity into governed funnel metrics, manual assisted-intake evidence, and reviewer-ready documentation.

- Built a Django job-search analytics tracker with funnel metrics, source/CV performance reporting, Evaluation Queue, and data-quality warnings tied to structured application records.
- Documented a manual, approval-based assisted-intake workflow with rule-based job-posting review, conversion-bridge pre-fill, field audit, and field-decision plan linked from README.
- Delivered evidence-first portfolio delivery: sprint evidence docs, metric definitions, curated screenshots, Career Evidence OS outputs, and workbook exports.
- Validated the codebase with 249 automated tests plus Ruff, Django system checks, and migration dry-run discipline.

**Tech:** Python, Django, Django ORM, HTML/CSS, JavaScript, Chart.js, SQLite, OpenPyXL, Ruff, Git

### LinkedIn Featured

CareerFunnel Tracker is my Django portfolio project for job-search analytics: structured applications, funnel and source/CV metrics, data-quality warnings, and reviewer-ready GitHub evidence. Sprint 25-26 added a claim-safe assisted-intake story -- manual, approval-based, rule-based review with field audit and decision documentation, not scraping or external AI. Curated screenshots and 249 tests support quick recruiter and technical review. Relevant for Data Analyst, BI Analyst, and Analytics Engineer roles.

### GitHub Pinned Repo

**Short:** Django job-search analytics tracker with governed metrics, manual assisted intake, and reviewer-ready evidence.

**Longer:** CareerFunnel Tracker is a Django portfolio project for structured job-search tracking, funnel analytics, data-quality warnings, and evidence-backed documentation. It uses rule-based fit review and a manual, approval-based assisted-intake workflow. README includes curated screenshots, Assisted Intake evidence links, and 249 passing tests. Portfolio scope only -- not a live SaaS product.

### Recruiter Message

Hello,

I would like to share CareerFunnel Tracker, a Django portfolio project that demonstrates job-search analytics, data-quality governance, and evidence-backed delivery. The repo includes funnel metrics, Evaluation Queue workflows, manual assisted-intake documentation, field audit evidence, curated screenshots, and 249 passing tests. It is designed for honest portfolio review rather than live SaaS claims. I believe it is relevant for Data Analyst, BI Analyst, and Analytics Engineer roles where structured data, reporting trust, and clear documentation matter. GitHub: https://github.com/aminul-portfolio/careerfunnel-tracker

Thank you for your time.

### Interview Answer

I built CareerFunnel Tracker to demonstrate analytics thinking on real operational data: Django tracking, governed metrics, and honest limitations. The assisted-intake workflow is manual -- I review rule-based fit guidance, decide apply or skip in the Evaluation Queue, and approve pre-filled fields before saving. Sprint 25 produced workflow, field audit, and decision-plan evidence; Sprint 26 confirmed the GitHub presentation is claim-safe. I can walk reviewers through README, screenshots, and tests. I do not present it as a live SaaS or AI product; it is portfolio evidence for analyst and analytics-engineering roles where data quality, traceability, and explainable logic matter.

## Manual Application Notes

- Review each asset before publishing; wording must still match README and evidence files on the date of use.
- Tailor recruiter message to the target role (emphasize reporting for BI, governance for AE, funnel metrics for DA).
- Do not paste all blocks into every channel at once; CV + GitHub + LinkedIn Featured is the core trio.
- Keep public wording aligned with Assisted Intake Evidence and What Is Not Claimed in README.
- If a platform character limit applies, shorten by removing secondary detail, not by adding automation or AI claims.
- Re-read the Sprint 26B Do Not Claim Checklist before any public update.

## Final Sprint 26C Decision

Sprint 26C approves the selected wording above for manual use in CV, LinkedIn Featured, GitHub pinned repo, recruiter messages, and interview preparation.

Sprint 26C does not apply those changes directly to any profile, document, or repository file outside this decision record.

Recommended next step:

**Sprint 26D -- CV / LinkedIn Application Pack Export**, only if the user wants a single consolidated copy/paste application pack document separate from this decision file.

Do not recommend V7-V10 API implementation yet unless explicitly approved later.

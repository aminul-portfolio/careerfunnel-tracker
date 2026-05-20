# Post-Sprint 25 GitHub / Portfolio Presentation Review

## Sprint Metadata

| Item | Value |
|---|---|
| Sprint | 26 |
| Scope type | GitHub / portfolio presentation review only |
| Implementation boundary | No README edit, no code changes, no model changes, no migrations, no screenshots, no AI/API integration, no Gmail, no Calendar, no scraping, no auto-apply |

## Purpose

Sprint 26 reviews the final public-facing GitHub and portfolio presentation after Sprint 25A-F completed the Assisted Intake evidence chain and Sprint 25F added the Assisted Intake Evidence block to README.

Sprint 26 does not change the product. It audits presentation quality, evidence clarity, claim safety, recruiter value, and next-step recommendations. Findings are based on README.md, Sprint 25A-F evidence documents, career-evidence portfolio packs, curated screenshots, and the evidence index -- without modifying any of those source files.

## Source Evidence Reviewed

### Public GitHub entry point

- README.md

### Assisted Intake evidence chain

- docs/evidence/assisted_job_intake_workflow.md
- docs/evidence/assisted_job_intake_field_audit.md
- docs/evidence/assisted_intake_field_decision_plan.md
- docs/evidence/assisted_intake_reviewer_path.md
- docs/evidence/assisted_intake_readme_link_plan.md

### Portfolio evidence pack

- docs/evidence/evidence_index.md
- docs/career_evidence/portfolio_project_index.md
- docs/career_evidence/portfolio_presentation_pack.md
- docs/career_evidence/cv_project_bullet_bank.md
- docs/career_evidence/interview_project_talking_points.md

### Curated screenshots

- docs/screenshots/curated/01-dashboard-overview.png
- docs/screenshots/curated/02-evaluation-queue.png
- docs/screenshots/curated/03-job-posting-analyzer-conversion.png
- docs/screenshots/curated/08-interview-evidence-workspace.png

## Executive Review Summary

- README is stronger after Sprint 25F because Assisted Intake evidence is publicly linked under Evidence And Verification.
- The Assisted Intake workflow is presented consistently as manual, approval-based, and rule-based across README and Sprint 25A-D documents.
- The repo now has a clear evidence chain: workflow -> field audit -> field decision plan -> reviewer path -> README link block (planned in 25E, applied in 25F).
- Claim safety is strong because README uses negative/safe wording in Technical Decisions, What Is Not Claimed, Live Demo Status, and Assisted Intake Evidence -- avoiding unsupported external AI, scraping, auto-apply, Gmail, Calendar, live SaaS, and production-user claims.
- The strongest portfolio value is the combination of Django workflow design (Evaluation Queue, conversion bridge), analytics and reviewer surfaces (Funnel Metrics, data quality), field governance (25B/25C audit and decision plan), and evidence-based documentation with 249 passing tests.
- No immediate code or model changes are needed based on this presentation review.
- Future work should focus on polishing reviewer navigation (README length) and possibly consolidating evidence links if the front door becomes too long; converting evidence into CV/LinkedIn wording (Sprint 26B) is the highest-value next step.

## README Presentation Review

| Area | Current Status | Strength | Risk / Gap | Recommendation |
|---|---|---|---|---|
| Five-Minute Reviewer Path | Present with six ordered steps from dashboard through evidence docs | Gives recruiters and technical reviewers a fast operational walkthrough without requiring local setup first | Does not yet reference Assisted Intake evidence links in the numbered path; depth is in Evidence And Verification instead | Optional future cross-link one line to Assisted Intake Evidence subsection; keep path short |
| Career Evidence reviewer path | Present as subsection under Five-Minute Reviewer Path with V1-V6 flow and regeneration note | Clear bridge from core tracker to Career Evidence OS; honest about local dev and login | Adds length to README; V7-V10 not documented here (correct -- not built) | Keep as-is; do not add API version claims until implemented |
| Screenshot gallery | Eight curated PNGs embedded with captions after Sprint 21 refresh | Strong visual proof of dashboard, queue, conversion bridge, metrics, quality, interview workspace | Gallery is long; not all eight are required for every reviewer | Consider 26A navigation polish only if skimming becomes difficult |
| Technical Decisions | Three subsections: rule-based logic, data-quality propagation, SQLite scope | Explicitly rejects fake AI/LLM, scraping, auto-apply, Gmail, Calendar | UI may still use "AI" labels elsewhere in app; README explains rule-based intent | Monitor UI labels vs README claims in future sprints |
| Evidence And Verification | Links to portfolio index, presentation pack, analytics docs, evidence index, 249 tests | Central verification hub for reviewers | Section grows with each sprint family; Assisted Intake block adds four more links | Watch total link count; 26A optional if README feels crowded |
| Assisted Intake Evidence | Present under Evidence And Verification with claim-safe intro and four doc links plus verification commands | Completes Sprint 25E/25F plan; makes 25A-D discoverable from GitHub front door | Reviewers must scroll to Evidence And Verification; not in Five-Minute numbered list | Strong as implemented; optional one-line pointer from walkthrough only |
| Claim-safety wording | Live Demo Status, Technical Decisions, Assisted Intake block, and What Is Not Claimed use negative/safe framing | Portfolio-honest; matches assisted intake and Career Evidence docs | Length of limitation lists may feel defensive to some recruiters | Keep negative claims; brevity polish only in 26A if needed |
| Portfolio relevance | Positions product for Data Analyst, BI, Reporting, Analytics Engineer, Junior Data Engineer, FinTech analytics roles | Aligns with docs/career_evidence packs and evidence index | README is dense for non-technical first scan | Use Sprint 26B to extract recruiter-facing bullets without changing README |

## Assisted Intake Evidence Review

| Evidence Item | Current Role | Reviewer Value | Claim Boundary | Status |
|---|---|---|---|---|
| Workflow evidence (`assisted_job_intake_workflow.md`) | Documents manual approval-based sequence from paste JD through tracker record | Shows end-to-end intake thinking without automation | No scraping, auto-apply, external AI, Gmail, Calendar | Strong |
| Field audit (`assisted_job_intake_field_audit.md`) | Maps Sprint 25A target fields to existing models, forms, and rule-based outputs | Proves governance discipline; explains alias vs stored vs suggested fields | Does not claim every suggestion is a model field | Strong |
| Field decision plan (`assisted_intake_field_decision_plan.md`) | Converts audit into persist vs suggest decisions; no migration in 25C | Shows why no immediate model expansion was needed | No field-add or migration claim | Strong |
| Reviewer path (`assisted_intake_reviewer_path.md`) | Walkthrough table tying screenshots to 25A-C docs and claim boundaries | Fast path for recruiters and interviewers | Warns on "AI" UI labels; no automation claims | Good |
| README link block (Sprint 25F) | Public entry point under Evidence And Verification with four links and test commands | Makes evidence chain discoverable on GitHub without reading sprint plans | Same manual/rule-based boundaries as 25A | Strong |

## GitHub / Recruiter Value Assessment

### What a recruiter can understand quickly

- CareerFunnel Tracker is a Django analytics product for job-search activity: applications, sources, funnel metrics, and data-quality reporting.
- README provides a Five-Minute Reviewer Path, embedded screenshots, and explicit limitations (no live SaaS, no production users).
- Sprint 25F links show a structured assisted intake story: manual workflow, field audit, decisions, and reviewer path.
- The project demonstrates structured data thinking, workflow governance, and claim-safe delivery suitable for analyst and BI portfolios.

### What a technical reviewer can inspect

- README evidence paths: analytics docs, evidence index, career evidence walkthrough, Assisted Intake four-doc chain.
- Sprint 25A-F evidence chain with field audit and decision-plan logic grounded in `apps/applications/` and rule-based services.
- Rule-based decision support (job posting analyzer, smart review, save-quality warnings) rather than external AI claims.
- Validation discipline: 249 tests, Ruff, Django check, migration dry-run commands listed in README and evidence index.

### What this supports in CV / LinkedIn wording

Safe wording only (not a CV rewrite):

- Manual assisted job-intake workflow with user approval at each step.
- Rule-based role-fit review and Evaluation Queue for apply/skip decisions.
- Evidence-backed application tracking with source, status, CV version, and quality warnings.
- Django analytics and reviewer surfaces (funnel metrics, data quality, exports).
- Data-quality and field-governance thinking documented in audit and decision-plan evidence.

## Claim-Safety Review

### Safe claims

- Manual assisted intake workflow
- Rule-based job-posting fit review
- Evaluation Queue for apply/skip decisions
- Tracker-ready field pre-fill for user review
- Evidence-backed field audit and field-decision plan
- Reviewer path using curated screenshots
- Django-based analytics and evidence surfaces
- Full validation through Ruff, Django checks, migration checks, and tests (249 passing per README)

### Claims to avoid

- External AI / OpenAI / Claude implementation
- LinkedIn or Indeed scraping
- Auto-apply
- Automatic application submission
- Gmail integration
- Google Calendar integration
- Live SaaS
- Production users
- Background workflow automation

## Portfolio Presentation Rating

| Category | Rating | Reason |
|---|---:|---|
| GitHub README clarity | 8/10 | Strong structure, walkthroughs, and screenshots; length and sprint history may slow first-time skimmers |
| Evidence traceability | 9/10 | Clear chain from README -> assisted intake docs -> field audit -> decisions -> reviewer path; evidence index and career evidence packs align |
| Recruiter readability | 7/10 | Good role positioning and screenshots; technical depth and long sections require selective reading |
| Technical credibility | 8/10 | 249 tests, metric governance docs, service-layer analytics, honest limitations; portfolio-scale SQLite clearly scoped |
| Claim safety | 9/10 | Consistent negative framing across README, 25A-D docs, and portfolio claim-safety rules |
| Screenshot support | 8/10 | Eight curated images cover core workflow; assisted intake relies on four key shots plus optional funnel/quality shots in reviewer path |
| Overall portfolio presentation after Sprint 25 | 8/10 | Presentation is review-ready and evidence-complete; main gap is converting repo depth into short external wording (26B), not product build |

## Risks / Gaps To Monitor

- README may become long if too many sprint-specific links are added without navigation polish.
- Assisted Intake evidence is strong, but reviewer navigation must remain concise; evidence is under Evidence And Verification, not the numbered Five-Minute list.
- UI labels containing "AI" must remain explained as rule-based/local assistance unless external APIs are implemented, tested, and documented later.
- Future V7-V10 API work must not be claimed until built, tested, and documented.
- Portfolio presentation should avoid sounding like a production SaaS product unless deployment and user evidence exist.
- evidence_index.md sprint checkpoint table may lag latest sprint families (24A, 25A-F, 26); index update is out of Sprint 26 scope but worth a future documentation pass.

## Recommended Next Sprint Options

| Option | Sprint Name | Purpose | Recommended? | Reason |
|---|---|---|---|---|
| 1 | Sprint 26A -- README Navigation Polish | Make README easier to skim without adding new claims | Maybe | Useful only if README feels too long for recruiters |
| 2 | Sprint 26B -- Portfolio/CV Wording Pack | Convert current evidence into CV bullets, LinkedIn wording, and interview explanation | Yes | Turns repo work into job-application value; cv_project_bullet_bank and interview talking points exist as inputs |
| 3 | Sprint 26C -- Screenshot Evidence Refresh Decision | Decide whether new screenshots are needed after Sprint 25F | Maybe | README link change does not require new screenshots; curated set still matches workflow |
| 4 | Sprint 27 -- Next Product Capability Planning | Choose next product sprint after evidence presentation review | Later | Presentation should be fully captured first |

## Final Sprint 26 Recommendation

Sprint 26 should remain review-only.

Recommended next best step after Sprint 26:

**Sprint 26B -- Portfolio/CV Wording Pack**

Reason:

The repository evidence is now strong enough to convert into recruiter-facing CV, LinkedIn, GitHub pinned repo description, and interview wording. README, Assisted Intake chain, career evidence packs, and curated screenshots provide sufficient source material without new product features.

Do not recommend V7-V10 API implementation yet unless explicitly approved later.

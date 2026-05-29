# CareerFunnel Tracker - Evidence Index

## Purpose

This document is the evidence index for CareerFunnel Tracker.

It gives reviewers, recruiters, and future maintainers a clear path through the project evidence: sprint checkpoints, screenshot proof, Git tags, test progression, analytics documentation, and what each artefact demonstrates.

CareerFunnel Tracker is positioned as a Django-based job-search intelligence and analytics platform. The evidence below proves that the project was built through controlled, tested, evidence-first sprints rather than one-off UI changes.

---

## Current Project Checkpoint

| Item | Current State |
|---|---|
| Current stable branch | `main` |
| Latest completed sprint family | Sprint 23 -- Career Evidence OS (23A-23F) |
| Latest sprint tags (23) | `sprint-23a-career-evidence-v1` through `sprint-23f-complete` |
| Current documentation sprint | Sprint 24A -- Portfolio Front Door Evidence Alignment (`sprint-24a-portfolio-front-door`) |
| Current verified test count | 249 tests passing |
| Sprint 21-22 evidence status | Complete (`sprint-21-complete`, `sprint-22-complete`) |
| Main evidence folder | `docs/evidence/screenshots/` |
| Career Evidence markdown | `docs/career_evidence/` |
| Career Evidence screenshots | `docs/screenshots/career_evidence/` |
| Analytics documentation folder | `docs/analytics/` |

**Sprint 35 (merged on `main`):** Interview + Email Workflow Polish - **419** tests validated at closure; evidence doc `docs/evidence/sprint_35_interview_email_workflow_polish.md`.

**Sprint 36 (feature branch `sprint-36-weekly-risk-final-os-polish`):** Weekly Risk / Final Operating System Polish - **441** tests validated; evidence doc `docs/evidence/sprint_36_weekly_risk_os_polish.md`. Sprint 34-35 remain documented below.

**Sprint 37 (feature branch `sprint-37-saas-foundation-audit-design-system-lock`):** SaaS Foundation Audit + Design System Lock - **16** foundation audit tests in `tests/test_sprint_37a_shell_foundation_audit.py`; app suite **441** tests unchanged; combined `apps tests` run **525** tests; evidence doc `docs/evidence/sprint_37_saas_foundation_audit.md`. Audit-only sprint: no redesign, no model/migration changes.

**Sprint 38 (feature branch `sprint-38-premium-saas-shell-navbar-sidebar`):** Premium SaaS Shell - navbar + sidebar upgrade with product workflow groups, claim-safe badges, Quick Add/user menus, responsive drawer controls; **25** shell audit tests; evidence doc `docs/evidence/sprint_38_premium_saas_shell.md`. Shell-only sprint: no dashboard/form/report redesign.

**Sprint 39 (feature branch `sprint-39-premium-dashboard-command-centre`):** Premium Dashboard Command Centre - nine dashboard modules, read-only service helpers, **28** dashboard tests; evidence doc `docs/evidence/sprint_39_premium_dashboard_command_centre.md`. Dashboard-only sprint: no forms/reporting/model changes.

**Sprint 40A (feature branch `sprint-40a-premium-reporting-foundation`):** Premium Reporting Foundation - funnel performance, data quality, and application quality reports with shared reporting components; **10** new `PremiumReportingFoundationTests`; evidence doc `docs/evidence/sprint_40a_premium_reporting_foundation.md`. Reporting-only sprint: no dashboard/forms/model/migration changes.

**Sprint 40B (feature branch `sprint-40b-source-cv-reports-search-filter-pagination`):** Source Performance + CV Version Performance with reusable search/filter/pagination; **15** new `PremiumReportingSourceCvTests`; evidence doc `docs/evidence/sprint_40b_source_cv_reports_search_filter_pagination.md`. Uses Django `Paginator` for portfolio-scale pagination.

**Sprint 40C (feature branch `sprint-40c-rejection-weekly-visual-export-polish`):** Rejection Patterns, Weekly Trend, Visual Analytics Evidence, and Export Centre polish; **7** new `PremiumReportingSprint40cTests`; **4** `ExportCentrePolishTests`; evidence doc `docs/evidence/sprint_40c_rejection_weekly_visual_export_polish.md`. Completes Sprint 40 reporting suite.

**Sprint 41 (feature branch `sprint-41-skill-intelligence-foundation`):** Skill Intelligence Foundation - manual evidence summary, gap review prompts, role-readiness checklists (DA/BI/AE/DE), portfolio mapping; **11** new `SkillIntelligenceFoundationTests`; evidence doc `docs/evidence/sprint_41_skill_intelligence_foundation.md`. No models/migrations.

**Sprint 42 (feature branch `sprint-42-javascript-dynamic-ux-foundation`):** JavaScript Dynamic UX Foundation - modular progressive enhancement (sidebar collapse, mobile drawer, table scan, form UX, report accordions, copy/toast); **11** new `Sprint42JavaScriptFoundationTests`; evidence doc `docs/evidence/sprint_42_javascript_dynamic_ux_foundation.md`. No models/migrations.

**Sprint 43 (feature branch `sprint-43-skill-gap-foundation`):** Skill Gap Foundation - new `apps.skill_gaps` app with `ApplicationSkillGap` model, rule-based services, admin, migration `0001_initial`; **14** tests in `apps.skill_gaps.tests`; SQL proof `G:\workflow_tools\sprint43_sqlmigrate_skill_gaps_0001.txt`; evidence doc `docs/evidence/sprint_43_skill_gap_foundation.md`. Failure counts use only `REJECTED` and `AUTO_REJECTED`.

**Sprint 44 (feature branch `sprint-44-skill-intelligence-dashboard`):** Skill Intelligence Dashboard Foundation - read-only `/skill-gaps/` page (`skill_gaps:dashboard`), user-scoped summaries and GET filters; **12** dashboard tests (**26** total in `apps.skill_gaps.tests`); evidence doc `docs/evidence/sprint_44_skill_intelligence_dashboard.md`. No model/migration changes.

**Sprint 45 (feature branch `sprint-45-skill-gap-action-plan-foundation`):** Skill Gap Action Plan Foundation - Manual action plan section on `/skill-gaps/` with grouped suggested next steps; **8** new action-plan tests (**34** total in `apps.skill_gaps.tests`); evidence doc `docs/evidence/sprint_45_skill_gap_action_plan_foundation.md`. Read-only, no model/migration changes.

**Sprint 46 (feature branch `sprint-46-skill-gap-learning-plan-foundation`):** Skill Gap Learning Plan Foundation - Manual learning plan section on `/skill-gaps/` with grouped learning focus and suggested practice; **10** new learning-plan tests (**44** total in `apps.skill_gaps.tests`); evidence doc `docs/evidence/sprint_46_skill_gap_learning_plan_foundation.md`. Read-only, ASCII-safe text, no model/migration changes.

**Sprint 47 (feature branch `sprint-47-skill-gap-evidence-readiness-foundation`):** Skill Gap Evidence Readiness Foundation - Manual evidence readiness section on `/skill-gaps/` with grouped evidence focus and suggested evidence prompts; **10** new evidence-readiness tests (**54** total in `apps.skill_gaps.tests`); evidence doc `docs/evidence/sprint_47_skill_gap_evidence_readiness_foundation.md`. Read-only, ASCII-safe text, no model/migration changes.

**Sprint 48 (feature branch `sprint-48-skill-gap-portfolio-evidence-mapping`):** Skill Gap Portfolio Evidence Mapping Foundation - Manual portfolio evidence mapping section on `/skill-gaps/` with grouped portfolio proof focus and manual proof prompts; **10** new portfolio-mapping tests (**64** total in `apps.skill_gaps.tests`); evidence doc `docs/evidence/sprint_48_skill_gap_portfolio_evidence_mapping.md`. Read-only, ASCII-safe text, no model/migration changes.

**Sprint 49 (feature branch `sprint-49-skill-gap-interview-story-mapping`):** Skill Gap Interview Story Mapping Foundation - Manual interview story mapping section on `/skill-gaps/` with grouped STAR-style story prompts; **10** new interview-story tests (**74** total in `apps.skill_gaps.tests`); evidence doc `docs/evidence/sprint_49_skill_gap_interview_story_mapping.md`. Read-only, ASCII-safe text, no model/migration changes.

**Sprint 50 (feature branch `sprint-50-skill-gap-cv-bullet-mapping`):** Skill Gap CV Bullet Mapping Foundation - Manual CV bullet mapping section on `/skill-gaps/` with grouped CV bullet prompts (no automatic rewriting); **10** new CV-bullet tests (**84** total in `apps.skill_gaps.tests`); evidence doc `docs/evidence/sprint_50_skill_gap_cv_bullet_mapping.md`. Read-only, ASCII-safe text, no model/migration changes.

**Sprint 51 (feature branch `sprint-51-final-reviewer-walkthrough-polish`):** Final Reviewer Walkthrough Polish - README "How to review", dashboard reviewer note (`templates/dashboard/overview.html`), skill-gaps reviewer workflow note; **4** dashboard + **3** skill-gaps reviewer tests; evidence doc `docs/evidence/sprint_51_final_reviewer_walkthrough_polish.md`. Copy/UX only; no view wiring changes; no models/migrations.

**Sprint 52 Phase 2 (feature branch `sprint-52-final-saas-premium-components-plotly-metrics`):** Premium SaaS component CSS foundation + Funnel Metrics local weekly trend SVG chart; remote chart script removed; **8** new `Sprint52Phase2FoundationTests`; evidence doc `docs/evidence/sprint_52_final_saas_premium_components_plotly_metrics.md`. No models/migrations/routes; no Plotly dependency.

**Sprint 52 Phase 3 (same branch):** Funnel Metrics visual analytics completion - funnel conversion, outcome breakdown, source performance, and CV version local SVG charts via extended `funnel-charts.js`; **8** new `Sprint52Phase3VisualAnalyticsTests`; tables and Phase 2 weekly trend retained. No Plotly/vendor/deps.

**Sprint 53 (feature branch `sprint-53-pptx-ai-capability-framework`):** PPTX AI Capability Framework - manual advisory framework service (`apps/skills/services/ai_capability_framework.py`), read-only page `/skills/ai-capability-framework/`, **16** tests in `apps.skills`; evidence doc `docs/evidence/sprint_53_pptx_ai_capability_framework.md`. No models/migrations, scoring, matching, recommendations, external AI calls, or automation.

**Sprint 54 (feature branch `sprint-54-ai-readiness-scoring-engine`):** AI Readiness Scoring Engine - rule-based scoring service (`apps/skills/services/ai_readiness_scoring.py`), read-only report `/skills/ai-readiness-report/`, **36** tests in `apps.skills`; evidence doc `docs/evidence/sprint_54_ai_readiness_scoring_engine.md`. Phase 2 exposes portfolio baseline readiness report; no models/migrations, external AI calls, job matching, recommendations, or automation.

**Sprint 55 (feature branch `sprint-55-job-to-ai-capability-matching`):** Job-to-AI Capability Matching - deterministic keyword matching service (`apps/skills/services/job_ai_capability_matching.py`), read-only demo report `/skills/job-ai-capability-match/`, **58** tests in `apps.skills`; evidence doc `docs/evidence/sprint_55_job_to_ai_capability_matching.md`. Phase 2 uses sample JD text only; no persistence, models/migrations, external AI calls, or automation.

**Sprint 56 (feature branch `sprint-56-learning-improvement-recommendation-engine`):** Learning and Improvement Recommendation Engine - deterministic service (`apps/skills/services/learning_recommendations.py`) combining Sprint 54 readiness and Sprint 55 job-match outputs, **12** new recommendation tests; evidence doc `docs/evidence/sprint_56_learning_improvement_recommendation_engine.md`. Phase 1 service only; no UI, models/migrations, external AI calls, or automation.

---

## Evidence Principles

CareerFunnel Tracker evidence follows these rules:

- Every major sprint should produce either code evidence, documentation evidence, screenshot evidence, or all three.
- UI screenshots must show real implemented pages, not mockups.
- Tests must pass before sprint commits are merged.
- Metrics and recommendations must be rule-based and evidence-based.
- No fake users, fake customers, fake AI claims, or hardcoded analytics values should be used.
- Documentation should explain what the project does, why it matters, and what limitations still exist.

---

# Sprint Evidence Summary

## Sprint 1 - Foundation + Dashboard Trust

### Status

Completed and tagged.

### Git Tag

```text
sprint-1-complete
```

### Main Evidence Screenshot

```text
docs/evidence/screenshots/sprint-1b-dashboard-trust-surfaces.png
```

### What This Screenshot Proves

- Dashboard page exists.
- Dashboard layout was upgraded from a basic interface into a more credible product surface.
- Real-data KPI cards are visible.
- Trust notes are visible.
- Dashboard content is based on stored tracker data.
- The project avoids fake dashboard metrics.

### Key Features Proven

- Foundation safety improvements.
- Application source choices improved.
- Job-fit scoring logic stabilised.
- Dashboard trust surfaces added.
- Real-data presentation approach established.

### Reviewer Value

This sprint proves the project has a stable base and a credible first impression.

---

## Sprint 2A - Source ROI + CV Version Performance

### Status

Completed and tagged.

### Git Tag

```text
sprint-2a-complete
```

### Main Evidence Screenshot

```text
docs/evidence/screenshots/sprint-2a-metrics-source-roi-cv-performance.png
```

### What This Screenshot Proves

- Metrics page includes Source ROI.
- Metrics page includes CV Version Performance.
- The platform groups outcomes by source.
- The platform groups outcomes by CV version.
- The UI explains performance tracking without pretending to be scientific A/B testing.
- Analytics are built from existing `JobApplication` records.

### Key Features Proven

- `build_source_roi(user)`
- `build_cv_version_performance(user)`
- Source-level response, interview, and offer metrics.
- CV-version-level response, interview, offer, and rejection metrics.
- Metrics UI tables.
- Service-layer tests.

### Reviewer Value

This sprint proves the project can turn raw application records into BI-style performance analysis.

---

## Sprint 2B - Rejection Pattern Analysis

### Status

Completed and tagged.

### Git Tag

```text
sprint-2b-complete
```

### Main Evidence Screenshot

```text
docs/evidence/screenshots/sprint-2b-rejection-pattern-analysis.png
```

### What This Screenshot Proves

- Metrics page includes Rejection Pattern Analysis.
- Total rejections and auto-rejections are visible.
- Rejection rates are calculated.
- Rejections are grouped by source.
- Rejections are grouped by CV version.
- Seniority or stretch-role risk is counted.
- Low-sample-size warning is shown where appropriate.
- Recommended actions are evidence-based.

### Key Features Proven

- `build_rejection_pattern_report(user)`
- Rejection status grouping.
- Auto-rejection analysis.
- Source-level rejection grouping.
- CV-version rejection grouping.
- Seniority-risk keyword detection.
- Evidence-based recommendation logic.

### Reviewer Value

This sprint proves the platform supports decision-making, not just passive reporting.

---

## Sprint 3 - Application Quality Intelligence

### Status

Completed and tagged.

### Git Tag

```text
sprint-3-complete
```

### Main Evidence Screenshot

```text
docs/evidence/screenshots/sprint-3-application-quality-report.png
```

### What This Screenshot Proves

- Metrics page includes Application Quality.
- The platform identifies applications with incomplete evidence.
- Missing CV version is tracked.
- Missing precise source is tracked.
- Missing job description is tracked.
- Missing required skills are tracked.
- Missing follow-up dates are tracked.
- Seniority or stretch-role risk is tracked.
- Applications needing action are shown.

### Key Features Proven

- `build_application_quality_report(user)`
- `ApplicationQualityIssue`
- `ApplicationQualityReport`
- Missing-field detection.
- Active-status follow-up detection.
- Seniority-risk detection.
- Recommended actions for application cleanup.

### Reviewer Value

This sprint proves the platform improves operational discipline and application-record quality.

---

## Sprint 4 - Data Quality + Analytics Governance

### Status

Completed and tagged.

### Git Tag

```text
sprint-4-complete
```

### Main Evidence Screenshot

```text
docs/evidence/screenshots/sprint-4-data-quality-analytics-governance.png
```

### Documentation Evidence

```text
docs/analytics/metric_definitions.md
docs/analytics/analytics_lineage.md
```

### What This Screenshot Proves

- Metrics page includes Data Quality.
- Analytics-ready application count is visible.
- Analytics-ready rate is visible.
- Data Quality Score is visible.
- Missing source and generic source counts are visible.
- Missing CV version, job description, required skills, and follow-up counts are visible.
- Data quality checks table is visible.
- Recommended cleanup actions are visible.

### What the Documentation Proves

`metric_definitions.md` proves:

- Metrics are governed and explainable.
- Each core metric has a business question, calculation, source field, value, and limitation.
- The project avoids black-box reporting.

`analytics_lineage.md` proves:

- The project follows Bronze -> Silver -> Gold analytics thinking.
- Raw records are transformed into cleaned logic and then business-ready outputs.
- The platform demonstrates Analytics Engineering principles.

### Key Features Proven

- `build_data_quality_report(user)`
- `DataQualityCheck`
- `DataQualityReport`
- Analytics-ready application logic.
- Data Quality Score.
- Completion-rate severity logic.
- Metric governance documentation.
- Analytics lineage documentation.

### Reviewer Value

This sprint proves the project is more than a Django CRUD app. It demonstrates data quality, metric governance, lineage, and reporting trust.

---

## Sprint 5 - Export + Evidence Centre

### Status

Completed and tagged.

### Git Tag

```text
sprint-5-complete
```

### Main Evidence Screenshot

```text
docs/evidence/screenshots/sprint-5-export-evidence-centre.png
```

### Documentation Evidence

```text
docs/evidence/evidence_index.md
README.md
```

### Sprint 5A Evidence

Commit:

```text
1818124 Sprint 5A: stabilise export routes and tests
```

What it proves:

- Existing export routes were reviewed.
- Missing `build_interviews_workbook` import was fixed.
- `export_notes` was protected with `@login_required`.
- Export-route tests were strengthened.
- Authenticated export access is tested.
- XLSX response content type and filename behaviour are tested.
- Unauthenticated redirects are tested.

### Sprint 5B Evidence

Commit:

```text
c0d878f Sprint 5B: upgrade export centre UI
```

What it proves:

- Export Centre page was upgraded.
- Template was reformatted from compressed markup into maintainable Django template structure.
- Full Tracker workbook export remains visible.
- Applications, Daily Logs, Weekly Reviews, Interview Prep, and Notes exports are visible.
- Trust and evidence note was added.
- Export links were preserved.

### Sprint 5C Evidence

This file:

```text
docs/evidence/evidence_index.md
```

What it proves:

- Evidence is organised.
- Sprint screenshots and tags are easy to review.
- Reviewer walkthrough path is documented.
- Project proof is traceable.

### Sprint 5D Evidence

README upgrade:

```text
README.md
```

What it proves:

- Project purpose is clear.
- Feature list is current.
- Analytics modules are explained.
- Screenshots and evidence are linked.
- Test status is visible.
- Known limitations are honest.
- Portfolio value is clear.

---

## Sprint 6 - UI Polish + Portfolio Presentation

### Status

Completed and tagged.

### Git Tag

```text
sprint-6-complete
```

### Main Evidence Screenshots

```text
docs/evidence/screenshots/sprint-6-dashboard-final-polish.png
docs/evidence/screenshots/sprint-6-metrics-final-polish.png
docs/evidence/screenshots/sprint-6-export-centre-final-polish.png
```

### Documentation Evidence

```text
docs/evidence/ui_polish_audit.md
docs/evidence/portfolio_presentation_notes.md
```

### What This Screenshot Set Proves

- Dashboard presentation was polished without changing analytics logic.
- Metrics page readability was improved while preserving rule-based calculations.
- Export Centre presentation remained reviewer-ready.
- Sprint 6 stayed within UI polish, screenshot evidence, and portfolio presentation scope.
- No fake users, fake customers, fake AI claims, or production deployment claims were introduced.

### Reviewer Value

This sprint proves the project can be polished for portfolio presentation while keeping claims honest and repository behaviour stable.

---

## Sprint 7 - Documentation Alignment + Deployment Preparation

### Status

Completed and tagged.

### Git Tag

```text
sprint-7-complete
```

### Main Evidence

```text
README.md
```

### What This Sprint Proves

- Project status documentation was aligned with the repository state.
- Optional deployment preparation notes were added without claiming live production hosting.

### Reviewer Value

This sprint proves documentation stays current as the project matures beyond early analytics sprints.

---

## Sprint 8 - Ruff Code Quality Cleanup

### Status

Completed and tagged.

### Git Tag

```text
sprint-8-complete
```

### Main Evidence

- Ruff-clean modules across applications, metrics, exports, AI agents, dashboard, and related apps.
- CI-style local verification remains passing.

### What This Sprint Proves

- Code quality tooling was applied repository-wide.
- Lint issues were resolved without changing analytics behaviour.

### Reviewer Value

This sprint proves the codebase is maintainable and review-ready for recruiters and technical interviewers.

---

## Sprint 9 - Today Action Panel

### Status

Completed and tagged.

### Git Tag

```text
sprint-9-complete
```

### What This Sprint Proves

- Dashboard includes a Today Action panel driven by stored records.
- Action logic is service-based and tested.

### Reviewer Value

This sprint proves the platform supports daily execution, not only retrospective reporting.

---

## Sprint 10 - Manual Follow-Up Email Draft

### Status

Completed and tagged.

### Git Tag

```text
sprint-10-complete
```

### What This Sprint Proves

- Manual follow-up email draft service and UI were added.
- Workflow remains user-controlled; no inbox automation is claimed.

### Reviewer Value

This sprint proves operational follow-up support without fake AI or email integration claims.

---

## Sprint 11 - Mark Follow-Up Sent Workflow

### Status

Completed and tagged.

### Git Tag

```text
sprint-11-complete
```

### What This Sprint Proves

- Users can mark follow-ups as sent through a manual workflow.
- UI copy clarifies the manual nature of the process.

### Reviewer Value

This sprint proves follow-up tracking stays honest and auditable.

---

## Sprint 12 - Status-Aware Follow-Up Action

### Status

Completed and tagged.

### Git Tag

```text
sprint-12-complete
```

### What This Sprint Proves

- Follow-up actions respect application pipeline status.
- Recommendations and actions avoid inappropriate stages.

### Reviewer Value

This sprint proves workflow logic is context-aware, not generic messaging only.

---

## Sprint 13 - Application Evidence Readiness

### Status

Completed and tagged.

### Git Tag

```text
sprint-13-complete
```

### What This Sprint Proves

- Application evidence readiness logic identifies whether records are strong enough for review.
- UI surfaces readiness on the application detail flow.

### Reviewer Value

This sprint proves the platform helps users improve record quality before analytics and exports rely on it.

---

## Sprint 14 - Weekly Trend Analytics + Documentation Integrity

### Status

Completed and tagged.

### Git Tag

```text
sprint-14-complete
```

### Commits

```text
6a9bb6d Sprint 14A: add weekly trend analytics service
3bd891c Sprint 14B: display weekly trend on funnel metrics
af2d9e7 Sprint 14C: optimize daily log aggregation
```

### Main Evidence Screenshot

```text
docs/evidence/screenshots/sprint-14-weekly-trend-analytics.png
```

Capture this screenshot manually from the Funnel Metrics Weekly Trend section before final Sprint 14 acceptance if the file is not yet in the repository.

### Documentation Evidence

```text
README.md
docs/analytics/metric_definitions.md
docs/evidence/evidence_index.md
```

### What This Sprint Proves

- `build_weekly_trend(user)` groups `JobApplication` records into Monday-starting weekly buckets (default 10 weeks).
- Zero-application weeks are included so the table shows a full lookback window.
- Response counts use existing `_RESPONSE_STATUSES`; response rate uses `safe_percentage()`.
- Funnel Metrics displays a Weekly Trend table (no chart in Sprint 14).
- `build_funnel_metrics()` aggregates `DailyLog` fields in one ORM `aggregate()` call instead of Python iteration.
- Metric definitions and evidence index reflect Sprints 7-14.

### Key Features Proven

- `WeeklyTrendRow` and `build_weekly_trend(user, weeks=10)`
- Funnel Metrics context: `weekly_trend_rows`, `weekly_trend_has_data`
- Weekly Trend section `id="weekly-trend"` with not-enough-data message when fewer than two active weeks exist
- DailyLog ORM aggregation with safe empty defaults
- Service and view tests for weekly trend and funnel metrics

### Reviewer Value

This sprint proves the project can add time-based funnel analytics with governed metrics, efficient aggregation, and reviewer-ready documentation--without charts, fake AI, or undeployed production claims.

---

## Sprint 15 - Intake-to-Application Conversion + Evaluation Queue

### Status

Completed and tagged.

### Git Tag

```text
sprint-15-complete
```

### Commits

```text
f8a652e Sprint 15B: unify role fit scoring constants
e5617c9 Sprint 15C: add intake to application conversion bridge
f111e06 Sprint 15D: add evaluation queue workflow
cd972fa Sprint 15E: display fit review on application detail
```

### Screenshot Evidence

```text
docs/evidence/screenshots/sprint-15-conversion-bridge.png
docs/evidence/screenshots/sprint-15-evaluation-queue.png
```

Capture these screenshots manually from the Job Posting Analyzer (Save as Application link after analysis) and Evaluation Queue pages before final Sprint 15 acceptance if the files are not yet in the repository.

### Documentation Evidence

```text
README.md
docs/analytics/metric_definitions.md
docs/evidence/evidence_index.md
```

### What This Sprint Proves

- Role-fit classification lists are shared from `apps/job_intelligence/constants.py` for Job Posting Analyzer and Application Smart Review.
- Job Posting Analyzer can open a pre-filled Add Application form via GET parameters; the user must review and submit before anything is saved.
- Evaluation Queue surfaces applications at Job Found or Fit Checked pipeline stages.
- Application Detail shows a compact rule-based Fit Review summary from `build_smart_review(application)`.
- Intake-to-application workflow stays manual and honest (no auto-save, auto-apply, scraping, or live AI/API claims).

### Key Features Proven

- Canonical constants module and shared scoring inputs.
- Save as Application prefill bridge with fit-score to role-fit mapping.
- `evaluation_queue` view, route, sidebar link, and template.
- Fit Review section on application detail.
- Regression tests for prefill, queue filtering, and Fit Review context.

### Known Limitations (Sprint 15)

- Fit review is rule-based and local; it is not a live AI/API integration.
- Job Posting Analyzer pre-fills an application form only; it does not save or submit applications automatically.

### Reviewer Value

This sprint proves the project connects pre-application analysis to saved application records with consistent scoring, a clear evaluation queue, and honest manual submission--without fake automation or external AI dependencies.

---

## Sprint 16 - Analytics-Critical Field Warnings + Data Quality Impact Reporting

### Status

Completed and tagged.

### Git Tag

```text
sprint-16-complete
```

### Commits

```text
dc4e62b Sprint 16B: add save quality warning service
13123fe Sprint 16C: show save quality warnings after application save
3e35542 Sprint 16D: add analytics impact notes to data quality report
```

### Screenshot Evidence

```text
docs/evidence/screenshots/sprint-16-quality-warnings.png
docs/evidence/screenshots/sprint-16-data-quality-impact-report.png
```

Capture these screenshots manually from the application create/update flow (post-save warning messages) and the Funnel Metrics Data Quality / Analytics Impact section before final Sprint 16 acceptance if the files are not yet in the repository.

### Documentation Evidence

```text
README.md
docs/analytics/metric_definitions.md
docs/evidence/evidence_index.md
```

### What This Sprint Proves

- `SaveQualityWarning` and `build_save_quality_warnings()` detect analytics-critical gaps on saved `JobApplication` records.
- Application create and update show advisory Django warning messages after a successful save; saves are not blocked and forms are not rejected with `form.add_error()`.
- Source warnings use accurate "cannot attribute / grouped under Other" wording for Source ROI impact.
- The Data Quality Report includes quantified Analytics Impact notes explaining which analytics reports are affected by current data gaps.
- Warnings are local and rule-based, not live AI/API integration.

### Key Features Proven

- Save-quality warning service with five analytics-critical conditions.
- Post-save warning messages on application create and update.
- Data Quality Report `analytics_impact_notes` with count-based impact wording.
- Analytics Impact partial on Funnel Metrics.
- Regression tests for warning service, views, and data quality impact notes.

### Known Limitations (Sprint 16)

- Warnings are advisory and do not block saving.
- Warnings are local/rule-based, not live AI/API.
- No scraping, auto-apply, email integration, OAuth, or background automation was added.
- `role_fit` and `follow_up_date` are intentionally excluded from this warning layer to reduce warning fatigue.

### Reviewer Value

This sprint proves the project guides users toward analytics-ready records at the point of entry and explains downstream report impact honestly--without blocking saves, fake AI claims, or undeployed automation.

---

# Screenshot Evidence Register

| Sprint | Screenshot File | Main Proof |
|---|---|---|
| Sprint 1B | `docs/evidence/screenshots/sprint-1b-dashboard-trust-surfaces.png` | Dashboard trust surfaces and real-data KPI presentation |
| Sprint 2A | `docs/evidence/screenshots/sprint-2a-metrics-source-roi-cv-performance.png` | Source ROI and CV Version Performance |
| Sprint 2B | `docs/evidence/screenshots/sprint-2b-rejection-pattern-analysis.png` | Rejection Pattern Analysis and recommendations |
| Sprint 3 | `docs/evidence/screenshots/sprint-3-application-quality-report.png` | Application Quality Report and applications needing action |
| Sprint 4 | `docs/evidence/screenshots/sprint-4-data-quality-analytics-governance.png` | Data Quality Score, checks, and analytics governance |
| Sprint 5 | `docs/evidence/screenshots/sprint-5-export-evidence-centre.png` | Export Centre and reviewer evidence flow |
| Sprint 6 | `docs/evidence/screenshots/sprint-6-dashboard-final-polish.png` | Dashboard final polish |
| Sprint 6 | `docs/evidence/screenshots/sprint-6-metrics-final-polish.png` | Metrics page final polish |
| Sprint 6 | `docs/evidence/screenshots/sprint-6-export-centre-final-polish.png` | Export Centre final polish |
| Sprint 14 | `docs/evidence/screenshots/sprint-14-weekly-trend-analytics.png` | Weekly Trend table on Funnel Metrics |
| Sprint 15 | `docs/evidence/screenshots/sprint-15-conversion-bridge.png` | Job Posting Analyzer Save as Application prefill bridge |
| Sprint 15 | `docs/evidence/screenshots/sprint-15-evaluation-queue.png` | Evaluation Queue for Job Found / Fit Checked opportunities |
| Sprint 16 | `docs/evidence/screenshots/sprint-16-quality-warnings.png` | Post-save advisory quality warnings on application create/update |
| Sprint 16 | `docs/evidence/screenshots/sprint-16-data-quality-impact-report.png` | Data Quality Report Analytics Impact notes |

---

# Git Tag Register

| Tag | Meaning |
|---|---|
| `sprint-1-complete` | Foundation and dashboard trust checkpoint |
| `sprint-2a-complete` | Source ROI and CV Version Performance checkpoint |
| `sprint-2b-complete` | Rejection Pattern Analysis checkpoint |
| `sprint-3-complete` | Application Quality Intelligence checkpoint |
| `sprint-4-complete` | Data Quality and Analytics Governance checkpoint |
| `sprint-5-complete` | Export and Evidence Centre checkpoint |
| `sprint-6-complete` | UI polish and portfolio presentation checkpoint |
| `sprint-7-complete` | Documentation alignment and deployment preparation checkpoint |
| `sprint-8-complete` | Ruff code-quality cleanup checkpoint |
| `sprint-9-complete` | Today action panel checkpoint |
| `sprint-10-complete` | Manual follow-up email draft checkpoint |
| `sprint-11-complete` | Mark follow-up sent workflow checkpoint |
| `sprint-12-complete` | Status-aware follow-up action checkpoint |
| `sprint-13-complete` | Application evidence readiness checkpoint |
| `sprint-14-complete` | Weekly Trend analytics, Funnel Metrics table, DailyLog aggregation, and documentation checkpoint |
| `sprint-15-complete` | Shared role-fit constants, intake prefill bridge, Evaluation Queue, Application Detail Fit Review, and documentation checkpoint |
| `sprint-16-complete` | Save-quality warnings, post-save advisory messages, Data Quality Analytics Impact notes, and documentation checkpoint |
| `sprint-17-complete` | Recruiter-facing case study README and deployment preparation checkpoint |
| `sprint-18-complete` | Visual analytics evidence, Tableau workbook/screenshots, inline weekly trend chart checkpoint |
| `sprint-19-complete` | Interview Evidence Workspace checkpoint |
| `sprint-20-complete` | Portfolio release-candidate documentation alignment and recruiter handoff checkpoint |
| `sprint-21-complete` | UI polish and curated screenshot refresh checkpoint |
| `sprint-22-complete` | Portfolio handoff documentation checkpoint |
| `sprint-23a-career-evidence-v1` | V1 project evidence report checkpoint |
| `sprint-23b-job-fit-matrix` | V2 job-fit matrix checkpoint |
| `sprint-23c-recruiter-evidence-pack` | V3 recruiter evidence pack checkpoint |
| `sprint-23d-complete` | V4 Career Evidence dashboard UI checkpoint |
| `sprint-23e-complete` | V5 Playwright screenshot automation checkpoint |
| `sprint-23f-complete` | V6 optional Notion metadata sync checkpoint |

---

# Test Count Progression

| Checkpoint | Test Count | Notes |
|---|---:|---|
| Sprint 1 complete | 81 | Foundation safety, dashboard trust, early regression coverage |
| Sprint 2A complete | 96 | Source ROI and CV Version Performance tests added |
| Sprint 2B complete | 107 | Rejection Pattern Analysis tests added |
| Sprint 3 complete | 119 | Application Quality Report tests added |
| Sprint 4 complete | 134 | Data Quality Report tests added |
| Sprint 5 complete | 133 | Export tests consolidated into broader route coverage using subtests |
| Sprint 6 complete | 133 | UI polish and documentation work preserved existing test coverage |
| Sprint 13 complete | 161 | Application evidence readiness and follow-up workflow tests |
| Sprint 14 complete | 176 | Weekly trend service, funnel metrics UI, and DailyLog aggregation tests |
| Sprint 15 complete | 204 | Role-fit constants, intake prefill bridge, Evaluation Queue, and Fit Review tests |
| Sprint 16 complete | 233 | Save-quality warning service, post-save warnings, and Data Quality Analytics Impact tests |
| Sprint 18 complete | 244 | Dashboard CSV exports, quality indicators, Tableau evidence, and inline weekly trend chart visualization |
| Sprint 19 complete | 249 | Interview Evidence Workspace tests and release-candidate documentation baseline |
| Sprint 21C validation | 249 | UI-only polish branch still pending closeout; tests passed after curated screenshot refresh |

## Test Count Note

A lower test count does not always mean weaker coverage.

In Sprint 5A, export tests were consolidated into loop-based `subTest` coverage. This reduced the raw number of Django test methods while improving route coverage across export endpoints.

---

# Reviewer Walkthrough Path

Use this order when reviewing the project.

## 1. Start With README

```text
README.md
```

Purpose:

- Understand the project problem.
- Review the feature list.
- See the tech stack.
- Follow setup instructions.
- Find screenshots and evidence links.

## 2. Review Dashboard Screenshot

```text
docs/evidence/screenshots/sprint-1b-dashboard-trust-surfaces.png
```

Purpose:

- Confirm the project has a credible dashboard surface.
- See real-data KPI presentation.

## 3. Review Metrics Screenshots

```text
docs/evidence/screenshots/sprint-2a-metrics-source-roi-cv-performance.png
docs/evidence/screenshots/sprint-2b-rejection-pattern-analysis.png
docs/evidence/screenshots/sprint-3-application-quality-report.png
docs/evidence/screenshots/sprint-4-data-quality-analytics-governance.png
docs/evidence/screenshots/sprint-6-metrics-final-polish.png
docs/evidence/screenshots/sprint-14-weekly-trend-analytics.png
docs/evidence/screenshots/sprint-15-conversion-bridge.png
docs/evidence/screenshots/sprint-15-evaluation-queue.png
docs/evidence/screenshots/sprint-16-quality-warnings.png
docs/evidence/screenshots/sprint-16-data-quality-impact-report.png
```

Purpose:

- Follow the analytics depth progression.
- Confirm metrics, decision support, data quality logic, weekly trend table, intake prefill bridge, Evaluation Queue, save-quality warnings, and Analytics Impact notes.

## 4. Review Analytics Documentation

```text
docs/analytics/metric_definitions.md
docs/analytics/analytics_lineage.md
```

Purpose:

- Understand how metrics are calculated.
- Understand the Bronze -> Silver -> Gold lineage.
- Confirm governance and limitations.

## 5. Review Export Centre

```text
/export/
docs/evidence/screenshots/sprint-6-export-centre-final-polish.png
```

Purpose:

- Confirm workbook exports are available.
- Confirm tracker data can be reviewed or backed up.
- Confirm no fake export data is used.

## 6. Review Career Evidence OS (Sprint 23)

```text
docs/evidence/career_evidence_walkthrough.md
docs/career_evidence/README.md
docs/career_evidence/01_project_evidence_report.md
docs/career_evidence/02_job_fit_matrix.md
docs/career_evidence/03_recruiter_evidence_pack.md
docs/screenshots/career_evidence/
/dashboard/career-evidence/   (local dev, authenticated)
docs/notion/README.md         (optional V6)
```

Purpose:

- Follow V1-V6 evidence flow from generated markdown through dashboard UI and screenshots.
- Confirm claims stay repository-derived and portfolio-safe.

## 7. Review Tests

```powershell
python manage.py test
python manage.py test tests.test_career_evidence_audit tests.test_career_job_fit_matrix tests.test_career_recruiter_pack tests.test_career_evidence_views tests.test_career_evidence_screenshot_config tests.test_notion_sync_config
```

Purpose:

- Confirm service-layer analytics logic is tested.
- Confirm export routes are protected and functional.
- Confirm Career Evidence tools, views, screenshot config, and Notion sync config behave as documented.
- Confirm the repository is stable.

---

# Feature-to-Evidence Map

| Feature | Evidence Type | Evidence Location |
|---|---|---|
| Dashboard trust surface | Screenshot | `docs/evidence/screenshots/sprint-1b-dashboard-trust-surfaces.png` |
| Source ROI | Screenshot + tests | Sprint 2A screenshot, `apps/metrics/tests.py` |
| CV Version Performance | Screenshot + tests | Sprint 2A screenshot, `apps/metrics/tests.py` |
| Rejection Pattern Analysis | Screenshot + tests | Sprint 2B screenshot, `apps/metrics/tests.py` |
| Application Quality Report | Screenshot + tests | Sprint 3 screenshot, `apps/metrics/tests.py` |
| Data Quality Report | Screenshot + tests + docs | Sprint 4 screenshot, `apps/metrics/tests.py`, `docs/analytics/` |
| Weekly Trend | Screenshot + tests + docs | Sprint 14 screenshot, `apps/metrics/services.py`, `apps/metrics/tests.py`, `docs/analytics/metric_definitions.md` |
| Metric governance | Documentation | `docs/analytics/metric_definitions.md` |
| Analytics lineage | Documentation | `docs/analytics/analytics_lineage.md` |
| Export Centre | UI + tests | `/export/`, `apps/exports/tests.py` |
| Export route protection | Tests | `apps/exports/tests.py` |

---

# What This Project Demonstrates

CareerFunnel Tracker demonstrates:

- Django application development.
- Service-layer analytics design.
- BI-style reporting logic.
- Data quality checks.
- Metric governance.
- Analytics lineage.
- Export workflows.
- Evidence-first sprint delivery.
- Test-driven stability.
- Recruiter-friendly documentation.

---

# What This Project Does Not Claim

The project does not claim:

- Real paying customers.
- No production SaaS scale claim.
- Live AI automation.
- Gmail inbox automation.
- No scientific CV A/B testing claim.
- Financial ROI calculation.
- Enterprise data warehouse architecture.
- Fully deployed commercial platform unless deployment is added later.

These limitations are intentional and documented to keep the portfolio honest.

---

# Current Known Limitations

- Status history is not tracked yet.
- Stage transition events are not modelled yet.
- Rejection reasons are not independently verified.
- Seniority-risk detection is keyword-based.
- CV Version Performance is directional, not scientific A/B testing.
- Source ROI means channel outcome performance, not financial ROI.
- Weekly Trend uses `date_applied`, not response date.
- Export files are workbook exports, not automated BI pipelines.
- No live LLM or AI integration is active.
- Fit review and job-posting scoring are rule-based and local, not live AI/API integrations.
- Job Posting Analyzer pre-fills the Add Application form only; it does not save or submit applications automatically.
- No Gmail / Smart Inbox integration is active.
- No Celery / Redis background processing is active.

---

# Evidence Quality Checklist

Before considering a sprint complete, confirm:

- [ ] `python manage.py check` passes
- [ ] `python manage.py makemigrations --check --dry-run` passes
- [ ] `python manage.py test` passes
- [ ] `git status` is clean
- [ ] screenshot evidence is saved if UI changed
- [ ] screenshot file name is clear
- [ ] commit message is specific
- [ ] sprint tag is created after merge
- [ ] Notion is updated
- [ ] evidence index is updated if needed

---

## Sprint 18 - Tableau Dashboard Evidence + Inline Weekly Trend Chart

### Status

Completed and tagged as `sprint-18-complete`.

### Commits

```text
5754243 Sprint 18A: add dashboard CSV export pipeline
578f621 Sprint 18A: add dashboard quality indicators
a563e45 Sprint 18B: add Tableau dashboard evidence
1a83f32 Sprint 18C: add inline weekly trend visualization
f46b162 Sprint 18C: add inline weekly trend chart screenshot evidence
```

### Evidence Files

```text
dashboards/data/applications.csv
dashboards/data/daily_logs.csv
dashboards/tableau/careerfunnel_sprint18_tableau_workbook.twbx
docs/evidence/screenshots/sprint-18-performance-dashboard.png
docs/evidence/screenshots/sprint-18-quality-dashboard.png
docs/evidence/screenshots/sprint-18-chartjs-weekly-trend.png
```

### What This Sprint Proves

- Dashboard-ready synthetic CSV export for Tableau-style analysis.
- Safe yes/no quality indicators for analytics-readiness reporting.
- Local Tableau performance dashboard evidence.
- Local Tableau quality dashboard evidence.
- Inline weekly trend visualization inside Funnel Metrics.
- Existing Weekly Trend table remains available alongside the chart.
- Chart data is rendered safely with Django `json_script`.
- Private fields are not exported in dashboard CSVs.

### Known Limitations

- No verified Tableau Public URL is claimed.
- No Power BI dashboard was implemented in Sprint 18.
- No verified live deployment URL is claimed.

### Reviewer Value

Sprint 18 proves the project can move from Django-native analytics into dashboard-ready BI evidence while preserving privacy boundaries and honest portfolio claims.

---

## Sprint 19 - Interview Evidence Workspace

### Status

Completed and tagged as `sprint-19-complete`.

### Commits

- e1597f3 Sprint 19A: add interview evidence workspace
- 87a8633 Sprint 19B: add interview workspace screenshot evidence

### Screenshot Evidence

- `docs/evidence/screenshots/sprint-19-interview-evidence-workspace.png`

### What This Sprint Proves

- InterviewPrep detail page was upgraded into an Interview Evidence Workspace.
- The workspace uses existing application evidence readiness logic.
- The workspace uses existing Smart Review positioning.
- It shows readiness label, ready evidence, missing evidence, and recommended next improvement.
- It shows recommended CV and recommended projects.
- It shows application context such as company, role, CV version, cover letter version, portfolio indicator, required skills, and job description.
- It keeps preparation manual and local.
- It does not add email/calendar automation, scraping, auto-apply, external AI/API integration, or background tasks.

### Reviewer Value

This sprint proves CareerFunnel Tracker supports downstream interview preparation by connecting application evidence, role-fit reasoning, portfolio positioning, and manual preparation evidence in one reviewer-readable workspace.

---

## Sprint 20 - Portfolio Release Candidate Documentation Alignment

### Status

Completed and tagged as `sprint-20-complete`.

### What This Sprint Proves

- Portfolio-facing documentation was aligned for recruiter review.
- Evidence and presentation notes were kept honest about deployment, automation, BI, and commercial limitations.
- The project entered a release-candidate documentation baseline before Sprint 21 UI polish.

### Reviewer Value

This sprint proves the repository can be handed to reviewers with clear evidence, limitations, and presentation guidance.

---

## Sprint 21 - CSS Completeness + Navigation Polish

### Status

Completed and tagged as `sprint-21-complete`.

### Included Sprint 21 Commits

- 86a78c1 Sprint 21A.1: fix CSS completeness gaps
- ded7279 Sprint 21A.2: add sidebar active state
- 1660096 Sprint 21B: add navigation grouping and application section nav
- 82c6754 Sprint 21C: refresh curated screenshots after UI polish

### Evidence Files

```text
README.md
docs/evidence/evidence_index.md
docs/evidence/portfolio_presentation_notes.md
docs/screenshots/curated/01-dashboard-overview.png
docs/screenshots/curated/02-evaluation-queue.png
docs/screenshots/curated/03-job-posting-analyzer-conversion.png
docs/screenshots/curated/04-funnel-metrics-weekly-trend.png
docs/screenshots/curated/05-save-quality-warnings.png
docs/screenshots/curated/06-data-quality-impact-report.png
docs/screenshots/curated/07-visual-analytics-dashboard.png
docs/screenshots/curated/08-interview-evidence-workspace.png
```

### What This Sprint Proves

- Sprint 21 is UI-only polish; it does not add analytics logic, automation, deployment, or commercial product claims.
- CSS completeness gaps were fixed for `workflow-list`, `diagnosis-box`, `small-empty-state`, and `message-warning`.
- Undefined CSS variable references were replaced with existing safe styling.
- Sidebar active state was added.
- Sidebar navigation was grouped into Overview, Workflow, and Analytics.
- Application Detail received section navigation for Status, Evidence, Fit Review, Follow-Up, Role Info, Assets, and Notes.
- The curated screenshot set was refreshed after real local browser capture.
- 249 tests passed after Sprint 21C validation.

### Reviewer Value

This sprint improves portfolio presentation quality and navigation clarity while preserving the project's existing rule-based, local, evidence-first scope.

---

## Sprint 22 - Portfolio Handoff Documentation

### Status

Completed and tagged as `sprint-22-complete`.

### Evidence Files

```text
docs/evidence/recruiter_conversion_pack.md
docs/evidence/interview_explanation_pack.md
docs/evidence/feature_skill_hiring_value_map.md
docs/evidence/portfolio_handoff_checklist.md
```

### What This Sprint Proves

- Recruiter conversion, interview explanation, feature-to-skill mapping, and handoff checklist live under `docs/evidence/`.
- Documentation supports portfolio review without changing analytics behaviour.

### Reviewer Value

This sprint gives reviewers structured talking points and handoff checklists separate from the core tracker UI.

---

# Sprint 23 -- Career Evidence OS

Sprint 23 adds a **repository-derived evidence layer** for portfolio and recruiter review: markdown reports (V1-V3), dashboard surfaces (V4), Playwright screenshots (V5), and optional Notion metadata sync (V6). No external AI, live deployment, or job-search automation is introduced.

| Sprint | Tag | Version | Primary evidence |
| --- | --- | --- | --- |
| 23A -- Career Evidence Report | `sprint-23a-career-evidence-v1` | V1 | `docs/career_evidence/01_project_evidence_report.md` |
| 23B -- Job-Fit Matrix | `sprint-23b-job-fit-matrix` | V2 | `docs/career_evidence/02_job_fit_matrix.md` |
| 23C -- Recruiter Evidence Pack | `sprint-23c-recruiter-evidence-pack` | V3 | `docs/career_evidence/03_recruiter_evidence_pack.md` |
| 23D -- Career Evidence Dashboard UI | `sprint-23d-complete` | V4 | `/dashboard/career-evidence/` (local) |
| 23E -- Playwright Screenshot Automation | `sprint-23e-complete` | V5 | `docs/screenshots/career_evidence/` |
| 23F -- Optional Notion Metadata Sync | `sprint-23f-complete` | V6 | `docs/notion/README.md` |

### Reviewer entry points

```text
docs/career_evidence/README.md
docs/evidence/career_evidence_walkthrough.md
README.md (Career Evidence OS + reviewer path)
```

### V1 -- Project Evidence Report (23A)

- Tool: `tools/career_evidence_audit.py`
- Output: `docs/career_evidence/01_project_evidence_report.md`
- Proves: inventory of docs, tests, templates, static assets, screenshots, and Git context from the repo only.

### V2 -- Job-Fit Matrix (23B)

- Tool: `tools/career_job_fit_matrix.py`
- Input: `docs/career_evidence/sample_job_description.txt`
- Output: `docs/career_evidence/02_job_fit_matrix.md`
- Proves: requirement rows with evidence strength (`Strong` / `Partial` / `Missing`) mapped to real repository paths.

### V3 -- Recruiter Evidence Pack (23C)

- Tool: `tools/career_recruiter_pack.py`
- Output: `docs/career_evidence/03_recruiter_evidence_pack.md`
- Proves: recruiter-facing bullets and summaries traced to README, V1, and V2 without inventing deployment or product claims.

### V4 -- Career Evidence Dashboard UI (23D)

- Routes: `/dashboard/career-evidence/`, `/dashboard/career-evidence/project-evidence/`, `/dashboard/career-evidence/job-fit-matrix/`, `/dashboard/career-evidence/recruiter-pack/`
- Proves: authenticated, read-only rendering of V1-V3 markdown for browser review (local dev).

### V5 -- Playwright screenshots (23E)

- Script: `scripts/capture_career_evidence_screenshots.py`
- Folder: `docs/screenshots/career_evidence/` (`career_evidence_overview.png`, `project_evidence_report.png`, `job_fit_matrix.png`, `recruiter_pack.png`)
- Guide: `docs/screenshots/career_evidence/README.md`
- Proves: reviewer-ready PNG evidence of the V4 pages; local capture only, not production browser automation.

### V6 -- Optional Notion metadata sync (23F)

- Script: `scripts/notion_sync_career_evidence.py`
- Guide: `docs/notion/README.md`
- Proves: optional metadata/status upsert (paths, dates, sprint, screenshot-ready flag); does not upload markdown binaries or change Django runtime.

### Known limitations (Sprint 23)

- V1-V3 are generated documentation; re-run tools after material repo changes.
- V4 requires local `runserver` and login; not a live deployment claim.
- V5 requires a running dev server and local credentials via environment variables.
- V6 is optional, requires Notion API credentials locally, and syncs metadata only.
- No external AI, Gmail, Calendar, scraping, auto-apply, or background workers are added.

### Reviewer value

Sprint 23 shows how operational Django/analytics work can be packaged into **auditable, recruiter-readable evidence** with explicit fit mapping and honest limitations--relevant to Data Analyst, BI Analyst, Reporting Analyst, and Analytics Engineer portfolios.

---

## Sprint 28 - Live Application Pilot + Intake Refinement (28A-28D)

### Status

- **28A:** Complete - manual recruiter email import (`sprint-28a-email-import-complete`)
- **28B:** Live pilot - real job intake tested (apply and skip paths)
- **28C:** Complete - intake workflow refinement (CTA, locked CV, README, evidence, CI fix)
- **28D:** Complete - live pilot closure after 28C refinements (three-role validation)

### Documentation Evidence

```text
docs/evidence/sprint_28_live_application_pilot.md
docs/evidence/sprint_28d_live_pilot_closure.md
```

### What These Documents Prove

- Live workflow: Analyze -> Review -> Approve -> Pre-fill Add Application -> Manual Save.
- 28B: Successful apply path (Sphere) and disciplined skip path (Legal & General) without false `Submitted` records.
- 28C refinements: **Review & Pre-fill Application** CTA, locked CV `Aminul_Islam_Data_Analyst_CV` in Smart Review, README sprint alignment, GitHub Actions passed after CI assertion fix.
- 28D closure (`sprint_28d_live_pilot_closure.md`): Strong apply (LiveMore Mortgages), BI/analytics apply (Dow Jones), and stretch/test-only (Starcom) without polluting Applications when not applied.
- Honest boundaries: no Gmail API, OAuth, scraping, auto-apply, automatic saving, external AI/LLM, or automatic email sending.

### Screenshot Evidence (pending)

Capture per checklist in `sprint_28_live_application_pilot.md` before final Sprint 28 acceptance.

### Reviewer Value

Shows the tracker was exercised on real roles with explicit manual gates - not demo-only UI - and documents gaps (seniority false positives, pre-application statuses, richer pre-fill, demo CSV cleanup) without overstating automation. Sprint 28D confirms the refined intake workflow is ready for sprint closure after repository validation and CI verification.

---

## Sprint 29 - Recruiter Email Workflow Enhancements (29A-29C)

### Status

- **29A:** Complete - Recruiter Email Actions on Application Detail (`sprint-29a-recruiter-email-action-alerts-complete`, merge `fb4c0b9`, 310 tests)
- **29B:** Complete - Recruiter Communication Context and manual follow-up guidance (`sprint-29b-recruiter-email-followup-history-complete`, merge `9409cba`, 315 tests)
- **29C:** Complete - Interview Prep Recommended prompt from interview/screening signals (`sprint-29c-interview-prep-trigger-complete`, merge `4cbc147`, 320 tests)

### Documentation Evidence

```text
docs/evidence/sprint_29_recruiter_email_workflow_enhancements.md
```

### What This Document Proves

- Manual import -> rule-based summary -> user decision -> manual follow-up or interview prep action.
- Application Detail surfaces needs reply, reply status, action due, suggested status (advisory), and interview/screening signals.
- Latest recruiter email context and manual follow-up guidance before using the follow-up draft workflow.
- Contextual **Create Interview Prep** prompt when `matched_signals` contains interview or screening; no automatic interview prep creation.
- Honest boundaries: no Gmail API, OAuth, inbox sync, scraping, automatic sending, automatic status mutation, background jobs, scheduler, Celery, or external AI / LLM integration.

### Reviewer Value

Shows recruiter emails move from stored imports to portfolio-safe, manual action intelligence on Application Detail without claiming inbox automation or AI integrations.

---

## Sprint 30 - Portfolio Readiness and Recruiter-Facing Summary (30A-30B)

### Status

- **30A:** Complete - README and portfolio doc alignment to Sprint 29 baseline (`sprint-30a-portfolio-readiness-alignment-complete`, main `284e040`, 320 tests)
- **30B:** Complete - Recruiter-facing project summary for GitHub, LinkedIn drafts, CV notes, messages, and interviews

### Documentation Evidence

```text
docs/evidence/sprint_30_recruiter_facing_project_summary.md
```

### What This Document Proves

- Reusable, claim-safe one-liner, paragraph, CV bullets, LinkedIn draft (not published), recruiter message, and interview explanation.
- Aligns positioning with 320 tests, rule-based manual workflows, and Sprint 29 recruiter-email enhancements.
- Explicit boundaries: no live SaaS, production users, Gmail, OAuth, inbox sync, scraping, auto-apply, automatic sending/status changes, automatic interview prep, or external AI / LLM integration.

### Reviewer Value

Gives recruiters and hiring managers consistent language for the project without overstating deployment, customers, or automation.

---

## Sprint 30C - LinkedIn Update Draft / Readiness Gate

### Status

- **30C:** Complete - LinkedIn project description, post drafts (not published), pinned-repo wording, and publish gate (`sprint-30c` branch; main baseline `ddddd23` when merged; 320 tests)

### Documentation Evidence

```text
docs/evidence/sprint_30c_linkedin_readiness_gate.md
```

### What This Document Proves

- LinkedIn-ready title options, project description, full and short post drafts labeled **draft only - not published yet**.
- Screenshot/media and publish readiness checklists with do-not-publish conditions.
- Same claim boundaries as Sprint 30A-30B: no live SaaS, production users, Gmail, OAuth, inbox sync, scraping, auto-apply, automatic sending/status changes, automatic interview prep, or external AI / LLM integration.

### Reviewer Value

Separates prepared LinkedIn language from actual publication so portfolio promotion stays evidence-based and manually controlled.

---

## Sprint 31 - CV Tailoring Advisor (31A-31D)

### Status

- **31A:** Complete - CV evidence source audit (`sprint-31a-cv-evidence-source-audit-complete`)
- **31B:** Complete - rule-based `build_cv_tailoring_advisor` service and tests (`sprint-31b-cv-tailoring-advisor-logic-complete`)
- **31C:** Complete - Job Posting Analyzer, Application AI Pack, Application Detail integration (`sprint-31c-cv-tailoring-advisor-integration-complete`; main `2132095`; **330 tests**)
- **31D:** In progress - Sprint 31 final closure documentation (`sprint-31d-evidence-and-closure` branch)

### Documentation Evidence

```text
docs/evidence/sprint_31a_cv_evidence_source_audit.md
docs/evidence/sprint_31_final_closure.md
```

### Code / Template Evidence (31B-31C)

```text
apps/ai_agents/services.py
apps/ai_agents/views.py
apps/ai_agents/tests.py
templates/ai_agents/job_posting_analyzer.html
templates/ai_agents/application_agent_pack.html
templates/applications/application_detail.html
```

### What Sprint 31 Proves

- Rule-based CV Tailoring Advisor suggests job-specific CV angle, projects, skills, risks, cover-letter themes, and interview points with locked CV `Aminul_Islam_Data_Analyst_CV`.
- Manual approval and claim-safety boundaries on every advisory output; no final CV generation, cover-letter finalization, auto-apply, Gmail, Calendar, scraping, external AI, or recruiter automation.
- Integration in Job Posting Analyzer POST flow, Application AI Pack for saved records, and Application Detail link to AI Pack.
- Validation after 31C: ruff, check, makemigrations --check, **330 tests**, CI green on main.

### Reviewer Value

Single sprint family showing evidence-first audit -> service logic -> UI integration -> closure, with explicit limitations suitable for portfolio and interview review.

---

## Sprint 32 - Calibrated AI-Assisted Fit Scoring, Mocked-First (32A-32E)

### Status

- **32A:** Complete - audit + scope lock (`sprint-32a-calibrated-ai-fit-scoring-audit-complete`)
- **32B:** Complete - AI scoring contract + mocked tests (`sprint-32b-ai-scoring-service-contract-mocked-tests-complete`)
- **32C:** Complete - OpenAI-shaped wrapper + safe fallback (`sprint-32c-openai-wrapper-safe-fallback-mocked-first-complete`)
- **32D:** Complete - Job Posting Analyzer rule-based vs AI score UI (`sprint-32d-rule-based-vs-ai-score-ui-complete`)
- **32E:** Complete - Sprint 32 final closure documentation (`sprint-32e-evidence-and-final-closure`)
- **External AI:** Not active - no real OpenAI call; UI shows fallback when no provider callable
- **Rule-based scoring:** Remains primary and visible

### Documentation Evidence

```text
docs/evidence/sprint_32a_calibrated_ai_fit_scoring_audit.md
docs/evidence/sprint_32_final_closure.md
```

### Code / Template Evidence (32B-32D)

```text
apps/ai_agents/services.py
apps/ai_agents/tests.py
apps/ai_agents/views.py
templates/ai_agents/job_posting_analyzer.html
```

### What Sprint 32 Proves

- Mocked-first AI scoring contract (`AIFitScoringResult`, `AIFitScoreComparison`) and OpenAI-shaped wrapper with dependency-injected callable and safe fallback.
- Job Posting Analyzer **Rule-Based vs AI Score Check** card with fallback status, manual review, and claim-safety copy (ASCII UI separators in 32D).
- No OpenAI SDK, API keys, settings changes, database persistence of AI output, auto-apply, Gmail, Calendar, scraping, or recruiter automation.
- Validation after 32D: **56** targeted `apps.ai_agents` tests, **351** full suite, ruff, check, makemigrations --check, CI green.

### Reviewer Value

Shows a disciplined path from audit -> contract -> wrapper -> UI with honest fallback-only behavior until a future provider sprint is approved.

---

## Sprint 34 - CV Tailoring Claude Enhancement (34A-34D)

### Status

- **34A:** Complete - evidence bank foundation (`0d84538`)
- **34B:** Complete - Claude CV tailoring provider and semantic parser (`e84da6a`)
- **34C:** Complete - CV Tailoring Advisor semantic fallback integration (`84aa5f3`)
- **34D:** Complete - documentation and evidence (README, evidence index, this sprint doc)

### Documentation Evidence

```text
docs/evidence/sprint_34_cv_tailoring_claude_enhancement.md
README.md (Sprint 34 position and claim boundaries)
```

### Code Evidence (34A-34C)

```text
apps/ai_agents/evidence_bank.py
apps/ai_agents/claude_provider.py
apps/ai_agents/services.py
apps/ai_agents/views.py
apps/ai_agents/tests.py
templates/ai_agents/job_posting_analyzer.html
templates/ai_agents/application_agent_pack.html
```

### What Sprint 34 Proves

- Structured evidence bank with strong / partial / gap-learning tiers and claim-safe helpers.
- Claude CV tailoring semantic provider returns JSON only; parser rejects forbidden CV/body fields.
- `build_cv_tailoring_advisor` keeps rule-based output authoritative with optional semantic merge and fallback.
- Locked CV `Aminul_Islam_Data_Analyst_CV`; manual approval wording preserved.
- Validation: **96** `apps.ai_agents` tests; **391** full project tests; ruff and Django check pass; no new migrations.

### Reviewer Value

Shows how optional LLM semantic matching can be added without abandoning rule-based safety, manual review, or honest portfolio claims.

---

## Sprint 35 - Interview + Email Workflow Polish (35A-35D)

### Status

- **35A:** Complete - interview prep handoff (`41a95c2`)
- **35B:** Complete - recruiter email manual workflow (`dfab82f`)
- **35C:** Complete - Application Detail / AI Pack cross-links (`bee1326`)
- **35D:** Complete - README and evidence closure (documentation only)

### Documentation Evidence

```text
docs/evidence/sprint_35_interview_email_workflow_polish.md
README.md (Sprint 35 position, workflow summary, claim boundaries)
docs/evidence/evidence_index.md (this section)
```

### What Sprint 35 Proves

- Manual interview prep create flow with `application=` pre-fill (no auto-save or auto-create).
- Recruiter email import/detail numbered manual workflows; mark-sent is status tracking only.
- Application Detail workflow map and cross-links to AI Pack and interview prep.
- Application AI Pack lists related interview prep and latest recruiter email (read-only context).
- **28** new targeted tests across four polish test classes; **419** full suite; no migrations.

### Reviewer Value

Shows end-to-end **manual** job-search operations UX: recruiter signal -> advisory drafts -> application context -> interview prep - without claiming inbox automation or SaaS deployment.

---

## Sprint 36 - Weekly Risk / Final Operating System Polish (36A-36D)

### Status

- **36A:** Complete - Weekly Review workflow clarity (`721e044`)
- **36B:** Complete - AI Weekly Coach / risk guidance (`36ac7cd`)
- **36C:** Complete - Dashboard / Today Action OS polish (`66e0e84`)
- **36D:** Complete - README and evidence closure (documentation only)

### Documentation Evidence

```text
docs/evidence/sprint_36_weekly_risk_os_polish.md
README.md (Sprint 36 position, operating rhythm summary, claim boundaries)
docs/evidence/evidence_index.md (this section)
```

### What Sprint 36 Proves

- Manual weekly operating workflow across Daily Log -> Applications -> Weekly Review -> AI Weekly Coach -> Dashboard Today Action.
- Weekly Review CRUD remains manual; saving a review does not mutate applications, send email, or create interview prep.
- AI Weekly Coach is advisory and rule-based on the coach page; optional Claude wording aligned on Agent Hub without claiming every tool calls an API.
- Dashboard week-end Today Action prompt links to manual Weekly Review create only.
- **21** new targeted tests (`WeeklyReviewWorkflowClaimSafetyTests`, `AiAgentWeeklyCoachPolishTests`, `DashboardWeeklyOsPolishTests`); **441** full suite; no migrations.

### Reviewer Value

Shows a coherent **manual, local, approval-based** weekly operating system for portfolio review without Gmail, Calendar, OAuth, auto-apply, or live SaaS claims.

---

## Sprint 37 - SaaS Foundation Audit + Design System Lock

### Status

- **37A:** Complete - shell, URL, and static audit tests (`f5dc8c3`)
- **37B-37D:** Complete - static asset audit completion, design-system lock, smoke-test completion, evidence documentation (audit-only; no redesign)

### Branch

```text
sprint-37-saas-foundation-audit-design-system-lock
```

### Documentation Evidence

```text
docs/evidence/sprint_37_saas_foundation_audit.md
docs/evidence/evidence_index.md (this section)
tests/test_sprint_37a_shell_foundation_audit.py
```

### What Sprint 37 Proves

- Sidebar, navbar, and root redirect URL safety with no invalid `dashboard:home` references.
- Required static assets and template `{% static %}` references resolve to existing source files.
- Authenticated major pages render server-side with accessibility landmarks and primary content before `app.js`.
- Design-system lock: stable shell, token-first CSS (`tokens.css` -> `layout.css` -> `components.css`), reserved future `cf-*` prefix, non-critical JavaScript only.
- **16** targeted foundation audit tests; app suite remains **441**; combined `apps tests` run **525**; no migrations or business-logic changes.

### Reviewer Value

Demonstrates foundation safety before premium redesign: route/static/template integrity, SSR-first rendering, and an explicit design-system direction without claiming live SaaS deployment or new integrations.

---

## Sprint 38 - Premium SaaS Shell: Navbar + Sidebar

### Status

- **38A-38C:** Complete - premium shell structure, grouped sidebar, topbar controls, responsive drawer, shell tests, evidence documentation

### Branch

```text
sprint-38-premium-saas-shell-navbar-sidebar
```

### Documentation Evidence

```text
docs/evidence/sprint_38_premium_saas_shell.md
docs/evidence/evidence_index.md (this section)
templates/base.html
templates/partials/sidebar.html
templates/partials/navbar.html
static/css/tokens.css
static/css/layout.css
static/css/components.css
static/js/app.js
tests/test_sprint_37a_shell_foundation_audit.py
```

### What Sprint 38 Proves

- Premium product shell with workflow groups: Command -> Pipeline -> Review -> Intelligence -> Reporting Suite -> Evidence -> Account.
- Claim-safe trust badges (Manual, Advisory, Evidence-based) and Local Portfolio Demo environment badge.
- Quick Add manual create links and user menu (Profile, Settings, Logout) in SSR-friendly topbar controls.
- Responsive drawer toggle, overlay, Escape/click close, active `aria-current="page"` navigation enhancement.
- **25** shell audit tests; dashboard/content templates unchanged; no migrations or business-logic changes.

### Reviewer Value

Shows a cohesive premium SaaS navigation experience while preserving manual, advisory, evidence-based product boundaries and server-side core rendering.

---

## Sprint 39 - Premium Dashboard Command Centre

### Status

- **39A-39C:** Complete - Career Command Centre modules, read-only dashboard service helpers, tests, evidence documentation

### Branch

```text
sprint-39-premium-dashboard-command-centre
```

### Documentation Evidence

```text
docs/evidence/sprint_39_premium_dashboard_command_centre.md
docs/evidence/evidence_index.md (this section)
apps/dashboard/services.py
apps/dashboard/tests.py
templates/dashboard/overview.html
static/css/components.css
```

### What Sprint 39 Proves

- Dashboard upgraded to Career Command Centre with signature insight, week pulse, KPI strip, today signals, pipeline health matrix, funnel snapshot, evidence readiness, weekly operating pipeline, and recent activity timeline.
- Read-only helpers: `build_week_pulse`, `build_pipeline_health_matrix`, `build_evidence_readiness_summary`, `build_today_signals`, `build_recent_activity_timeline`.
- Dashboard GET does not mutate records; all actions link to manual workflow pages.
- **28** dashboard tests; no migrations or schema changes; forms/reporting unchanged.

### Reviewer Value

Demonstrates a premium command-centre dashboard for portfolio walkthroughs while keeping manual, advisory, evidence-based boundaries explicit.

---

## Sprint 30D - Evidence / Final Closure

### Status

- **30D:** Complete - Sprint 30 final closure document (`sprint-30d-evidence-final-closure` branch; main before merge `3772477`; tag `sprint-30c-linkedin-readiness-gate-complete`; 320 tests)

### Documentation Evidence

```text
docs/evidence/sprint_30_final_closure.md
```

### What This Document Proves

- Sprint 30A-30C summary: portfolio README alignment (30A), recruiter-facing summary (30B), LinkedIn readiness gate (30C); all documentation only.
- Final evidence package paths and recruiter-facing outcomes without new product features.
- LinkedIn **not published** in Sprint 30; manual publish gate remains in 30C doc.
- Validation through 30C: 320 tests, ruff, check, makemigrations --check, CI green; 30D merge/tag/push validation still required for full closure.

### Reviewer Value

Single closure entry for Sprint 30 portfolio readiness work with explicit boundaries and evidence links.

---

# Final Reviewer Summary

CareerFunnel Tracker is a job-search analytics platform built with Django.

Its evidence shows a progression from a stable tracker into a more complete analytics product:

```text
Sprint 1:
Foundation and dashboard trust

Sprint 2:
Source ROI, CV Version Performance, and Rejection Pattern Analysis

Sprint 3:
Application Quality Intelligence

Sprint 4:
Data Quality, Metric Definitions, and Analytics Lineage

Sprint 5:
Exports, Evidence Centre, and reviewer handoff

Sprint 6:
UI polish, final screenshot evidence, and portfolio presentation notes

Sprint 7-13:
Documentation alignment, code quality, dashboard actions, manual follow-up workflows, and application evidence readiness

Sprint 14:
Weekly trend analytics, Funnel Metrics table display, DailyLog aggregation optimization, and documentation integrity

Sprint 15:
Shared role-fit constants, Job Posting Analyzer to Add Application prefill bridge, Evaluation Queue, and Application Detail Fit Review

Sprint 16:
Analytics-critical save-quality warnings, post-save advisory messages, and Data Quality Report Analytics Impact notes

Sprint 17-22:
Recruiter-facing README, visual/interview evidence, UI polish, and portfolio handoff packs

Sprint 23:
Career Evidence OS -- V1-V3 markdown tools, V4 dashboard UI, V5 Playwright screenshots, V6 optional Notion metadata sync
```

The strongest portfolio signal is that the project does not only display data. It explains where the data comes from, how it is transformed, what each metric means, what limitations exist, and what action the user should take next. Sprint 23 extends that discipline to **job-fit and recruiter evidence** with explicit repository paths and honest scope boundaries.

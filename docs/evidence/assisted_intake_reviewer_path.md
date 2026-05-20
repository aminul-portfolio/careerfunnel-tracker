# Assisted Intake Reviewer Path

## Sprint Metadata

| Item | Value |
|---|---|
| Sprint | 25D |
| Scope type | Reviewer path / UI evidence planning only |
| Implementation boundary | No code changes, no model changes, no migrations, no README update, no AI/API integration, no Gmail, no Calendar, no scraping, no auto-apply |

---

## Purpose

Sprint 25D turns Sprint 25A, 25B, and 25C evidence into a clear reviewer-facing walkthrough for recruiters, technical reviewers, and interviewers.

**Sprint 25D does not add new features.** It only documents how to review the existing Assisted Job Intake workflow using curated UI screenshots and the Sprint 25A-C evidence documents.

---

## Source Evidence Reviewed

- README.md
- docs/evidence/assisted_job_intake_workflow.md
- docs/evidence/assisted_job_intake_field_audit.md
- docs/evidence/assisted_intake_field_decision_plan.md
- docs/screenshots/curated/

Confirmed baseline used in this path:

- README references Evaluation Queue, Job Posting Analyzer conversion bridge, and Interview Evidence Workspace.
- README states rule-based local logic and does not claim external AI, scraping, auto-apply, Gmail, or Calendar automation.
- Sprint 25A documents the manual approval-based Assisted Job Intake workflow.
- Sprint 25B audits implemented vs partial fields.
- Sprint 25C recommends no immediate model changes.

---

## Reviewer Path Summary

Recommended inspection sequence:

1. Start at README project overview.
2. Review the dashboard overview screenshot.
3. Review Evaluation Queue.
4. Review Job Posting Analyzer conversion bridge.
5. Review the manual Add/Edit Application workflow.
6. Review Funnel Metrics and quality warnings.
7. Review Interview Evidence Workspace.
8. Read Sprint 25A workflow evidence.
9. Read Sprint 25B field audit.
10. Read Sprint 25C field decision plan.

---

## Recommended Reviewer Walkthrough Table

| Step | Reviewer Question | Evidence To Open | What It Proves | Claim Boundary |
|---|---|---|---|---|
| 1 | What is the product? | README.md; docs/screenshots/curated/01-dashboard-overview.png | CareerFunnel is a manual career application tracker with analytics and evidence surfaces. | No SaaS or live-user claim. |
| 2 | How does an opportunity enter the workflow? | docs/screenshots/curated/02-evaluation-queue.png | Roles can be reviewed before conversion or next action. | No scraping or auto-import claim. |
| 3 | How does job-posting review support intake? | docs/screenshots/curated/03-job-posting-analyzer-conversion.png | Rule-based review can pre-fill tracker fields for user review. | No external AI/API claim. |
| 4 | How does the user approve the application record? | Application form / conversion bridge path; docs/evidence/assisted_job_intake_workflow.md | User reviews and manually submits/saves the record. | No auto-apply or automatic submission. |
| 5 | How are fields classified? | docs/evidence/assisted_job_intake_field_audit.md | Core fields exist; some are aliases or generated suggestions. | No claim that every suggested item is a first-class model field. |
| 6 | Why were no fields added? | docs/evidence/assisted_intake_field_decision_plan.md | No immediate model changes are recommended. | No migration or field-expansion claim. |
| 7 | How is quality protected? | docs/screenshots/curated/05-save-quality-warnings.png; docs/screenshots/curated/06-data-quality-impact-report.png | Quality warnings and impact reporting support reliable tracking. | No background automation claim. |
| 8 | How does this support interview preparation? | docs/screenshots/curated/08-interview-evidence-workspace.png | Evidence links to CV/project/interview prep. | No interview automation or external AI claim. |

**Add/Edit Application note (Step 4):** README and Sprint 25A describe the conversion bridge opening a pre-filled Add Application form. Reviewers can cross-check `templates/applications/application_form.html` in the repo if live UI access is unavailable; Sprint 25D does not add a separate curated screenshot for that form in this sprint.

**Funnel Metrics note (Step 6):** docs/screenshots/curated/04-funnel-metrics-weekly-trend.png supports pipeline and weekly-trend review after intake.

---

## Screenshot Evidence Map

| Screenshot | Path | Reviewer Purpose | Status |
|---|---|---|---|
| Dashboard overview | docs/screenshots/curated/01-dashboard-overview.png | Product context, KPI trust surfaces, funnel entry point | Available in curated screenshots |
| Evaluation Queue | docs/screenshots/curated/02-evaluation-queue.png | Apply/skip and conversion decisions before full application save | Available in curated screenshots |
| Job Posting Analyzer conversion | docs/screenshots/curated/03-job-posting-analyzer-conversion.png | Rule-based fit review -> pre-filled application form for user approval | Available in curated screenshots |
| Funnel Metrics weekly trend | docs/screenshots/curated/04-funnel-metrics-weekly-trend.png | Post-intake funnel and trend evidence | Available in curated screenshots |
| Save quality warnings | docs/screenshots/curated/05-save-quality-warnings.png | Save-time quality signals on application data | Available in curated screenshots |
| Data quality impact report | docs/screenshots/curated/06-data-quality-impact-report.png | Governance and impact of missing or weak tracker data | Available in curated screenshots |
| Interview Evidence Workspace | docs/screenshots/curated/08-interview-evidence-workspace.png | CV/project/interview prep linked to application readiness | Available in curated screenshots |

---

## Safe Reviewer Narrative

CareerFunnel supports a manual, approval-based assisted job intake path. A user can review job-posting fit, decide whether to apply or skip, convert suitable roles into tracker-ready application records, review field suggestions, connect the role to CV/project/interview evidence, and then manually submit and update the application record.

---

## Claims Safe To Make

- Manual assisted job intake workflow
- Rule-based job-posting fit review
- Evaluation queue for apply/skip decisions
- Tracker-ready field pre-fill for user review
- Application tracking with source, status, CV version, follow-up, notes, and evidence fields
- Quality warnings and data-quality impact reporting
- Interview evidence workspace using existing tracker data
- Documentation-backed field audit and field-decision plan

---

## Claims To Avoid

- LinkedIn or Indeed scraping
- automatic job-board extraction
- auto-apply
- automatic application submission
- recruiter email sending
- Gmail integration
- Google Calendar integration
- automatic scheduling
- OpenAI / Claude implementation
- live SaaS
- production users
- full automation
- background workflow automation

---

## Reviewer Path Decision

Sprint 25D recommends using existing UI screenshots plus Sprint 25A-C evidence documents as the reviewer path.

Sprint 25D does not recommend adding fields, migrations, or automation.

Reviewers should treat UI labels such as "AI Job Posting Analyzer" as **rule-based local assistance** unless a future sprint documents and validates external API integration.

---

## Suggested Future Follow-Up

**Sprint 25E -- Assisted Intake README / GitHub Evidence Link Plan**

Goal: Decide whether the README should link to the Sprint 25A-D evidence documents, without overstating automation.

Sprint 25E should not automatically update README; any link plan requires explicit review of claim boundaries first.

---

## Validation Commands

Run from the repository root (`G:\final_polish\careerfunnel-tracker`):

```powershell
& "G:\workflow_tools\run_and_capture.ps1" -TaskName "sprint_25d_reviewer_path_doc_validation" -Commands @'
Write-Host "=== CURRENT PATH ==="
Get-Location

Write-Host "=== CURRENT BRANCH ==="
git branch --show-current

Write-Host "=== STATUS BEFORE VALIDATION ==="
git status --short

Write-Host "=== TARGET FILE CHECK ==="
Test-Path docs/evidence/assisted_intake_reviewer_path.md
Get-Item docs/evidence/assisted_intake_reviewer_path.md | Select-Object FullName, Length, LastWriteTime

Write-Host "=== TARGET FILE PREVIEW ==="
Get-Content docs/evidence/assisted_intake_reviewer_path.md -TotalCount 180

Write-Host "=== REQUIRED SCREENSHOT PATH CHECKS ==="
Test-Path docs/screenshots/curated/01-dashboard-overview.png
Test-Path docs/screenshots/curated/02-evaluation-queue.png
Test-Path docs/screenshots/curated/03-job-posting-analyzer-conversion.png
Test-Path docs/screenshots/curated/04-funnel-metrics-weekly-trend.png
Test-Path docs/screenshots/curated/05-save-quality-warnings.png
Test-Path docs/screenshots/curated/06-data-quality-impact-report.png
Test-Path docs/screenshots/curated/08-interview-evidence-workspace.png

Write-Host "=== SEARCH FOR REQUIRED REVIEWER TERMS ==="
Select-String -Path docs/evidence/assisted_intake_reviewer_path.md -Pattern "Evaluation Queue","Job Posting Analyzer","manual","approval-based","field audit","field decision","quality warnings","Interview Evidence Workspace","Sprint 25E" -CaseSensitive:$false

Write-Host "=== SEARCH FOR CLAIM-RISK WORDING ==="
Select-String -Path docs/evidence/assisted_intake_reviewer_path.md -Pattern "external AI","OpenAI","Claude","Gmail","Calendar","scraping","auto-apply","automatic application submission","model changes","migrations","live SaaS","production users" -CaseSensitive:$false

Write-Host "=== SEARCH FOR ENCODING ARTIFACTS ==="
Select-String -Path docs/evidence/assisted_intake_reviewer_path.md -Pattern "Ô","├","Ç","â","†","ó","å","Æ","é","¼","Ø" -SimpleMatch

Write-Host "=== RUFF ==="
ruff check .

Write-Host "=== DJANGO CHECK ==="
python manage.py check

Write-Host "=== MIGRATION CHECK ==="
python manage.py makemigrations --check --dry-run

Write-Host "=== TESTS ==="
python manage.py test

Write-Host "=== DIFF STAT ==="
git diff --stat

Write-Host "=== FINAL STATUS ==="
git status --short
'@
```

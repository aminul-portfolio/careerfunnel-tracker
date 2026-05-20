# Assisted Job Intake Workflow Evidence

## Sprint Metadata

| Item | Value |
|---|---|
| Sprint | 25A |
| Scope type | Evidence alignment / documentation only |
| Implementation boundary | No new scraping, AI, Gmail, Calendar, auto-apply, or background automation |

---

## Purpose

This document records the **manual, approval-based Assisted Job Intake Workflow** for CareerFunnel Tracker.

CareerFunnel **assists, suggests, drafts, and organises** job-search activity. The user **reviews and approves all final actions**. Suitable opportunities become tracker-ready application records only after user confirmation.

### Workflow sequence

Paste job URL + full job description
-> quick role-fit review
-> fit rating / priority / apply-skip decision
-> suggested tracker fields
-> CV / project / interview evidence suggestions
-> cover-letter direction or draft support
-> follow-up planning
-> manual application submission
-> user confirms status in CareerFunnel
-> tracker records status, notes, and follow-up schedule

### What this sprint does not include

- This is **not** a fully automated workflow.
- The user reviews fit assessments, field suggestions, evidence pointers, and draft text before saving or acting.
- CareerFunnel does **not** scrape job boards, auto-apply, send recruiter emails, or schedule calendar events in Sprint 25A.
- No Gmail integration, Google Calendar integration, OpenAI/Claude APIs, background automation, or live SaaS claims apply to this workflow evidence.

---

## Current Evidence Baseline

Existing CareerFunnel areas that support the Assisted Job Intake Workflow:

- Application tracking
- Source tracking
- Status tracking
- CV version tracking
- Follow-up dates
- Job descriptions
- Required skills
- Interview notes and preparation
- Daily activity and weekly reviews
- Rule-based job-posting fit review
- Next actions
- Follow-up drafting support
- Interview preparation support
- Quality warnings
- Workbook exports
- Evidence documentation

### Relevant repository paths

README.md  
docs/evidence/  
docs/career_evidence/  
apps/applications/  
apps/metrics/  
apps/job_intelligence/  
apps/exports/

---

## Workflow Status Summary

| Step | Workflow Item | Status | Evidence / Notes |
|---|---|---|---|
| 1 | Paste job URL and full JD manually | Partial / manual | User-driven paste; no scraping |
| 2 | Store/review pasted information | Partial / implemented through tracker fields | Application and JD fields in tracker |
| 3 | Quick role-fit review | Implemented | Rule-based job posting analyzer |
| 4 | Fit rating | Partial / needs field verification | Sprint 25B should confirm model/form support |
| 5 | Priority recommendation | Partial / needs field verification | Sprint 25B should confirm model/form support |
| 6 | Apply / skip recommendation | Implemented / rule-based | Fit rules and evaluation queue |
| 7 | Auto-suggest tracker fields | Partial / mostly implemented | Conversion bridge; user approves before save |
| 8 | Best CV angle | Partial / implemented in evidence/interview workflow | Career evidence and CV version tracking |
| 9 | Relevant project evidence | Implemented | Career evidence packs and interview workspace |
| 10 | Cover letter direction | Partial | Guidance present; user approves final text |
| 11 | Tailored cover-letter draft | Roadmap / partial | Draft support limited; not auto-send |
| 12 | Follow-up plan | Partial / implemented manually | Follow-up dates and drafting support |
| 13 | Likely interview topics | Implemented | Interview preparation and evidence packs |
| 14 | User manually submits application | External manual action | Outside CareerFunnel; user responsibility |
| 15 | User confirms submission | Implemented / manual | Status update by user |
| 16 | Update status, notes, and follow-up schedule | Implemented / manual | Tracker fields and metrics |

**Status legend:** Implemented = available today; Partial = partly manual or needs field verification; Roadmap = planned or limited; External manual action = outside the application.

---

## Auto-Suggested Tracker Field Audit

| Field | Target Status | Sprint 25A Classification |
|---|---|---|
| Company | Tracker-ready | Documented; verify in 25B |
| Role title | Tracker-ready | Documented; verify in 25B |
| Job URL | Tracker-ready | Documented; verify in 25B |
| Source | Tracker-ready | Documented; verify in 25B |
| Location | Tracker-ready | Documented; verify in 25B |
| Work mode | Tracker-ready | Documented; verify in 25B |
| Fit rating | Assisted suggestion | Documented; verify in 25B |
| Priority | Assisted suggestion | Documented; verify in 25B |
| Status | User-confirmed | Documented; verify in 25B |
| CV version | Assisted suggestion | Documented; verify in 25B |
| Cover letter | User-approved draft | Documented; verify in 25B |
| Main project evidence | Assisted suggestion | Documented; verify in 25B |
| Notes | User-edited | Documented; verify in 25B |

Sprint 25A documents the **intended field set** for assisted intake. Sprint 25B should audit exact model, form, template, and test support. Sprint 25A should **not** add model fields.

---

## Safe Product Wording

CareerFunnel supports a manual, approval-based Assisted Job Intake Workflow. The user manually records or pastes job information, reviews a rule-based fit assessment, decides whether to apply or skip, converts suitable opportunities into tracker-ready application records, reviews suggested CV/project/interview evidence, manually submits the application, and updates CareerFunnel with status, notes, and follow-up details.

Manual assisted job intake: from pasted job description to rule-based fit review, tracker-ready application record, evidence suggestions, and follow-up tracking.

---

## Claims To Avoid

Do not state or imply:

- LinkedIn or Indeed scraping
- automatic job-board extraction
- auto-apply
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

## Screenshot Evidence Checklist

| Screenshot | Purpose | Status |
|---|---|---|
| Dashboard overview | KPI trust surfaces and funnel context | Pending |
| Evaluation Queue | Apply/skip evaluation before conversion | Pending |
| Job Posting Analyzer conversion bridge | Fit review -> tracker field suggestions | Pending |
| Add/Edit Application form | Manual field entry and user confirmation | Pending |
| Funnel Metrics | Pipeline metrics after intake | Pending |
| Data Quality Report | Quality warnings aligned to tracker data | Pending |
| Interview Evidence Workspace | CV/project/interview evidence suggestions | Pending |
| Career Evidence Dashboard | Career evidence alignment for applications | Pending |

Existing screenshot references may appear under `docs/evidence/screenshots/` and `docs/screenshots/career_evidence/`. Sprint 25A does not add or edit screenshot files.

---

## Acceptance Criteria

- [ ] `docs/evidence/assisted_job_intake_workflow.md` exists.
- [ ] The document describes the manual approval-based workflow.
- [ ] Each workflow step is classified as Implemented, Partial, Roadmap, or Out of scope.
- [ ] The document includes safe wording and claims to avoid.
- [ ] The document includes a screenshot checklist.
- [ ] No new automation, AI, Gmail, Calendar, scraping, or auto-apply claim is introduced.
- [ ] Validation passes.

---

## Validation Commands

Run from the repository root (`G:\final_polish\careerfunnel-tracker`):

```powershell
& "G:\workflow_tools\run_and_capture.ps1" -TaskName "sprint_25a_assisted_job_intake_evidence_validation" -Commands @'
Write-Host "=== CURRENT PATH ==="
Get-Location

Write-Host "=== BRANCH ==="
git branch --show-current

Write-Host "=== STATUS BEFORE VALIDATION ==="
git status --short

Write-Host "=== TARGET FILE CHECK ==="
Test-Path docs/evidence/assisted_job_intake_workflow.md
Get-Item docs/evidence/assisted_job_intake_workflow.md | Select-Object FullName, Length, LastWriteTime

Write-Host "=== TARGET FILE PREVIEW ==="
Get-Content docs/evidence/assisted_job_intake_workflow.md -TotalCount 120

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

Write-Host "=== STATUS AFTER VALIDATION ==="
git status --short
'@
```

---

## Recommended Commit

When validation passes and the diff is reviewed:

```bash
git add docs/evidence/assisted_job_intake_workflow.md
git commit -m "Sprint 25A: add assisted job intake workflow evidence"
```

**Do not commit until ChatGPT reviews the validation output and diff.**

---

## Next Sprint

**Sprint 25B -- Tracker Field Audit**

Goal: Confirm whether the auto-suggested fields already exist in models, forms, templates, services, and tests.


# Assisted Intake Field Decision Plan

## Sprint Metadata

| Item | Value |
|---|---|
| Sprint | 25C |
| Scope type | Decision / implementation planning only |
| Implementation boundary | No model changes, no migrations, no form changes, no template changes, no AI/API integration, no Gmail, no Calendar, no scraping, no auto-apply |

---

## Purpose

This document converts Sprint 25B audit findings into explicit field decisions for the Assisted Job Intake workflow.

Sprint 25C records what should remain as an existing model field, an alias or documentation label, a generated rule-based suggestion, a future optional model field, or a rejected/unnecessary addition.

**Sprint 25C does not implement changes.** It decides what should remain as existing fields, aliases, suggestions, or future optional fields. No code, forms, templates, or migrations are modified in this sprint.

---

## Source Evidence Reviewed

- docs/evidence/assisted_job_intake_workflow.md
- docs/evidence/assisted_job_intake_field_audit.md
- apps/applications/models.py
- apps/applications/forms.py
- apps/ai_agents/services.py
- apps/job_intelligence/services.py

Confirmed baseline facts used in this plan:

- `work_type` exists in apps/applications/models.py and apps/applications/forms.py.
- `role_fit` exists in apps/applications/models.py and apps/applications/forms.py.
- `cv_version` exists in model/form.
- `cover_letter_version` exists in model/form.
- `is_cover_letter_tailored` exists in model/form.
- `portfolio_project_included` exists in model/form.
- `notes` exists in model/form.
- `fit_score` exists as computed rule-based output in apps/ai_agents/services.py.
- `job_fit_score` exists as computed rule-based output in apps/job_intelligence/services.py.
- `priority` exists in rule-based `AgentAction` outputs, not as a `JobApplication` model field.
- `recommended_projects` exists in rule-based services.
- `cover_letter_focus` exists in rule-based services.
- `main_project_evidence` does not exist as a direct `JobApplication` field.

---

## Executive Decision Summary

1. Do not rename `work_type` to `work_mode`; use alias/documentation only.
2. Keep `role_fit` as the stored fit rating.
3. Keep numeric `fit_score` and `job_fit_score` as computed rule-based suggestions for now.
4. Keep `priority` as generated/rule-based action priority for now.
5. Do not add full cover-letter body storage yet.
6. Keep `cover_letter_version` and `is_cover_letter_tailored` as stored fields.
7. Do not add `main_project_evidence` as a free-text application field yet.
8. Keep project evidence as `portfolio_project_included` plus rule-based `recommended_projects` and Career Evidence docs.
9. No migration is required for Sprint 25C.
10. Any future persistence decision should be handled in a later implementation sprint after UI and reporting impact are reviewed.

---

## Decision Matrix

| Field / Concept | Current Evidence | Decision | Reason | Future Action |
|---|---|---|---|---|
| `work_mode` vs `work_type` | `work_type` on `JobApplication` with `WorkType` choices; form label "Work Type" | Use alias/documentation only. Do not rename. | `work_type` already exists in model/form and likely templates. Renaming would create migration and compatibility risk with no clear portfolio value. | Use recruiter-facing label "Work mode" while keeping internal field `work_type`. |
| numeric `fit_score` vs `role_fit` | `role_fit` stored on model; `fit_score` from `analyze_job_posting()`; `job_fit_score` from `calculate_job_fit_score()` | Keep `role_fit` as stored field. Keep numeric scores computed for now. | `role_fit` already stores a simple categorical decision. Numeric scores are useful as rule-based analysis output but may not need persistence. | Consider persisting numeric analyzer score only if future reporting needs score history. |
| `priority` | `AgentAction.priority` in apps/ai_agents/services.py; not on `JobApplication` | Keep as rule-based suggestion for now. | Priority appears in action recommendations; storing it on `JobApplication` may duplicate status, role fit, and next-action logic. | Consider persistence only if the UI needs saved priority filters or reporting. |
| full `cover_letter` | `cover_letter_version`, `is_cover_letter_tailored` on model/form; paste-based `check_cover_letter_quality()` | Do not add full cover-letter body storage yet. | Current fields already store cover-letter version and whether it is tailored. Full body storage creates privacy/content-management complexity. | Keep paste-based checker and draft support. Consider draft model later only if a future sprint requires approved draft history. |
| `main_project_evidence` | `portfolio_project_included` on model; `recommended_projects` in rule-based services; docs/career_evidence/ | Do not add free-text `main_project_evidence` field yet. | Existing support uses boolean flag, project name lists, and Career Evidence docs. A text field may become stale or duplicate evidence files. | Prefer structured project recommendation outputs. Revisit only if applications need saved selected project evidence. |
| `cover_letter_focus` | List output in `JobPostingAnalysis` from apps/ai_agents/services.py | Keep as generated/rule-based suggestion. | Useful as temporary guidance from job-posting analysis, but not necessarily a stable application field. | Could be stored later in an approved application-prep snapshot if needed. |
| `recommended_projects` | Lists in `JobPostingAnalysis` and `SmartApplicationReview` | Keep as generated/rule-based suggestion. | Project recommendations depend on JD context and portfolio evidence; storing them without snapshot/version control may become stale. | Could be stored later as selected evidence snapshot if interview prep needs it. |

---

## Persist vs Suggest Decision Table

| Item | Persist Now? | Keep As Suggestion? | Rationale |
|---|---|---|---|
| Work mode label | No | No | Already represented by `work_type` on `JobApplication`. |
| Role fit | Already persisted | Also pre-filled by analyzer | Existing model field `role_fit`. |
| Numeric fit score | No | Yes | Computed analysis output (`fit_score`, `job_fit_score`). |
| Priority | No | Yes | Action-level recommendation (`AgentAction.priority`). |
| Cover-letter body | No | Optional later | Privacy/history complexity; not a first-class model field today. |
| Cover-letter version | Already persisted | No | Existing model field `cover_letter_version`. |
| Cover-letter tailored flag | Already persisted | No | Existing model field `is_cover_letter_tailored`. |
| Main project evidence | No | Yes | Better as recommendation/evidence reference; no `main_project_evidence` column. |
| Recommended projects | No | Yes | Generated from JD and evidence logic. |
| Cover-letter focus | No | Yes | Generated guidance from job-posting analysis. |

---

## Implementation Plan Recommendation

- **Sprint 25D should not immediately add fields.**
- Sprint 25D should create a UI/documentation alignment plan or reviewer path if needed.
- Model changes should only happen if a later sprint proves a reporting or workflow need after reviewing UI impact, data quality, and claim safety.

Recommended sequencing:

1. Align reviewer-facing labels with internal field names (documentation and UI copy only).
2. Keep conversion bridge behavior: analyzer pre-fill -> user review -> manual form submit.
3. Defer any migration until a future sprint documents a concrete reporting or filtering requirement.

---

## If Future Model Fields Are Considered

Possible later fields only if justified by workflow or reporting need:

| Candidate field | Sprint 25C status |
|---|---|
| `assisted_priority` | Not approved in Sprint 25C. |
| `fit_score_snapshot` | Not approved in Sprint 25C. |
| `selected_project_evidence` | Not approved in Sprint 25C. |
| `approved_cover_letter_draft` | Not approved in Sprint 25C. |

Each candidate would require: migration review, form/template updates, tests, privacy review (for draft text), and updated evidence documentation before implementation.

---

## Claim-Safety Notes

- Do not claim external AI implementation.
- Do not claim OpenAI or Claude API integration.
- Do not claim Gmail or Google Calendar integration.
- Do not claim scraping or auto-apply.
- Do not claim automatic application submission.
- Rule-based/local assistant wording must remain clear until external APIs are truly implemented and validated.

Current product behavior remains manual and approval-based: suggestions and scores do not replace user review of the application form before save.

---

## Final Sprint 25C Decision

**Sprint 25C recommends no immediate model changes.**

The current architecture should keep:

- core tracker data on `JobApplication`
- rule-based recommendations in assistant/job-intelligence services
- portfolio evidence in Career Evidence docs
- final user decisions in manually reviewed application records

Partial intake concepts (`work_mode` label, numeric fit score, priority, cover-letter focus, recommended projects, main project evidence text) remain aliases or generated outputs unless a later sprint proves persistence is required.

---

## Recommended Next Sprint

**Sprint 25D -- Assisted Intake Reviewer Path / UI Evidence Plan**

Goal: Turn the assisted intake workflow, field audit, and field-decision plan into a clear reviewer path without adding automation or new model fields.

---

## Validation Commands

Run from the repository root (`G:\final_polish\careerfunnel-tracker`):

```powershell
& "G:\workflow_tools\run_and_capture.ps1" -TaskName "sprint_25c_decision_plan_doc_validation" -Commands @'
Write-Host "=== CURRENT PATH ==="
Get-Location

Write-Host "=== CURRENT BRANCH ==="
git branch --show-current

Write-Host "=== STATUS BEFORE VALIDATION ==="
git status --short

Write-Host "=== TARGET FILE CHECK ==="
Test-Path docs/evidence/assisted_intake_field_decision_plan.md
Get-Item docs/evidence/assisted_intake_field_decision_plan.md | Select-Object FullName, Length, LastWriteTime

Write-Host "=== TARGET FILE PREVIEW ==="
Get-Content docs/evidence/assisted_intake_field_decision_plan.md -TotalCount 180

Write-Host "=== SEARCH FOR REQUIRED DECISION TERMS ==="
Select-String -Path docs/evidence/assisted_intake_field_decision_plan.md -Pattern "work_type","role_fit","fit_score","priority","cover_letter_version","main_project_evidence","recommended_projects","no immediate model changes","Sprint 25D" -CaseSensitive:$false

Write-Host "=== SEARCH FOR CLAIM-RISK WORDING ==="
Select-String -Path docs/evidence/assisted_intake_field_decision_plan.md -Pattern "external AI","OpenAI","Claude","Gmail","Calendar","scraping","auto-apply","automatic application submission","model changes","migrations" -CaseSensitive:$false

Write-Host "=== SEARCH FOR ENCODING ARTIFACTS ==="
Select-String -Path docs/evidence/assisted_intake_field_decision_plan.md -Pattern "Ô","├","Ç","â","†","ó","å","Æ","é","¼","Ø" -SimpleMatch

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

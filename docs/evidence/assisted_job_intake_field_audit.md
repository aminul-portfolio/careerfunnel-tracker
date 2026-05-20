# Assisted Job Intake Field Audit

## Sprint Metadata

| Item | Value |
|---|---|
| Sprint | 25B |
| Scope type | Audit / documentation only |
| Implementation boundary | No model changes, no migrations, no AI/API integration, no Gmail, no Calendar, no scraping, no auto-apply |

---

## Purpose

This document audits whether the target Assisted Job Intake fields from Sprint 25A are already represented in the current CareerFunnel codebase.

The audit inspects models, forms, choices, admin, views, services, tests, templates, and rule-based assistant surfaces. It records what exists today, what uses different internal names, and what appears only as generated suggestions or supporting workflow output.

**Sprint 25B does not add fields.** It only checks existing support and recommends next steps for a later implementation sprint if needed.

---

## Source Evidence Reviewed

### Application tracker

- apps/applications/models.py
- apps/applications/forms.py
- apps/applications/choices.py
- apps/applications/admin.py
- apps/applications/views.py
- apps/applications/services.py
- apps/applications/tests.py
- templates/applications/

### Rule-based assistant / AI-style support

- apps/ai_agents/forms.py
- apps/ai_agents/services.py
- apps/ai_agents/views.py
- apps/ai_agents/tests.py
- templates/ai_agents/

### Job intelligence (conversion bridge and smart review)

- apps/job_intelligence/services.py (read for cross-reference; not in Sprint 25B edit list)
- templates/job_intelligence/application_smart_review.html (read for cross-reference)

### Documentation

- README.md
- docs/evidence/assisted_job_intake_workflow.md

---

## Executive Summary

- Most core tracker fields already exist on `JobApplication` and appear in `JobApplicationForm`, admin, templates, and tests.
- Several Sprint 25A labels use different internal names (`company_name`, `job_title`, `work_type`, `role_fit`, `cover_letter_version`).
- Fit assessment appears in two layers: stored `role_fit` on the application and computed `fit_score` from rule-based analyzers that can pre-fill `role_fit` on create.
- Priority appears in rule-based `AgentAction` outputs (`apps/ai_agents/services.py`), not as a stored `JobApplication` field.
- Cover letter support mixes stored version/tailored flags with draft-quality checking and suggestion lists; there is no full cover-letter body field on `JobApplication`.
- Main project evidence appears as rule-based project recommendations plus `portfolio_project_included`; there is no dedicated `main_project_evidence` text field on `JobApplication`.
- Sprint 25B does not require migrations based on current evidence.
- Any future field additions should happen in a separate implementation sprint only after this audit is reviewed.

---

## Field Audit Table

| Target Field | Existing Support | Evidence Paths | Classification | Sprint 25B Recommendation |
|---|---|---|---|---|
| Company | `JobApplication.company_name` (CharField, required) | apps/applications/models.py; apps/applications/forms.py; apps/applications/admin.py; templates/applications/application_form.html; apps/applications/tests.py | Implemented as application field | No model change needed. Keep label mapping documented (`Company` -> `company_name`). |
| Role title | `JobApplication.job_title` (CharField, required) | apps/applications/models.py; apps/applications/forms.py; templates/applications/application_form.html; apps/applications/tests.py | Implemented as application field | No model change needed. Keep label mapping documented (`Role title` -> `job_title`). |
| Job URL | `JobApplication.job_url` (URLField, blank allowed) | apps/applications/models.py; apps/applications/forms.py; templates/applications/application_form.html; apps/job_intelligence/services.py (readiness check) | Implemented as application field | No model change needed. |
| Source | `JobApplication.source` with `ApplicationSource` choices | apps/applications/models.py; apps/applications/choices.py; apps/applications/forms.py; apps/applications/admin.py; apps/applications/tests.py | Implemented as application field | No model change needed. |
| Location | `JobApplication.location` (CharField, blank) | apps/applications/models.py; apps/applications/forms.py; templates/applications/application_form.html; apps/ai_agents/forms.py (analyzer input) | Implemented as application field | No model change needed. |
| Work mode | `JobApplication.work_type` with `WorkType` choices (not `work_mode`) | apps/applications/models.py; apps/applications/choices.py; apps/applications/forms.py; templates/applications/application_form.html (label "Work Type") | Implemented under different field name | Document alias only. Do not rename to `work_mode` in Sprint 25B. |
| Fit rating | Stored: `role_fit` (`RoleFit` choices). Computed: `fit_score` in `analyze_job_posting()` and `calculate_job_fit_score()`; create bridge maps score to `role_fit` | apps/applications/models.py; apps/applications/choices.py; apps/applications/views.py (`_build_application_create_initial`); apps/ai_agents/services.py; apps/job_intelligence/services.py; templates/ai_agents/job_posting_analyzer.html; apps/applications/tests.py | Partial / needs model-field decision | Keep `role_fit` as stored fit rating. Treat numeric `fit_score` as rule-based suggestion only unless a later sprint decides to persist it. |
| Priority | `AgentAction.priority` in rule-based action lists (High/Medium/Low/Strategic); not on `JobApplication` | apps/ai_agents/services.py; apps/ai_agents/tests.py | Implemented as rule-based suggestion | Do not add a `priority` model field in Sprint 25B. Decide in Sprint 25C whether persistence is needed. |
| Status | `JobApplication.status` with `ApplicationStatus` choices | apps/applications/models.py; apps/applications/choices.py; apps/applications/forms.py; apps/applications/admin.py; templates/applications/evaluation_queue.html; apps/applications/tests.py | Implemented as application field | No model change needed. |
| CV version | `JobApplication.cv_version` (CharField, blank) | apps/applications/models.py; apps/applications/forms.py; templates/applications/application_form.html; apps/job_intelligence/services.py (`recommend_cv`); apps/applications/services.py (readiness warnings) | Implemented as application field | No model change needed. Distinguish stored version label from rule-based CV recommendation text. |
| Cover letter | Stored: `cover_letter_version`, `is_cover_letter_tailored`. Suggestions: `cover_letter_focus` in job posting analysis. Draft check: `check_cover_letter_quality()` with pasted draft text (not stored on model) | apps/applications/models.py; apps/applications/forms.py; apps/ai_agents/forms.py; apps/ai_agents/services.py; apps/ai_agents/views.py; templates/ai_agents/cover_letter_quality_checker.html | Partial / needs model-field decision | Keep version/tailored flags. Full letter body does not need model storage unless a later sprint requires history; draft checking can remain paste-based. |
| Main project evidence | Stored flag: `portfolio_project_included`. Suggestions: `recommended_projects` in `JobPostingAnalysis` and `SmartApplicationReview` | apps/applications/models.py; apps/ai_agents/services.py; apps/job_intelligence/services.py; templates/ai_agents/job_posting_analyzer.html; templates/job_intelligence/application_smart_review.html; docs/career_evidence/ (supporting packs) | Implemented as supporting evidence only | Do not add `main_project_evidence` text field in Sprint 25B. Use recommendations + career evidence docs unless Sprint 25C decides otherwise. |
| Notes | `JobApplication.notes` (TextField, blank) | apps/applications/models.py; apps/applications/forms.py; apps/applications/admin.py (search_fields); apps/job_intelligence/services.py (`_text` helper) | Implemented as application field | No model change needed. |

---

## Strongly Supported Fields

These target fields map directly to `JobApplication` model and form fields with template and test coverage:

- **Company** (`company_name`)
- **Role title** (`job_title`)
- **Job URL** (`job_url`)
- **Source** (`source` / `ApplicationSource`)
- **Location** (`location`)
- **Work mode** (`work_type` / `WorkType` -- different internal name)
- **Status** (`status` / `ApplicationStatus`)
- **CV version** (`cv_version`)
- **Notes** (`notes`)

Evidence: `JobApplicationForm.Meta.fields` in apps/applications/forms.py lists all of the above except cover-letter-related fields are listed separately below.

---

## Partially Supported Fields

These fields exist but not always under the Sprint 25A label or not as a single first-class stored value:

- **Fit rating** -- Stored as `role_fit` (Strong/Medium/Weak/Unknown). Numeric `fit_score` is computed in rule-based services and can pre-fill `role_fit` when saving from the job posting analyzer (`fit_score` query param in apps/applications/views.py). `job_fit_score` on smart review is computed per application, not persisted.
- **Priority** -- Appears only on rule-based `AgentAction` objects in apps/ai_agents/services.py, not on `JobApplication`.
- **Cover letter** -- `cover_letter_version` and `is_cover_letter_tailored` are stored; `cover_letter_focus` and quality-check results are ephemeral suggestion outputs.
- **Main project evidence** -- `portfolio_project_included` boolean plus `recommended_projects` lists from rule-based services; career evidence markdown under docs/career_evidence/ supports narrative evidence outside the application record.

---

## Missing Or Not Yet First-Class Fields

No target field is completely absent from the product, but these are **not** direct `JobApplication` columns under the Sprint 25A names:

| Target label | Current state | Recommendation |
|---|---|---|
| `work_mode` | Implemented as `work_type` | Alias/documentation only; no rename required |
| `fit_rating` (numeric) | Computed `fit_score` / `job_fit_score`; stored categorical `role_fit` | Keep computed scores as suggestions unless persistence is justified |
| `priority` | Rule-based `AgentAction.priority` only | Likely better kept as generated suggestion, not model storage |
| `cover_letter` (full body) | Paste-based quality checker; version label stored | May not need model storage |
| `main_project_evidence` (free text) | Project names recommended in services; boolean `portfolio_project_included` | Likely better kept as suggestions + career evidence docs |

**Sprint 25B does not recommend adding all missing-named fields.** Separate future work into:

- **Fields that do not need model storage:** priority, numeric fit score, full cover-letter body, recommended project name lists
- **Fields that may be better kept as generated suggestions:** cover letter focus bullets, project recommendations, CV angle text from smart review
- **Fields that may need model fields later (only if reviewed):** optional persistence of analyzer fit score or priority -- decision deferred to Sprint 25C

---

## Model-Change Risk Assessment

- Sprint 25B does not add migrations.
- Sprint 25B does not modify apps/applications/models.py or forms.
- Current `JobApplication` already covers most intake labels via existing column names.
- Adding new columns (for example `priority`, `fit_score`, `main_project_evidence`, full `cover_letter` body) would require a later implementation sprint with migration review, form/template updates, tests, and claim-safety review.
- Recommended future sprint: **Sprint 25C or later**, after reviewing this audit and the Sprint 25A workflow evidence document.

---

## Claim-Safety Notes

Based on README.md and existing evidence docs:

- Do not claim external AI implementation.
- Do not claim OpenAI or Claude API integration.
- Do not claim Gmail or Google Calendar integration.
- Do not claim job-board scraping or auto-apply.
- UI labels such as "AI Job Posting Analyzer" refer to **rule-based local logic** in apps/ai_agents/services.py and apps/job_intelligence/services.py unless external APIs are added and verified in a future sprint.
- Assisted intake remains **manual and approval-based**: pre-fill and suggestions do not save until the user submits the application form (see templates/ai_agents/job_posting_analyzer.html conversion bridge copy).

---

## Recommended Next Sprint

**Sprint 25C -- Assisted Intake Field Decision / Implementation Plan**

Goal: Decide which partial fields should remain as suggestions and which, if any, deserve first-class model fields.

Sprint 25C should **not** automatically add model fields. It should produce an explicit decision record (persist vs suggest vs document-only) before any migration work.

---

## Validation Commands

Run from the repository root (`G:\final_polish\careerfunnel-tracker`):

```powershell
& "G:\workflow_tools\run_and_capture.ps1" -TaskName "sprint_25b_field_audit_doc_validation" -Commands @'
Write-Host "=== CURRENT PATH ==="
Get-Location

Write-Host "=== CURRENT BRANCH ==="
git branch --show-current

Write-Host "=== STATUS BEFORE VALIDATION ==="
git status --short

Write-Host "=== TARGET FILE CHECK ==="
Test-Path docs/evidence/assisted_job_intake_field_audit.md
Get-Item docs/evidence/assisted_job_intake_field_audit.md | Select-Object FullName, Length, LastWriteTime

Write-Host "=== TARGET FILE PREVIEW ==="
Get-Content docs/evidence/assisted_job_intake_field_audit.md -TotalCount 180

Write-Host "=== SEARCH FOR CLAIM-RISK WORDING ==="
Select-String -Path docs/evidence/assisted_job_intake_field_audit.md -Pattern "external AI","OpenAI","Claude","Gmail","Calendar","scraping","auto-apply","migrations","model changes" -CaseSensitive:$false

Write-Host "=== SEARCH FOR ENCODING ARTIFACTS ==="
Select-String -Path docs/evidence/assisted_job_intake_field_audit.md -Pattern "Ô","├","Ç","â","†","ó","å","Æ","é","¼","Ø" -SimpleMatch

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

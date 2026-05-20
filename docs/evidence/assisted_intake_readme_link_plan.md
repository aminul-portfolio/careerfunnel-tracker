# Assisted Intake README Link Plan

## Sprint Metadata

| Item | Value |
|---|---|
| Sprint | 25E |
| Scope type | README / GitHub evidence link planning only |
| Implementation boundary | No README edit, no code changes, no model changes, no migrations, no AI/API integration, no Gmail, no Calendar, no scraping, no auto-apply |

---

## Purpose

Sprint 25E decides whether and how the README should link to the Sprint 25A-D Assisted Intake evidence documents for GitHub reviewers.

**Sprint 25E does not update README.** It creates a safe link plan for human review before any README change is applied in a separate sprint.

---

## Source Evidence Reviewed

- README.md
- docs/evidence/assisted_job_intake_workflow.md
- docs/evidence/assisted_job_intake_field_audit.md
- docs/evidence/assisted_intake_field_decision_plan.md
- docs/evidence/assisted_intake_reviewer_path.md

Confirmed baseline used in this plan:

- README already has a core tracker walkthrough.
- README already references Evaluation Queue, Job Posting Analyzer conversion bridge, and Interview Evidence Workspace.
- README already has an Evidence And Verification section with links to analytics and evidence docs.
- README already states rule-based logic and avoids claiming external AI, scraping, auto-apply, Gmail, or Calendar automation.
- Sprint 25D recommends deciding whether README should link to Sprint 25A-D evidence without overstating automation.

---

## Executive Decision Summary

1. README should eventually include a short Assisted Intake evidence link section.
2. The section should be placed under or near **Evidence And Verification**.
3. The README wording should remain concise and claim-safe.
4. The README should link to Sprint 25A-D evidence documents.
5. README should not claim automation, external AI, scraping, auto-apply, Gmail, Calendar, SaaS, or production users.
6. README should describe Assisted Intake as manual, approval-based, and rule-based.
7. README update should be a separate reviewed step after this plan is approved.

---

## Recommended README Placement

**Preferred location:** Under README section `## Evidence And Verification`, after the existing evidence bullet list or as a new `### Assisted Intake Evidence` subsection.

**Reason:** The Assisted Intake documents are evidence and reviewer documentation, not new product features. They belong with other verification and evidence links already listed in that section.

**Alternative location:** Near the core tracker walkthrough, only if the wording remains short (one paragraph plus four links). Not recommended as the primary placement because the walkthrough is operational; evidence depth belongs under Evidence And Verification.

**Decision:** Use **Evidence And Verification** as the recommended placement.

---

## Recommended README Link Block

Proposed block for a future README edit (not applied in Sprint 25E):

```markdown
### Assisted Intake Evidence

The assisted intake workflow is documented as a manual, approval-based, rule-based path from job-posting review to tracker-ready application evidence. It does not claim scraping, auto-apply, external AI/API integration, Gmail, Calendar automation, or live SaaS usage.

- Workflow evidence: `docs/evidence/assisted_job_intake_workflow.md`
- Field audit: `docs/evidence/assisted_job_intake_field_audit.md`
- Field decision plan: `docs/evidence/assisted_intake_field_decision_plan.md`
- Reviewer path: `docs/evidence/assisted_intake_reviewer_path.md`
```

Optional one-line cross-reference in the core walkthrough (future sprint only, if approved):

```markdown
For full assisted-intake evidence and reviewer steps, see **Assisted Intake Evidence** under [Evidence And Verification](#evidence-and-verification).
```

---

## Wording Rules For Future README Edit

When README is updated in a later sprint:

- Use **manual**, **approval-based**, and **rule-based** for assisted intake.
- Say **pre-fill for user review**, not automatic save or automatic application.
- Say **Evaluation Queue** and **Job Posting Analyzer conversion bridge** as existing UI paths already shown in README screenshots.
- Do not add new feature bullets for Sprint 25A-E; only add links and one short explanatory paragraph.
- Do not rename or expand the Evidence And Verification section into a marketing-style feature list.
- Keep link paths relative to repo root as shown above (consistent with existing README evidence links).

---

## What The README Should Not Add

Do not add to README in a future edit:

- Claims of LinkedIn or Indeed scraping or automatic job-board extraction
- Auto-apply or automatic application submission language
- Gmail, Google Calendar, or automatic scheduling integration
- OpenAI, Claude, or generic "AI-powered" product claims without API evidence
- Live SaaS, production users, or customer counts
- Statements that all suggested intake fields are stored on `JobApplication` (Sprint 25B/25C document partial/suggestion fields)
- Promises of new model fields or migrations (Sprint 25C deferred model changes)

---

## GitHub / Reviewer Link Strategy

| Audience | Primary entry | Secondary depth |
|---|---|---|
| Quick GitHub skim | README Evidence And Verification + curated screenshots already in README | Assisted Intake Evidence subsection (proposed) |
| Recruiter / hiring manager | docs/evidence/assisted_intake_reviewer_path.md | Sprint 25A workflow + screenshot map in 25D |
| Technical reviewer | docs/evidence/assisted_job_intake_field_audit.md | docs/evidence/assisted_intake_field_decision_plan.md |
| Maintainer | docs/evidence/assisted_job_intake_workflow.md | Full 25A-D chain in order |

GitHub does not require a separate wiki page if README links are claim-safe and the four evidence files remain in `docs/evidence/`.

---

## Relationship To Existing README Content

README already covers assisted-intake **UI surfaces** without naming the Sprint 25A-D doc set:

| README area | Overlap with Assisted Intake |
|---|---|
| Core tracker walkthrough | Evaluation Queue, analyzer bridge, application save, quality, interview workspace |
| Screenshot gallery | Curated images referenced in Sprint 25D reviewer path |
| Evidence And Verification | Natural home for deep-dive doc links |
| Technical Decisions / claims control | Rule-based logic; no external AI (align with 25A-E boundaries) |

Sprint 25E links **documentation depth** without duplicating the full walkthrough text in README.

---

## Sprint 25E Decision

**Approved plan (documentation only):**

- Add Assisted Intake evidence links to README under **Evidence And Verification** using the proposed link block.
- Keep README concise; defer actual file edit to a separate implementation sprint after review.
- Do not change code, models, or Sprint 25A-D evidence files in Sprint 25E.

**Not approved in Sprint 25E:**

- Immediate README edit
- New README sections outside Evidence And Verification (except optional one-line cross-link if explicitly approved later)
- Any wording that implies automation or external AI APIs

---

## Recommended Next Step (Post-25E)

**Sprint 25F -- README Assisted Intake Link Implementation** (or equivalent reviewed README sprint)

Goal: Apply the approved link block to README.md after ChatGPT/human review of this plan and claim boundaries.

Sprint 25F should:

1. Insert `### Assisted Intake Evidence` under `## Evidence And Verification`.
2. Run README link checks and full test suite.
3. Avoid changing unrelated README sections.

Sprint 25F is not required to start automatically; it begins only when explicitly scheduled.

---

## Validation Commands

Run from the repository root (`G:\final_polish\careerfunnel-tracker`):

```powershell
& "G:\workflow_tools\run_and_capture.ps1" -TaskName "sprint_25e_readme_link_plan_doc_validation" -Commands @'
Write-Host "=== CURRENT PATH ==="
Get-Location

Write-Host "=== CURRENT BRANCH ==="
git branch --show-current

Write-Host "=== STATUS BEFORE VALIDATION ==="
git status --short

Write-Host "=== TARGET FILE CHECK ==="
Test-Path docs/evidence/assisted_intake_readme_link_plan.md
Get-Item docs/evidence/assisted_intake_readme_link_plan.md | Select-Object FullName, Length, LastWriteTime

Write-Host "=== TARGET FILE PREVIEW ==="
Get-Content docs/evidence/assisted_intake_readme_link_plan.md -TotalCount 180

Write-Host "=== LINKED EVIDENCE FILE CHECKS ==="
Test-Path docs/evidence/assisted_job_intake_workflow.md
Test-Path docs/evidence/assisted_job_intake_field_audit.md
Test-Path docs/evidence/assisted_intake_field_decision_plan.md
Test-Path docs/evidence/assisted_intake_reviewer_path.md

Write-Host "=== SEARCH FOR REQUIRED PLAN TERMS ==="
Select-String -Path docs/evidence/assisted_intake_readme_link_plan.md -Pattern "Evidence And Verification","Assisted Intake Evidence","manual","approval-based","rule-based","Sprint 25A","Sprint 25F","does not update README" -CaseSensitive:$false

Write-Host "=== SEARCH FOR CLAIM-RISK WORDING ==="
Select-String -Path docs/evidence/assisted_intake_readme_link_plan.md -Pattern "external AI","OpenAI","Claude","Gmail","Calendar","scraping","auto-apply","live SaaS","production users","migrations","model changes" -CaseSensitive:$false

Write-Host "=== SEARCH FOR ENCODING ARTIFACTS ==="
Select-String -Path docs/evidence/assisted_intake_readme_link_plan.md -Pattern "Ô","├","Ç","â","†","ó","å","Æ","é","¼","Ø" -SimpleMatch

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

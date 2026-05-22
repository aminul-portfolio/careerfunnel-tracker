# Sprint 28 - Live Application Pilot Evidence

## Sprint position

| Sprint | Status | Notes |
|---|---|---|
| **28A** | Complete | Manual recruiter email import (paste, classify, draft reply - rule-based only) |
| Latest tag | `sprint-28a-email-import-complete` | |
| **28B** | Complete (live pilot) | Real job intake tested end-to-end and selectively skipped |
| **28C** | Active | Intake workflow refinement (CTA wording, locked CV parity, README alignment, evidence capture) |

---

## Purpose

This evidence document records **live use** of CareerFunnel Tracker during real job-search workflow testing in Sprint 28B, and the refinement scope addressed in Sprint 28C.

It is portfolio-safe documentation only. It does not claim Gmail integration, external AI, auto-apply, or automatic saving.

---

## Current workflow

Intake follows a deliberate manual gate:

```text
Analyze -> Review -> Approve -> Pre-fill Add Application -> Manual Save
```

| Step | What happens |
|---|---|
| **Analyze** | Job Posting Analyzer runs **local, rule-based** fit/risk/CV/project checks on pasted posting text. |
| **Review** | User reads fit score, risks, deal-breakers, and recommendation before acting. |
| **Approve** | User decides apply, stretch apply, or skip - no system override. |
| **Pre-fill** | **Review & Pre-fill Application** opens Add Application with GET parameters (e.g. company, title, location, fit score). |
| **Manual Save** | User reviews the form and submits; **nothing is persisted until submit**. |

Boundaries in this flow:

- The Job Posting Analyzer is **rule-based**, not an external LLM.
- Pre-fill opens the Add Application form; it does **not** create a `JobApplication` record.
- The system does **not** auto-apply, silently save, or mutate application status without user action.

---

## Live pilot examples

### Example 1 - Sphere (apply path)

| Field | Value |
|---|---|
| Role | Data Analyst (entry-level) - UK fintech |
| Decision | Apply |
| Action | Saved as application after review |
| Status | Submitted |
| Follow-up date | 28/05/2026 |
| Outcome | **Successful end-to-end workflow** - analyze -> pre-fill -> manual save -> detail page with evidence, follow-up, Fit Review, and recruiter email section available |

### Example 2 - Legal & General (skip path)

| Field | Value |
|---|---|
| Role | Index Junior Analyst - Analytics and Technology |
| Analyzer score | 54/100 |
| Manual review score | 7.8/10 (human judgment overlay) |
| Decision | Skip / closed / not applied |
| Action | Add Application form opened then **cancelled** |
| Outcome | **Correct discipline** - no false `Submitted` record; low-fit role rejected without polluting the pipeline |

---

## What worked

- **Job Posting Analyzer** supports structured fit/risk review before applying.
- **Pre-fill bridge** links analyzer output to Add Application without auto-save.
- **Manual save gate** prevents silent persistence; cancel leaves no application row.
- **Application detail** surfaces evidence readiness, follow-up plan, rule-based **Fit Review** (including locked CV recommendation), and **Recruiter Emails** (manual import section).
- **Recruiter email import** (Sprint 28A) remains manual paste + rule-based classification; no inbox sync.

---

## Findings / gaps

| Finding | Sprint 28C / follow-up |
|---|---|
| Pre-fill was initially narrow (company, title, location, fit score only) | Richer pre-fill (URL, source, work type, salary, CV, notes) recommended later |
| Add Application has no pre-application statuses (e.g. Ready to Apply, Evaluating, Saved for Later) | Pre-application statuses on roadmap |
| Button wording **Save as Application** implied auto-save | Renamed to **Review & Pre-fill Application** with explicit "nothing is saved until review and submit" copy |
| Smart Review returned phantom CV filenames | Aligned to locked CV: `Aminul_Islam_Data_Analyst_CV` in `apps/job_intelligence/services.py` |
| README still said Sprint 28A not implemented | Sprint position corrected (28A complete, 28B pilot, 28C active) |
| Demo dashboard CSV still lists legacy CV names (`Finance_DA_CV_v1`, `DA_CV_v2`, etc.) | Demo data cleanup deferred to a later sprint |

---

## Claims boundaries

CareerFunnel Tracker **does not** provide:

- No Gmail API
- No OAuth
- No scraping
- No auto-apply
- No automatic saving
- No external AI / LLM integration
- No automatic email sending
- No automatic application status mutation

All intake, save, follow-up, and recruiter-email workflows are **manual and rule-based**.

---

## Recommended next improvements

1. **Pre-application statuses** - Ready to Apply, Evaluating, Saved for Later before `Submitted`.
2. **Richer pre-fill** - job URL, source, work type, salary range, CV version, notes from analyzer context.
3. **Evaluation queue bridge** - clearer path from analyzer skip/apply decision into queue stages.
4. **Demo data cleanup** - align `dashboards/data/applications.csv` with locked CV naming.
5. **Screenshot evidence** - capture UI after final 28C refinement (see checklist below).
6. **Role-specific CV angle advice** - deferred to Sprint 31; filename stays locked until then.

---

## Evidence checklist

Capture after Sprint 28C UI/copy refinement is stable:

- [ ] Screenshot: Job Analyzer after CTA rename (**Review & Pre-fill Application**)
- [ ] Screenshot: Pre-filled Add Application form (Sphere or equivalent)
- [ ] Screenshot: Saved Sphere application detail (status, follow-up, Fit Review)
- [ ] Screenshot: Recruiter Emails section on application detail
- [ ] Screenshot: Fit Review showing locked CV `Aminul_Islam_Data_Analyst_CV`
- [ ] GitHub Actions / CI proof after Sprint 28C merge

Store screenshots under `docs/evidence/screenshots/` when captured; reference filenames in this document or `evidence_index.md`.

---

## Related paths

| Artefact | Path |
|---|---|
| Job Posting Analyzer template | `templates/ai_agents/job_posting_analyzer.html` |
| Locked CV (Smart Review) | `apps/job_intelligence/services.py` (`LOCKED_CV`) |
| Application detail sections | `templates/applications/application_detail.html` |
| Sprint position (README) | `README.md` - Current Sprint Position |

# Sprint 28D - Live Pilot Closure Evidence

## Purpose

Sprint 28D resumed live pilot testing after Sprint 28C refinements and tested the workflow:

```text
Analyze -> Review -> Approve -> Pre-fill Add Application -> Manual Save
```

This evidence document records portfolio-safe closure outcomes from three real-role pilot paths: two successful apply saves and one stretch/test-only path without polluting the Applications pipeline.

It does not claim Gmail integration, external AI, auto-apply, or automatic saving.

---

## Starting state

| Item | State |
|---|---|
| Main branch | Clean |
| Latest stable main | Included Sprint 28C CI fix |
| CTA wording | Updated to **Review & Pre-fill Application** |
| Locked CV | `Aminul_Islam_Data_Analyst_CV` |
| Sprint 28 evidence | `docs/evidence/sprint_28_live_application_pilot.md` already existed |
| GitHub Actions | Passed after Sprint 28C CI assertion fix |

---

## Pilot role summary

| # | Company | Role | Manual decision | Manual fit | CareerFunnel action | Follow-up date | Outcome | Finding |
|---|---|---|---|---|---|---|---|---|
| 1 | LiveMore Mortgages | Junior Data Analyst | Apply | 9.2/10 | Saved as Submitted | 29/05/2026 | Successful strong-fit apply path | Analyzer under-scored due to false-positive "Head of Data Science & Engineering" seniority signal |
| 2 | Dow Jones | Analyst, People Insights | Apply | 8.3/10 | Saved as Submitted | 29/05/2026 | Successful BI/People Analytics apply path | Required Skills field needed manual enrichment for reliable matching |
| 3 | Starcom | Data Analyst (Digital, Data & Technology) | Stretch / good backup | 7.4/10 | Tested only, not saved | Not applicable | Valid stretch role test, not saved because user did not apply | Analyzer under-scored due to false-positive "directors" seniority signal |

---

## What worked

- **Review & Pre-fill Application** wording is clearer than Save as Application.
- Nothing is saved until manual form submission.
- Apply-path records can be saved successfully.
- Skip/stretch/test-only roles can be avoided without polluting Applications.
- Locked CV remains consistent.
- Follow-up planning works after saving.
- Notes field captures manual fit, claim-safety, evidence, and product findings.

---

## Product findings

### 1. Seniority/deal-breaker false positives

- "Reports to Head of Data Science & Engineering" should not be treated as Head-level requirement.
- "Alongside senior analysts and directors" should not be treated as Director-level requirement.

### 2. Required Skills pre-fill / matching

Required Skills pre-fill / matching can be too short and may require manual enrichment.

### 3. Job Analyzer UX gap

Job Analyzer has no Clear Form / Reset button.

### 4. Pre-application statuses still needed

- Ready to Apply
- Evaluating
- Saved for Later

### 5. Richer pre-fill still needed

- URL
- Source
- Work type
- Salary
- CV version
- Notes

---

## Claim-safety boundaries

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

## Sprint 28D conclusion

Sprint 28D successfully validated the refined Sprint 28 intake workflow across:

- Strong apply path
- BI/analytics apply path
- Stretch/test-only path

Sprint 28 can be considered ready for closure after repository validation, merge/push if needed, and CI verification.

---

## Recommended backlog for future sprints

1. Improve seniority keyword context logic.
2. Add Clear Form / Reset Analyzer button.
3. Add pre-application statuses.
4. Improve richer pre-fill.
5. Add demo data cleanup for legacy CV names.
6. Consider Sprint 29 recruiter email workflow enhancements next.

---

## Related paths

| Artefact | Path |
|---|---|
| Sprint 28 live pilot (28A-28C) | `docs/evidence/sprint_28_live_application_pilot.md` |
| Evidence index | `docs/evidence/evidence_index.md` |
| Sprint position (README) | `README.md` - Current Sprint Position |

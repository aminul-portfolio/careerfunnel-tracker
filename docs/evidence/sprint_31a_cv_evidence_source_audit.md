# Sprint 31A — CV Evidence Source Audit

## 1. Purpose

Sprint 31A audits **existing** documentation and evidence sources in the CareerFunnel Tracker repository before any **CV Tailoring Advisor** workflow is designed or built in Sprint 31B.

This sprint answers:

- Which evidence files already exist and are claim-safe?
- Which categories of evidence can support job-specific CV positioning suggestions?
- Which claims must remain forbidden or future-only?
- What manual approval rules must govern any Sprint 31B recommendations?

Sprint 31A produces a **source audit only**. It does not implement tailoring logic, UI, services, or automated document generation.

---

## 2. Sprint Boundary

Sprint 31A is **documentation and audit only**. The following boundaries apply to Sprint 31A and remain in force for Sprint 31B unless explicitly approved and evidenced later:

| Boundary | State in Sprint 31A |
|---|---|
| CV automatically rewritten | **No** — not in scope |
| Cover letter automatically finalized | **No** — not in scope |
| Applications auto-submitted | **No** — not in scope |
| Recruiter automation added | **No** — not in scope |
| Gmail, OAuth, scraping, or external AI integration | **No** — not in scope |
| Product code, templates, models, migrations, services, tests, or UI | **No edits** in Sprint 31A |

Sprint 31A may only change:

- `docs/evidence/sprint_31a_cv_evidence_source_audit.md` (this document)
- `docs/evidence/evidence_index.md` (index entry for this audit)

---

## 3. Safe Evidence Sources

The table below lists **documented** sources present in the repository at the time of this audit. Sources not listed were not used to infer capabilities.

| Evidence Source | File / Location | Safe Use in Sprint 31 | Claim-Safety Notes |
|---|---|---|---|
| README project summary | `README.md` | Yes — scope, features, reviewer path, test baseline, explicit non-claims | States 320 passing tests; no live SaaS, Gmail, OAuth, scraping, auto-apply, or external AI. Deployment not verified. |
| Sprint 30 final closure | `docs/evidence/sprint_30_final_closure.md` | Yes — Sprint 30 evidence package map and boundaries | Documentation-only Sprint 30; LinkedIn **not published**. Aligns README and portfolio docs to Sprint 29 baseline. |
| Sprint 30 recruiter-facing summary | `docs/evidence/sprint_30_recruiter_facing_project_summary.md` | Yes — one-liner, paragraph, CV bullets, recruiter message, interview explanation (draft/reference) | Marked draft/reference; repeats explicit non-claims. LinkedIn draft labeled not published. |
| Sprint 30C LinkedIn readiness gate | `docs/evidence/sprint_30c_linkedin_readiness_gate.md` | Yes — public wording drafts and publish gate only | **Draft only — not published yet.** No profile update claimed. Use for wording discipline, not as proof of publication. |
| Sprint 29 recruiter email workflow | `docs/evidence/sprint_29_recruiter_email_workflow_enhancements.md` | Yes — manual recruiter-email workflow boundaries and Application Detail surfaces | Manual import → rule-based summary → user decision. No inbox sync, auto-send, auto status change, or external AI. |
| Evidence index | `docs/evidence/evidence_index.md` | Yes — sprint map, screenshot register, limitations, reviewer path | Historical test counts vary by sprint; prefer README and Sprint 30 docs for current 320-test baseline. |
| Assisted job intake workflow | `docs/evidence/assisted_job_intake_workflow.md` | Yes — manual approval-based intake sequence and gaps | Sprint 25A evidence alignment; user reviews fit, fields, evidence pointers before save. No scraping or auto-apply. |
| Assisted intake field audit | `docs/evidence/assisted_job_intake_field_audit.md` | Yes — which tracker fields exist for job-to-application mapping | Documentation of field coverage; use for Sprint 31B input mapping, not automation claims. |
| Assisted intake decision plan | `docs/evidence/assisted_intake_field_decision_plan.md` | Yes — field decisions for intake evidence chain | Supports understanding what can be suggested vs. what requires user entry. |
| Assisted intake reviewer path | `docs/evidence/assisted_intake_reviewer_path.md` | Yes — reviewer walkthrough for intake evidence | Portfolio/review context only. |
| Live application pilot (28B–28D) | `docs/evidence/sprint_28_live_application_pilot.md`, `docs/evidence/sprint_28d_live_pilot_closure.md` | Yes — real-role manual apply/skip discipline | Analyze → Review → Approve → Pre-fill → Manual Save. No auto-save or auto-apply. |
| Career Evidence V1 project report | `docs/career_evidence/01_project_evidence_report.md` | Yes — repo inventory (docs, tests, templates, paths) | Generated report; re-run tool after material repo changes. |
| Career Evidence V2 job-fit matrix | `docs/career_evidence/02_job_fit_matrix.md` | Yes — requirement-to-repository evidence strength | Sample JD mapping; Strong/Partial/Missing tied to paths. |
| Career Evidence V3 recruiter pack | `docs/career_evidence/03_recruiter_evidence_pack.md` | Yes — CV bullets, LinkedIn summary, interview points from V1/V2 | Generated; honest deployment limits. |
| Career Evidence walkthrough | `docs/evidence/career_evidence_walkthrough.md` | Yes — V1–V6 flow and boundaries | No external AI or production deployment claims. |
| Portfolio project review (this repo) | `docs/career_evidence/portfolio_projects/careerfunnel_tracker.md` | Yes — feature list, evidence paths, validation status | Documents 320 tests and Sprint 29 recruiter-email layer; lists planned/unimplemented APIs (V7–V10) as not proven. |
| Portfolio project index | `docs/career_evidence/portfolio_project_index.md` | Yes — cross-project portfolio map | Use for selecting **which project** to cite; verify each project’s own evidence. |
| CV project bullet bank | `docs/career_evidence/cv_project_bullet_bank.md` | Yes — evidence-backed project bullets | Derived from portfolio project reviews; user adapts for each role. |
| Portfolio / CV wording pack | `docs/evidence/portfolio_cv_wording_pack.md` | Yes — claim-safe CV/LinkedIn/interview wording options | Sprint 26B wording only; no product changes claimed. |
| Recruiter conversion / interview packs | `docs/evidence/recruiter_conversion_pack.md`, `docs/evidence/interview_explanation_pack.md`, `docs/evidence/feature_skill_hiring_value_map.md` | Yes — structured talking points | Supporting evidence; align with README and Sprint 30 summary. |
| Analytics metric definitions | `docs/analytics/metric_definitions.md` | Yes — governed metric language for role-fit / reporting angles | Explains calculations and limitations; not job-specific CV text. |
| Analytics lineage | `docs/analytics/analytics_lineage.md` | Yes — Bronze/Silver/Gold framing for technical interviews | Portfolio analytics engineering evidence. |
| GitHub pinned repo strategy | `docs/career_evidence/github_pinned_repo_strategy.md` | Yes — short public repo descriptions | Concise wording; align with Sprint 30C gate before publishing. |
| Curated screenshots | `docs/screenshots/curated/` | Yes — visual proof of implemented UI (with demo data discipline) | Not a live deployment claim; avoid private data in shared images. |
| Sprint evidence screenshots | `docs/evidence/screenshots/` | Yes — sprint-by-sprint UI proof register | Referenced from evidence index; capture may be pending for some sprints. |

**Not used as safe product evidence in Sprint 31A** (code exists but out of documentation-only boundary for this sprint): `apps/ai_agents/` CV Gap Analyzer UI, `analyze_cv_gap` service, and related tests — these were not audited as implementation deliverables in Sprint 31A and must not be cited as shipped CV tailoring without a future sprint and evidence update.

---

## 4. Candidate Evidence Categories for Sprint 31B

| Category | Examples of Evidence | How CV Tailoring Advisor Can Use It | Claim Risk |
|---|---|---|---|
| Professional experience evidence | FX/FinTech operations background referenced in Sprint 30 summary and portfolio wording packs; role explanations in `sprint_30_recruiter_facing_project_summary.md` | Suggest which **experience angles** to emphasize (e.g. operational reporting, reconciliation-minded tracking) for a given JD | **Medium** — only use wording already documented; do not invent employers, dates, or metrics |
| Portfolio project evidence | `docs/career_evidence/portfolio_projects/*.md`, `cv_project_bullet_bank.md`, V1 inventory paths | Suggest **which projects** and **which bullets** to prioritize for a role family (DA, BI, FinTech) | **Medium** — cross-check each project file; some projects note incomplete validation |
| Technical skills evidence | V2 job-fit matrix rows; README tech stack; `feature_skill_hiring_value_map.md` | Map JD required/preferred skills to **repository-proven** skills (Python, Django, SQL, exports, metrics) | **Low–Medium** — label gaps as Partial/Missing per V2; do not claim skills without repo evidence |
| Domain evidence | README business problem; FinTech angle in Sprint 30 summary; analytics/BI explanations | Suggest domain framing (job-search analytics, data quality, funnel KPIs) aligned to JD | **Low** if tied to documented features; **High** if implying production domain systems |
| Job-search workflow evidence | Assisted intake workflow; Sprint 28 pilot; Evaluation Queue and prefill bridge (README, evidence index) | Suggest workflow talking points (“manual gates”, “data quality at save”) for cover letter or interview angles | **Low** for documented workflows; **High** if implying automation |
| Recruiter/interview evidence | Sprint 29 doc; Interview Evidence Workspace (README, Sprint 19); `interview_explanation_pack.md` | Suggest **interview prep points** and follow-up discipline tied to imported recruiter email context | **Low** if manual/advisory; **High** if implying Gmail or auto outreach |
| Public wording evidence | Sprint 30B/30C drafts; `github_pinned_repo_strategy.md`; LinkedIn drafts marked not published | Reuse **approved draft phrases** for consistency; flag publish gate before any external use | **Medium** — drafts are not publication proof |

---

## 5. Manual Approval Rules

Any Sprint 31B **CV Tailoring Advisor** output must remain **advisory** and **approval-based**:

| Output type | Rule |
|---|---|
| Suggested CV evidence | Pointers to existing bullets, projects, or experience angles — not a final CV file |
| Suggested project evidence | Which portfolio projects to cite and why — user selects what to include |
| Suggested cover-letter angle | Themes or paragraphs to draft manually — not auto-sent or auto-finalized |
| Suggested interview points | Talking points from documented evidence — user decides what to say |
| Human decision | User chooses what to use, edit, or discard for each application |
| Final CV generation | **No** final CV generation without explicit manual review and user approval |

The assisted intake workflow already documents the intended discipline: CareerFunnel **assists and suggests**; the user **reviews and approves** all final actions (`docs/evidence/assisted_job_intake_workflow.md`). Sprint 31B must preserve that pattern.

---

## 6. Unsafe or Future-Only Claims

The following must **not** appear in Sprint 31B recommendations, generated wording, or evidence citations unless a future sprint implements, tests, documents, and the user explicitly approves new claims:

| Unsafe / future-only claim | Why excluded |
|---|---|
| AI scoring / AI fit / LLM review | Repository uses rule-based logic; README and Sprint 29–30 docs deny external AI / LLM integration |
| Claude second-opinion reviewer | Listed as planned/not implemented in portfolio project review (V8) |
| Gmail integration / inbox sync | Explicitly not implemented; manual import only |
| Calendar integration | Not implemented; listed as future-only in portfolio project review |
| Notification automation | No background notification system claimed |
| Auto-apply | Denied across README, intake workflow, and Sprint 28–30 evidence |
| Scraping | Job descriptions are user-pasted; no scraping claim |
| Recruiter automation | Sprint 29 is manual, rule-based, advisory only |
| Production SaaS / customer claims | Portfolio-scale local product only; no production users |
| Guaranteed job-fit outcomes | Fit review is rule-based and directional; no outcome guarantees |

Also excluded: presenting **CV Gap Analyzer** (`apps/ai_agents/`) as the Sprint 31B Tailoring Advisor without a dedicated implementation sprint and updated evidence.

---

## 7. Recommended Inputs for Sprint 31B

Sprint 31B can safely accept the following inputs when designing an advisory tailoring flow:

| Input | Source / notes |
|---|---|
| Job title | User-entered or from Job Posting Analyzer / application prefill |
| Full job description | Tracker fields and assisted intake paste path |
| Required skills | Application and analyzer fields documented in intake field audit |
| Preferred skills | Same; treat as secondary to required |
| Location / work mode | If captured in application or intake evidence |
| Seniority requirements | Rule-based fit / seniority-risk signals (keyword-based; limitations documented) |
| Existing project evidence | `docs/career_evidence/portfolio_projects/`, bullet bank, V2 matrix |
| Existing CV / project positioning evidence | Sprint 30B summary, portfolio CV wording pack, V3 recruiter pack |
| Known deal-breakers | User-defined skip/fit decisions from intake workflow and live pilot docs |
| Manual user approval | Required gate before any text is treated as final for CV, cover letter, or application submission |

Sprint 31B should log or display **which evidence file** supported each suggestion (traceability), matching the Career Evidence OS discipline.

---

## 8. Sprint 31B Readiness Decision

| Decision item | Status |
|---|---|
| Sprint 31A deliverable | This source audit document |
| Implementation of CV Tailoring Advisor | **Not started** — awaits Sprint 31B |
| Automatic CV rewrite | **Out of scope** |
| Evidence sources inventoried | **Yes** — see Section 3 |
| Claim boundaries documented | **Yes** — see Sections 2, 5, and 6 |

**Readiness statement:**

Sprint 31A prepares the **source audit only**. Sprint 31B may proceed **only after**:

1. This document is reviewed for accuracy against the repository.
2. Sprint 31A validation passes (repository checks per project validation routine).
3. The user explicitly approves moving forward to Sprint 31B design/implementation.

Until those steps complete, no CV Tailoring Advisor feature should be treated as delivered or portfolio-claimable.

---

## Audit Metadata

| Item | Value |
|---|---|
| Sprint | 31A — CV Evidence Source Audit |
| Branch | `sprint-31a-cv-evidence-source-audit` |
| Scope | Documentation / audit only |
| Primary output | This file |
| Index update | `docs/evidence/evidence_index.md` |
| Baseline cited in source docs | 320 passing tests (README, Sprint 30 evidence); verify locally before Sprint 31B |
| Related deferred work (documented elsewhere) | Role-specific CV angle advice noted in Sprint 28 pilot and code comments — not implemented in Sprint 31A |

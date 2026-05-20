# Sprint 27B -- Application Pack Usage Mapping

## Sprint Metadata

| Item | Value |
|---|---|
| Sprint | Sprint 27B |
| Title | Application Pack Usage Mapping |
| Scope type | Manual application-pack-to-tracker mapping documentation only |
| CV source | Aminul_Islam_Data_Analyst_CV |
| Sprint 27A source | docs/evidence/sprint_27_live_application_workflow.md |
| Application Pack index | docs/evidence/final_application_pack_index_and_usage_guide.md |
| Latest completed tag before sprint | sprint-27a-complete |
| Implementation boundary | No README edit, no CV edit, no LinkedIn edit, no GitHub profile edit, no code changes, no migrations, no automation, no scraping, no Gmail, no Calendar, no external AI/API, no auto-apply |

## Purpose

Sprint 27B maps the completed Application Pack to CareerFunnel Tracker usage.

This document does not update the CV, LinkedIn, GitHub, README, or the CareerFunnel Tracker codebase. It defines what to record manually for each application: which pack document was used, which evidence was cited, claim-safety outcome, and follow-up plan.

Use with:

- Sprint 27A live workflow: `docs/evidence/sprint_27_live_application_workflow.md`
- Application Pack Steps 1-5
- Locked CV: `Aminul_Islam_Data_Analyst_CV`
- CareerFunnel Tracker application records and notes (manual entry only)

## Current Starting Point

- [x] Sprint 27A live application workflow complete
- [x] Application Pack Step 1 complete
- [x] Application Pack Step 2 complete
- [x] Application Pack Step 3 complete
- [x] Application Pack Step 4 complete
- [x] Application Pack Step 5 complete
- [x] Locked CV ready: `Aminul_Islam_Data_Analyst_CV`
- [x] LinkedIn update postponed until after Sprint 30
- [x] No automation or integration claims added

## Application Pack To Tracker Mapping Summary

| Application Pack Document | Use Case | Tracker Field Impact |
|---|---|---|
| `master_cover_letter_recruiter_message_pack.md` (Step 1) | General/fallback cover letter; master evidence blocks; baseline recruiter wording | Cover letter used; Main evidence; Recruiter message used (if short baseline used) |
| `role_specific_cover_letter_variants.md` (Step 2) | Role type clear: Data, BI/Reporting, FinTech, Operations/Commercial | Cover letter used; Main evidence; Project evidence by role table |
| `job_specific_cover_letter_builder.md` (Step 3) | Full JD available; requirement mapping; tailored letter | Cover letter used; Notes (JD intake); Main evidence; Project evidence; Claim-safety result |
| `recruiter_outreach_message_variants.md` (Step 4) | Outreach, follow-up, CV/GitHub/SQL/BI replies | Recruiter message used; Status (Outreach Sent / Follow-Up Due); Follow-up date |
| `final_application_pack_index_and_usage_guide.md` (Step 5) | Which document to open; decision tree; claim-safety checklist | Reference only; guides Notes and Application quality level |
| `sprint_27_live_application_workflow.md` (Sprint 27A) | Daily apply workflow; role-fit gate; weekly review | Status progression; Application quality level; Fit rating and Priority rules |

## Tracker Field Mapping

| Tracker Field | Record This | Source Document / Evidence |
|---|---|---|
| Company | Legal or trading name from posting | JD; Step 3 intake form |
| Role title | Exact title from job ad | JD; Step 3 intake |
| Job URL | Full live posting link | JD; portal apply page |
| Source | Indeed, LinkedIn jobs, company site, recruiter, referral | Your search log |
| Location | City/region or Remote UK | JD; Purley/London/UK remote fit |
| Work mode | On-site, hybrid, remote | JD |
| Fit rating | Numeric or label per Fit Rating Rules (9-10 down to Skip) | Sprint 27A role-fit gate; Step 3 apply/skip decision |
| Priority | High, Medium-High, Medium, Low, or Skip | Fit rating + timing + company quality |
| Status | Saved through Skipped per Status Mapping Rules | Application lifecycle |
| CV version | Always `Aminul_Islam_Data_Analyst_CV` | Locked CV rule; Step 4 CV reply |
| Cover letter used | Step 1 / Step 2 variant / Step 3 tailored / None | Steps 1-3; Cover Letter Recording Rules |
| Recruiter message used | Step 4 message type if sent | `recruiter_outreach_message_variants.md` |
| Main evidence | One domain block (Acaelus, Bliss, FX ops, etc.) | Step 1 evidence blocks; Role Type To Evidence Mapping |
| Project evidence | One or two portfolio projects maximum | Role Type To Evidence Mapping; Project Evidence Recording Rules |
| Claim-safety result | Pass, Adjusted, Stretch wording, Skip, Needs human review | Claim-Safety Result Mapping; Step 5 checklist |
| Notes | JD summary, must-haves, blocker, recruiter name, portal confirmation | Step 3 intake; Skip Reason Mapping |
| Follow-up date | Planned 3-day or 7-day date if outreach or apply-and-wait | Step 4 follow-up variants |
| Application quality level | Quick Apply, Standard Apply, High-Value Apply, Stretch Apply, Skip | Sprint 27A Application Quality Levels |
| Skip reason | Standard skip code if not applying | Skip Reason Mapping |

## Role Type To Evidence Mapping

| Role Type | Work Evidence | Project Evidence | Cover Letter Variant | Claim-Safety Risk |
|---|---|---|---|---|
| Data Analyst | Acaelus reconciliation, FX/money transfer, in-house Excel reconciliation, KPI reporting | BakeOps Intelligence; CareerFunnel Tracker | Step 2 Data Analyst variant; Step 3 if full JD | Production SQL project claims; listing all four repos |
| BI / Reporting Analyst | Bliss KPI reporting, Acaelus reconciliation controls, Excel/Power Query/DAX, reporting discipline | BakeOps Intelligence; TradeIntel 360 | Step 2 BI / Reporting variant; Step 3 if unusual must-haves | Production Power BI or Tableau artefacts |
| FinTech / FX / Payments Analytics | Acaelus FX/remittance, AML-aware workflows, multi-currency reconciliation, around £30,000 daily cash volume (where accurate on CV) | TradeIntel 360; DataBridge Market API | Step 2 FinTech variant; Step 3 for requirement mapping | Live trading-system, SaaS, or production infra claims |
| Operations Analyst / Commercial Analyst | Acaelus/Bliss process control, discrepancy review, 800-agent support context, KPI reporting | BakeOps Intelligence; CareerFunnel Tracker | Step 2 Operations / Commercial variant | Automation, live SaaS, external AI claims |
| Analytics Engineer stretch | Reconciliation discipline, KPI definitions, Python portfolio depth; junior/analyst-friendly JD only | DataBridge Market API; CareerFunnel Tracker | Step 3 + honest stretch wording; Application quality level: Stretch Apply | Airflow/dbt/cloud orchestration overclaim |
| Junior Data Engineer stretch | Platform support, ingestion interest; junior JD only, not cloud-heavy | DataBridge Market API (primary) | Step 3 + stretch wording only if JD allows | Senior warehouse or production pipeline claims |

## Application Situation Mapping

| Situation | Application Pack Document To Use | Tracker Status | Evidence To Record |
|---|---|---|---|
| Full JD available | Step 3 `job_specific_cover_letter_builder.md` (+ Step 2 variant) | Reviewing -> Apply -> Submitted | Step 3 tailored; JD in Notes; Main + Project evidence; Claim-safety Pass/Adjusted |
| Quick apply role | Step 2 role variant or Step 1 fallback | Apply -> Submitted | Cover letter variant name; CV version; Application quality level: Quick Apply |
| High-value role | Step 3 full mapping + Step 2 variant | Apply -> Submitted | High-Value Apply; best project pair; optional Outreach Sent |
| Stretch role | Step 3 + stretch wording; Step 2 if role type clear | Apply -> Submitted or Skipped | Stretch Apply; Claim-safety: Stretch wording; Analytics Engineer or Junior DE only |
| Recruiter outreach before applying | Step 4 outreach variant | Outreach Sent | Recruiter message type; Follow-up date; CV version in message |
| Recruiter follow-up after applying | Step 4: 3-day or 7-day follow-up | Follow-Up Due -> Outreach Sent | Follow-up variant; reference Submitted date in Notes |
| Recruiter asks for GitHub | Step 4: Portfolio Link Message | Outreach Sent (reply) | GitHub links only; portfolio scope in Notes |
| Recruiter asks about SQL | Step 4: SQL reply template | Outreach Sent (reply) | Honest SQL skill wording; no production SQL projects |
| Recruiter asks about Power BI/Tableau | Step 4: BI platform reply template | Outreach Sent (reply) | Excel/Power Query; BI-ready exports; no unverified dashboards |
| Role skipped due to blocker | Step 3 apply/skip decision or Sprint 27A gate | Skipped | Skip reason from mapping table; brief Notes only |
| Role skipped due to seniority | Sprint 27A role-fit gate | Skipped | Skip reason: Seniority too high |
| Role skipped due to location | Sprint 27A role-fit gate | Skipped | Skip reason: Location does not work |
| Role skipped due to scam/vague company risk | Sprint 27A role-fit gate | Skipped | Skip reason: Scam/vague company risk |

## Fit Rating Rules

| Fit Rating | Meaning | Apply Decision | Tracker Note |
|---|---|---|---|
| 9-10 Strong fit | Title, tools, location, and seniority align with target roles | Apply now; Standard or High-Value Apply | Record numeric fit; Priority High or Medium-High |
| 7-8 Apply | Good fit with minor gaps you can address honestly | Apply; use Step 2 or Step 3 | Standard Apply; full evidence mapping |
| 6-6.9 Maybe / stretch | Stretch or needs extra tailoring; not ideal | Stretch Apply only if worth time; else Skip | Note stretch reason; Claim-safety: Stretch wording |
| Below 6 Skip | Poor fit; not worth tailoring time | Skip; record skip reason | Brief outcome in Notes; move on |
| Blocker Skip immediately | Hard must-have you cannot evidence | Skip immediately | Skip reason code; no cover letter sent |

For roles below 7/10, record outcome briefly and move on unless you need detail for weekly review.

## Priority Rules

| Priority | Use When | Action |
|---|---|---|
| High | Fit 9-10; strong company; deadline soon | Apply within 1-2 days; High-Value or Standard Apply |
| Medium-High | Fit 7-8; good role; reasonable timing | Apply this week; Standard Apply |
| Medium | Fit 7-8; acceptable but not urgent | Queue for normal weekday slot |
| Low | Fit 6-6.9 stretch; or timing uncertain | Stretch apply only if bandwidth; else Saved for later review |
| Skip | Blocker or below 6 fit | Status Skipped; record Skip reason; no apply |

## Status Mapping Rules

| Status | Use When | Follow-Up Rule |
|---|---|---|
| Saved | JD found; not yet reviewed | None until Reviewing |
| Reviewing | JD saved; fit/priority being assessed | Move to Apply or Skipped after gate |
| Apply | Preparing cover letter and materials | Claim-safety before Submitted |
| Submitted | Application sent on portal or email | Plan 3-day follow-up if no response |
| Outreach Sent | Recruiter email or LinkedIn DM sent | 3-day or 7-day follow-up per Step 4 |
| Follow-Up Due | Follow-up date reached | Send one follow-up; update Notes |
| Interview | Interview invite received | Record date in Notes |
| Rejected | Rejection received | Brief reason in Notes if stated |
| Withdrawn | You withdrew application | Note reason |
| Skipped | Did not apply | Skip reason required |

## CV Version Recording Rules

- Always record CV version as: `Aminul_Islam_Data_Analyst_CV`
- Do not rename the master CV for normal applications.
- Do not rewrite the CV during Sprint 27B.
- Use cover letter and recruiter message tailoring first; CV stays locked.
- LinkedIn update remains postponed until after Sprint 30.

## Cover Letter Recording Rules

| Cover Letter Source | Record As | Use When |
|---|---|---|
| Step 1 master cover letter | `Step 1 master` | General/fallback; simple portal; time-limited |
| Step 2 Data Analyst variant | `Step 2 Data Analyst` | Clear Data Analyst posting |
| Step 2 BI / Reporting variant | `Step 2 BI Reporting` | BI, Reporting, or management reporting role |
| Step 2 FinTech / FX / Payments variant | `Step 2 FinTech FX Payments` | FinTech, FX, payments, remittance analytics |
| Step 2 Operations / Commercial variant | `Step 2 Operations Commercial` | Operations or Commercial Analyst role |
| Step 3 job-specific tailored letter | `Step 3 tailored [Company]` | Full JD; requirement mapping completed |
| No cover letter used | `None` | Portal CV-only apply; recruiter message only |

## Recruiter Message Recording Rules

| Message Type | Record As | Use When |
|---|---|---|
| General recruiter email | `Step 4 general email` | First contact before or without formal apply |
| General LinkedIn recruiter DM | `Step 4 general LinkedIn DM` | Short LinkedIn outreach |
| Data Analyst outreach | `Step 4 Data Analyst outreach` | Role-specific Step 4 or Step 2 email variant |
| BI / Reporting outreach | `Step 4 BI Reporting outreach` | BI or reporting recruiter contact |
| FinTech / FX / Payments outreach | `Step 4 FinTech outreach` | FinTech or payments recruiter contact |
| Operations / Commercial outreach | `Step 4 Operations outreach` | Operations or commercial recruiter contact |
| 3-day follow-up | `Step 4 follow-up 3-day` | No response 3 days after apply or outreach |
| 7-day follow-up | `Step 4 follow-up 7-day` | No response 7 days after apply or outreach |
| CV reply | `Step 4 CV reply` | Recruiter requests CV; attach `Aminul_Islam_Data_Analyst_CV` |
| GitHub portfolio reply | `Step 4 GitHub reply` | Recruiter asks for portfolio or repos |
| SQL reply | `Step 4 SQL reply` | Recruiter asks about SQL; no production SQL project claims |
| Power BI/Tableau reply | `Step 4 BI platform reply` | Recruiter asks about BI tools; honest Excel/export wording |
| Salary/location reply | `Step 4 salary location reply` | Recruiter asks expectations; UK-based; no invented range |
| Rejection reply | `Step 4 rejection reply` | Polite close after rejection |

## Project Evidence Recording Rules

| Project | Best Used For | Safe Tracker Note | Avoid |
|---|---|---|---|
| BakeOps Intelligence | Data Analyst; BI/Reporting; Operations/Commercial | Portfolio KPI surfaces, BI-ready CSV exports, rank-inversion insight | Production users; live SaaS |
| CareerFunnel Tracker | Data Analyst; Operations; Analytics Engineer stretch | Django funnel metrics, Evaluation Queue, data-quality warnings, 249 tests, manual workflow | Auto-apply; scraping; external AI/API |
| TradeIntel 360 | BI/Reporting; FinTech / FX / Payments | CSV-upload trading KPIs with documented methodology | Live brokerage; production trading infra |
| DataBridge Market API | FinTech; Analytics Engineer stretch; Junior DE stretch (junior JD) | Market-data ingestion, run logging, normalised storage, inspection workflow | Production pipelines; cloud platform delivery |
| MarketVista Dashboard | FinTech monitoring secondary mention only | Portfolio monitoring dashboard; sparse-intraday handling | Live trading decisions; production alerting; investment advice |

Do not claim production users, live SaaS, external AI/API, scraping, auto-apply, Gmail, Calendar, production SQL projects, Power BI/Tableau artefacts, or V7-V10 implementation in tracker Notes or outbound messages.

## Skip Reason Mapping

| Skip Reason | Use When | Tracker Note Example |
|---|---|---|
| Seniority too high | Lead, principal, or senior platform role | `Skipped: seniority too high for target band` |
| Location does not work | Not Purley/London/UK remote viable | `Skipped: location/hybrid requirement not workable` |
| Sponsorship mismatch | Sponsorship required | `Skipped: sponsorship required` |
| Mandatory Power BI/Tableau artefact not evidenced | JD requires verified dashboards you do not have | `Skipped: mandatory PBI/Tableau artefact not evidenced` |
| Advanced SQL / data warehouse requirement too high | Production warehouse/SQL delivery expected | `Skipped: advanced SQL/warehouse requirement beyond evidence` |
| Cloud/dbt/Airflow/Spark/Kafka hard requirement | Orchestration stack mandatory | `Skipped: cloud/dbt/Airflow/Spark/Kafka hard requirement` |
| Data Engineer role too senior | Senior DE/ML platform role | `Skipped: Data Engineer role too senior` |
| Data Scientist / ML role | DS/ML primary focus | `Skipped: Data Scientist / ML role outside target` |
| Finance/accounting qualification hard requirement | ACA/ACCA/qualified accountant mandatory | `Skipped: finance qualification hard requirement` |
| Scam/vague company risk | Unverifiable employer or posting | `Skipped: scam or vague company risk` |
| Salary/commute not worth time | Below acceptable range or commute | `Skipped: salary/commute not worth time` |
| Duplicate role | Already applied or same posting resurfaced | `Skipped: duplicate of [Company] [Role]` |

## Claim-Safety Result Mapping

| Result | Meaning | Action |
|---|---|---|
| Pass | All checklist items satisfied; ready to send | Submitted or Outreach Sent |
| Adjusted | Wording changed to remove risky claims before send | Note what was removed in Notes |
| Stretch wording | Honest stretch apply; Analytics Engineer or Junior DE only | Application quality level: Stretch Apply |
| Skip | Blocker found during claim-safety review | Status Skipped; record Skip reason |
| Needs human review | Unsure about one claim | Do not send until reviewed; keep Reviewing status |

## Manual Application Mapping Record Template

Copy this block for each application:

```markdown
## Sprint 27B Application Mapping Record

Date:
Company:
Role:
Job URL:
Source:
Location:
Work mode:
Fit rating:
Priority:
Status:
Application quality level:
CV version: Aminul_Islam_Data_Analyst_CV
Cover letter source:
Recruiter message source:
Main work evidence:
Project evidence:
Claim-safety result:
Skip reason:
Follow-up date:
Notes:
```

## Example Records

### Example 1 -- Data Analyst Apply

```markdown
Date:
Company: Example Company
Role: Junior Data Analyst
Job URL: [Saved URL]
Source: LinkedIn / Company site
Location: London / Hybrid
Work mode: Hybrid
Fit rating: 8/10
Priority: High
Status: Submitted
Application quality level: Standard Apply
CV version: Aminul_Islam_Data_Analyst_CV
Cover letter source: Step 2 Data Analyst variant
Recruiter message source: None
Main work evidence: Acaelus reconciliation, Excel controls, KPI reporting
Project evidence: BakeOps Intelligence; CareerFunnel Tracker
Claim-safety result: Pass
Skip reason:
Follow-up date: [Date if needed]
Notes: Role matched analyst direction; no unsupported Power BI/Tableau or production SQL claims used.
```

### Example 2 -- FinTech / FX Apply

```markdown
Date:
Company: Example Payments Company
Role: Payments / FinTech Data Analyst
Job URL: [Saved URL]
Source: Company site
Location: London / Remote UK
Work mode: Remote
Fit rating: 8.5/10
Priority: High
Status: Submitted
Application quality level: High-Value Apply
CV version: Aminul_Islam_Data_Analyst_CV
Cover letter source: Step 2 FinTech / FX / Payments variant + Step 3 tailoring
Recruiter message source: Step 4 FinTech outreach if recruiter contacted
Main work evidence: Acaelus FX/remittance, AML-aware workflows, multi-currency reconciliation, around £30,000 daily cash volume
Project evidence: TradeIntel 360; DataBridge Market API
Claim-safety result: Pass
Skip reason:
Follow-up date: [Date if needed]
Notes: Domain evidence used carefully; no live trading-system, SaaS, or production-user claims.
```

### Example 3 -- BI / Reporting Stretch

```markdown
Date:
Company: Example Reporting Team
Role: BI / Reporting Analyst
Job URL: [Saved URL]
Source: Indeed / LinkedIn
Location: London / Hybrid
Work mode: Hybrid
Fit rating: 7/10
Priority: Medium-High
Status: Submitted
Application quality level: Stretch Apply
CV version: Aminul_Islam_Data_Analyst_CV
Cover letter source: Step 2 BI / Reporting variant
Recruiter message source: Step 4 BI / Reporting outreach if used
Main work evidence: Bliss KPI reporting, Excel / Power Query / DAX workbook logic, reporting discipline
Project evidence: BakeOps Intelligence; TradeIntel 360
Claim-safety result: Adjusted
Skip reason:
Follow-up date: [Date if needed]
Notes: Used careful wording for Power BI/Tableau; did not claim verified platform artefacts.
```

### Example 4 -- Skip Role

```markdown
Date:
Company: Example Company
Role: Senior Data Engineer
Job URL: [Saved URL]
Source: Job board
Location: Outside London / On-site
Work mode: On-site
Fit rating: Below 6/10
Priority: Skip
Status: Skipped
Application quality level: Skip
CV version: Aminul_Islam_Data_Analyst_CV
Cover letter source: None
Recruiter message source: None
Main work evidence:
Project evidence:
Claim-safety result: Skip
Skip reason: Seniority too high; cloud/dbt/Airflow/Spark/Kafka hard requirement
Follow-up date:
Notes: Skipped quickly because role did not match current analyst-focused positioning.
```

## Daily Usage Checklist

- [ ] Job URL saved.
- [ ] JD saved.
- [ ] Fit rating recorded.
- [ ] Priority recorded.
- [ ] Status recorded.
- [ ] Application quality level recorded.
- [ ] CV version recorded as `Aminul_Islam_Data_Analyst_CV`.
- [ ] Cover letter source recorded.
- [ ] Recruiter message source recorded if used.
- [ ] Main work evidence recorded.
- [ ] Project evidence recorded.
- [ ] Claim-safety result recorded.
- [ ] Skip reason recorded if skipped.
- [ ] Follow-up date set if needed.
- [ ] LinkedIn profile update remains postponed until after Sprint 30.

## What Sprint 27B Includes

- [x] Application Pack to tracker mapping summary
- [x] Tracker field mapping with source documents
- [x] Role type to evidence mapping
- [x] Application situation mapping
- [x] Fit rating and priority rules
- [x] Status mapping rules
- [x] CV, cover letter, and recruiter message recording rules
- [x] Project evidence and skip reason mapping
- [x] Claim-safety result mapping
- [x] Manual application mapping record template
- [x] Example records (apply, stretch, skip)
- [x] Daily usage checklist

## What Sprint 27B Does Not Include

- [ ] CV rewrite
- [ ] LinkedIn profile update
- [ ] README update
- [ ] Code changes
- [ ] New Django fields or migrations
- [ ] Scraping
- [ ] Auto-apply
- [ ] Gmail integration
- [ ] Calendar integration
- [ ] External AI/API integration
- [ ] Power BI/Tableau artefact claim
- [ ] Production SQL project claim

These items remain excluded for claim safety and sprint discipline.

## Final Decision

Sprint 27B approves this Application Pack usage mapping for manual CareerFunnel Tracker recording with the locked CV `Aminul_Islam_Data_Analyst_CV`.

Recommended next step:
Sprint 27C -- Final Sprint 27 Readiness Index And Closure

Do not recommend LinkedIn profile update until after Sprint 30.

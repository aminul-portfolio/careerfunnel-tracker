# Job-Specific Cover Letter Builder

## Step Metadata

| Item | Value |
|---|---|
| Step | Application Pack Step 3 |
| Scope type | Job-specific cover letter builder only |
| CV source | Aminul_Islam_Data_Analyst_CV |
| Source pack 1 | docs/evidence/master_cover_letter_recruiter_message_pack.md |
| Source pack 2 | docs/evidence/role_specific_cover_letter_variants.md |
| Implementation boundary | No README edit, no CV edit, no LinkedIn edit, no GitHub profile edit, no code changes, no migrations, no screenshots, no AI/API integration, no Gmail, no Calendar, no scraping, no auto-apply |

## Purpose

This document converts a pasted job description into a tailored, claim-safe cover letter using the locked master CV **Aminul_Islam_Data_Analyst_CV** and Application Pack Step 1/2 evidence.

This file does not update the CV, LinkedIn, GitHub, README, or any public profile. It provides a manual, copy/paste-ready builder workflow: intake the JD, select one role variant, map requirements to provable evidence, pick one or two portfolio projects, draft the letter, and run claim-safety review before sending.

## Source Evidence Used

- README.md
- docs/evidence/master_cover_letter_recruiter_message_pack.md
- docs/evidence/role_specific_cover_letter_variants.md
- docs/evidence/cv_linkedin_application_pack_export.md
- docs/evidence/application_pack_public_profile_update_decision.md
- docs/evidence/portfolio_cv_wording_pack.md

## Builder Workflow Summary

1. Paste the job description into the Pasted JD Intake Form.
2. Complete the Requirement Extraction Checklist.
3. Select one role variant in Role Variant Selector.
4. Map must-haves in Requirement-To-Evidence Mapping Table.
5. Select one or two projects in Project Evidence Selector.
6. Draft the letter using Job-Specific Cover Letter Template.
7. Run Final Claim-Safety Checklist Before Sending.
8. Save output in Final Output Format and attach **Aminul_Islam_Data_Analyst_CV**.

## Pasted JD Intake Form

Copy this block for each application:

```markdown
## Job Description Intake

Company:
Role title:
Job URL:
Job source:
Location:
Work mode:
Salary range:
Deadline:
Hiring contact / recruiter:
Must-have requirements:
Nice-to-have requirements:
Tools mentioned:
Domain mentioned:
Main responsibilities:
Evidence I can prove:
Evidence I cannot prove:
Best role variant:
Best project evidence:
Apply / skip decision:
Notes:
```

## Requirement Extraction Checklist

Complete after pasting the JD.

| Field | What to capture |
|---|---|
| Company | Legal or trading name |
| Role title | Exact posting title |
| Tools | Named tools only if in JD |
| Domain | Industry context |
| Location / work mode | Purley / London / UK remote fit |

### Must-Have Requirements

- [ ] Role title fits target direction.
- [ ] Location/work mode works from Purley/London/UK remote.
- [ ] Required experience is realistic.
- [ ] Required tools are honestly covered.
- [ ] No hard blocker such as mandatory Power BI/Tableau if not evidenced.
- [ ] No hard blocker such as cloud/dbt/Airflow/Spark/Kafka if required as must-have.
- [ ] No unsupported seniority requirement.

### Strong Match Signals

- [ ] Excel reporting
- [ ] KPI reporting
- [ ] Data analysis
- [ ] Reconciliation
- [ ] Financial services
- [ ] FX / payments / FinTech
- [ ] Operations analysis
- [ ] Python
- [ ] SQL as a skill
- [ ] Data quality
- [ ] Stakeholder reporting

### Risk Signals

- [ ] Power BI/Tableau hard requirement.
- [ ] SQL-heavy role with technical SQL test.
- [ ] Senior/Lead/Manager title.
- [ ] Cloud data warehouse hard requirement.
- [ ] dbt/Airflow/Spark/Kafka hard requirement.
- [ ] Requires prior Data Analyst job title only.
- [ ] Requires sponsorship or location does not work.

**Apply / skip rule:** Apply when strong match signals outweigh risk signals and must-haves map in Requirement-To-Evidence Mapping Table.

## Role Variant Selector

Pick **one** base variant from `docs/evidence/role_specific_cover_letter_variants.md`.

| If JD emphasises... | Select variant | Stretch? |
|---|---|---|
| data analysis, MIS, reporting, SQL/Python, operational data | Data Analyst | No |
| BI, dashboards, KPI packs, Power Query, management reporting | BI / Reporting Analyst | No |
| FX, payments, remittance, FinTech, trading ops, AML, reconciliation | FinTech / FX / Payments Analytics | No |
| operations, commercial, process, platform support, workflow | Operations Analyst / Commercial Analyst | No |
| analytics engineering, ETL, pipelines, data modelling | Data Analyst + note AE stretch | Yes |
| data engineer, ingestion, APIs, warehouse | FinTech or Data Analyst + DataBridge | Yes |

**Domain block (one only) after variant is chosen:**

| Role variant | Domain block to adapt |
|---|---|
| Data Analyst | Excel reconciliation + FX/money transfer + KPI reporting |
| BI / Reporting Analyst | Bliss KPI + Acaelus controls + Excel/Power Query/DAX |
| FinTech / FX / Payments | Acaelus AML/reconciliation/cash volume + exception review |
| Operations / Commercial | Acaelus/Bliss process control + KPI + platform support |

## Requirement-To-Evidence Mapping Table

Map each must-have to CV or portfolio evidence. Do not map to "Evidence I cannot prove" items.

| JD theme | CV / work evidence (prove) | Portfolio evidence (prove) | Wording caution |
|---|---|---|---|
| Excel / reconciliation | In-house Excel reconciliation system; Acaelus multi-currency reconciliation | BakeOps Intelligence | Do not claim every Excel macro unless on CV |
| KPI / management reporting | Bliss KPI reporting; Acaelus reporting cycles | BakeOps, TradeIntel 360 | No fake dashboard counts |
| Python / analytics | Skill on CV; portfolio repos | CareerFunnel, BakeOps, TradeIntel, DataBridge | Portfolio scope only |
| SQL | Skill on CV | Do not claim production SQL projects unless evidenced | Use Step 2 SQL tailoring block |
| Power BI / Tableau | Only if verified artefact exists | BI-ready CSV, dashboard-style portfolio | Use careful transfer wording |
| FinTech / FX / payments | Acaelus FX/remittance, AML, around £30,000 daily cash volume | TradeIntel 360, DataBridge | Domain first; no live trading infra |
| Operations / process | Bliss 800-agent support; Acaelus controls | CareerFunnel, BakeOps | No automation claims |
| Data quality / governance | Reconciliation discipline; KPI definitions | CareerFunnel data-quality warnings | No external AI |
| Stakeholder communication | Bliss, platform support, training | GitHub evidence docs | Not "led enterprise transformation" |

## Project Evidence Selector

**Rule:** Maximum **two** projects per application.

### BakeOps Intelligence

- **Best for:** Data Analyst, BI/Reporting Analyst, Operations Analyst
- **Use when JD asks for:** operational KPIs, profitability, margins, BI-ready exports, metric documentation
- **Safe wording:** Portfolio project showing KPI dashboards, BI-ready exports, metric documentation, and a rank-inversion insight where revenue and waste-adjusted margin rankings differ.
- **Avoid:** production users, live SaaS, external client work.

### TradeIntel 360

- **Best for:** BI/Reporting Analyst, FinTech / FX / Payments Analytics
- **Use when JD asks for:** trading KPIs, performance reporting, CSV/Excel exports, FinTech analyst context
- **Safe wording:** Portfolio project calculating trading KPIs from CSV uploads with configurable reporting and transparent Sharpe methodology documentation.
- **Avoid:** institutional trading system claims, live brokerage integration claims.

### CareerFunnel Tracker

- **Best for:** Data Analyst, Operations Analyst, Analytics Engineer stretch
- **Use when JD asks for:** structured metrics, data quality, workflow governance, testing, documentation
- **Safe wording:** Portfolio project showing structured application records, funnel metrics, data-quality warnings, manual assisted intake, and 249 automated tests.
- **Avoid:** auto-apply, scraping, external AI integration, live job-platform claims.

### DataBridge Market API

- **Best for:** FinTech / FX analytics, Analytics Engineer stretch, Junior Data Engineer stretch
- **Use when JD asks for:** market data, ingestion, API, ETL, pipeline logging
- **Safe wording:** Portfolio project showing market-data ingestion, run logging, normalised storage, and inspection workflow at portfolio scope.
- **Avoid:** production pipeline claims, cloud platform claims, enterprise API service claims.

### MarketVista Dashboard

- **Best for:** FinTech monitoring (secondary only)
- **Use when JD asks for:** signals, watchlists, alerts, monitoring dashboards
- **Safe wording:** Portfolio project showing market-data monitoring, watchlist, alert, and asset-inspection dashboard logic with sparse-intraday handling.
- **Avoid:** live trading decisions, production alerting, investment advice.

| Role variant | First pick | Second pick (optional) |
|---|---|---|
| Data Analyst | BakeOps Intelligence | CareerFunnel Tracker |
| BI / Reporting Analyst | BakeOps Intelligence | TradeIntel 360 |
| FinTech / FX / Payments | TradeIntel 360 | DataBridge Market API |
| Operations / Commercial | BakeOps Intelligence | CareerFunnel Tracker |

## Job-Specific Cover Letter Template

Copy/paste and replace every placeholder. Target **250-330 words**.

Dear Hiring Manager,

I am applying for the [Role Title] position at [Company Name], which I found via [Job Source]. I am a UK-based analyst candidate with 15 years of experience in financial operations, reconciliation, and KPI reporting. I am eligible to work in the UK without sponsorship. [Why This Company] [Company Context]

Your emphasis on [Top Requirement 1] aligns with my background. [Domain Evidence] In regulated environments I supported multi-currency reconciliation, exception review, and management-facing reporting, including an in-house Excel reconciliation system for daily control.

Your need for [Top Requirement 2] matches how I combine operational discipline with a Python/Django analytics portfolio on GitHub. [Project Evidence 1] demonstrates this through reviewer-ready evidence tied to your role. [Project Evidence 2] adds complementary proof where relevant. I present portfolio work honestly: no external AI, scraping, auto-apply, live SaaS, or unverified BI platform artefacts.

I would welcome the opportunity to discuss the role. My CV (**Aminul_Islam_Data_Analyst_CV**) is attached. [Closing Availability Note]

Yours sincerely,

Aminul Islam

**Placeholders:** [Company Name], [Role Title], [Job Source], [Company Context], [Top Requirement 1], [Top Requirement 2], [Domain Evidence], [Project Evidence 1], [Project Evidence 2], [Why This Company], [Closing Availability Note]

## Final Output Format

```markdown
## Final Cover Letter Output

Company:
Role:
CV attached: Aminul_Islam_Data_Analyst_CV
Cover letter variant used:
Main evidence:
Project evidence:
Claim-safety result:
Final cover letter:

[Paste final cover letter here]
```

## Example Built Cover Letter -- Data Analyst

Dear Hiring Manager,

I am applying for the Data Analyst position at Example Payments Ltd, which I found via LinkedIn. I am a UK-based Data Analyst candidate with 15 years of experience across FX and money transfer operations, AML-aware reconciliation, KPI reporting, and platform support. I am eligible to work in the UK without sponsorship. I am interested in Example Payments because the role combines operational reporting discipline with structured analytics for payments data.

Your emphasis on Excel-led reconciliation and stakeholder reporting aligns with my background. I built and used an in-house Excel reconciliation system in regulated financial operations, supported multi-currency exception review, and delivered recurring KPI packs for management decisions. Your need for Python-based analysis matches my portfolio work on GitHub.

My portfolio includes BakeOps Intelligence, which shows KPI dashboards, BI-ready exports, and a rank-inversion insight where revenue rank and waste-adjusted margin rank diverge. CareerFunnel Tracker adds structured funnel metrics, data-quality warnings, manual assisted intake, and 249 automated tests with evidence-backed documentation. I do not claim production users, live SaaS, or external AI.

I would welcome the opportunity to discuss this Data Analyst role. My CV (**Aminul_Islam_Data_Analyst_CV**) is attached and I am available to start after notice.

Yours sincerely,

Aminul Islam

## Example Built Cover Letter -- FinTech / Payments Analyst

Dear Hiring Manager,

I am applying for the Payments Analytics Analyst position at Example FinTech Ltd, via the company careers site. I am a UK-based analyst with 15 years of experience in money transfer and FX operations, AML-aware customer verification, multi-currency reconciliation, and high-volume daily cash handling (including around £30,000 daily cash volume in prior operational context). I hold UK work authorisation and do not require sponsorship. Example FinTech's focus on payments control and reporting is a strong match for my domain background.

Your requirement for reconciliation discipline and exception review fits my Acaelus-era operational experience. I am used to explaining discrepancies, supporting control workflows, and turning operational activity into structured reporting inputs rather than informal spreadsheets alone.

Your need for analytics evidence is supported by my portfolio. TradeIntel 360 is a portfolio project calculating trading KPIs from CSV uploads with configurable reporting and transparent Sharpe methodology documentation. DataBridge Market API shows market-data ingestion, run logging, normalised storage, and inspection workflow at portfolio scope. I avoid claiming institutional trading systems, live brokerage integration, production pipelines, or cloud platform delivery.

I would welcome a conversation about how my payments operations experience and portfolio work could support your team. My CV (**Aminul_Islam_Data_Analyst_CV**) is attached.

Yours sincerely,

Aminul Islam

## Final Claim-Safety Checklist Before Sending

- [ ] Every must-have in the letter maps to "Evidence I can prove" in intake.
- [ ] I used only one role variant (not mixed DA + FinTech + BI letters).
- [ ] I used at most two portfolio projects.
- [ ] I did not claim Power BI or Tableau artefacts unless verified.
- [ ] I did not claim production SQL project delivery unless evidenced.
- [ ] I did not claim external AI, OpenAI, or Claude.
- [ ] I did not claim scraping, auto-apply, Gmail, or Calendar.
- [ ] I did not claim live SaaS or production users.
- [ ] I did not claim cloud warehouse, dbt, Airflow, Spark, or Kafka unless implemented.
- [ ] I did not claim V7-V10 API work as implemented.
- [ ] Currency uses £30,000 only where needed; no corrupted currency symbols, non-UK currency text formatting, or incorrect currency formatting.
- [ ] Letter is 250-330 words, under one page, CV filename is **Aminul_Islam_Data_Analyst_CV**.

## Final Decision

Application Pack Step 3 approves this builder for manual job-specific cover letters aligned with **Aminul_Islam_Data_Analyst_CV** and Step 1/2 packs.

Recommended next step:

Application Pack Step 4 -- Recruiter Outreach Message Variants

Do not recommend LinkedIn profile update until after Sprint 30.

Do not recommend V7-V10 API implementation unless explicitly approved later.

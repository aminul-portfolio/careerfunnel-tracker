# CareerFunnel Tracker - Analytics Lineage

## Purpose

This document explains how CareerFunnel Tracker transforms raw job-search records into business-ready analytics.

It is designed to make the project understandable for recruiters, reviewers, and future maintainers. The goal is to show clear Analytics Engineering thinking: source data, transformation logic, metric governance, and trusted reporting outputs.

CareerFunnel Tracker uses a simple Bronze -> Silver -> Gold analytics model:

```text
Bronze = raw user-entered records
Silver = cleaned, normalised, grouped, and classified logic
Gold = business-ready metrics, reports, dashboards, and recommendations
```

The system is intentionally realistic for a solo-developer portfolio project. It avoids fake AI claims, fake users, fake customers, and unnecessary enterprise architecture.

---

# Analytics Engineering Principles

CareerFunnel Tracker follows these principles:

- Raw records should remain traceable.
- Business metrics should be explainable.
- Missing data should be visible, not hidden.
- Low sample sizes should be treated carefully.
- Recommendations should be rule-based and evidence-based.
- Dashboards should show how conclusions were reached.
- Portfolio claims should be supported by code, tests, screenshots, and documentation.

---

# High-Level Data Flow

```text
User enters job-search activity
        ↓
Bronze Layer
Raw Django model records
        ↓
Silver Layer
Normalisation, grouping, classification, and quality checks
        ↓
Gold Layer
Metrics services, dashboard outputs, recommendations, and evidence screenshots
```

---

# Bronze Layer - Raw Records

The Bronze layer contains the raw records entered into the system.

These records are not assumed to be perfect. They may contain blank fields, generic values, missing follow-up dates, thin job descriptions, or incomplete CV-version tracking.

## Bronze Models

| Model | Role in Analytics |
|---|---|
| `JobApplication` | Main source of application funnel data, sources, statuses, CV versions, job descriptions, required skills, follow-up dates, and outcomes |
| `DailyLog` | Captures daily target and actual application activity |
| `WeeklyReview` | Captures weekly review/diagnosis information |
| `Note` | Captures supporting notes and decisions where relevant |

---

## JobApplication as Primary Bronze Source

`JobApplication` is the most important analytics source in the project.

### Key Fields

| Field | Analytics Use |
|---|---|
| `user` | Scopes records to the authenticated user |
| `company_name` | Identifies the employer or organisation |
| `job_title` | Supports role analysis and seniority-risk checks |
| `status` | Drives funnel, response, interview, offer, rejection, and auto-rejection metrics |
| `source` | Drives Source ROI and source-level rejection analysis |
| `cv_version` | Drives CV Version Performance and CV-level rejection analysis |
| `job_description` | Supports role evidence, seniority-risk detection, and data quality checks |
| `required_skills` | Supports role evidence, skill matching, seniority-risk detection, and data quality checks |
| `follow_up_date` | Supports operational follow-up quality |
| `date_applied` | Supports sorting and timeline-based review |

### Bronze Layer Limitation

Bronze data depends on what the user enters. If fields are blank or incomplete, the system does not hide that problem. Instead, later layers expose missing data through quality checks.

---

## DailyLog as Bronze Source

`DailyLog` records planned versus actual job-search activity.

### Key Fields

| Field | Analytics Use |
|---|---|
| `target_applications` | Planned daily activity |
| `actual_applications` | Actual submitted applications |
| `date` | Timeline of activity |

### Downstream Metrics

- Daily Target Total
- Daily Actual Total
- Daily Variance Total
- Daily Target Hit Rate

---

## WeeklyReview as Bronze Source

`WeeklyReview` supports weekly diagnosis and reflection.

### Analytics Use

- Tracks review outcomes.
- Supports funnel diagnosis.
- Helps connect activity with weekly improvement decisions.

---

# Silver Layer - Normalised and Classified Logic

The Silver layer transforms raw records into cleaner, more consistent analytical logic.

This layer does not create fake data. It applies transparent rules so the Gold layer can produce trusted outputs.

---

## Silver Transformation 1 - Status Grouping

Raw `JobApplication.status` values are grouped into analytical categories.

### Response Statuses

```text
acknowledged
screening_call
technical_screen
interview
offer
rejected
auto_rejected
```

### Interview Statuses

```text
interview
offer
```

### Rejection Statuses

```text
rejected
auto_rejected
```

### Auto-Rejection Status

```text
auto_rejected
```

### Active Pipeline Statuses

Used for follow-up-date quality checks:

```text
submitted
acknowledged
screening_call
technical_screen
interview
```

### Why This Matters

Status grouping turns operational statuses into business metrics such as:

- Response Rate
- Interview Rate
- Offer Rate
- Rejection Rate
- Auto-Rejection Rate
- Missing Follow-Up Date Count

---

## Silver Transformation 2 - Source Normalisation

Raw `source` values are normalised for reporting.

### Rule

```text
Blank or missing source -> Other
```

### Precise Source Requirement

For data quality and analytics readiness, a source is considered precise only if it is not blank and not `Other`.

### Why This Matters

Without source normalisation, Source ROI and source-level rejection patterns become unreliable.

---

## Silver Transformation 3 - CV Version Normalisation

Raw `cv_version` values are normalised for reporting.

### Rule

```text
Blank or missing CV version -> Unspecified
```

### Why This Matters

CV Version Performance depends on knowing which CV version was used for each application.

When CV version is missing, the platform does not ignore the record. It groups it under `Unspecified` and exposes the missing data in quality checks.

---

## Silver Transformation 4 - Role Evidence Checks

The platform checks whether each application has enough role evidence for reliable analysis.

### Job Description Evidence

```text
Valid if job_description has at least 40 characters after stripping whitespace
```

### Required Skills Evidence

```text
Valid if required_skills has at least 10 characters after stripping whitespace
```

### Why This Matters

Role evidence supports:

- Seniority-risk detection
- Application Quality Report
- Data Quality Report
- Future role-fit analysis
- Rejection Pattern Analysis

---

## Silver Transformation 5 - Seniority and Stretch-Role Signal Detection

The system checks `job_title`, `required_skills`, and `job_description` for seniority or stretch-role signals.

### Signals

```text
senior
lead
principal
manager
head of
3+ years
5+ years
minimum 3
minimum 5
```

### Used By

- Rejection Pattern Analysis
- Application Quality Report

### Why This Matters

This helps identify whether the user may be applying to roles that are above the intended target level.

### Limitation

This is keyword-based and directional. It does not prove that a role is unsuitable.

---

## Silver Transformation 6 - Application Quality Issue Detection

The system identifies incomplete or weak application records.

### Issue Types

```text
Missing CV version
Missing precise source
Missing or thin job description
Missing required skills
Missing follow-up date
Seniority or stretch-role risk
```

### Why This Matters

This layer turns raw records into actionable quality intelligence.

It answers:

```text
Which applications need better evidence or follow-up?
```

---

## Silver Transformation 7 - Data Quality Check Logic

The system creates a data-quality summary across all applications.

### Checks

- Precise application source
- Specific source channel, not generic `Other`
- CV version recorded
- Job description evidence
- Required skills captured
- Follow-up date for active pipeline applications

### Severity Rules

```text
success = issue_count == 0
warning = issue_count > 0 and completion_rate >= 70
danger = completion_rate < 70
```

### Why This Matters

This gives the platform an analytics governance layer instead of only dashboard visuals.

---

# Gold Layer - Business-Ready Analytics Outputs

The Gold layer contains business-facing metrics, reports, tables, recommendations, screenshots, and documentation.

These outputs are ready for users, reviewers, and portfolio presentation.

---

## Gold Output 1 - Funnel Metrics

### Business Questions

- How many applications were submitted?
- How many received a response?
- How many reached interview stage?
- How many converted to offers?

### Core Metrics

- Total Applications
- Response Count
- Response Rate
- Interview Count
- Interview Rate
- Offer Count
- Offer Rate

### Service Layer

```text
build_funnel_metrics(user)
```

### UI Surface

```text
Metrics page
Dashboard page
```

---

## Gold Output 2 - Funnel Diagnosis

### Business Question

Where is the job-search funnel leaking?

### Output

A diagnosis panel with:

- diagnosis title
- explanation
- recommended action
- severity class

### Service Layer

```text
diagnose_funnel(metrics)
```

### Why It Matters

This turns raw metrics into decision-support language.

---

## Gold Output 3 - Source ROI

### Business Question

Which job sources are producing stronger outcomes?

### Output

A source-level performance table with:

- Source
- Applications
- Responses
- Response Rate
- Interviews
- Interview Rate
- Offers
- Offer Rate

### Service Layer

```text
build_source_roi(user)
```

### UI Surface

```text
Metrics page
```

### Portfolio Value

Shows grouped channel performance and BI-style source attribution.

---

## Gold Output 4 - CV Version Performance

### Business Question

Which CV versions are producing stronger or weaker outcomes?

### Output

A CV-version table with:

- CV Version
- Applications
- Responses
- Response Rate
- Interviews
- Interview Rate
- Offers
- Offer Rate
- Rejections
- Rejection Rate

### Service Layer

```text
build_cv_version_performance(user)
```

### UI Surface

```text
Metrics page
```

### Governance Note

This is performance tracking, not scientific A/B testing.

---

## Gold Output 5 - Rejection Pattern Analysis

### Business Questions

- How many applications are rejected?
- How many are auto-rejected?
- Which sources are producing rejections?
- Which CV versions are linked to rejections?
- Are senior/stretch roles contributing to rejection patterns?

### Output

A rejection analysis section with:

- Total Applications
- Total Rejections
- Auto Rejections
- Rejection Rate
- Auto-Rejection Rate
- Seniority Risk Count
- Rejections by Source
- Rejections by CV Version
- Recommended Actions
- Low-sample-size warning where relevant

### Service Layer

```text
build_rejection_pattern_report(user)
```

### UI Surface

```text
Metrics page
```

---

## Gold Output 6 - Application Quality Report

### Business Questions

- Which applications are incomplete?
- Which applications need better evidence?
- Which applications need follow-up?
- Which applications may be too senior or stretch-level?

### Output

A report with:

- Applications With Issues
- Quality Issue Rate
- Missing CV Version Count
- Missing Source Count
- Missing Job Description Count
- Missing Required Skills Count
- Missing Follow-Up Date Count
- Seniority Risk Count
- Applications Needing Action
- Recommended Actions

### Service Layer

```text
build_application_quality_report(user)
```

### UI Surface

```text
Metrics page
```

---

## Gold Output 7 - Data Quality Report

### Business Questions

- Is the dataset complete enough for reliable analytics?
- How many records are analytics-ready?
- Which fields most weaken reporting trust?
- What should be cleaned first?

### Output

A report with:

- Total Applications
- Analytics-Ready Applications
- Analytics-Ready Rate
- Data Quality Score
- Missing Source Count
- Generic Source Count
- Missing CV Version Count
- Missing Job Description Count
- Missing Required Skills Count
- Missing Follow-Up Date Count
- Data Quality Checks
- Recommended Cleanup Actions

### Service Layer

```text
build_data_quality_report(user)
```

### UI Surface

```text
Metrics page
```

### Analytics-Ready Criteria

An application is analytics-ready when:

```text
source is precise and not blank/Other
cv_version is present
job_description has at least 40 characters after stripping
required_skills has at least 10 characters after stripping
```

Follow-up date is not included in analytics-ready status because it is operational rather than core analytical evidence.

---

# Service Layer Lineage

This section maps business outputs to the service functions that generate them.

| Gold Output | Service Function | Main Source Model |
|---|---|---|
| Funnel Metrics | `build_funnel_metrics(user)` | `JobApplication`, `DailyLog`, `WeeklyReview` |
| Funnel Diagnosis | `diagnose_funnel(metrics)` | `FunnelMetrics` |
| Funnel Stage Rows | `build_funnel_stage_rows(metrics)` | `FunnelMetrics` |
| Source ROI | `build_source_roi(user)` | `JobApplication` |
| CV Version Performance | `build_cv_version_performance(user)` | `JobApplication` |
| Rejection Pattern Analysis | `build_rejection_pattern_report(user)` | `JobApplication` |
| Application Quality Report | `build_application_quality_report(user)` | `JobApplication` |
| Data Quality Report | `build_data_quality_report(user)` | `JobApplication` |

---

# UI Lineage

## Dashboard Page

The dashboard focuses on quick operational visibility.

It shows:

- KPI cards
- funnel summary
- recent applications
- recent daily logs
- recent weekly reviews
- trust notes

## Metrics Page

The metrics page is the main Gold-layer analytics surface.

It shows:

- Funnel Metrics
- Daily Discipline
- Source ROI
- CV Version Performance
- Rejection Pattern Analysis
- Application Quality
- Data Quality

---

# Documentation Lineage

The project includes documentation to make analytics logic transparent.

| Document | Purpose |
|---|---|
| `docs/analytics/metric_definitions.md` | Defines each metric, calculation, source field, business question, and limitation |
| `docs/analytics/analytics_lineage.md` | Explains Bronze -> Silver -> Gold data flow and transformation logic |
| `docs/evidence/screenshots/` | Stores screenshot evidence for completed sprints |

---

# Evidence Lineage

Screenshots are used to prove that implemented features exist in the UI.

| Sprint | Evidence File | Purpose |
|---|---|---|
| Sprint 1B | `docs/evidence/screenshots/sprint-1b-dashboard-trust-surfaces.png` | Dashboard trust surfaces |
| Sprint 2A | `docs/evidence/screenshots/sprint-2a-metrics-source-roi-cv-performance.png` | Source ROI and CV Version Performance |
| Sprint 2B | `docs/evidence/screenshots/sprint-2b-rejection-pattern-analysis.png` | Rejection Pattern Analysis |
| Sprint 3 | `docs/evidence/screenshots/sprint-3-application-quality-report.png` | Application Quality Report |
| Sprint 4 | `docs/evidence/screenshots/sprint-4-data-quality-analytics-governance.png` | Data Quality and Analytics Governance |

---

# Testing Lineage

Each major analytics feature is backed by tests.

## Current Test Coverage Themes

- Safe percentage calculations
- Funnel metrics
- Source ROI
- CV Version Performance
- Rejection Pattern Analysis
- Application Quality Report
- Data Quality Report
- Low-sample-size warnings
- Missing-field detection
- Normalisation rules
- Severity rules
- Recommendation output

## Why This Matters

Tests prove that the analytics logic is stable and repeatable.

This is important because the project is not only a UI demo. It is a service-layer analytics product.

---

# Known Lineage Limitations

The current lineage is intentionally realistic and scoped for a solo-developer portfolio project.

Known limitations:

- The platform uses the current status of an application, not full status history.
- Stage movement history is not tracked yet.
- Rejection reasons are not independently verified.
- Seniority-risk detection is keyword-based.
- CV Version Performance is not scientific A/B testing.
- Source ROI is channel outcome tracking, not financial ROI.
- No Gmail integration is active.
- No live AI or LLM features are active.
- No Celery/Redis background job architecture is active.
- No enterprise data warehouse is used.

These limitations are documented rather than hidden.

---

# Future Lineage Opportunities

Future improvements could include:

- `StageEvent` model for full status history
- status transition analysis
- time-to-response analysis
- time-to-interview analysis
- export contracts for BI tools
- CSV export lineage
- optional email response classification
- optional AI-assisted explanation layer

These should be added only when the core platform remains stable and the use case justifies the complexity.

---

# Portfolio Interpretation

CareerFunnel Tracker demonstrates Analytics Engineering thinking because it includes:

- raw operational records
- cleaned and normalised logic
- governed KPI definitions
- service-layer metrics
- data-quality checks
- transparent recommendations
- dashboard-ready outputs
- screenshot evidence
- tests
- documentation

This makes the project stronger than a basic Django CRUD app or generic job tracker.

It shows the ability to build a realistic data product where business users can understand:

```text
What data was captured
How it was transformed
Which metrics were calculated
Why the metrics matter
What limitations exist
What action should be taken next
```

---

# Summary

CareerFunnel Tracker follows this analytics path:

```text
Bronze:
Raw job applications, daily logs, weekly reviews, and notes

Silver:
Normalised sources, CV versions, status groups, quality checks, seniority-risk rules, and completeness checks

Gold:
Funnel metrics, Source ROI, CV Version Performance, Rejection Pattern Analysis, Application Quality Report, Data Quality Report, recommendations, screenshots, and documentation
```

The result is a recruiter-ready analytics product that demonstrates Django development, BI thinking, analytics engineering discipline, and evidence-based decision support.

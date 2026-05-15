# CareerFunnel Tracker - Metric Definitions

## Purpose

This document defines the main analytics metrics used in CareerFunnel Tracker.

The goal is to make the platform transparent, reviewer-friendly, and suitable for a Data Analyst / BI Analyst / Analytics Engineer portfolio review.

The metrics are intentionally rule-based and evidence-based. They are calculated from real `JobApplication`, `DailyLog`, and `WeeklyReview` records. No fake users, fake customers, fake AI claims, or hardcoded analytics values are used.

---

## Metric Governance Principles

CareerFunnel Tracker follows these principles:

- Metrics must be explainable.
- Metrics must be calculated from stored application records.
- Missing or thin data should be visible, not hidden.
- Low sample sizes should be treated as directional only.
- Rule-based recommendations should support decisions, not pretend to be artificial intelligence.
- Portfolio claims should remain realistic and evidence-based.

---

## Fit Review and Job Posting Scoring Consistency

Fit Review (Application Detail), Application Smart Review, and Job Posting Analyzer use the same canonical role-fit classification lists from:

```text
apps/job_intelligence/constants.py
```

Shared inputs include target titles, location signals, skill keywords, deal-breakers, and learning-target terms. Job Posting Analyzer and Application Smart Review therefore apply the same rule-based classification inputs, which reduces score inconsistency between pre-application analysis and saved-application review.

Scoring remains deterministic and local. No live AI or external API integration is used for these features.

---

## Source Data

| Model | Purpose |
|---|---|
| `JobApplication` | Core application records, statuses, sources, CV versions, job descriptions, required skills, follow-up dates, and outcomes |
| `DailyLog` | Daily application targets and actual application activity |
| `WeeklyReview` | Weekly diagnosis and reflection data |
| `Note` | Supporting notes and decisions where relevant |

---

# Core Funnel Metrics

## 1. Total Applications

**Business question:** How many job applications have been logged?

**Calculation:**

```text
Total Applications = count(JobApplication records for the user)
```

**Source fields:** `JobApplication.id`, `JobApplication.user`

**Why it matters:** This is the base denominator for most funnel and conversion metrics.

**Known limitation:** A higher total does not automatically mean better job-search quality. Application quality, fit, and follow-up discipline must also be considered.

---

## 2. Response Count

**Business question:** How many applications received any company response?

**Response statuses:**

```text
acknowledged
screening_call
technical_screen
interview
offer
rejected
auto_rejected
```

**Calculation:**

```text
Response Count = count(JobApplication where status is in response statuses)
```

**Source field:** `JobApplication.status`

**Why it matters:** This shows whether applications are getting any signal back from employers.

**Known limitation:** A rejection is counted as a response because it confirms the application was processed, but it is not a positive outcome.

---

## 3. Response Rate

**Business question:** What percentage of applications received any company response?

**Calculation:**

```text
Response Rate = (Response Count / Total Applications) * 100
```

**Safe calculation rule:**

```text
If Total Applications = 0, Response Rate = 0.0
```

**Why it matters:** A low response rate may indicate weak targeting, weak CV alignment, poor application quality, or insufficient evidence in applications.

**Known limitation:** Response rates can be unstable when the application count is low.

---

## 4. Interview Count

**Business question:** How many applications reached interview-level progress?

**Interview statuses:**

```text
interview
offer
```

**Calculation:**

```text
Interview Count = count(JobApplication where status is interview or offer)
```

**Why it matters:** This shows whether the CV, screening, and initial application quality are strong enough to move into serious selection stages.

**Known limitation:** The current metric uses the latest application status. It does not yet track full status history.

---

## 5. Interview Rate

**Business question:** What percentage of applications reached interview-level progress?

**Calculation:**

```text
Interview Rate = (Interview Count / Total Applications) * 100
```

**Safe calculation rule:**

```text
If Total Applications = 0, Interview Rate = 0.0
```

**Why it matters:** This is one of the strongest indicators of application-market fit.

**Known limitation:** If an application progressed through an interview and later moved to another status, the current model may not preserve the historical stage unless status history is added later.

---

## 6. Offer Count

**Business question:** How many applications converted to offers?

**Calculation:**

```text
Offer Count = count(JobApplication where status = offer)
```

**Why it matters:** This is the strongest outcome metric in the job-search funnel.

**Known limitation:** A low or zero offer count is expected early in a job-search dataset. It should not be overinterpreted with small sample sizes.

---

## 7. Offer Rate

**Business question:** What percentage of applications converted to offers?

**Calculation:**

```text
Offer Rate = (Offer Count / Total Applications) * 100
```

**Safe calculation rule:**

```text
If Total Applications = 0, Offer Rate = 0.0
```

**Why it matters:** Offer rate is the final conversion metric for the job-search funnel.

**Known limitation:** Offer rate usually requires a larger dataset and longer timeline to become meaningful.

---

# Daily Discipline Metrics

## 8. Daily Target Total

**Business question:** How many applications were planned across logged daily activity?

**Calculation:**

```text
Daily Target Total = sum(DailyLog.target_applications)
```

**Why it matters:** This measures planned job-search activity.

**Known limitation:** Targets measure intent, not actual output.

---

## 9. Daily Actual Total

**Business question:** How many applications were actually submitted across logged daily activity?

**Calculation:**

```text
Daily Actual Total = sum(DailyLog.actual_applications)
```

**Why it matters:** This measures actual job-search execution.

**Known limitation:** Actual application count does not measure application quality.

---

## 10. Daily Variance Total

**Business question:** Was actual activity above or below target?

**Calculation:**

```text
Daily Variance Total = Daily Actual Total - Daily Target Total
```

**Why it matters:** This shows whether the user is consistently meeting job-search activity targets.

**Known limitation:** A negative variance is not always bad if the user focused on fewer but higher-quality applications.

---

## 11. Daily Target Hit Rate

**Business question:** What percentage of planned application volume was achieved?

**Calculation:**

```text
Daily Target Hit Rate = (Daily Actual Total / Daily Target Total) * 100
```

**Safe calculation rule:**

```text
If Daily Target Total = 0, Daily Target Hit Rate = 0.0
```

**Why it matters:** This is an operational discipline metric.

**Known limitation:** This metric should be interpreted alongside application quality and outcomes.

---

# Weekly Trend Metrics

## 12. Weekly Trend (per week)

**Business question:** How are application volume and response rate changing across recent weeks?

**Calculation:**

Applications are grouped by Monday-starting week of `date_applied`.

Per week:

```text
Applications = count(JobApplication where date_applied falls in that week)
Responses = count(JobApplication in that week where status is in response statuses)
Response Rate = safe_percentage(Responses, Applications)
```

**Response statuses used:**

```text
acknowledged
screening_call
technical_screen
interview
offer
rejected
auto_rejected
```

These match the existing `_RESPONSE_STATUSES` set used elsewhere in funnel metrics.

**Week boundary rule:**

```text
week_start = date_applied - timedelta(days=date_applied.weekday())
```

Python `weekday()` treats Monday as `0`, so each week bucket starts on Monday.

**Lookback window:**

```text
Default = 10 Monday-starting weeks
Includes the current week
Includes weeks with zero applications
Applications outside the window are excluded
```

**Timezone note:**

Week boundaries use `timezone.localdate()` for “today” and the current-week end date when building the lookback window.

**Source fields:**

```text
JobApplication.date_applied
JobApplication.status
```

**Service function:**

```text
build_weekly_trend(user, weeks=10)
```

**UI behaviour:**

- Funnel Metrics shows a table only (Week Starting, Applications, Responses, Response Rate).
- No chart is included in Sprint 14.
- A not-enough-data message appears when fewer than two weeks contain applications.

**Why it matters:** This gives a simple week-over-week view of whether application activity and employer responses are improving, flat, or declining.

**Known limitation:** The trend is based on application date (`date_applied`), not response date. A response received in a later week still counts in the week the application was submitted.

---

# Source ROI Metrics

## 13. Source ROI

**Business question:** Which application sources are producing better outcomes?

Applications are grouped by `source`.

**Calculation per source:**

```text
Total Applications = count(applications from source)
Responses = count(response statuses from source)
Interviews = count(interview statuses from source)
Offers = count(offer statuses from source)
Response Rate = Responses / Total Applications * 100
Interview Rate = Interviews / Total Applications * 100
Offer Rate = Offers / Total Applications * 100
```

**Source fields:** `JobApplication.source`, `JobApplication.status`

**Normalisation rule:**

```text
Blank or missing source values are treated as Other
```

**Why it matters:** This helps compare channels such as LinkedIn, Reed.co.uk, Indeed, company websites, recruiters, and referrals.

**Known limitation:** This is not financial ROI. It is outcome performance by source. The term "ROI" means application-channel return in job-search outcomes.

---

# CV Version Performance Metrics

## 14. CV Version Performance

**Business question:** Which CV versions are producing stronger job-search outcomes?

Applications are grouped by `cv_version`.

**Calculation per CV version:**

```text
Total Applications = count(applications using CV version)
Responses = count(response statuses)
Interviews = count(interview statuses)
Offers = count(offer statuses)
Rejections = count(rejected + auto_rejected)
Response Rate = Responses / Total Applications * 100
Interview Rate = Interviews / Total Applications * 100
Offer Rate = Offers / Total Applications * 100
Rejection Rate = Rejections / Total Applications * 100
```

**Source fields:** `JobApplication.cv_version`, `JobApplication.status`

**Normalisation rule:**

```text
Blank or missing CV versions are treated as Unspecified
```

**Why it matters:** This helps identify whether a specific CV positioning may be linked to stronger or weaker outcomes.

**Known limitation:** This is performance tracking, not scientific A/B testing. Results are directional unless sample sizes are large and role types are comparable.

---

# Rejection Pattern Metrics

## 15. Total Rejections

**Business question:** How many applications ended in rejection?

**Rejection statuses:**

```text
rejected
auto_rejected
```

**Calculation:**

```text
Total Rejections = count(JobApplication where status is rejected or auto_rejected)
```

**Why it matters:** This identifies negative outcomes that may require targeting, CV, or application-quality improvements.

**Known limitation:** Rejection reasons are not always known. The platform identifies patterns, not guaranteed causes.

---

## 16. Auto-Rejections

**Business question:** How many applications were rejected before meaningful human engagement?

**Calculation:**

```text
Auto-Rejections = count(JobApplication where status = auto_rejected)
```

**Why it matters:** High auto-rejection volume may indicate poor keyword alignment, weak CV targeting, seniority mismatch, or unsuitable roles.

**Known limitation:** The system cannot prove whether an ATS caused the rejection unless the user records that evidence.

---

## 17. Rejection Rate

**Business question:** What percentage of applications ended in rejection?

**Calculation:**

```text
Rejection Rate = (Total Rejections / Total Applications) * 100
```

**Safe calculation rule:**

```text
If Total Applications = 0, Rejection Rate = 0.0
```

**Why it matters:** This helps monitor whether job-search targeting is improving or weakening over time.

**Known limitation:** Rejection rate is normal in job searching and should not be viewed alone. It should be interpreted with response rate, interview rate, and role fit.

---

## 18. Auto-Rejection Rate

**Business question:** What percentage of applications were auto-rejected?

**Calculation:**

```text
Auto-Rejection Rate = (Auto-Rejections / Total Applications) * 100
```

**Safe calculation rule:**

```text
If Total Applications = 0, Auto-Rejection Rate = 0.0
```

**Why it matters:** This can highlight weak CV-role matching or unsuitable application channels.

**Known limitation:** The system uses the user-selected status. It does not independently verify whether a rejection was automated.

---

## 19. Rejections by Source

**Business question:** Which sources are producing the most rejections?

**Calculation per source:**

```text
Rejection Count = count(rejected + auto_rejected from source)
Total Applications = count(applications from source)
Rejection Rate = Rejection Count / Total Applications * 100
```

**Why it matters:** This helps detect weak channels or poor-fit platforms.

**Known limitation:** A high rejection count may simply reflect higher application volume from that source.

---

## 20. Rejections by CV Version

**Business question:** Which CV versions are linked to more rejections?

**Calculation per CV version:**

```text
Rejection Count = count(rejected + auto_rejected using CV version)
Total Applications = count(applications using CV version)
Rejection Rate = Rejection Count / Total Applications * 100
```

**Why it matters:** This helps identify CV versions that may need improvement.

**Known limitation:** CV versions may be used for different role types, so comparisons should be interpreted carefully.

---

## 21. Seniority Risk Count

**Business question:** How many applications may be too senior or stretch-level?

**Signals checked:**

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

**Calculation:**

```text
Seniority Risk Count = count(applications where job_title, required_skills, or job_description contains seniority signals)
```

**Why it matters:** This helps detect whether the user is applying to roles above the intended target level.

**Known limitation:** Keyword detection is directional. Some roles may include words like "manager" in a non-senior context.

---

# Application Quality Metrics

## 22. Applications With Issues

**Business question:** How many applications have incomplete or weak evidence?

An application has issues if it triggers one or more quality flags:

```text
missing CV version
missing precise source
missing or thin job description
missing required skills
missing follow-up date
seniority or stretch-role risk
```

**Why it matters:** This shows whether records are strong enough to support reliable analytics and follow-up decisions.

**Known limitation:** A record can be analytically incomplete even if the application itself was high quality.

---

## 23. Quality Issue Rate

**Business question:** What percentage of applications have at least one quality issue?

**Calculation:**

```text
Quality Issue Rate = (Applications With Issues / Total Applications) * 100
```

**Safe calculation rule:**

```text
If Total Applications = 0, Quality Issue Rate = 0.0
```

**Why it matters:** This measures the overall completeness and usability of application records.

**Known limitation:** This metric reflects record quality, not necessarily application quality in the real world.

---

## 24. Missing CV Version Count

**Business question:** How many applications do not identify which CV version was used?

**Calculation:**

```text
Missing CV Version Count = count(applications where cv_version is blank, null, or whitespace-only)
```

**Why it matters:** Without CV versions, CV performance analysis becomes less reliable.

---

## 25. Missing Source Count

**Business question:** How many applications do not have a precise source?

**Calculation:**

```text
Missing Source Count = count(applications where source is blank, null, whitespace-only, or Other)
```

**Why it matters:** Without precise source tracking, Source ROI cannot be trusted.

---

## 26. Missing Job Description Count

**Business question:** How many applications lack enough job-description evidence?

**Calculation:**

```text
Missing Job Description Count = count(applications where job_description is blank, null, whitespace-only, or fewer than 40 characters)
```

**Why it matters:** Job descriptions are needed for role-fit, seniority-risk, and rejection-pattern analysis.

---

## 27. Missing Required Skills Count

**Business question:** How many applications lack enough required-skills evidence?

**Calculation:**

```text
Missing Required Skills Count = count(applications where required_skills is blank, null, whitespace-only, or fewer than 10 characters)
```

**Why it matters:** Required skills support better CV matching and application-quality analysis.

---

## 28. Missing Follow-Up Date Count

**Business question:** How many active applications need a follow-up date?

**Active statuses:**

```text
submitted
acknowledged
screening_call
technical_screen
interview
```

**Calculation:**

```text
Missing Follow-Up Date Count = count(active applications where follow_up_date is blank or null)
```

**Why it matters:** This supports operational discipline and prevents active applications from being forgotten.

**Known limitation:** Follow-up date is operational. It does not block analytics-ready status.

---

# Data Quality Metrics

## 29. Analytics-Ready Applications

**Business question:** How many application records are complete enough for reliable analytics?

An application is analytics-ready if:

```text
source is precise and not blank/Other
cv_version is present
job_description has at least 40 characters after stripping
required_skills has at least 10 characters after stripping
```

**Calculation:**

```text
Analytics-Ready Applications = count(applications meeting all analytics-ready criteria)
```

**Why it matters:** This is a governance metric showing whether the dataset is strong enough for trustworthy reporting.

**Known limitation:** Follow-up date is excluded because it is an operational field, not a core analytics-evidence field.

---

## 30. Analytics-Ready Rate

**Business question:** What percentage of application records are complete enough for reliable analytics?

**Calculation:**

```text
Analytics-Ready Rate = (Analytics-Ready Applications / Total Applications) * 100
```

**Safe calculation rule:**

```text
If Total Applications = 0, Analytics-Ready Rate = 0.0
```

**Why it matters:** This directly measures data readiness for analytics.

---

## 31. Data Quality Score

**Business question:** What is the overall data-quality score for analytics readiness?

**Calculation:**

```text
Data Quality Score = Analytics-Ready Rate
```

**Why it matters:** This creates a simple top-level score for how trustworthy the dataset is.

**Known limitation:** This score intentionally focuses on field completeness. It does not prove that the user applied to the right roles.

---

## 32. Data Quality Check Completion Rate

**Business question:** How complete is each individual data-quality check?

**Calculation:**

```text
Completion Rate = ((Total Applications - Issue Count) / Total Applications) * 100
```

**Safe calculation rule:**

```text
If Total Applications = 0, Completion Rate = 0.0
```

**Severity rules:**

```text
success = issue_count == 0
warning = issue_count > 0 and completion_rate >= 70
danger = completion_rate < 70
```

**Why it matters:** This gives a clear, explainable status for each data-quality dimension.

---

# Recommendation Logic

## Principle

Recommendations are rule-based and evidence-based. They do not use AI or LLM reasoning.

| Signal | Recommendation |
|---|---|
| Missing source or generic source exists | Replace blank or generic sources with precise channels |
| Missing CV version exists | Assign CV versions so CV performance can be measured |
| Missing job description or skills exists | Capture role evidence for fit and rejection analysis |
| Missing follow-up dates exist | Add follow-up dates for active applications |
| Data quality score is strong | Continue consistent logging |

---

# Low Sample Size Guidance

Some metrics should be treated as directional when the dataset is small.

CareerFunnel Tracker uses this warning where relevant:

```text
Not enough applications yet for strong pattern conclusions. Treat this as directional only.
```

This is especially important for:

```text
CV Version Performance
Rejection Pattern Analysis
Source ROI
Offer Rate
Weekly Trend
```

---

# Known Limitations of the Current Metrics System

The current version is intentionally realistic for a solo-developer portfolio project.

Known limitations:

- Status history is not tracked yet.
- The project uses current status, not full stage movement history.
- Rejection reasons are not independently verified.
- Seniority risk uses keyword-based detection.
- CV Version Performance is not scientific A/B testing.
- Source ROI is channel-performance tracking, not financial ROI.
- No live AI or LLM features are used.
- Fit Review and Job Posting Analyzer scoring share constants but remain rule-based, not live AI/API integrations.
- Job Posting Analyzer pre-fills the Add Application form only; it does not save or submit applications automatically.
- No Gmail or inbox integration is active.
- Analytics outputs depend on the completeness of user-entered records.
- Weekly Trend uses application date, not response date.

---

# Portfolio Value

These metrics demonstrate:

- Django service-layer design
- Analytics engineering thinking
- KPI governance
- Data quality logic
- Evidence-based recommendations
- BI-style reporting
- Transparent business logic
- Recruiter-ready documentation

This makes CareerFunnel Tracker stronger for:

- Data Analyst roles
- BI Analyst roles
- Reporting Analyst roles
- Analytics Engineer roles
- Junior Data Engineer roles
- FinTech analytics roles


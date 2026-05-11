# CareerFunnel Tracker

CareerFunnel Tracker is a Django-based job-search intelligence platform. It tracks applications, daily activity, weekly reviews, funnel metrics, follow-ups, interview preparation, strategic notes, and exportable evidence.

It is not just an application tracker. It is a diagnostic and decision-support platform that helps identify where a job-search funnel is leaking and what action should happen next.

## Key Features

- Dashboard overview with live KPI cards
- Applications tracker with lifecycle stage, status, CV version, role fit, source, and response date
- Smart Application Review with job fit score, readiness score, CV recommendation, project recommendation, and next action
- Follow-Up Due system with follow-up date, status, and “mark sent” workflow
- Interview Prep module with preparation checklist, topics, project walkthroughs, and readiness score
- Daily target vs actual activity logging
- Weekly review and diagnostic reflection workflow
- Funnel metrics for response, screening, interview, and offer rates
- Notes and decision log for recruiter feedback, CV changes, blockers, and lessons learned
- Excel export centre for applications, daily logs, weekly reviews, notes, interview prep, and full tracker backup
- Seeded demo data for reviewer walkthroughs
- Django authentication and user-specific records
- Service-layer business logic and automated tests

## Smart Logic Included

The smart review layer evaluates each application using rule-based business logic:

- Role/title fit
- Location/work-pattern fit
- Junior/graduate suitability
- Skills match
- Deal-breaker detection
- CV version recommendation
- Portfolio project recommendation
- Application readiness checklist
- Follow-up due logic
- Interview preparation readiness

## Tech Stack

- Python
- Django
- SQLite for local development
- Django Templates
- HTML / CSS / JavaScript
- OpenPyXL
- WhiteNoise
- GitHub Actions CI

## Project Apps

```text
apps/
├── accounts/
├── dashboard/
├── applications/
├── job_intelligence/
├── followups/
├── interviews/
├── daily_log/
├── weekly_review/
├── metrics/
├── notes/
└── exports/
```

## Local Setup

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\activate
```

Install and run:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

## Demo Login

```text
Username: demo
Password: DemoPass12345
```

## Run Tests

```bash
python manage.py test
```

Current verification:

```text
57 tests passing
python manage.py check passing
```

## Portfolio Value

This project demonstrates Django app architecture, relational data modelling, CRUD workflows, service-layer business logic, user-specific data filtering, authentication-protected views, diagnostic metric logic, smart recommendation logic, Excel export generation, dashboard design, test coverage, and business-facing analytics thinking.

## Recruiter-Friendly Summary

CareerFunnel Tracker is a Django-based job-search intelligence platform that turns application activity into diagnostic insight. It tracks applications, daily targets, weekly reviews, follow-ups, interview preparation, funnel conversion rates, notes, and exportable evidence. The smart review engine recommends CV versions, portfolio projects, readiness improvements, and next actions based on job-fit and application-quality signals.

---

## Agentic AI Assistance Layer

The upgraded project includes a local AI-style assistant layer under `/ai-agents/`.

These features run without an external API key and use deterministic business rules so the project works immediately in local development and portfolio review.

### Added AI Agent Features

- **AI Job Posting Analyzer** — paste a job description and receive a fit score, apply/skip recommendation, matched skills, risks, recommended CV version, recommended projects, and next actions.
- **AI Next Best Action Agent** — reviews applications, follow-ups, interviews, missing CV versions, weekly volume, and funnel diagnosis to recommend what to do next.
- **AI Follow-Up Message Writer** — generates a professional follow-up message from a saved application record.
- **AI Interview Prep Generator** — creates a role-specific interview prep pack with profile angle, projects to mention, likely questions, technical topics, STAR examples, and questions to ask the employer.
- **AI Weekly Coach** — reviews weekly activity, funnel diagnosis, risks, wins, and produces a practical next-week plan.

### AI Agent URLs

```text
/ai-agents/
/ai-agents/job-posting-analyzer/
/ai-agents/next-best-actions/
/ai-agents/follow-up-writer/
/ai-agents/interview-prep-generator/
/ai-agents/weekly-coach/
```

### Why This Matters

This turns CareerFunnel Tracker from a tracker into a decision-support workflow. It does not only record what happened; it helps decide what should happen next.

---

## Advanced AI Assistance Features

This version also includes a deeper AI-style assistance layer in `apps/ai_agents/`:

- AI CV Gap Analyzer — compares a job description against CV/project evidence.
- AI Cover Letter Quality Checker — scores cover-letter drafts for role fit, company relevance, project evidence, business value, length, and exaggeration risk.
- AI Rejection Pattern Analyzer — detects patterns across rejected and auto-rejected applications.
- CV Version A/B Testing — compares CV versions by applications, responses, interviews, offers, and rejections.
- Smart Notifications Centre — surfaces overdue follow-ups, missing CV versions, missing job URLs, incomplete interview prep, missing daily logs, and weekly-review reminders.

These features are implemented with local deterministic business logic, so the project runs without external API keys while still demonstrating agentic decision-support workflows.

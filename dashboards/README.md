# Dashboard CSV Export Pipeline

## Purpose

This folder contains dashboard-ready CSV extracts for portfolio BI tools. The export pipeline is designed to make CareerFunnel Tracker metrics easy to inspect in local Tableau evidence and future BI-tool imports without exposing private job-search records.

## Demo Data Only

The generated CSV files are synthetic demo data only. They are produced from the `demo` user created by the demo seed command.
The seeded demo applications intentionally include a small number of incomplete quality fields so dashboard views can show realistic analytics-readiness gaps.

## Reproducibility

Run these commands from the project root:

```powershell
python manage.py seed_demo_data
python manage.py export_for_dashboards
```

The export command writes:

- `dashboards/data/applications.csv`
- `dashboards/data/daily_logs.csv`

## applications.csv Schema

- `application_id`
- `date_applied`
- `company_name`
- `job_title`
- `status`
- `source`
- `cv_version`
- `role_fit`
- `location`
- `work_type`
- `pipeline_stage`
- `response_date`
- `follow_up_status`
- `experience_level`
- `has_cv_version`
- `has_precise_source`
- `has_job_description`
- `has_required_skills`
- `has_follow_up_date`
- `is_analytics_ready`

The six quality indicator fields are safe yes/no flags. They expose whether important fields are present without exporting private text such as job descriptions, required skills, notes, URLs, or contact details.

## daily_logs.csv Schema

- `log_date`
- `target_applications`
- `actual_applications`
- `hours_spent`

## Tableau Usage / Future BI Imports

Use these CSVs as local dashboard inputs. Tableau evidence is stored as a local workbook and screenshot proof. A Tableau Public URL is not added unless it is verified. Power BI is not part of Sprint 18 implementation; the CSV format remains simple enough for a future Sprint 20 or later BI-tool import.

## Sprint 18 Dashboard Evidence

Sprint 18 dashboard evidence includes:

- Local Tableau workbook: `dashboards/tableau/careerfunnel_sprint18_tableau_workbook.twbx`
- Performance dashboard screenshot: `docs/evidence/screenshots/sprint-18-performance-dashboard.png`
- Quality dashboard screenshot: `docs/evidence/screenshots/sprint-18-quality-dashboard.png`

These artefacts prove local Tableau dashboard construction from synthetic dashboard CSVs. They do not claim Tableau Public hosting, a live deployment URL, a Power BI dashboard, or use of real/private job-search data.

## Quality Dashboard Usage

- Analytics-ready rate: percentage of `applications.csv` rows where `is_analytics_ready` is `yes`
- Missing CV count: rows where `has_cv_version` is `no`
- Missing source count: rows where `has_precise_source` is `no`
- Missing job description count: rows where `has_job_description` is `no`
- Missing required skills count: rows where `has_required_skills` is `no`
- Missing follow-up date count: rows where `has_follow_up_date` is `no`

## Safety

Do not export real/private data through this demo command. The command refuses non-demo usernames and intentionally excludes private fields such as job URLs, contact names, contact emails, notes, job descriptions, and required skills.

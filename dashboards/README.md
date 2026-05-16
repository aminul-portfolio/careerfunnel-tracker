# Dashboard CSV Export Pipeline

## Purpose

This folder contains dashboard-ready CSV extracts for portfolio BI tools. The export pipeline is designed to make CareerFunnel Tracker metrics easy to inspect in tools such as Tableau Public or Power BI without exposing private job-search records.

## Demo Data Only

The generated CSV files are synthetic demo data only. They are produced from the `demo` user created by the demo seed command.

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

## daily_logs.csv Schema

- `log_date`
- `target_applications`
- `actual_applications`
- `hours_spent`

## Tableau / Power BI Usage

Use these CSVs as local dashboard inputs. Tableau Public evidence can be added after the dashboards are created and verified. Power BI is not part of Sprint 18 implementation, but the CSV format is intentionally simple enough for future BI-tool import.

## Safety

Do not export real/private data through this demo command. The command refuses non-demo usernames and intentionally excludes private fields such as job URLs, contact names, contact emails, notes, job descriptions, and required skills.

# Project Evidence Review -- GoalTracker -- KPI Tracking & BI Reporting

## Project Identity

| Field | Value |
|---|---|
| Project name | GoalTracker -- KPI Tracking & BI Reporting |
| GitHub URL | https://github.com/aminul-portfolio/goaltracker-kpi-reporting |
| Latest visible tag/release | No public release visible at review time |
| Latest visible commit | bead76e -- Add updated GoalTracker showcase screenshots |
| Current branch | main |
| Evidence checked date | 19 May 2026 |
| Evidence source | GitHub URL + uploaded ZIP review |
| Local validation | Pending |

## Project Goal

Django-based KPI tracking and BI reporting project that converts session-level work activity into quality-weighted effective minutes, persisted daily/weekly snapshots, target-vs-actual reporting, CSV export contracts, and Power BI-ready outputs.

## Target Roles

- Data Analyst
- BI Analyst
- Reporting Analyst
- Analytics Engineer
- Junior Data Engineer
- Python/Django data-product roles

## Implemented Features

- Django KPI dashboard
- Active day lifecycle
- Timer-driven session creation
- Manual session entry
- Session-level category attribution
- Work-item attribution
- Quality-level input
- Quality-weighted effective minutes
- Morning / Afternoon / Evening block classification
- Raw vs effective minutes reporting
- Target-vs-actual analysis
- DaySnapshot reporting
- WeekSnapshot reporting
- Snapshot history
- Day snapshot detail page
- Export hub
- Legacy CSV exports
- v2 Power BI-oriented fact/dimension exports
- Power BI .pbix proof asset
- Screenshot evidence
- Basic export contract tests

## Planned / Not Implemented / Not Proven

- Production SaaS
- Real business users/customers
- Live deployment
- Strong automated test coverage (only 2 real test functions found)
- GitHub Actions/CI validation (no CI workflow found)
- Enterprise BI system
- Production Power BI Service deployment
- Clean `requirements.txt` (encoding/null-byte concern noted)
- Public release/tag
- Local validation

## Key Evidence Paths

| Evidence Area | Path / Location | What It Proves |
|---|---|---|
| Session model | Timer/manual session workflows (ZIP/GitHub review) | Activity capture |
| Snapshots | DaySnapshot, WeekSnapshot | Persisted reporting layer |
| Quality weighting | Quality-level -> effective minutes | KPI methodology |
| Exports | Legacy CSV + v2 fact/dimension exports | BI handoff contract |
| Power BI | `.pbix` proof asset | Desktop reporting evidence (not Service deployment) |
| Tests | Test module (2 real functions found) | Limited automated coverage |
| CI | Not found in review | Do not claim CI |
| requirements.txt | Dependency file | **Concern:** possible encoding/null-byte issue |

## Signature Evidence

Quality-weighted effective minutes with Morning/Afternoon/Evening blocks, persisted DaySnapshot/WeekSnapshot reporting, and v2 Power BI-oriented fact/dimension CSV exports plus a `.pbix` proof asset.

## Validation Proof Needed

- Fix `requirements.txt` encoding if needed
- `python manage.py check`
- `python manage.py test` (2+ tests; expand later)
- Export hub smoke test for CSV contracts
- Add GitHub Actions workflow before claiming CI
- Expand test coverage beyond export contracts

## Safe Claims

- Built a Django KPI tracking app with session-level activity capture, quality-weighted effective minutes, and daily/weekly snapshots.
- Provides target-vs-actual reporting and Power BI-oriented fact/dimension CSV exports with a desktop `.pbix` proof asset.
- Basic export contract tests exist (GitHub/ZIP review; full validation and CI pending).

## Claims To Avoid

- Production SaaS
- Real business users/customers
- Live deployment
- Strong automated test coverage
- GitHub Actions/CI validation
- Enterprise BI system
- Production Power BI Service deployment

## CV Bullets

- Developed a Django KPI tracking platform with quality-weighted effective minutes, day/week snapshots, and target-vs-actual reporting.
- Delivered an export hub with Power BI-oriented fact/dimension CSV contracts and a `.pbix` portfolio proof file.
- Identified gaps: limited tests (2 functions), no CI workflow, and `requirements.txt` encoding concern -- validation pending.

## LinkedIn Wording

Portfolio project: Django KPI and BI reporting -- session tracking, quality-weighted effective minutes, daily/weekly snapshots, and Power BI-ready CSV exports with a `.pbix` proof file. Supporting BI portfolio evidence; not enterprise SaaS; CI and full validation pending.

## Interview Talking Points

### 60-second explanation

GoalTracker captures work sessions with quality levels, converts them into effective minutes by time block, stores daily and weekly snapshots, and exports CSVs shaped for Power BI plus a proof `.pbix` file.

### Business value

Demonstrates KPI definition, snapshot persistence, and BI export contracts -- core skills for reporting and BI analyst roles.

### Technical value

Django dashboards, snapshot models, export hub with v2 fact/dimension schema, and export contract tests.

### Limitation answer

Only two real test functions and no CI workflow found. Requirements file may need encoding fix. Not deployed for real business users or Power BI Service.

## Next Recommended Sprint

Sprint name: GoalTracker validation/test/CI gaps
Goal: Fix requirements encoding; add CI workflow; expand tests; run local validation.
Allowed scope: `requirements.txt`, `.github/workflows/`, tests, validation README note
Do not add: Enterprise SaaS, Power BI Service production, or strong test-coverage claims until proven
Validation plan: Fix deps -> `manage.py test` -> add CI -> capture terminal proof

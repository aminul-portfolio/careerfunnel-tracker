# Project Evidence Review -- RiskWise Planner

## Project Identity

| Field | Value |
|---|---|
| Project name | RiskWise Planner |
| GitHub URL | https://github.com/aminul-portfolio/riskwise-planner |
| Latest visible tag/release | No public release visible at review time |
| Latest visible commit | b0ff9e7 -- Add .gitattributes to ignore HTML and templates |
| Current branch | main |
| Evidence checked date | 19 May 2026 |
| Evidence source | GitHub URL + uploaded ZIP review |
| Local validation | Pending |

## Project Goal

Django-based pre-trade risk planning and scenario-modelling project that converts observed trade outcomes into planning baselines, Monte Carlo simulations, stress-test reviews, scenario comparisons, saved-run archives, and capital-preservation decision support.

## Target Roles

- Data Analyst
- BI Analyst
- Reporting Analyst
- Analytics Engineer
- Junior Data Engineer
- FinTech analytics roles
- Python/Django data-product roles

## Implemented Features

- Django pre-trade risk planning platform
- Manual CSV/XLSX/XLS upload workflow
- Planning baseline generation
- Capital Preservation Dashboard
- Monte Carlo simulation workflow
- Stress-test review
- Scenario comparison
- Saved runs archive
- Run detail/audit view
- Position sizing calculator
- Trade risk controls calculator
- Strategy exposure review
- SL/TP planner
- Session-backed planning context
- Ownership isolation
- Login-protected planning surfaces
- Service-layer simulation and risk logic
- Matplotlib chart generation
- Screenshot evidence
- Reviewer documentation
- Seed demo command
- GitHub Actions workflow configuration
- 64 real test functions visible in `riskwise/tests.py`

## Planned / Not Implemented / Not Proven

- Live broker integration
- Live market feed integration
- Trading automation
- Trade execution
- Direct API sync with TradeIntel
- Production SaaS deployment
- Real customer/user usage
- Guaranteed capital protection or trading profitability
- CI passed (unless verified)
- README architecture wording fully aligned with `riskwise/models.py` (concern noted)
- Local validation

## Key Evidence Paths

| Evidence Area | Path / Location | What It Proves |
|---|---|---|
| Risk models | `riskwise/models.py` | Domain model source of truth |
| Tests | `riskwise/tests.py` | 64 test functions (GitHub/ZIP review) |
| Upload workflow | CSV/XLSX/XLS import surfaces | Manual data intake boundary |
| Simulation services | Service-layer logic (ZIP review) | Monte Carlo and stress-test implementation |
| Dashboards | Capital Preservation Dashboard, scenario views | Analyst-facing planning UI |
| Auth | Login-protected surfaces, ownership isolation | Session and access boundaries |
| CI | `.github/workflows/` | Workflow configuration (success not verified) |
| README | Architecture section | **Concern:** wording may not match actual model names -- align later |

## Signature Evidence

Pre-trade planning workflow from uploaded trade history through baselines, Monte Carlo simulation, stress tests, and saved-run audit views -- with 64 test functions visible in `riskwise/tests.py` (not locally executed from CareerFunnel repo).

## Validation Proof Needed

- `git status --short`
- `python manage.py check`
- `python manage.py makemigrations --check --dry-run`
- `python manage.py test`
- `python manage.py seed_demo` (or equivalent seed command per README)
- Align README architecture diagram/names with `riskwise/models.py`

## Safe Claims

- Built a Django pre-trade risk planning platform with manual upload, planning baselines, Monte Carlo simulation, stress tests, and scenario comparison.
- Implemented calculators for position sizing, trade risk controls, strategy exposure, and SL/TP planning with login-protected, ownership-isolated surfaces.
- 64 test functions visible in repository (GitHub/ZIP review; local test run pending).

## Claims To Avoid

- Live broker integration
- Live market feed integration
- Trading automation
- Trade execution
- Direct API sync with TradeIntel
- Production SaaS deployment
- Real customer/user usage
- Guaranteed capital protection or trading profitability
- CI passed unless verified

## CV Bullets

- Developed a Django pre-trade risk planning platform with Monte Carlo simulation, stress-test review, and scenario comparison from uploaded trade history.
- Implemented capital preservation dashboards, position sizing and risk control calculators, and saved-run audit views with service-layer simulation logic.
- Repository shows 64 test functions in `riskwise/tests.py` (local validation and README/model alignment pending).

## LinkedIn Wording

Portfolio project: Django pre-trade risk and scenario planning with Monte Carlo simulation, stress tests, capital preservation dashboards, and saved-run archives -- FinTech analytics portfolio evidence; not live trading or broker-integrated; local validation pending.

## Interview Talking Points

### 60-second explanation

RiskWise Planner helps a user plan risk before trading by uploading history, generating baselines, running Monte Carlo and stress scenarios, and comparing outcomes with calculators for sizing and controls -- all in a login-protected Django app.

### Business value

Demonstrates decision-support analytics for capital preservation and scenario comparison without claiming live execution.

### Technical value

Service-layer simulation logic, Matplotlib charts, session context, ownership isolation, and a substantial test file count in the repository.

### Limitation answer

No broker feeds, execution, or guaranteed outcomes. README architecture labels should be reconciled with actual models. Tests and CI not verified from CareerFunnel workspace.

## Next Recommended Sprint

Sprint name: RiskWise README alignment + validation
Goal: Align README model wording with `riskwise/models.py`; run full test suite locally.
Allowed scope: README/docs in RiskWise repo; validation capture
Do not add: Broker, market feed, TradeIntel live sync, or SaaS claims
Validation plan: `python manage.py test` + README patch listing actual model names

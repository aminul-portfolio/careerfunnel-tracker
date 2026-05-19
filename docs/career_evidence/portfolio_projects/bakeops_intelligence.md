# Project Evidence Review -- BakeOps Intelligence

## Project Identity

| Field | Value |
|---|---|
| Project name | BakeOps Intelligence |
| GitHub URL | https://github.com/aminul-portfolio/bakeops-intelligence |
| Latest visible tag/release | v3.0.0-commercial-foundation |
| Latest visible commit | 77fdb52 -- Fix README visual evidence screenshots |
| Current branch | main |
| Evidence checked date | 19 May 2026 |
| Evidence source | GitHub URL + uploaded ZIP review |
| Local validation | Pending |

## Project Goal

Django-based bakery operations analytics platform that turns seeded operational records into KPI dashboards, product profitability analysis, waste tracking, ingredient risk visibility, data-quality review, and BI-ready CSV exports.

## Target Roles

- Data Analyst
- BI Analyst
- Reporting Analyst
- Analytics Engineer
- Junior Data Engineer
- Python/Django data-product roles

## Implemented Features

- Seeded bakery operations dataset
- Django operational models
- Metric build command
- Gold-layer analytics snapshot models
- KPI dashboard
- Product profitability analysis
- Waste-adjusted margin analysis
- Ingredient risk analysis
- Waste analysis
- Occasion analytics
- Customer analytics
- Data-quality review surface
- BI-ready CSV export workflow
- Screenshot evidence
- Metric governance documentation
- Data lineage documentation
- Reviewer walkthrough
- GitHub Actions workflow
- 37 documented tests

## Planned / Not Implemented / Not Proven

- Live SaaS deployment
- Real bakery customers
- Production deployment
- Billing/subscriptions
- Shopify/Square/POS integration
- Automated onboarding
- Multi-tenant SaaS account management
- Real customer usage
- Local validation (pending terminal proof)

## Key Evidence Paths

| Evidence Area | Path / Location | What It Proves |
|---|---|---|
| Product overview | `README.md` | Scope, reviewer path, feature list |
| Operational models | Django apps / models (ZIP review) | Seeded bakery operations domain |
| Metric build | `build_bakery_metrics` management command | Gold-layer snapshot generation |
| BI export | `export_bi_csv` management command | Analyst-ready CSV workflow |
| Dashboards | KPI / profitability / waste surfaces (ZIP review) | Operational analytics UI |
| Tests | Test suite (37 documented) | Automated coverage claim (not locally verified here) |
| CI | `.github/workflows/` | Workflow configuration (success not verified here) |
| Documentation | Metric governance, data lineage, walkthrough docs | Governed metrics narrative |

## Signature Evidence

Birthday Classic ranks #1 by revenue but #4 by waste-adjusted margin, with action flag review.

Proof string: **Birthday Classic 1 4 review**

## Validation Proof Needed

- `git status --short`
- `python -m ruff check .`
- `python manage.py check`
- `python manage.py makemigrations --check --dry-run`
- `python manage.py test`
- `python manage.py seed_demo_data --reset`
- `python manage.py build_bakery_metrics`
- `python manage.py export_bi_csv`

## Safe Claims

- Built a Django bakery operations analytics platform with seeded data, KPI dashboards, profitability and waste-adjusted margin analysis, and BI-ready CSV exports.
- Documented metric governance, data lineage, and a reviewer walkthrough with screenshot evidence.
- Demonstrates gold-layer snapshot modelling and operational data-quality review (based on GitHub/ZIP review; local validation pending).

## Claims To Avoid

- Live SaaS product
- Real bakery customers
- Production deployment
- Billing/subscriptions
- Shopify/Square/POS integration
- Automated onboarding
- Multi-tenant SaaS account management
- Real customer usage
- CI passed unless verified locally

## CV Bullets

- Developed a Django bakery operations analytics platform with KPI dashboards, product profitability, waste-adjusted margins, and ingredient risk visibility from seeded operational data.
- Implemented gold-layer metric snapshots, a metric build command, and BI-ready CSV exports for analyst review.
- Documented metric governance and data lineage with reviewer walkthrough and screenshot evidence (GitHub/ZIP review; local validation pending).

## LinkedIn Wording

Portfolio project: Django bakery operations analytics with KPI dashboards, profitability and waste analysis, gold-layer metric snapshots, and BI CSV exports -- reviewed from GitHub and archive; local validation pending. Not a live commercial SaaS or POS-integrated product.

## Interview Talking Points

### 60-second explanation

BakeOps Intelligence models a bakery's operational data -- products, waste, ingredients, occasions -- and builds analytics snapshots for dashboards and CSV export. A signature insight is that top revenue does not always mean top margin after waste.

### Business value

Shows how operations teams might prioritise products differently when waste-adjusted margin is visible, not just revenue rank.

### Technical value

Django models, management commands for seeding and metric builds, gold-layer snapshots, data-quality surfaces, and documented metric governance.

### Limitation answer

Data is seeded for portfolio proof; there are no real bakery customers, POS integrations, or verified production deployment. Local validation on my machine is still pending.

## Next Recommended Sprint

Sprint name: BakeOps local validation
Goal: Run full Django checks, tests, seed, metric build, and CSV export; capture terminal proof.
Allowed scope: Local validation only; README validation-status note if needed in BakeOps repo
Do not add: Live SaaS, POS, billing, or real-customer claims
Validation plan: Execute all commands listed under Validation Proof Needed and archive output

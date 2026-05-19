# Project Evidence Review -- PureLaka Commerce Platform

## Project Identity

| Field | Value |
|---|---|
| Project name | PureLaka Commerce Platform |
| GitHub URL | https://github.com/aminul-portfolio/purelaka-commerce-platform |
| Latest visible tag/release | Not confirmed. Public GitHub URL was not accessible during review. |
| Latest visible commit | Not confirmed from public GitHub. ZIP archive reviewed. |
| Current branch | Likely main based on uploaded ZIP archive name; public branch should be confirmed. |
| Evidence checked date | 19 May 2026 |
| Evidence source | Uploaded ZIP review |
| Local validation | Pending |

## Project Goal

Django-based transactional commerce analytics and reporting project that connects products, cart, orders, payments, subscriptions, monitoring, audit trails, and analytics dashboards into a proof-oriented e-commerce data product.

## Target Roles

- Data Analyst
- BI Analyst
- Reporting Analyst
- Analytics Engineer
- Junior Data Engineer
- Python/Django data-product roles

## Implemented Features

- Django multi-app commerce platform
- Product catalogue
- Product variants and images
- Cart workflow
- Checkout workflow
- Order lifecycle workflow
- Wishlist workflow
- Customer account and address handling
- Role-based access control surfaces
- Stripe-ready PaymentIntent pattern
- Stripe webhook/idempotency boundary via StripeEvent
- Refund-related handling
- Subscription workflow scaffold
- Subscription / MRR analytics surfaces
- Analytics dashboard
- KPI reporting
- Plotly-based visual outputs
- CSV export surfaces
- Monitoring dashboard
- Data-quality issue model
- Operational checks via management commands
- Audit logging support
- Screenshot evidence
- Acceptance matrix
- Proof index
- KPI definitions
- Service boundary documentation
- Security baseline documentation
- Runbook documentation
- GitHub Actions CI workflow configuration
- Docker and Docker Compose scaffolding

## Planned / Not Implemented / Not Proven

- Live SaaS product
- Real customers or production users
- Public production deployment
- Real Stripe transactions currently processing
- Enterprise-grade production readiness
- Public CI passed (unless verified)
- Public license (unless license file exists)
- Public GitHub access confirmed
- Local validation

## Key Evidence Paths

| Evidence Area | Path / Location | What It Proves |
|---|---|---|
| Commerce apps | Multi-app Django structure (ZIP review) | Catalogue, cart, checkout, orders |
| Payments | Stripe-ready PaymentIntent, StripeEvent idempotency | Payment boundary design (not live processing) |
| Subscriptions | Subscription scaffold + MRR analytics surfaces | Recurring revenue reporting shape |
| Analytics | KPI dashboard, Plotly outputs, CSV exports | Reporting and export evidence |
| Operations | Monitoring dashboard, data-quality model, management commands | Operational checks |
| Documentation | Acceptance matrix, proof index, KPI definitions, runbooks | Portfolio proof packaging |
| Infrastructure | Docker / Docker Compose scaffolding | Local deployment shape (not production proof) |
| CI | `.github/workflows/` (ZIP review) | CI configuration (success not verified) |

## Signature Evidence

End-to-end commerce domain modelling -- cart through order lifecycle, Stripe-ready payment boundary with webhook idempotency, subscription/MRR analytics surfaces, and KPI/monitoring documentation in a proof-oriented package.

## Validation Proof Needed

- Confirm public GitHub URL accessibility and default branch
- `git status --short`
- `python manage.py check`
- `python manage.py test` (if runnable)
- Docker Compose local smoke (optional)
- Verify license file exists before any public-license claim
- Verify CI locally before claiming CI passed

## Safe Claims

- Built a Django multi-app commerce platform with product catalogue, cart/checkout, order lifecycle, and analytics dashboards (ZIP review).
- Implemented Stripe-ready PaymentIntent pattern and webhook idempotency boundary; subscription/MRR analytics scaffold.
- Documented KPI definitions, service boundaries, security baseline, runbooks, and proof index (public GitHub and local validation pending).

## Claims To Avoid

- Live SaaS product
- Real customers or production users
- Public production deployment
- Real Stripe transactions currently processing
- Enterprise-grade production readiness
- Public CI passed unless verified
- Public license unless license file exists
- Confirmed public GitHub repo (not verified at review time)

## CV Bullets

- Developed a Django e-commerce data product spanning catalogue, cart, checkout, orders, and role-based access control (ZIP-reviewed evidence).
- Designed Stripe-ready payment flows with webhook idempotency and subscription/MRR analytics surfaces.
- Produced KPI reporting, monitoring, data-quality checks, and operational runbooks for portfolio proof (GitHub access and local validation pending).

## LinkedIn Wording

Portfolio project: Django commerce analytics platform with catalogue-to-order workflows, Stripe-ready payment boundaries, subscription/MRR surfaces, and KPI dashboards -- reviewed from archive; public repo access and local validation not yet confirmed.

## Interview Talking Points

### 60-second explanation

PureLaka models an e-commerce domain in Django: products, cart, checkout, orders, payments with a Stripe-ready boundary, subscriptions, and analytics dashboards with exports and operational monitoring docs.

### Business value

Shows how transactional data can feed KPI and MRR-style reporting with audit and data-quality surfaces -- relevant to commerce and reporting analyst roles.

### Technical value

Multi-app Django design, RBAC, PaymentIntent pattern, StripeEvent idempotency, Plotly/CSV exports, Docker scaffolding, and extensive proof documentation.

### Limitation answer

Reviewed from ZIP only; public GitHub was not accessible during review. Not a live SaaS with real Stripe volume or customers. CI and local runs unverified from CareerFunnel workspace.

## Next Recommended Sprint

Sprint name: PureLaka GitHub confirmation + validation
Goal: Confirm public repo access; run checks/tests; document validation status.
Allowed scope: Access fix, validation log, README status in PureLaka repo
Do not add: Live SaaS, real Stripe production, or enterprise readiness claims
Validation plan: Confirm URL -> `manage.py check` -> targeted test run -> optional Docker smoke

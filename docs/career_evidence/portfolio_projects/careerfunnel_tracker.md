# Project Evidence Review -- CareerFunnel Tracker

_Originally reviewed on 22 May 2026 and manually refreshed in Sprint 124C against the verified Sprint 124B repository baseline._

## Project Identity

| Field | Value |
|---|---|
| Project name | CareerFunnel Tracker |
| GitHub URL | https://github.com/aminul-portfolio/careerfunnel-tracker |
| Current branch baseline | `main` |
| Verified main commit | `68f2cac285bb2ef950cf047d00b4f2d96fce24a0` |
| Latest verified completion tag | `sprint-124b-accessibility-freeze-patch-complete` |
| Verified test baseline | **3,012 / 3,012 PASS** |
| Verified CI | **GitHub Actions Django CI #241 PASS** |
| Evidence source | Current repository, local terminal validation, sprint closure evidence, and exact-SHA CI proof |
| Local validation | Complete as of Sprint 124B |
| Project state | Product-feature roadmap complete; maintenance/evidence-alignment work continuing through Sprint 124C-124E |

The test count and CI references above are point-in-time evidence from Sprint 124B and should be refreshed after future repository changes.

## Project Goal

CareerFunnel Tracker is a Django/Python analytics and AI application workflow project that turns job-search activity into explainable funnel metrics, source/CV performance reporting, data-quality signals, employability evidence, recruiter-ready portfolio proof, and controlled AI-assisted decision support.

The platform combines:

- deterministic analytics and reporting;
- structured application and evidence workflows;
- controlled LLM integration;
- offline AI evaluation;
- claim-safety and evidence-alignment controls;
- small private-corpus retrieval evaluation;
- bounded read-only tool-calling;
- authenticated reviewer-facing AI evidence surfaces;
- human-in-the-loop approval and manual action/save boundaries.

## Target Roles

Repository evidence supports positioning toward:

- Data Analyst
- BI Analyst
- Reporting Analyst
- Analytics Engineer
- Junior Data Engineer
- Python/Django data-product roles
- FinTech and FX operations analytics
- AI Application Engineering where claims remain limited to the implemented controlled AI architecture and evaluation evidence

The project should not be presented as a production autonomous-agent platform, enterprise RAG system, production vector-database system, or production AI service.

## Implemented Features

### Analytics and application workflow

- Application tracking
- Daily logs
- Weekly reviews
- Follow-up tracking
- Interview preparation records
- Funnel metrics
- Source performance reporting
- CV version performance
- Rejection pattern analysis
- Application quality checks
- Data quality reporting
- Workbook export centre
- Evaluation queue
- Job-posting review and application-intelligence workflows
- Skill-gap tracking
- Application-readiness checks
- Manual recruiter-email workflow support
- Interview Evidence Workspace
- Career Evidence OS
- Optional metadata-only Notion sync
- Authenticated reviewer-facing evidence surfaces

### Skill and evidence layer

- Skill Ledger
- Evidence-level classification
- Evidence alignment
- Skill-gap advisory signals
- Human-reviewed application intelligence
- Claim-safe evidence presentation

### Controlled AI engineering layer

- Fail-closed LLM provider boundary
- Mode-authoritative provider activation
- API key necessary but not sufficient for live-provider use
- Controlled provider factory seam
- Offline AI evaluation harnesses
- Adversarial and claim-safety evaluation
- Evidence-alignment explanation validation
- Safe rejection paths
- Human-in-the-loop review
- Configuration-gated AI features
- Per-case regression gating in CI-supported evaluation workflows

### Small private-corpus RAG

- Private-corpus retrieval evaluation
- Cached embeddings
- Deterministic cosine-style similarity retrieval
- Source-grounded output evaluation
- Offline RAG regression suite

Required qualification:

> This is small private-corpus RAG/retrieval evidence, not enterprise RAG and not a production vector database.

### Bounded tool-calling

- Read-only tool access
- Closed tool registry
- Call-budget constraints
- Offline deterministic tool-assistant evaluation
- Safe rejection and claim-safety boundaries

Required qualification:

> Tool use is bounded and advisory. It is not autonomous-agent execution.

### Controlled live-provider evidence

A controlled synthetic live-provider canary was executed under explicit safeguards:

- one synthetic call;
- `cap=1`;
- `retries=0`;
- cost bounded;
- explicitly gated;
- request integrity checks;
- integration evidence only.

Required qualification:

> The canary proves that the controlled provider path was exercised under a narrow test condition. It does not prove production reliability, scale, availability, or real-user performance.

## AI Evaluation Evidence

Three principal offline evaluation suites provide **166 total cases**:

| Evaluation Area | Cases | Boundary |
|---|---:|---|
| AI quality evaluation | 54 | Offline quality and regression evidence |
| RAG evaluation | 31 | Small private-corpus retrieval evaluation |
| Bounded tool-assistant evaluation | 81 | Read-only closed-registry tool evaluation |
| **Total** | **166** | Offline evaluation evidence |

These counts represent offline evaluation cases. They are not production-user metrics or production reliability measurements.

Additional AI evaluation work also exists around evidence-alignment explanations, adversarial cases, safe rejection, privacy, and controlled live-canary integration.

## Human-in-the-Loop Boundary

AI-assisted outputs remain:

- advisory;
- evidence-grounded;
- claim-safe;
- human-reviewed;
- manually acted upon or saved.

The application workflow remains:

**Analyse -> Review -> Approve -> Pre-fill Add Application -> Manual Save**

The project does not autonomously submit applications or bypass user approval.

Permanent safety wording includes:

- "Pre-filling this form does not save your application."
- "Saving creates a tracking record only."
- "Documents are not generated here."
- "Follow-up email drafts are for manual use only."
- "Skill gap signals are advisory only."
- "Learning recommendations are planning aids."
- "Pre-fill Add Application"
- "Draft - tracking record only"

## Key Evidence Paths

| Evidence Area | Path / Location | What It Proves |
|---|---|---|
| Product overview | `README.md` | Current architecture, reviewer path, limitations, AI evidence positioning |
| Application workflows | `apps/applications/` | Tracking, application workflow, approval/manual-save boundaries |
| Metrics and reporting | `apps/metrics/` | Funnel, source, CV, rejection, data-quality logic |
| Skill/evidence layer | `apps/skills/`, `apps/skill_gaps/` | Skill Ledger, evidence alignment, advisory skill-gap workflows |
| Controlled AI layer | `apps/ai_agents/` and supporting evaluation modules | Provider boundaries, AI-assisted workflow, evaluation seams |
| Career Evidence V1-V3 | `docs/career_evidence/01_project_evidence_report.md`, `02_job_fit_matrix.md`, `03_recruiter_evidence_pack.md` | Repository-derived and recruiter-facing evidence packs |
| Career Evidence dashboard | `/dashboard/career-evidence/` | Authenticated reviewer-facing evidence |
| AI engineering evidence surface | authenticated Career Evidence AI engineering view | Recruiter/reviewer proof of implemented AI architecture without triggering live provider use |
| Analytics lineage | `docs/analytics/analytics_lineage.md` | Metric lineage and governance |
| Metric definitions | `docs/analytics/metric_definitions.md` | KPI definitions and calculation discipline |
| Evaluation evidence | AI quality, RAG, tool-assistant, evidence-alignment evaluation modules/tests | Offline deterministic evaluation and regression proof |
| CI | `.github/workflows/django-ci.yml` | GitHub Actions validation workflow |
| Sprint evidence | `docs/evidence/` and sprint closure records | Exact-SHA delivery and validation history |

## Signature Evidence

CareerFunnel's strongest current evidence is the combination of:

1. governed Django analytics;
2. Skill Ledger and evidence alignment;
3. a fail-closed LLM provider boundary;
4. offline and adversarial AI evaluation;
5. claim-safety and safe rejection;
6. small private-corpus RAG evaluation;
7. bounded read-only tool-calling;
8. a controlled one-call live-provider canary;
9. human-in-the-loop approval;
10. authenticated AI engineering evidence surfaces;
11. exact-SHA GitHub Actions validation;
12. **3,012 passing tests as of Sprint 124B**.

The project demonstrates AI application engineering discipline without claiming production autonomy or enterprise infrastructure.

## Validation Proof

Verified Sprint 124B baseline:

```text
ruff check .                                      PASS
python manage.py check                            PASS
python manage.py makemigrations --check --dry-run No changes detected
python manage.py test                             3012 / 3012 PASS
GitHub Actions Django CI #241                     PASS

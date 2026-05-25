# Sprint 41 - Skill Intelligence Foundation Evidence

## 1. Sprint Objective

Sprint 41 introduces the first **Skill Intelligence Foundation** in CareerFunnel Tracker: a manual, advisory, read-only page that helps review skills, gaps, role readiness, and portfolio evidence for Data Analyst, BI Analyst, Analytics Engineer, and Data Engineer targets - without fake AI, automation, scraping, or unsupported claims.

**Branch:** `sprint-41-skill-intelligence-foundation`

---

## 2. Implemented Skill Intelligence Foundation Summary

| Module | Route | Service |
| --- | --- | --- |
| Skill Intelligence page | `job_intelligence:skill_intelligence` | `build_skill_intelligence_context(user)` |

**Template:** `templates/job_intelligence/skill_intelligence.html`
**Navigation:** Intelligence sidebar link (minimal addition; shell audit updated)

---

## 3. Skill Evidence Summary

Ten claim-safe skill categories:

- Python, SQL, Excel, Django, Data analysis, Reporting, KPI dashboards, ETL / data preparation, Business operations / FX operations, Portfolio evidence

Each card includes:

- Static evidence summary
- Portfolio project references (BakeOps, CareerFunnel Tracker, MarketVista, TradeIntel, DataBridge, etc.)
- Career Evidence note
- Keyword match count from saved application text (not AI extraction)

---

## 4. Skill Gap Review

- Advisory prompts framed as **manual review** tasks
- Missing catalog keywords in logged applications generate "Review X manually before applying..."
- `LEARNING_TARGETS` from constants generate stretch-role review prompts (dbt, Airflow, Spark, etc.)
- Not framed as weaknesses, judgments, predictions, or hiring decisions
- Capped list length for readability

---

## 5. Role-Readiness Checklist

Manual checklists (no numeric job-fit score on this page) for:

| Role | Focus |
| --- | --- |
| Data Analyst | SQL/Excel, Python examples, stakeholder reporting, application evidence |
| BI Analyst | Dashboards, metric definitions, data quality, tooling honesty |
| Analytics Engineer | Pipelines, SQL+Python, documentation, stretch-role honesty |
| Data Engineer | Pipeline ownership, operations, modelling, learning-target review |

---

## 6. Portfolio Evidence Mapping

Read-only table mapping portfolio projects to skill areas with link to **Career Evidence** index (`dashboard:career_evidence_index`).

Projects include CareerFunnel Tracker, BakeOps Intelligence, MarketVista Dashboard, TradeIntel 360, DataBridge Market API.

---

## 7. Manual Workflow Safety

Page copy states Skill Intelligence is:

- Manual
- Advisory
- Evidence-based
- Read-only (GET does not mutate records)
- Not a hiring decision engine
- Not automatic CV rewriting or auto-apply
- Not predictive AI/ML

Manual action links: application list, Smart Review, Career Evidence, add application.

---

## 8. Claim-Safety Confirmation

Sprint 41 does **not** claim:

- Auto-apply or automatic submission
- No automatic CV rewriting was added.
- No Gmail, Calendar, OAuth, or scraping integration was added.
- No live job-board ingestion was added.
- No predictive AI/ML or autonomous agents were added.
- No live SaaS users or production deployment claims were added.
- Numeric job-fit scoring on the Skill Intelligence page

Existing **Smart Review** (rule-based scores) remains unchanged on its own route.

---

## 9. What Was Deliberately Not Changed

- Models, migrations, database schema
- Dashboard layout and modules (sidebar link only)
- Application forms
- Recruiter email and interview prep workflows
- Metrics/reporting logic
- README and GitHub workflows
- Sprint 42 scope

---

## 10. Test Coverage Summary

**File:** `apps/job_intelligence/tests.py`

| Test class | Tests | Focus |
| --- | ---: | --- |
| `SkillIntelligenceFoundationTests` | 11 | Page render, all sections, mutation safety, claim safety, Sprint 42 guard, login, no models |

Shell audit updated for `job_intelligence:skill_intelligence` URL resolution and page render.

---

## 11. Validation Commands

```powershell
ruff check apps/job_intelligence/
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test apps.job_intelligence.tests tests.test_sprint_37a_shell_foundation_audit
```

---

## Files Changed (Sprint 41)

- `apps/job_intelligence/services.py`
- `apps/job_intelligence/views.py`
- `apps/job_intelligence/urls.py`
- `apps/job_intelligence/tests.py`
- `templates/job_intelligence/skill_intelligence.html`
- `templates/partials/sidebar.html`
- `static/css/components.css`
- `tests/test_sprint_37a_shell_foundation_audit.py`
- `docs/evidence/sprint_41_skill_intelligence_foundation.md`
- `docs/evidence/evidence_index.md`

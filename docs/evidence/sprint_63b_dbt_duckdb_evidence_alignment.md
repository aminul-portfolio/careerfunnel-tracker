# Sprint 63B Phase 1 - dbt/DuckDB Evidence Alignment

Date: 2026-06-14
Scope: Internal CareerFunnel evidence stores only (Phase 1)

## Summary

Aligned internal evidence catalogs with the Master CV update dated 2026-06-14.
dbt and DuckDB are now portfolio-verified skills through the shipped bakeops-dbt
project. BakeOps Intelligence remains a separate canonical project.

## What changed

### Evidence bank (`apps/ai_agents/evidence_bank.py`)

- Removed `dbt` from `GAP_LEARNING_SKILL_IDS` and `HARD_GAP_SKILL_IDS`.
- Promoted `dbt` to `partial` tier with bakeops-dbt portfolio wording.
- Added `duckdb` as `partial` tier with local DuckDB portfolio wording.
- Added canonical project entry `bakeops-dbt` (display name exactly `bakeops-dbt`).
- Updated pipeline stretch angle to reference bakeops-dbt portfolio evidence.

### Hard-gap and learning-target logic

- Removed `dbt` from `HARD_GAP_TERMS` in `apps/ai_agents/services.py`.
- Removed `dbt` from `LEARNING_TARGETS` in `apps/job_intelligence/constants.py`.
- Snowflake, Airflow, Spark, Kafka, AWS Redshift, SC clearance, and DV clearance
  remain hard-gap / learning-target handling unchanged.

### Project recommendations

- AE / dbt / DuckDB / data modelling job signals now recommend `bakeops-dbt` where
  relevant (not injected into default DA/BI default lists).
- BakeOps Intelligence is unchanged and not renamed.

### Skill Intelligence (`apps/job_intelligence/services.py`)

- Added `dbt (portfolio)` and `DuckDB (portfolio)` catalog entries tied to bakeops-dbt.
- Extended ETL evidence projects to include bakeops-dbt where appropriate.
- Added bakeops-dbt portfolio skill mapping.

### Draft documents and master CV baseline

- Internal draft headline includes Junior Analytics Engineer positioning.
- Added bakeops-dbt as fifth portfolio project in master CV source order.
- Added dbt and DuckDB to technical skills as portfolio-verified entries only.
- Draft generator includes bakeops-dbt evidence wording for AE/dbt roles.

### Interview prep pack

- Added bakeops-dbt project profile and dbt/DuckDB technical topic for relevant roles.

## Claim-safety boundary

### Allowed (portfolio scope)

- dbt modelling via bakeops-dbt (7 models, 26 tests, v1.0.1).
- DuckDB as local portfolio warehouse in bakeops-dbt.
- Junior Analytics Engineer as stretch/internal headline positioning.
- Analytics engineering stretch angles with honest tool boundaries.

### Still blocked / not claimable

- Production dbt, enterprise dbt, or cloud warehouse dbt (Snowflake, BigQuery, etc.).
- Airflow orchestration or production pipeline ownership.
- Snowflake, BigQuery, Spark, Kafka, AWS Redshift as proven skills (gap_learning).
- SC clearance and DV clearance (hard gaps).
- Full CV body, cover letter body, or auto-generated application copy from services.

### Tier behaviour

- dbt and DuckDB: `partial` tier - claimable as portfolio evidence via
  `is_claimable_skill()`, but excluded from strong-only promotion paths such as
  `filter_claimable_for_matched()`.
- Snowflake / Airflow / etc.: remain `gap_learning` and not claimable.

## Files touched (Phase 1 allow-list only)

- apps/ai_agents/evidence_bank.py
- apps/ai_agents/services.py
- apps/ai_agents/tests.py
- apps/ai_agents/interview_prep_pack.py
- apps/ai_agents/tests_interview_prep_pack.py
- apps/job_intelligence/constants.py
- apps/job_intelligence/services.py
- apps/job_intelligence/draft_documents.py
- apps/job_intelligence/tests.py
- apps/applications/master_cv.py
- apps/applications/tests_professional_exports.py
- apps/applications/test_master_cv_fixtures.py (unchanged - uses dynamic headline)
- docs/evidence/sprint_63b_dbt_duckdb_evidence_alignment.md

## Not touched (by design)

- README.md, dashboards/README.md, docs/career_evidence/*
- models.py, migrations, fixtures, seed_demo_data
- CSV/data files, binaries, screenshots, .pbix files
- Public LinkedIn wording or external career evidence docs

## Tests added/updated

- dbt/DuckDB portfolio partial claimability vs strong-only filters
- Snowflake/Airflow remain gap/hard-gap/not claimable
- bakeops-dbt accepted as canonical project; unknown projects still rejected
- CV gap analyser treats dbt as matched portfolio evidence, Snowflake as missing
- AE draft prioritisation and learning-gap behaviour for airflow-only gaps
- Interview prep selects bakeops-dbt for dbt/DuckDB roles

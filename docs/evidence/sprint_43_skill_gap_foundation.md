# Sprint 43 — Skill Gap Foundation Evidence

## 1. Sprint Objective

Sprint 43 creates the **model-changing foundation** for saved, application-level skill gaps in a new Django app `apps.skill_gaps`. Records are manual and advisory, with deterministic rule-based priority scoring. No Skill Intelligence Dashboard, no Sprint 44 features.

**Branch:** `sprint-43-skill-gap-foundation`

---

## 2. JobApplication Source Evidence Captured

Pre-implementation evidence file: `G:\workflow_tools\sprint43_jobapplication_source_evidence.txt`

Confirmed facts used in services:

| Fact | Source |
| --- | --- |
| `JobApplication.status` exists | `apps/applications/models.py` lines 57–60 |
| Uses `ApplicationStatus.choices` | Same |
| Default `ApplicationStatus.SUBMITTED` | Same |
| Failure statuses for counting | **Only** `REJECTED` and `AUTO_REJECTED` |

No other rejection/failure statuses were assumed (e.g. `WITHDREW`, `NO_RESPONSE` are not counted).

Skill matching uses `required_skills` and `job_description` text fields only.

---

## 3. Model and Migration Summary

**Model:** `ApplicationSkillGap`
**App:** `apps.skill_gaps`
**Migration:** `apps/skill_gaps/migrations/0001_initial.py`
**Registered in:** `config/settings/base.py` → `INSTALLED_APPS`

Fields: `application`, `stage`, `skill_name`, `current_tier`, `priority`, `goal_weight`, `failure_count`, `stage_weight`, `priority_score`, `jd_requirement`, `identified_by`, `suggested_action`, `long_term_goal`, `resolved`, `resolved_date`, `resolved_tier`, `created_at`, `updated_at`.

---

## 4. Constraint and Index Summary

**Unique constraint** (`models.UniqueConstraint`):

- `application` + `skill_name` + `stage` → `uniq_application_skill_gap_stage`

**Indexes:**

| Index name | Field(s) |
| --- | --- |
| `skill_gap_application_idx` | `application` |
| `skill_gap_stage_idx` | `stage` |
| `skill_gap_priority_idx` | `priority` |
| `skill_gap_skill_name_idx` | `skill_name` |
| `skill_gap_resolved_idx` | `resolved` |

---

## 5. Service-Layer Summary

| Function | Purpose |
| --- | --- |
| `compute_priority_score` | `failure_count × stage_weight × goal_weight` (quantized) |
| `assign_priority` | Maps score to low / medium / high / critical bands |
| `get_stage_weight` | Deterministic stage multipliers |
| `get_goal_weight` | Deterministic long-term goal multipliers |
| `get_global_failure_count` | User-scoped count of rejected/auto-rejected apps mentioning skill |
| `create_or_update_gap` | `update_or_create` with computed weights and priority |
| `mark_gap_resolved` | Sets `resolved`, `resolved_date`, `resolved_tier` |

Return type: frozen `SkillGapUpsertResult` dataclass for upsert calls.

---

## 6. Manual / Advisory / Claim-Safe Behaviour

- No automatic gap creation from job boards or scraping
- No predictive AI/ML wording in services
- `get_global_failure_count` is historical evidence from saved applications only
- Mutations only through explicit service calls (`create_or_update_gap`, `mark_gap_resolved`)
- No `/skill-gaps/` dashboard route or views

---

## 7. What Was Deliberately Not Changed

- `apps/applications/models.py` and `choices.py`
- Application workflow, dashboard templates, README, GitHub workflows
- Sprint 41 Skill Intelligence page (separate advisory UI)
- Sprint 44 scope (MasterSkillProfile, Learning ROI, dashboard route, interview prep bridge)

---

## 8. SQL Migration Review Summary

Proof file (outside repo): `G:\workflow_tools\sprint43_sqlmigrate_skill_gaps_0001.txt`

SQL review highlights:

- Creates `skill_gaps_applicationskillgap` with FK to `applications_jobapplication` (`ON DELETE` via Django CASCADE)
- Enforces `uniq_application_skill_gap_stage` UNIQUE on `(application_id, skill_name, stage)`
- Creates five named indexes plus Django FK index
- No destructive alterations to existing tables

---

## 9. Test Coverage Summary

**File:** `apps/skill_gaps/tests.py` — **14 tests**

| Area | Tests |
| --- | ---: |
| Model create + unique constraint + Meta | 3 |
| Scoring and weights | 3 |
| Failure count (status + user scope) | 3 |
| create_or_update + mark_gap_resolved | 2 |
| Sprint guards (no route, no Sprint 44 copy, claim language) | 3 |

---

## 10. Validation Commands

```powershell
python manage.py makemigrations skill_gaps
python manage.py migrate skill_gaps
python manage.py sqlmigrate skill_gaps 0001 > G:\workflow_tools\sprint43_sqlmigrate_skill_gaps_0001.txt
python manage.py test apps.skill_gaps.tests
ruff check apps/skill_gaps/
```

---

## Files Created (Sprint 43)

- `apps/skill_gaps/` (app package, model, services, admin, tests, migration)
- `config/settings/base.py` (added `apps.skill_gaps`)
- `docs/evidence/sprint_43_skill_gap_foundation.md`
- `docs/evidence/evidence_index.md` (updated)

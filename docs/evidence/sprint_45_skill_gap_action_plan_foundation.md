# Sprint 45 - Skill Gap Action Plan Foundation Evidence

## 1. Sprint Objective

Sprint 45 extends the read-only `/skill-gaps/` dashboard with a **Manual action plan** section that helps the user see suggested next steps from existing saved `ApplicationSkillGap` records - without creating gaps, learning plans, or any automation.

**Branch:** `sprint-45-skill-gap-action-plan-foundation`

---

## 2. Baseline from Sprint 44

| Sprint 44 | Sprint 45 extension |
| --- | --- |
| `/skill-gaps/` dashboard | Same route - no new URL |
| User-scoped gap list + GET filters | Unchanged |
| Summary KPI cards | Unchanged |
| Read-only GET view | Unchanged - action plan added above table |

---

## 3. Action-Plan Section Summary

**Location:** `#manual-action-plan` on `templates/skill_gaps/dashboard.html`

**Service helpers** (`apps/skill_gaps/services.py`):

| Function | Role |
| --- | --- |
| `get_action_plan_items(user)` | Unresolved gaps, `-priority_score` order |
| `group_action_plan_items(...)` | Splits into priority groups + resolved context |
| `build_skill_gap_action_plan_context(user)` | Full read-only action-plan context |

**Groups:**

1. High-priority unresolved gaps (`high`, `critical`)
2. Medium-priority unresolved gaps
3. Lower-priority backlog (`low`)
4. Resolved context (informational only)

**Empty state:** When no unresolved gaps exist.

---

## 4. User-Scoping Behaviour

- Action plan built from `get_user_skill_gaps_queryset(user)` - same `application__user` filter as Sprint 44
- Included in `build_skill_gap_dashboard_context` for every dashboard GET
- Tests confirm other users' gaps never appear in action-plan groups

---

## 5. Read-Only Behaviour

- No POST forms in action-plan section
- View does not call `create_or_update_gap`, `mark_gap_resolved`, `.save()`, `.delete()`, or `.update()`
- Dashboard GET does not change skill-gap record counts
- List GET filters apply only to the table below; action plan always reflects all unresolved saved gaps

---

## 6. Advisory / Manual Wording

- Manual action plan
- Suggested next steps
- Advisory only
- Based on saved skill-gap records
- Review and decide manually
- Does not create learning plans or change gap records

---

## 7. What Was Deliberately Not Changed

- `apps/skill_gaps/models.py`, migrations, `urls.py`, `config/urls.py`
- `apps/applications/*`, README, GitHub workflows, CSS/JS
- Sprint 46 scope (MasterSkillProfile, Learning ROI, interview prep bridge, auto gap creation)

---

## 8. Claim-Safety Notes

No claims for: predictions, AI/ML, auto-apply, auto-send, Gmail/Calendar/OAuth, scraping, background polling, live SaaS, or production deployment.

Priority grouping is rule-based from saved `priority` field - not predictive hiring advice.

---

## 9. Test Coverage Summary

**File:** `apps/skill_gaps/tests.py` - **34 tests** total (**8** new action-plan tests)

| Action-plan test | Focus |
| --- | --- |
| Section on dashboard | Manual action plan copy |
| User scoping | Other user gaps excluded |
| Priority grouping | Critical in high group, low in backlog |
| Resolved exclusion | Primary groups exclude resolved |
| Empty unresolved state | Copy + `has_unresolved=False` |
| GET no mutation | Record count unchanged |
| Item ordering | `-priority_score` on unresolved queryset |
| Claim language | Forbidden terms absent |

Sprint 43/44 dashboard tests updated for action-plan coexisting with table filters.

---

## 10. Validation Commands

```powershell
python manage.py makemigrations --check --dry-run
python manage.py test apps.skill_gaps.tests
ruff check apps/skill_gaps/
```

---

## Files Changed (Sprint 45)

- `apps/skill_gaps/services.py`
- `apps/skill_gaps/views.py`
- `apps/skill_gaps/tests.py`
- `templates/skill_gaps/dashboard.html`
- `docs/evidence/sprint_45_skill_gap_action_plan_foundation.md`
- `docs/evidence/evidence_index.md`

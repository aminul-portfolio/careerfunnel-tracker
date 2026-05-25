# Sprint 46 - Skill Gap Learning Plan Foundation Evidence

## 1. Sprint Objective

Sprint 46 extends the read-only `/skill-gaps/` dashboard with a **Manual learning plan** section that helps the user see practical learning focus areas from existing saved `ApplicationSkillGap` records - without creating courses, learning records, gaps, or any automation.

**Branch:** `sprint-46-skill-gap-learning-plan-foundation`

---

## 2. Baseline from Sprint 45

| Sprint 45 | Sprint 46 extension |
| --- | --- |
| `/skill-gaps/` dashboard | Same route - no new URL |
| Manual action plan section | Unchanged |
| User-scoped gap list + GET filters | Unchanged |
| Read-only GET view | Unchanged - learning plan added above table |

---

## 3. Learning-Plan Section Summary

**Location:** `#manual-learning-plan` on `templates/skill_gaps/dashboard.html`

**Service helpers** (`apps/skill_gaps/services.py`):

| Function | Role |
| --- | --- |
| `get_learning_plan_items(user)` | Unresolved gaps, `-priority_score` order |
| `group_learning_plan_items(...)` | Splits into learning-focus groups + resolved context |
| `build_skill_gap_learning_plan_context(user)` | Full read-only learning-plan context |

**Groups:**

1. Immediate learning focus (`high`, `critical`)
2. Practice next (`medium`)
3. Backlog learning items (`low`)
4. Resolved learning context (informational only)

**Empty state:** When no unresolved gaps exist.

---

## 4. User-Scoping Behaviour

- Learning plan built from `get_user_skill_gaps_queryset(user)` - same `application__user` filter as Sprint 44/45
- Included in `build_skill_gap_dashboard_context` for every dashboard GET
- Tests confirm other users' gaps never appear in learning-plan groups

---

## 5. Read-Only Behaviour

- No POST forms in learning-plan section
- View does not call `create_or_update_gap`, `mark_gap_resolved`, `.save()`, `.delete()`, or `.update()`
- Dashboard GET does not change skill-gap record counts
- List GET filters apply only to the table below; learning plan always reflects all unresolved saved gaps

---

## 6. Advisory / Manual Wording

- Manual learning plan
- Learning focus
- Suggested practice
- Advisory only
- Based on saved skill-gap records
- Review and decide manually
- Does not create courses or change gap records

---

## 7. What Was Deliberately Not Changed

- `apps/skill_gaps/models.py`, migrations, `urls.py`, `config/urls.py`
- `apps/applications/*`, README, GitHub workflows, CSS/JS
- Sprint 47 scope (MasterSkillProfile, Learning ROI, interview prep bridge, auto gap/learning creation)

---

## 8. Claim-Safety Notes

No claims for: predictions, AI/ML, auto-apply, auto-send, Gmail/Calendar/OAuth, scraping, background polling, live SaaS, or production deployment.

Learning focus grouping is rule-based from saved `priority` field - not predictive hiring or learning advice.

---

## 9. ASCII / Encoding Cleanup Note

All Sprint 46 user-facing copy uses ASCII punctuation only (hyphens, straight apostrophes). No em dashes, middle dots, or curly quotes in changed template or service strings. Tests assert ASCII safety on changed files.

---

## 10. Test Coverage Summary

**File:** `apps/skill_gaps/tests.py` - **44 tests** total (**10** new learning-plan tests)

| Learning-plan test | Focus |
| --- | --- |
| Section on dashboard | Manual learning plan copy |
| User scoping | Other user gaps excluded |
| Priority grouping | Critical in immediate focus, low in backlog |
| Resolved exclusion | Primary groups exclude resolved |
| Empty unresolved state | Copy + `has_unresolved=False` |
| GET no mutation | Record count unchanged |
| Item ordering | `-priority_score` on unresolved queryset |
| Claim language | Forbidden terms absent |
| No migrations | Still only `0001_initial.py` |
| ASCII safety | Changed files are 7-bit clean |

Sprint 43/44/45 tests updated: dashboard guard renamed to `test_no_sprint_47_text_on_dashboard_page`.

---

## 11. Validation Commands

```powershell
python manage.py makemigrations --check --dry-run
python manage.py test apps.skill_gaps.tests
ruff check apps/skill_gaps/
```

---

## Files Changed (Sprint 46)

- `apps/skill_gaps/services.py`
- `apps/skill_gaps/views.py`
- `apps/skill_gaps/tests.py`
- `templates/skill_gaps/dashboard.html`
- `docs/evidence/sprint_46_skill_gap_learning_plan_foundation.md`
- `docs/evidence/evidence_index.md`

# Sprint 50 - Skill Gap CV Bullet Mapping Foundation Evidence

## 1. Sprint Objective

Sprint 50 extends the read-only `/skill-gaps/` dashboard with a **Manual CV bullet mapping** section that helps the user connect unresolved skill gaps to practical CV bullet prompts - without writing final CV bullets, rewriting CVs automatically, or any automation.

**Branch:** `sprint-50-skill-gap-cv-bullet-mapping`

---

## 2. Baseline from Sprint 49

| Sprint 49 | Sprint 50 extension |
| --- | --- |
| `/skill-gaps/` dashboard | Same route - no new URL |
| Manual sections through interview story mapping | Unchanged |
| User-scoped gap list + GET filters | Unchanged |
| Read-only GET view | Unchanged - CV bullet mapping added above table |

---

## 3. CV Bullet Mapping Section Summary

**Location:** `#manual-cv-bullet-mapping` on `templates/skill_gaps/dashboard.html`

**Service helpers** (`apps/skill_gaps/services.py`):

| Function | Role |
| --- | --- |
| `get_cv_bullet_mapping_items(user)` | Unresolved gaps, `-priority_score` order |
| `group_cv_bullet_mapping_items(...)` | Splits into CV bullet groups + resolved context |
| `build_skill_gap_cv_bullet_mapping_context(user)` | Full read-only CV bullet mapping context |

**Groups:**

1. Draft CV bullet prompts now (`high`, `critical`)
2. Strengthen CV evidence next (`medium`)
3. CV bullet backlog (`low`)
4. Resolved CV context (informational only)

**Manual prompts:** skill evidence, project evidence, business impact, data-quality/reconciliation, dashboard/reporting, action/result, keyword alignment - all labeled as manual prompts.

**Empty state:** When no unresolved gaps exist.

---

## 4. User-Scoping Behaviour

- CV bullet mapping built from `get_user_skill_gaps_queryset(user)` - same `application__user` filter as prior sprints
- Included in `build_skill_gap_dashboard_context` for every dashboard GET
- Tests confirm other users' gaps never appear in CV bullet mapping groups

---

## 5. Read-Only Behaviour

- No POST forms in CV bullet mapping section
- View does not call `create_or_update_gap`, `mark_gap_resolved`, `.save()`, `.delete()`, or `.update()`
- Dashboard GET does not change skill-gap record counts
- List GET filters apply only to the table below; mapping section always reflects all unresolved saved gaps

---

## 6. Advisory / Manual Wording

- Manual CV bullet mapping
- CV bullet focus
- Suggested CV bullet prompts
- Advisory only
- Based on saved skill-gap records
- Review and decide manually
- Does not rewrite CV automatically; prompts only

---

## 7. What Was Deliberately Not Changed

- `apps/skill_gaps/models.py`, migrations, `urls.py`, `config/urls.py`
- `apps/applications/*`, README, GitHub workflows, CSS/JS
- Sprint 51 scope (MasterSkillProfile, Learning ROI, automated interview prep bridge, auto CV bullet creation)

---

## 8. Claim-Safety Notes

No claims for: predictions, AI/ML, auto-apply, auto-send, automatic CV rewriting, Gmail/Calendar/OAuth, scraping, background polling, live SaaS, or production deployment.

CV grouping is rule-based from saved `priority` field - not predictive hiring advice. Prompts do not assert bullets or evidence already exist.

---

## 9. ASCII / Encoding Cleanup Note

All Sprint 50 user-facing copy uses ASCII punctuation only (hyphens, straight apostrophes). No em dashes, middle dots, or curly quotes in changed template or service strings. Tests assert ASCII safety on changed files.

---

## 10. Test Coverage Summary

**File:** `apps/skill_gaps/tests.py` - **84 tests** total (**10** new CV-bullet tests)

| CV-bullet test | Focus |
| --- | --- |
| Section on dashboard | Manual CV bullet mapping + prompt copy |
| User scoping | Other user gaps excluded |
| Priority grouping | Critical in draft now, low in backlog |
| Resolved exclusion | Primary groups exclude resolved |
| Empty unresolved state | Copy + `has_unresolved=False` |
| GET no mutation | Record count unchanged |
| Item ordering | `-priority_score` on unresolved queryset |
| Claim language | Forbidden terms + no automatic CV rewriting |
| No migrations | Still only `0001_initial.py` |
| ASCII safety | Changed files are 7-bit clean |

Dashboard guard renamed to `test_no_sprint_51_text_on_dashboard_page`.

---

## 11. Validation Commands

```powershell
python manage.py makemigrations --check --dry-run
python manage.py test apps.skill_gaps.tests
ruff check apps/skill_gaps/
```

---

## Files Changed (Sprint 50)

- `apps/skill_gaps/services.py`
- `apps/skill_gaps/views.py`
- `apps/skill_gaps/tests.py`
- `templates/skill_gaps/dashboard.html`
- `docs/evidence/sprint_50_skill_gap_cv_bullet_mapping.md`
- `docs/evidence/evidence_index.md`

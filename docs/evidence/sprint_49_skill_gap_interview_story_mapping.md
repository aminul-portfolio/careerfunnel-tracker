# Sprint 49 - Skill Gap Interview Story Mapping Foundation Evidence

## 1. Sprint Objective

Sprint 49 extends the read-only `/skill-gaps/` dashboard with a **Manual interview story mapping** section that helps the user connect unresolved skill gaps to practical interview story prompts (STAR-style) - without creating interview prep records, rewriting CVs, or any automation.

**Branch:** `sprint-49-skill-gap-interview-story-mapping`

---

## 2. Baseline from Sprint 48

| Sprint 48 | Sprint 49 extension |
| --- | --- |
| `/skill-gaps/` dashboard | Same route - no new URL |
| Manual action plan through portfolio evidence mapping | Unchanged |
| User-scoped gap list + GET filters | Unchanged |
| Read-only GET view | Unchanged - interview story mapping added above table |

---

## 3. Interview Story Mapping Section Summary

**Location:** `#manual-interview-story-mapping` on `templates/skill_gaps/dashboard.html`

**Service helpers** (`apps/skill_gaps/services.py`):

| Function | Role |
| --- | --- |
| `get_interview_story_mapping_items(user)` | Unresolved gaps, `-priority_score` order |
| `group_interview_story_mapping_items(...)` | Splits into story-focus groups + resolved context |
| `build_skill_gap_interview_story_mapping_context(user)` | Full read-only interview story mapping context |

**Groups:**

1. Prepare interview stories now (`high`, `critical`)
2. Strengthen evidence stories next (`medium`)
3. Story backlog (`low`)
4. Resolved story context (informational only)

**Manual story prompts:** situation, task, action, result, business impact, data-quality/reconciliation, dashboard/reporting explanation, learning/improvement - all labeled as manual prompts.

**Empty state:** When no unresolved gaps exist.

---

## 4. User-Scoping Behaviour

- Interview story mapping built from `get_user_skill_gaps_queryset(user)` - same `application__user` filter as prior sprints
- Included in `build_skill_gap_dashboard_context` for every dashboard GET
- Tests confirm other users' gaps never appear in story mapping groups

---

## 5. Read-Only Behaviour

- No POST forms in interview story mapping section
- View does not call `create_or_update_gap`, `mark_gap_resolved`, `.save()`, `.delete()`, or `.update()`
- Dashboard GET does not change skill-gap record counts
- List GET filters apply only to the table below; mapping section always reflects all unresolved saved gaps

---

## 6. Advisory / Manual Wording

- Manual interview story mapping
- Interview story focus
- Suggested story prompts
- Advisory only
- Based on saved skill-gap records
- Review and decide manually
- Story prompts are manual only - not completed interview evidence unless saved

---

## 7. What Was Deliberately Not Changed

- `apps/skill_gaps/models.py`, migrations, `urls.py`, `config/urls.py`
- `apps/applications/*`, README, GitHub workflows, CSS/JS
- Sprint 50 scope (MasterSkillProfile, Learning ROI, automated interview prep bridge, auto story creation)

---

## 8. Claim-Safety Notes

No claims for: predictions, AI/ML, auto-apply, auto-send, Gmail/Calendar/OAuth, scraping, background polling, live SaaS, or production deployment.

Story grouping is rule-based from saved `priority` field - not predictive hiring advice. Prompts do not assert stories already exist.

---

## 9. ASCII / Encoding Cleanup Note

All Sprint 49 user-facing copy uses ASCII punctuation only (hyphens, straight apostrophes). No em dashes, middle dots, or curly quotes in changed template or service strings. Tests assert ASCII safety on changed files.

---

## 10. Test Coverage Summary

**File:** `apps/skill_gaps/tests.py` - **74 tests** total (**10** new interview-story tests)

| Interview-story test | Focus |
| --- | --- |
| Section on dashboard | Manual interview story mapping + STAR prompt copy |
| User scoping | Other user gaps excluded |
| Priority grouping | Critical in prepare now, low in backlog |
| Resolved exclusion | Primary groups exclude resolved |
| Empty unresolved state | Copy + `has_unresolved=False` |
| GET no mutation | Record count unchanged |
| Item ordering | `-priority_score` on unresolved queryset |
| Claim language | Forbidden terms absent |
| No migrations | Still only `0001_initial.py` |
| ASCII safety | Changed files are 7-bit clean |

Dashboard guard renamed to `test_no_sprint_50_text_on_dashboard_page`.

---

## 11. Validation Commands

```powershell
python manage.py makemigrations --check --dry-run
python manage.py test apps.skill_gaps.tests
ruff check apps/skill_gaps/
```

---

## Files Changed (Sprint 49)

- `apps/skill_gaps/services.py`
- `apps/skill_gaps/views.py`
- `apps/skill_gaps/tests.py`
- `templates/skill_gaps/dashboard.html`
- `docs/evidence/sprint_49_skill_gap_interview_story_mapping.md`
- `docs/evidence/evidence_index.md`

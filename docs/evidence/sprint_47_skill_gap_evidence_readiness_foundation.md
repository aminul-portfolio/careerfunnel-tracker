# Sprint 47 - Skill Gap Evidence Readiness Foundation Evidence

## 1. Sprint Objective

Sprint 47 extends the read-only `/skill-gaps/` dashboard with a **Manual evidence readiness** section that helps the user see which unresolved skill gaps need stronger portfolio, CV, interview, or reporting evidence - without creating files, rewriting CVs, or any automation.

**Branch:** `sprint-47-skill-gap-evidence-readiness-foundation`

---

## 2. Baseline from Sprint 46

| Sprint 46 | Sprint 47 extension |
| --- | --- |
| `/skill-gaps/` dashboard | Same route - no new URL |
| Manual action plan + learning plan sections | Unchanged |
| User-scoped gap list + GET filters | Unchanged |
| Read-only GET view | Unchanged - evidence readiness added above table |

---

## 3. Evidence-Readiness Section Summary

**Location:** `#manual-evidence-readiness` on `templates/skill_gaps/dashboard.html`

**Service helpers** (`apps/skill_gaps/services.py`):

| Function | Role |
| --- | --- |
| `get_evidence_readiness_items(user)` | Unresolved gaps, `-priority_score` order |
| `group_evidence_readiness_items(...)` | Splits into evidence-focus groups + resolved context |
| `build_skill_gap_evidence_readiness_context(user)` | Full read-only evidence-readiness context |

**Groups:**

1. Evidence needed now (`high`, `critical`)
2. Strengthen next (`medium`)
3. Evidence backlog (`low`)
4. Resolved evidence context (informational only)

**Evidence prompts per item (advisory):** portfolio project, CV bullet, interview story, dashboard/reporting.

**Empty state:** When no unresolved gaps exist.

---

## 4. User-Scoping Behaviour

- Evidence readiness built from `get_user_skill_gaps_queryset(user)` - same `application__user` filter as prior sprints
- Included in `build_skill_gap_dashboard_context` for every dashboard GET
- Tests confirm other users' gaps never appear in evidence-readiness groups

---

## 5. Read-Only Behaviour

- No POST forms in evidence-readiness section
- View does not call `create_or_update_gap`, `mark_gap_resolved`, `.save()`, `.delete()`, or `.update()`
- Dashboard GET does not change skill-gap record counts
- List GET filters apply only to the table below; evidence section always reflects all unresolved saved gaps

---

## 6. Advisory / Manual Wording

- Manual evidence readiness
- Evidence focus
- Suggested evidence
- Advisory only
- Based on saved skill-gap records
- Review and decide manually
- Does not create files or rewrite CVs

---

## 7. What Was Deliberately Not Changed

- `apps/skill_gaps/models.py`, migrations, `urls.py`, `config/urls.py`
- `apps/applications/*`, README, GitHub workflows, CSS/JS
- Sprint 48 scope (MasterSkillProfile, Learning ROI, automated interview prep bridge, auto evidence creation)

---

## 8. Claim-Safety Notes

No claims for: predictions, AI/ML, auto-apply, auto-send, Gmail/Calendar/OAuth, scraping, background polling, live SaaS, or production deployment.

Evidence grouping is rule-based from saved `priority` field - not predictive hiring advice.

---

## 9. ASCII / Encoding Cleanup Note

All Sprint 47 user-facing copy uses ASCII punctuation only (hyphens, straight apostrophes). No em dashes, middle dots, or curly quotes in changed template or service strings. Tests assert ASCII safety on changed files.

---

## 10. Test Coverage Summary

**File:** `apps/skill_gaps/tests.py` - **54 tests** total (**10** new evidence-readiness tests)

| Evidence-readiness test | Focus |
| --- | --- |
| Section on dashboard | Manual evidence readiness + prompt copy |
| User scoping | Other user gaps excluded |
| Priority grouping | Critical in evidence needed now, low in backlog |
| Resolved exclusion | Primary groups exclude resolved |
| Empty unresolved state | Copy + `has_unresolved=False` |
| GET no mutation | Record count unchanged |
| Item ordering | `-priority_score` on unresolved queryset |
| Claim language | Forbidden terms absent |
| No migrations | Still only `0001_initial.py` |
| ASCII safety | Changed files are 7-bit clean |

Dashboard guard renamed to `test_no_sprint_48_text_on_dashboard_page`.

---

## 11. Validation Commands

```powershell
python manage.py makemigrations --check --dry-run
python manage.py test apps.skill_gaps.tests
ruff check apps/skill_gaps/
```

---

## Files Changed (Sprint 47)

- `apps/skill_gaps/services.py`
- `apps/skill_gaps/views.py`
- `apps/skill_gaps/tests.py`
- `templates/skill_gaps/dashboard.html`
- `docs/evidence/sprint_47_skill_gap_evidence_readiness_foundation.md`
- `docs/evidence/evidence_index.md`

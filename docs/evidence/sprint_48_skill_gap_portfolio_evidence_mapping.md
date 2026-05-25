# Sprint 48 - Skill Gap Portfolio Evidence Mapping Foundation Evidence

## 1. Sprint Objective

Sprint 48 extends the read-only `/skill-gaps/` dashboard with a **Manual portfolio evidence mapping** section that helps the user connect unresolved skill gaps to practical proof ideas across portfolio projects, CV bullets, interview stories, and reporting evidence - without creating proof files, rewriting CVs, or any automation.

**Branch:** `sprint-48-skill-gap-portfolio-evidence-mapping`

---

## 2. Baseline from Sprint 47

| Sprint 47 | Sprint 48 extension |
| --- | --- |
| `/skill-gaps/` dashboard | Same route - no new URL |
| Manual action plan, learning plan, evidence readiness | Unchanged |
| User-scoped gap list + GET filters | Unchanged |
| Read-only GET view | Unchanged - portfolio mapping added above table |

---

## 3. Portfolio Evidence Mapping Section Summary

**Location:** `#manual-portfolio-evidence-mapping` on `templates/skill_gaps/dashboard.html`

**Service helpers** (`apps/skill_gaps/services.py`):

| Function | Role |
| --- | --- |
| `get_portfolio_evidence_mapping_items(user)` | Unresolved gaps, `-priority_score` order |
| `group_portfolio_evidence_mapping_items(...)` | Splits into mapping groups + resolved context |
| `build_skill_gap_portfolio_evidence_mapping_context(user)` | Full read-only portfolio mapping context |

**Groups:**

1. Map to portfolio proof now (`high`, `critical`)
2. Strengthen CV/interview evidence next (`medium`)
3. Evidence backlog (`low`)
4. Resolved evidence mapping context (informational only)

**Manual proof prompts (not claims of existing proof):** portfolio project, CV bullet, interview story, dashboard/reporting, business impact, data-quality/reconciliation where relevant.

**Empty state:** When no unresolved gaps exist.

---

## 4. User-Scoping Behaviour

- Portfolio mapping built from `get_user_skill_gaps_queryset(user)` - same `application__user` filter as prior sprints
- Included in `build_skill_gap_dashboard_context` for every dashboard GET
- Tests confirm other users' gaps never appear in portfolio mapping groups

---

## 5. Read-Only Behaviour

- No POST forms in portfolio mapping section
- View does not call `create_or_update_gap`, `mark_gap_resolved`, `.save()`, `.delete()`, or `.update()`
- Dashboard GET does not change skill-gap record counts
- List GET filters apply only to the table below; mapping section always reflects all unresolved saved gaps

---

## 6. Advisory / Manual Wording

- Manual portfolio evidence mapping
- Portfolio proof focus
- Suggested proof ideas
- Advisory only
- Based on saved skill-gap records
- Review and decide manually
- Proof prompts only - not proof that already exists unless saved

---

## 7. What Was Deliberately Not Changed

- `apps/skill_gaps/models.py`, migrations, `urls.py`, `config/urls.py`
- `apps/applications/*`, README, GitHub workflows, CSS/JS
- Sprint 49 scope (MasterSkillProfile, Learning ROI, automated interview prep bridge, auto portfolio evidence creation)

---

## 8. Claim-Safety Notes

No claims for: predictions, AI/ML, auto-apply, auto-send, Gmail/Calendar/OAuth, scraping, background polling, live SaaS, or production deployment.

Portfolio grouping is rule-based from saved `priority` field - not predictive hiring advice. Prompts do not assert proof already exists.

---

## 9. ASCII / Encoding Cleanup Note

All Sprint 48 user-facing copy uses ASCII punctuation only (hyphens, straight apostrophes). No em dashes, middle dots, or curly quotes in changed template or service strings. Tests assert ASCII safety on changed files.

---

## 10. Test Coverage Summary

**File:** `apps/skill_gaps/tests.py` - **64 tests** total (**10** new portfolio-mapping tests)

| Portfolio-mapping test | Focus |
| --- | --- |
| Section on dashboard | Manual portfolio mapping + proof prompt copy |
| User scoping | Other user gaps excluded |
| Priority grouping | Critical in map now, low in backlog |
| Resolved exclusion | Primary groups exclude resolved |
| Empty unresolved state | Copy + `has_unresolved=False` |
| GET no mutation | Record count unchanged |
| Item ordering | `-priority_score` on unresolved queryset |
| Claim language | Forbidden terms absent |
| No migrations | Still only `0001_initial.py` |
| ASCII safety | Changed files are 7-bit clean |

Dashboard guard renamed to `test_no_sprint_49_text_on_dashboard_page`.

---

## 11. Validation Commands

```powershell
python manage.py makemigrations --check --dry-run
python manage.py test apps.skill_gaps.tests
ruff check apps/skill_gaps/
```

---

## Files Changed (Sprint 48)

- `apps/skill_gaps/services.py`
- `apps/skill_gaps/views.py`
- `apps/skill_gaps/tests.py`
- `templates/skill_gaps/dashboard.html`
- `docs/evidence/sprint_48_skill_gap_portfolio_evidence_mapping.md`
- `docs/evidence/evidence_index.md`

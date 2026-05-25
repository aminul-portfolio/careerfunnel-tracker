# Sprint 44 — Skill Intelligence Dashboard Foundation Evidence

## 1. Sprint Objective

Sprint 44 adds a **read-only Skill Intelligence Dashboard** that surfaces saved `ApplicationSkillGap` records from Sprint 43 in a user-scoped, claim-safe page. No automatic gap creation, no model changes, no Sprint 45 features.

**Branch:** `sprint-44-skill-intelligence-dashboard`

---

## 2. Baseline from Sprint 43

| Sprint 43 deliverable | Sprint 44 usage |
| --- | --- |
| `ApplicationSkillGap` model | Listed on dashboard |
| `apps.skill_gaps` services (mutation) | Unchanged; read-only helpers added |
| Admin registration | Still available for record management |
| No dashboard in Sprint 43 | `/skill-gaps/` added in Sprint 44 |

---

## 3. Dashboard Route / Page Summary

| Item | Value |
| --- | --- |
| URL path | `/skill-gaps/` |
| URL name | `skill_gaps:dashboard` |
| View | `apps.skill_gaps.views.dashboard` |
| Template | `templates/skill_gaps/dashboard.html` |
| Root include | `config/urls.py` → `path("skill-gaps/", include("apps.skill_gaps.urls"))` |

HTTP methods: **GET only** (`@require_http_methods(["GET"])`).

---

## 4. User-Scoping Behaviour

- `@login_required` on the view
- Queryset: `ApplicationSkillGap.objects.filter(application__user=request.user)`
- `select_related("application")` for company/job title display
- Tests confirm other users’ gaps never appear in HTML or service context

---

## 5. Read-Only Behaviour

- No create/update/delete actions on the dashboard
- Filter form uses **GET** only
- POST returns **405 Method Not Allowed**
- Copy states records are manually saved and not auto-created on this page

---

## 6. Filters / Summary Cards

**Summary cards** (always from full user queryset, not filter subset):

| Card | Logic |
| --- | --- |
| Total saved skill gaps | All user gaps |
| Unresolved | `resolved=False` |
| Resolved | `resolved=True` |
| High-priority gaps | `priority` in `high`, `critical` |

**GET filters** (list only):

| Parameter | Values |
| --- | --- |
| `priority` | low / medium / high / critical |
| `stage` | application / screening / technical / interview |
| `resolved` | yes / no |

**Table columns:** skill_name, application (company + role), stage, current_tier, priority, priority_score, resolved status, suggested_action.

---

## 7. What Was Deliberately Not Changed

- `apps/skill_gaps/models.py`
- `apps/skill_gaps/migrations/0001_initial.py`
- `apps/applications/*`
- README, GitHub workflows, unrelated CSS/JS/templates
- Sprint 41 Skill Intelligence page (`job_intelligence:skill_intelligence`) — separate advisory page
- Sprint 45 scope

---

## 8. Claim-Safety Notes

Page copy includes:

- Saved skill gaps
- Advisory only
- Based on manually saved application skill-gap records
- Not hiring decisions, predictions, or automatic CV changes

Does **not** claim: auto-apply, scraping, Gmail/Calendar/OAuth, predictive AI/ML, live SaaS, production deployment, or automatic gap creation.

---

## 9. Test Coverage Summary

**File:** `apps/skill_gaps/tests.py` — **26 tests** total (**12** new dashboard tests)

| Dashboard test | Focus |
| --- | --- |
| Login required | 302 when anonymous |
| Authenticated access | 200 + hero copy |
| User scoping | Other user gaps hidden |
| Empty state | No records message |
| Summary counts | Service + page context |
| Priority / stage / resolved filters | GET filter behaviour |
| Read-only | POST → 405, count unchanged |
| No new migrations | Only `0001_initial.py` |
| Sprint 45 guard | No Sprint 45 copy on page |
| Claim language | Forbidden terms absent |

---

## 10. Validation Commands

```powershell
python manage.py makemigrations --check --dry-run
python manage.py test apps.skill_gaps.tests
ruff check apps/skill_gaps/
```

Manual check (logged in):

```powershell
python manage.py runserver
# Visit http://127.0.0.1:8000/skill-gaps/
```

---

## Files Changed (Sprint 44)

- `apps/skill_gaps/views.py` (created)
- `apps/skill_gaps/urls.py` (created)
- `apps/skill_gaps/services.py` (read-only dashboard helpers)
- `apps/skill_gaps/tests.py` (dashboard tests)
- `templates/skill_gaps/dashboard.html` (created)
- `config/urls.py` (include route)
- `docs/evidence/sprint_44_skill_intelligence_dashboard.md`
- `docs/evidence/evidence_index.md`

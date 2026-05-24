# Sprint 37 - SaaS Foundation Audit + Design System Lock Evidence

## 1. Sprint Objective

Sprint 37 establishes a **foundation safety layer** before any premium redesign work. The sprint audits the Django shell, URL references, static assets, template safety, server-side rendering behaviour, and design-system direction - without changing product logic, models, migrations, or UI styling.

Sprint 37 is an **audit and lock sprint**, not a redesign sprint.

| Phase | Title | Summary |
| --- | --- | --- |
| **37A** | Shell, URL, and Static Audit Tests | Foundation smoke tests for navigation URLs, static references, accessibility landmarks, major page renders, and SSR safety |
| **37B** | Static Asset Audit Completion | Confirmed required CSS/JS source files, template `{% static %}` integrity, and non-critical JavaScript scope |
| **37C** | Design System Lock | Locked approved design direction: stable shell, token-first CSS, reserved `cf-*` future prefix, no mixed class migration without plan |
| **37D** | Smoke Test Completion + Evidence | Extended SSR coverage, evidence documentation, evidence index update |

**Branch:** `sprint-37-saas-foundation-audit-design-system-lock`
**37A commit:** `f5dc8c3` - Sprint 37A: add shell URL and static audit tests

---

## 2. What Was Audited

### Shell and navigation
- `templates/base.html`
- `templates/partials/sidebar.html`
- `templates/partials/navbar.html`
- `templates/partials/messages.html`

### Major authenticated surfaces
- Dashboard overview
- Applications list and evaluation queue
- Daily Log, Weekly Review, Interview Prep, Notes, Follow-ups
- Smart Review, AI Agents hub, Funnel Metrics, Export Centre
- Recruiter email import form and detail pages

### Static and design-system assets
- `static/css/tokens.css`
- `static/css/layout.css`
- `static/css/components.css`
- `static/css/career_evidence.css`
- `static/js/app.js`

### URL and redirect configuration
- Root `/` redirect
- Sidebar and navbar named URL targets
- Absence of invalid `dashboard:home` references

---

## 3. Route / Static / Template Safety Findings

| Check | Result |
| --- | --- |
| Sidebar URL names resolve | **Pass** - 12 sidebar links reverse successfully |
| Navbar auth URLs resolve | **Pass** - login, register, logout |
| Root redirect | **Pass** - `/` redirects to `dashboard:overview` |
| Invalid `dashboard:home` | **Pass** - not present in templates; not registered in URLconf |
| Required static source files | **Pass** - tokens, layout, components, career_evidence CSS; app.js |
| Template `{% static %}` references | **Pass** - all template static tags map to existing source files |
| Major authenticated pages render | **Pass** - 12 hub/list pages + recruiter email import/detail return HTTP 200 |
| Shell accessibility landmarks | **Pass** - `lang`, `aside`, `nav`, `main`, `header`, page content section |
| SSR before JavaScript | **Pass** - primary `<h1>` content and sidebar hrefs present before `app.js` on all major pages |
| Core stylesheet chain | **Pass** - authenticated shell includes tokens -> layout -> components |

**Broken references found:** none. No template, URL, or static fixes were required.

---

## 4. Design-System Lock Decision

### Decision

Lock the **current shell and token-first CSS architecture** as the approved baseline for future premium work. Do not redesign the shell in Sprint 37. Do not introduce parallel styling systems without an explicit migration plan.

### Approved design direction

1. **Keep the existing shell stable**
   - Preserve `app-shell`, fixed sidebar, `main-content`, topbar, and `page-content` structure.
   - Preserve current sidebar information architecture (Overview / Workflow / Analytics sections).

2. **CSS tokens remain the foundation**
   - `static/css/tokens.css` is the single source for colours, spacing-related radius values, typography (`--font-main`), shadows, and border tokens.
   - Layout structure stays in `layout.css`.
   - Reusable UI primitives stay in `components.css`.
   - Career Evidence pages may continue using `career_evidence.css` via `{% block extra_css %}` only.

3. **Future premium direction: product-level `cf-*` classes**
   - New premium components introduced in a future sprint should use a `cf-*` prefix (for example `cf-card`, `cf-shell`, `cf-nav-item`).
   - **No `cf-*` classes exist in the repository today.** This sprint reserves the prefix and migration rule only.
   - Do not mix legacy semantic classes (for example `content-card`, `sidebar-link`) with new `cf-*` classes on the same component without a documented migration step.

4. **JavaScript remains non-critical**
   - `static/js/app.js` only adds sidebar active-state styling.
   - Core page content, navigation links, forms, and tables must continue to render from Django templates without JavaScript.

5. **Avoid unplanned class-system mixing**
   - Do not add ad hoc inline styles or third-party CSS frameworks in foundation sprints.
   - Any visual refresh must extend tokens first, then layout/components, then introduce `cf-*` surfaces deliberately.

---

## 5. What Was Deliberately Not Changed

- Models and migrations
- Business logic and service functions
- Dashboard, form, or reporting redesign
- Template markup or CSS styling (audit only)
- README public claims
- GitHub workflow files
- Skill Intelligence Engine
- Gmail, Calendar, OAuth, auto-send, auto-apply, background polling, scraping, billing, or live SaaS deployment claims

---

## 6. Claim-Safety Confirmation

Sprint 37 does **not** introduce or imply:

- Gmail integration
- Calendar integration
- OAuth
- Auto-send or auto-apply
- Automatic application submission or status updates
- Background polling or scraping
- Billing or live SaaS / production deployment claims

The audit confirms existing manual, local, approval-based product boundaries remain intact. JavaScript does not gate core HTML rendering.

---

## 7. Test Coverage Summary

**File:** `tests/test_sprint_37a_shell_foundation_audit.py`

| Test class | Tests | Purpose |
| --- | ---: | --- |
| `SidebarAndNavbarUrlResolutionTests` | 3 | Sidebar/navbar URL resolution and root redirect |
| `InvalidDashboardHomeReferenceTests` | 2 | Guard against invalid `dashboard:home` |
| `RequiredStaticReferenceTests` | 2 | Static source files and template static tags |
| `DesignSystemLockTests` | 2 | Token foundation variables; app.js non-critical scope |
| `BaseShellStylesheetTests` | 1 | Core stylesheet chain in authenticated shell |
| `ShellAccessibilityLandmarkTests` | 1 | Basic accessibility landmarks |
| `MajorAuthenticatedPageRenderTests` | 2 | Major page renders + recruiter email pages |
| `ServerSideShellRenderTests` | 3 | SSR before JS on key and all major pages; sidebar links in HTML |

**Sprint 37 foundation audit suite:** **16 tests**

**37B-37D additions (on top of 37A):**
- `DesignSystemLockTests` - token variables and app.js scope
- `BaseShellStylesheetTests` - stylesheet chain
- `ServerSideShellRenderTests.test_all_major_authenticated_pages_render_primary_content_before_app_script` - full major-page SSR coverage

**Recommended validation runs:**

| Command | Expected |
| --- | --- |
| `python manage.py test` | App suite passes (441 tests) |
| `python manage.py test tests.test_sprint_37a_shell_foundation_audit` | 16 audit tests pass |
| `python manage.py test apps tests` | Combined suite passes (525 tests) |

---

## 8. Validation Commands

Run from repository root:

```powershell
ruff check .
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
python manage.py test tests.test_sprint_37a_shell_foundation_audit
python manage.py test apps tests
git status --short -uall
git diff --stat
```

---

## 9. Files Changed in Sprint 37

### 37A (committed `f5dc8c3`)
- `tests/test_sprint_37a_shell_foundation_audit.py` - initial 12 audit tests

### 37B-37D (this phase)
- `tests/test_sprint_37a_shell_foundation_audit.py` - 4 additional smoke/design-system tests (16 total)
- `docs/evidence/sprint_37_saas_foundation_audit.md` - this document
- `docs/evidence/evidence_index.md` - Sprint 37 index entry

No models, migrations, services, templates, or static CSS/JS were modified.

---

## 10. Reviewer Value

Sprint 37 proves the product shell is **safe to evolve** without hidden broken routes, missing static assets, or JavaScript-dependent core rendering. The design-system lock gives future premium work a clear rule set: stable shell, token-first CSS, reserved `cf-*` prefix, and no unplanned class mixing.

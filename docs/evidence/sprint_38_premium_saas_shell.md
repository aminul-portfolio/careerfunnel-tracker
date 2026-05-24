# Sprint 38 - Premium SaaS Shell: Navbar + Sidebar Evidence

## 1. Sprint Objective

Sprint 38 upgrades the **global shell and navigation** so CareerFunnel Tracker reads as one premium SaaS product while preserving manual, advisory, evidence-based, approval-based, and claim-safe operation.

This sprint changes **shell, sidebar, topbar, responsive controls, and shell tests only**. It does not redesign dashboard content, forms, or reporting pages.

| Phase | Title | Summary |
| --- | --- | --- |
| **38A** | Premium shell structure | Product logo area, trust badges, grouped sidebar, breadcrumb topbar |
| **38B** | Topbar controls | Environment badge, Quick Add menu, user menu |
| **38C** | Responsive + tests | Mobile drawer, overlay, Escape/click close, shell test coverage, evidence |

**Branch:** `sprint-38-premium-saas-shell-navbar-sidebar`

---

## 2. Shell / Navigation Changes Made

### Product logo area (sidebar)
- **CareerFunnel** brand title
- **Job Search Operating System** tagline
- Claim-safe trust badges: **Manual**, **Advisory**, **Evidence-based**

### Grouped sidebar navigation
Replaced Django-app-style section labels with product workflow groups and preserved all existing route targets.

### Premium topbar
- Breadcrumb: `CareerFunnel / {page heading}`
- Subtitle slot with default claim-safe operating copy
- **Local Portfolio Demo** environment badge
- **Quick Add** menu (SSR `<details>` - manual create links only)
- **User menu** with Profile, Settings, Logout

### Responsive shell
- Mobile navigation toggle button
- Sidebar overlay for drawer mode
- JavaScript adds `cf-js-ready` for progressive enhancement
- Without JavaScript: sidebar remains stacked/accessible on mobile
- Escape key and overlay click close drawer when JavaScript is available

### Active navigation
- Preserved longest-prefix active link behaviour
- Added `aria-current="page"` on active sidebar link via `app.js`

---

## 3. Product Workflow Groups Used

| Group | Navigation items |
| --- | --- |
| **Command** | Dashboard |
| **Pipeline** | Applications, Evaluation Queue, Follow-ups, Interview Prep |
| **Review** | Daily Log, Weekly Review, Notes & Decisions |
| **Intelligence** | Smart Review, AI Agents |
| **Reporting Suite** | Funnel Metrics, Export Centre |
| **Evidence** | Career Evidence |
| **Account** | Profile, Settings |

Profile links to the command centre (`dashboard:overview`). Settings links to Notes & Decisions (`notes:note_list`) as the local configuration/decision memory surface. Logout uses the existing accounts logout form.

---

## 4. Accessibility / Responsive Behaviour

- Skip link to `#main-content`
- Semantic landmarks preserved: `aside`, `nav`, `main`, `header`, page content section
- `aria-label` on primary sidebar navigation and breadcrumb
- `aria-controls`, `aria-expanded`, and labelled mobile toggle button
- `focus-visible` ring styles on shell controls
- `prefers-reduced-motion` support for sidebar transition tokens
- Quick Add and user menus use native `<details>` for keyboard access without JavaScript dependency
- Core page `<h1>` content still renders server-side before `app.js`

---

## 5. Claim-Safety Confirmation

Sprint 38 shell copy and controls do **not** introduce or imply:

- Gmail integration
- Calendar integration
- OAuth
- Auto-send or auto-apply
- Automatic application submission or status updates
- Background polling or scraping
- Billing/subscription features
- Live SaaS users or production deployment

Trust badges explicitly state **Manual**, **Advisory**, and **Evidence-based** operation. Quick Add links open manual create forms only. Environment badge reads **Local Portfolio Demo**.

---

## 6. What Was Deliberately Not Changed

- Models, migrations, and database schema
- Business logic and service functions
- Dashboard content layout and copy (hero, KPIs, Today Action, etc.)
- Forms and reporting page templates
- README public claims
- GitHub workflow files
- Skill Intelligence Engine

---

## 7. Test Coverage Summary

**File:** `tests/test_sprint_37a_shell_foundation_audit.py` (extended for Sprint 38 shell coverage)

| Area | Tests |
| --- | ---: |
| Sprint 37 foundation audit (URLs, static, SSR, landmarks) | 16 |
| Sprint 38 premium shell (`Sprint38PremiumShellTests`) | 9 |
| **Total shell audit suite** | **25** |

Sprint 38 tests verify:
- Premium shell markers render on dashboard
- Product navigation groups present
- Sidebar links resolve
- Quick Add menu and manual create links
- Mobile drawer controls exist
- `aria-current="page"` support in shell JavaScript
- Claim-safe trust badges
- User menu items (Profile, Settings, Logout)
- No invalid `dashboard:home` URL (inherited Sprint 37 guard)

---

## 8. Validation Commands

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

Expected:
- App suite passes (441 tests)
- Shell audit suite passes (25 tests)

---

## 9. Files Changed

- `templates/base.html`
- `templates/partials/sidebar.html`
- `templates/partials/navbar.html`
- `static/css/tokens.css`
- `static/css/layout.css`
- `static/css/components.css`
- `static/js/app.js`
- `tests/test_sprint_37a_shell_foundation_audit.py`
- `docs/evidence/sprint_38_premium_saas_shell.md`
- `docs/evidence/evidence_index.md`

---

## 10. Reviewer Value

Sprint 38 presents CareerFunnel Tracker as a coherent premium SaaS shell with product workflow language, claim-safe trust signals, and responsive navigation - while keeping all page content and business logic unchanged and preserving server-side rendering for core HTML.

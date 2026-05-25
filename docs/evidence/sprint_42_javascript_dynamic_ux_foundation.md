# Sprint 42 - JavaScript Dynamic UX Foundation Evidence

## 1. Sprint Objective

Sprint 42 adds **progressive JavaScript UX** so CareerFunnel Tracker feels more premium and dynamic while keeping Django server-rendered pages as the source of truth. Usability only - no hidden automation, no fetch/XHR database mutation, no JavaScript-dependent core content.

**Branch:** `sprint-42-javascript-dynamic-ux-foundation`

---

## 2. JavaScript Modules Implemented

| Module | Responsibility |
| --- | --- |
| `static/js/modules/toasts.js` | Local UI toast feedback (`CF.toast.show`) |
| `static/js/modules/confirmations.js` | `window.confirm` for risky manual actions |
| `static/js/modules/forms.js` | Unsaved-change warning + submit loading state |
| `static/js/modules/sidebar.js` | Active nav, mobile drawer, Escape/overlay close, collapse + `localStorage` |
| `static/js/modules/table-controls.js` | Debounced client-side row scan (visible rows only) |
| `static/js/modules/filters.js` | Server filter hint (no auto-submit) |
| `static/js/modules/copy-evidence.js` | Copy-to-clipboard for evidence paths |
| `static/js/modules/report-accordions.js` | Report/dashboard section expand/collapse |
| `static/js/app.js` | Module bootstrap (`cf-js-ready`) |

Loaded from `templates/base.html` in dependency order before `app.js`.

---

## 3. Progressive Enhancement Safety

- `html.no-js` removed at runtime; all core content renders without JS
- Primary `<h1>` content appears before script tags (SSR tests)
- Collapsed/hidden UI uses CSS that defaults to **visible** without JS
- `localStorage` stores sidebar collapse preference only (not business data)
- No `fetch`, `XMLHttpRequest`, polling, or autosave

---

## 4. Shell / Mobile UX Summary

- Desktop sidebar collapse toggle (`#sidebar-collapse-toggle`)
- Mobile drawer: toggle, overlay click, Escape key (unchanged behaviour, moved to `sidebar.js`)
- `cf-sidebar-collapsed` layout token (`--sidebar-collapsed-width`)
- Keyboard: `aria-expanded`, `aria-controls`, focus rings preserved

---

## 5. Table / Filter UX Summary

- **Applications list:** optional client-side row scan (`data-cf-client-table-filter`) - does not replace GET filter form
- **Metrics reports:** filter bar hint clarifies server-side Apply filters (no auto-submit)
- Debounced input (220ms) for client table scan only

---

## 6. Reporting / Dashboard UX Summary

- **Funnel metrics:** `data-cf-report-accordions` on report page - collapse toggles per `.cf-report-section`
- **Dashboard:** `data-cf-collapsible-card` on Week Pulse and Pipeline Health cards
- No fake live updates, polling, or background refresh

---

## 7. Copy / Toast Convenience Summary

- Career Evidence index: **Copy path** buttons (`data-cf-copy`) for source file paths
- Toast root in `base.html` - messages such as "Copied to clipboard (local UI only)."
- Toasts do not imply sync, automation, AI, or submission

---

## 8. No Hidden Automation Confirmation

JavaScript does not:

- Auto-apply or auto-send
- Scrape job boards or poll APIs
- Do not integrate Gmail, Calendar, or OAuth.
- Do not run predictive AI/ML.
- Claim live SaaS or production deployment

---

## 9. No Mutation Without Explicit User Action Confirmation

- No fetch/XHR writes
- POST forms still require explicit submit
- Follow-up **Mark Sent** uses `data-cf-confirm` before POST
- Form loading state runs only after user submits

---

## 10. What Was Deliberately Not Changed

- Models, migrations, database schema
- README and GitHub workflows
- Backend business logic (metrics, job intelligence scoring, applications)
- Recruiter email and interview prep workflows
- Sprint 43 scope

---

## 11. Test Coverage Summary

| File | Tests | Focus |
| --- | ---: | --- |
| `tests/test_sprint_42_javascript_dynamic_ux_foundation.py` | 11 | Static modules, hooks, SSR order, forbidden JS patterns, Sprint 43 guard |
| `tests/test_sprint_37a_shell_foundation_audit.py` | updated | `sidebar.js` active nav + Escape |

---

## 12. Validation Commands

```powershell
ruff check tests/test_sprint_42_javascript_dynamic_ux_foundation.py
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test tests.test_sprint_42_javascript_dynamic_ux_foundation tests.test_sprint_37a_shell_foundation_audit apps.dashboard.tests apps.job_intelligence.tests apps.metrics.tests
```

---

## Files Changed (Sprint 42)

- `static/js/app.js` + `static/js/modules/*.js` (8 modules)
- `static/css/tokens.css`, `layout.css`, `components.css`
- `templates/base.html`, `partials/sidebar.html`
- `templates/metrics/funnel_metrics.html`, `dashboard/overview.html`, `applications/application_list.html`, `dashboard/career_evidence/index.html`, `followups/followup_list.html`
- `tests/test_sprint_42_javascript_dynamic_ux_foundation.py`, `tests/test_sprint_37a_shell_foundation_audit.py`
- `docs/evidence/sprint_42_javascript_dynamic_ux_foundation.md`, `docs/evidence/evidence_index.md`

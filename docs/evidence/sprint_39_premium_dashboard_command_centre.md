# Sprint 39 — Premium Dashboard Command Centre Evidence

## 1. Sprint Objective

Sprint 39 upgrades the dashboard into a **Career Command Centre** that surfaces today’s strongest manual action, pipeline health, weekly pulse, evidence readiness, reporting confidence, and recent activity — using read-only service helpers and dashboard template changes only.

This sprint is **dashboard-only**. It does not redesign forms, reporting pages, models, migrations, or automation workflows.

**Branch:** `sprint-39-premium-dashboard-command-centre`

---

## 2. Dashboard Modules Added

| Module | Purpose |
| --- | --- |
| **Signature Career Insight** | One diagnosis, best manual action, why it matters, link to manual workflow |
| **Week Pulse** | Current week range, target vs actual, weekly review status, follow-ups due, interview prep status |
| **KPI Strip** | Total applications, this week, response rate, interview rate, data readiness |
| **Today Signals** | High / Medium / Low / Info priorities with reason, manual action, workflow link |
| **Pipeline Health Matrix** | Six discipline signals with score, status, and manual workflow links |
| **Funnel Snapshot** | Applications → Responses → Interviews → Offers |
| **Evidence Readiness** | Missing CV versions, job descriptions, required skills, follow-up data |
| **Weekly Operating Pipeline** | Capture → Analyze → Decide → Track → Review → Improve |
| **Recent Activity Timeline** | Latest application, daily log, weekly review, recruiter email, interview prep |
| **Reporting Confidence** | Existing funnel diagnosis panel retained with manual action copy |

---

## 3. Service / Helper Logic Summary

**File:** `apps/dashboard/services.py`

| Helper | Description |
| --- | --- |
| `build_week_pulse(user)` | Current week range, aggregated daily-log target/actual, weekly review status, follow-ups due, interview prep summary |
| `build_pipeline_health_matrix(user)` | Six scored discipline metrics with status labels and manual URLs |
| `build_evidence_readiness_summary(user)` | Data-quality counts via `build_data_quality_report(user)` |
| `build_today_signals(user)` | Maps `build_today_action_panel` to signals; adds Info empty-state signal when clear |
| `build_signature_career_insight(user)` | Top urgent signal or funnel diagnosis as signature insight |
| `build_funnel_snapshot(user)` | Application funnel stage counts from `build_funnel_metrics` |
| `build_weekly_operating_pipeline()` | Static six-step manual operating pipeline with workflow URLs |
| `build_recent_activity_timeline(user)` | Latest records across core tracker entities |
| `build_dashboard_context(user)` | Extended read-only dashboard context assembly |

All helpers are **read-only**. Dashboard GET does not mutate records.

---

## 4. Manual Workflow / Action-Link Safety

- Every command-centre action links to an existing manual page (application detail, create forms, list pages, metrics).
- Signature insight and pipeline health cards use explicit “Open manual workflow” links.
- Today Signals retain rule-based priorities from saved records only.
- Weekly Operating Pipeline copy states **Manual rhythm only** and does not trigger automatic actions.
- No automatic status updates, email sending, interview prep creation, auto-apply, or background polling.

---

## 5. Claim-Safety Confirmation

Sprint 39 dashboard copy confirms CareerFunnel Tracker:

- Does **not** submit applications
- Does **not** send email
- Does **not** update statuses automatically
- Does **not** create interview prep automatically
- Does **not** auto-apply or run background polling
- Does **not** claim live SaaS deployment

Guidance remains **manual, advisory, and evidence-based**.

---

## 6. What Was Deliberately Not Changed

- Models, migrations, and database schema
- Forms and reporting templates
- Recruiter email workflow logic
- Interview prep creation logic
- Global shell (Sprint 38)
- README public claims
- GitHub workflow files
- Skill Intelligence Engine

---

## 7. Test Coverage Summary

**File:** `apps/dashboard/tests.py`

| Test class | Tests | Focus |
| --- | ---: | --- |
| `DashboardCommandCentrePolishTests` | 14 | Command centre modules, claim safety, mutation safety, empty state, timeline, funnel snapshot |
| Existing dashboard tests | 14 | Updated for Today Signals / Weekly Operating Pipeline copy |

Key tests include:

- `test_dashboard_renders_career_command_centre_copy`
- `test_dashboard_shows_week_pulse`
- `test_dashboard_shows_pipeline_health_matrix`
- `test_dashboard_shows_evidence_readiness_summary`
- `test_dashboard_today_signals_remain_manual_and_claim_safe`
- `test_dashboard_get_does_not_mutate_records`
- `test_dashboard_links_to_manual_workflow_pages`
- `test_dashboard_empty_state_for_new_user`
- `test_dashboard_shows_recent_activity_timeline`
- `test_dashboard_shows_funnel_snapshot`
- `test_dashboard_does_not_claim_automation_or_live_saas`

**Dashboard test suite:** **28 tests** passing.

Shell audit test updated for new dashboard hero copy (`tests/test_sprint_37a_shell_foundation_audit.py`).

---

## 8. Validation Commands

```powershell
ruff check .
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test apps.dashboard.tests
python manage.py test tests.test_sprint_37a_shell_foundation_audit
python manage.py test apps tests
git status --short -uall
git diff --stat
```

---

## 9. Files Changed

- `apps/dashboard/services.py`
- `apps/dashboard/tests.py`
- `templates/dashboard/overview.html`
- `static/css/components.css`
- `tests/test_sprint_37a_shell_foundation_audit.py` (dashboard hero copy expectation)
- `docs/evidence/sprint_39_premium_dashboard_command_centre.md`
- `docs/evidence/evidence_index.md`

---

## 10. Reviewer Value

Sprint 39 presents the dashboard as a coherent **Career Command Centre** for portfolio review: one place to see manual priorities, weekly discipline, evidence gaps, funnel movement, and recent activity — without implying automation or live SaaS operation.

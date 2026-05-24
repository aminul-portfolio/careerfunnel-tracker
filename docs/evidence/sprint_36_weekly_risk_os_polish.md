# Sprint 36 — Weekly Risk / Final Operating System Polish Evidence

## 1. Sprint Objective

Sprint 36 polishes the **manual weekly operating system** across Weekly Review, AI Weekly Coach, Dashboard, and Today Action. The goal is clearer workflow copy, cross-links, and advisory risk guidance while preserving **local, manual, approval-based** operation. No new automation, external integrations, or database changes were introduced.

---

## 2. Implemented Phases

| Phase | Title | Summary |
| --- | --- | --- |
| **36A** | Weekly Review Workflow Clarity Polish | Manual workflow steps, trust copy, lessons learned on detail, navigation to Dashboard and AI Weekly Coach |
| **36B** | AI Weekly Coach / Risk Guidance Polish | Advisory trust copy, read-only latest Weekly Review card, claim-safe Agent Hub optional Claude wording, Weekly Review nav link |
| **36C** | Dashboard / Today Action Final Operating System Polish | Weekly operating rhythm strip, week-end weekly review Today Action prompt, diagnosis support links |
| **36D** | README / Evidence / Final Closure | README sprint position, evidence index, this document (documentation only) |

---

## 3. Files Changed by Phase

### 36A

- `apps/weekly_review/services.py`
- `apps/weekly_review/tests.py`
- `apps/weekly_review/views.py`
- `templates/weekly_review/weekly_review_confirm_delete.html`
- `templates/weekly_review/weekly_review_detail.html`
- `templates/weekly_review/weekly_review_form.html`
- `templates/weekly_review/weekly_review_list.html`

### 36B

- `apps/ai_agents/services.py`
- `apps/ai_agents/tests.py`
- `apps/ai_agents/views.py`
- `templates/ai_agents/_agent_nav.html`
- `templates/ai_agents/agent_dashboard.html`
- `templates/ai_agents/weekly_coach.html`

### 36C

- `apps/dashboard/services.py`
- `apps/dashboard/tests.py`
- `templates/dashboard/overview.html`

### 36D

- `README.md`
- `docs/evidence/evidence_index.md`
- `docs/evidence/sprint_36_weekly_risk_os_polish.md`

---

## 4. Claim-Safety Guarantees

- **Manual workflow only** — users create and edit Weekly Reviews; Today Action links open manual pages.
- **Local / rule-based guidance where applicable** — Weekly Coach and Today Action use tracker data and deterministic rules on the coach page.
- **Advisory guidance only** — coach output is not a guarantee; user compares with saved Weekly Review.
- **User approval required** — no automatic saves, sends, submissions, or status changes from Sprint 36 surfaces.
- **No Gmail integration**
- **No Calendar integration**
- **No OAuth**
- **No auto-send**
- **No auto-apply**
- **No automatic submission**
- **No automatic application status updates**
- **No automatic interview prep creation**
- **No background polling**
- **No scraping**
- **No production users** claimed
- **No live SaaS** deployment claim

Sprint 34 CV Tailoring optional Claude paths were **not modified** in Sprint 36. Sprint 35 interview/recruiter-email workflow logic was **not modified** (navigation references only).

---

## 5. Validation Evidence

| Check | Result |
| --- | --- |
| `WeeklyReviewWorkflowClaimSafetyTests` | 8 tests |
| `AiAgentWeeklyCoachPolishTests` | 7 tests |
| `DashboardWeeklyOsPolishTests` | 6 tests |
| Full project suite | **441 tests** passing |
| `ruff check .` | passed |
| `python manage.py check` | passed |
| `python manage.py makemigrations --check --dry-run` | no changes detected |

Representative commits on feature branch `sprint-36-weekly-risk-final-os-polish`:

- `721e044` — Sprint 36A: polish weekly review workflow
- `36ac7cd` — Sprint 36B: polish AI weekly coach guidance
- `66e0e84` — Sprint 36C: polish dashboard today action workflow

---

## 6. Public Wording

CareerFunnel Tracker includes a manual weekly operating workflow connecting Daily Logs, Applications, Weekly Review, AI Weekly Coach, Dashboard, and Today Action guidance. The workflow is advisory and approval-based: it helps users review activity, record weekly reflections, identify risks, and choose next manual actions. It does not send emails, sync Gmail or Calendar, auto-apply, submit applications, update statuses automatically, create interview prep automatically, run background polling, scrape job sites, or claim live SaaS production users.

---

## 7. What Is Not Implemented

- No Gmail integration
- No Calendar integration
- No OAuth
- No automatic email sending
- No auto-apply
- No automatic application submission
- No automatic application status update
- No automatic interview prep creation
- No background polling
- No scraping
- No production deployment claim
- No production user base claim

---

## 8. Closure Status

Sprint 36 implementation phases **36A–36C** are complete and validated on feature branch `sprint-36-weekly-risk-final-os-polish` (**441** tests).

Sprint **36D** updates README, evidence index, and this evidence document before final merge, tag, and push to `main`.

# Sprint 29 - Recruiter Email Workflow Enhancements

## Purpose

Sprint 29 improved the manual recruiter-email workflow on Application Detail so imported recruiter emails provide clearer action visibility, follow-up context, and interview-prep prompts.

The workflow remains:

```text
Manual import -> Rule-based summary -> User decision -> Manual follow-up or interview prep action
```

All recruiter email handling stays manual, rule-based, and advisory. CareerFunnel Tracker does not connect to inboxes, send messages, or mutate application records automatically.

---

## Starting state

| Item | State |
|---|---|
| Sprint 28 | Validated the intake workflow (manual assisted intake, recruiter email import foundation) |
| Sprint 29 baseline | Sprint 28D / Sprint 29A stable main |
| Latest Sprint 29C main commit | `4cbc147` |
| Latest Sprint 29C tag | `sprint-29c-interview-prep-trigger-complete` |
| Tests at Sprint 29C closure | 320 |
| GitHub Actions / Django CI | Passed for Sprint 29C |

---

## Sprint 29A - Recruiter Email Action Alerts

| Item | Detail |
|---|---|
| Tag | `sprint-29a-recruiter-email-action-alerts-complete` |
| Merge commit | `fb4c0b9` |

### What was added

- **Recruiter Email Actions** subsection on Application Detail inside the Recruiter Emails section.
- Per imported email visibility for:
  - **Needs reply** (when `requires_reply` is true and reply is not marked sent manually)
  - **Reply status**
  - **Action due** (when `action_due_at` is set)
  - **Suggested status** (suggestion only)
  - **Interview/screening signal** (when `matched_signals` contains interview or screening language)
- Preserved **Import Recruiter Email** button and imported email list with View links.
- Kept imported recruiter email handling **manual** and **rule-based**.

### Test progression

- Tests increased to **310** at Sprint 29A closure.

---

## Sprint 29B - Recruiter Communication Context / Follow-Up Integration

| Item | Detail |
|---|---|
| Tag | `sprint-29b-recruiter-email-followup-history-complete` |
| Merge commit | `9409cba` |

### What was added

- **Recruiter Communication Context** subsection on Application Detail (shown only when recruiter emails exist).
- Latest recruiter email summary using `application.recruiter_emails.all` ordering (newest `date_received` first):
  - Latest recruiter email subject
  - Date received
  - Reply status
  - Requires reply
  - Action due (when present)
  - Suggested application status (suggestion only)
- **Manual follow-up guidance** list for reviewing history, marking replies sent manually, and updating the application record yourself.
- **Suggested statuses are advisory only.**
- **Application record must be updated manually** after the user decides.

### Test progression

- Tests increased to **315** at Sprint 29B closure.

---

## Sprint 29C - Interview-Prep Trigger

| Item | Detail |
|---|---|
| Tag | `sprint-29c-interview-prep-trigger-complete` |
| Merge commit | `4cbc147` |

### What was added

- **Interview Prep Recommended** prompt inside the Recruiter Emails section when any imported email `matched_signals` contains **interview** or **screening**.
- Contextual **Create Interview Prep** button linking to `interviews:interview_create`.
- Prompt is **manual/advisory only**.
- **CareerFunnel Tracker does not create interview prep automatically.**
- Global hero **Create Interview Prep** link remains; recruiter-section prompt is an additional contextual cue only.

### Test progression

- Tests increased to **320** at Sprint 29C closure.

---

## User-facing outcome

After Sprint 29, a user can:

1. Manually import a recruiter email (Sprint 28A foundation, unchanged).
2. Open Application Detail and see **action-needed context** from Recruiter Email Actions.
3. See whether a recruiter email **needs reply** and its **reply status**.
4. See **follow-up context** from recruiter history via Recruiter Communication Context.
5. See when **interview prep is recommended** from interview/screening signals in imported email history.
6. Choose to open interview prep creation, send follow-up manually outside the app, or update the application record - **the user remains in control of all actions**.

---

## Claim-safety boundaries

Sprint 29 does **not** implement or claim:

- No Gmail API
- No OAuth
- No inbox sync
- No scraping
- No automatic email sending
- No automatic reply sending
- No automatic application status mutation
- No automatic interview prep creation
- No background jobs
- No scheduler
- No Celery
- No external AI / LLM integration

Recruiter email classification and prompts use **local, rule-based** logic on pasted content and stored `RecruiterEmail` fields only.

---

## Evidence paths

| Path | Role |
|---|---|
| `templates/applications/application_detail.html` | Recruiter Emails section UI: Communication Context, Email Actions, interview-prep prompt, imported list |
| `apps/applications/tests.py` | Application Detail tests for Sprint 29A, 29B, and 29C behavior and claim-safe wording |
| `docs/evidence/sprint_29_recruiter_email_workflow_enhancements.md` | This document |

Related Sprint 28 recruiter import foundation:

- `apps/recruiter_emails/` (models, services, import views - not modified in Sprint 29)

---

## Validation evidence

Sprint 29C closure validation (commit `4cbc147`):

| Check | Result |
|---|---|
| `ruff check .` | Passed |
| `python manage.py check` | Passed |
| `python manage.py makemigrations --check --dry-run` | Passed |
| `python manage.py test` | Passed |
| Final Sprint 29C test count | **320** |
| GitHub Actions / Django CI | Passed for `4cbc147` |

---

## Backlog / future improvements

- Improve recruiter signal context logic if false positives appear in `matched_signals` matching.
- Add richer recruiter email filtering or search on Application Detail later.
- Consider pre-filling `InterviewPrep.application` from the source application when creating prep from the recruiter prompt (not implemented in Sprint 29).
- Consider a clearer UI distinction between global **Create Interview Prep** (hero) and recruiter-triggered **Interview Prep Recommended** prompt.
- Keep all future recruiter email actions **manual** unless real integrations are implemented, tested, and documented with updated claim-safety boundaries.

---

## Sprint 29 conclusion

Sprint 29 successfully upgraded recruiter email handling from passive imported records into **manual, rule-based action intelligence** across:

- **Action alerts** (Sprint 29A)
- **Communication context** (Sprint 29B)
- **Interview-prep trigger** (Sprint 29C)

Sprint 29 can be considered ready for closure after repository validation, merge, tag, push, and GitHub Actions verification.

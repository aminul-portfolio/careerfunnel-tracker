# Career Evidence (Sprint 23 - Phase 1A)

This folder holds **local, repository-derived evidence** for CareerFunnel Tracker. Content is produced by the stdlib-only scanner in `tools/career_evidence_audit.py`; it does not claim live deployment, production usage, or integrations that were not verified in the repo.

## Files

| File | Purpose |
| --- | --- |
| `01_project_evidence_report.md` | Auto-generated inventory: docs, tests, templates, static assets, screenshots, and Git status |

## Regenerate the report

From the repository root:

```bash
python tools/career_evidence_audit.py
```

## Run scanner tests

```bash
python -m unittest tests.test_career_evidence_audit -v
```

Or, when the `tests` package is on the import path:

```bash
python manage.py test tests.test_career_evidence_audit
```

## Principles

- Count only what exists in the repository; mark gaps as **missing**, never guessed.
- Project summary lines are taken from `README.md` (non-heading lines), not invented marketing copy.
- Phase 1A is audit-only: no dashboard UI, API, or integration changes.

# Career Evidence (Sprint 23 - Phase 1A / Sprint 23B)

This folder holds **local, repository-derived evidence** for CareerFunnel Tracker. Tools use the Python standard library only and do not call external APIs, LLMs, or integrations.

## Files

| File | Purpose |
| --- | --- |
| `01_project_evidence_report.md` | V1 inventory: docs, tests, templates, static assets, screenshots, Git status |
| `02_job_fit_matrix.md` | V2 job-fit matrix: maps a pasted job description to repository evidence |
| `sample_job_description.txt` | Input job description for the matrix generator |

## Regenerate the evidence report (V1)

From the repository root:

```bash
python tools/career_evidence_audit.py
```

## Regenerate the job-fit matrix (V2)

1. Paste or edit the target role text in `docs/career_evidence/sample_job_description.txt`.
2. Run:

```bash
python tools/career_job_fit_matrix.py
```

3. Review `docs/career_evidence/02_job_fit_matrix.md`.

### What the matrix does

- Reads the sample job description and scans **real paths** under `README.md`, `docs/`, `tests/`, `apps/`, `templates/`, and `static/`.
- Builds a requirement table with **Evidence Strength** (`Strong`, `Partial`, `Missing`) and **Confidence** (`High`, `Medium`, `Low`).
- Summarizes strongest matches, partial matches, gaps, and an overall fit assessment without inventing deployments, APIs, users, or integrations.

### Evidence-only rules

- Every **Repository Evidence** cell must point to files or Git metadata that exist in this repo.
- Use `Missing` when no supporting path is found; do not guess.
- Do not claim production usage, live demos, external AI, Gmail/Calendar automation, or public REST APIs unless verified in the repository.
- Re-run the generator after evidence or job-description changes.

## Run tool tests

```bash
python -m unittest tests.test_career_evidence_audit tests.test_career_job_fit_matrix -v
```

Or:

```bash
python manage.py test tests.test_career_evidence_audit tests.test_career_job_fit_matrix
```

## Principles

- Count and cite only what exists in the repository.
- Project summaries come from README or the sample job file, not invented marketing copy.
- Phase 1A/23B are audit-only: no dashboard UI, API, or integration changes.

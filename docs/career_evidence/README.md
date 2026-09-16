# Career Evidence - V1 / V2 / V3 + Sprint 124C Recruiter Evidence

This folder holds **local, repository-derived evidence** for CareerFunnel Tracker. The historical V1/V2/V3 generator tools use the Python standard library only and do not call external APIs, LLMs, or integrations. CareerFunnel itself now includes a separately implemented **controlled AI engineering layer**; those generator tools remain local documentation utilities and were not modified or re-run in Sprint 124C.

## Files

| File | Purpose |
| --- | --- |
| `01_project_evidence_report.md` | V1 inventory: docs, tests, templates, static assets, screenshots, Git status |
| `02_job_fit_matrix.md` | V2 job-fit matrix: maps a job description to repository evidence |
| `03_recruiter_evidence_pack.md` | V3 recruiter pack: CV bullets, LinkedIn summary, interview points |
| `sample_job_description.txt` | Input job description for the V2 matrix generator |

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

## Regenerate the recruiter evidence pack (V3)

Prerequisites: V1 and V2 outputs should exist (`01_project_evidence_report.md`, `02_job_fit_matrix.md`) plus `README.md`.

```bash
python tools/career_recruiter_pack.py
```

Review `docs/career_evidence/03_recruiter_evidence_pack.md`.

### What V3 does

- Reads existing evidence from README, V1 inventory report, and V2 job-fit matrix.
- Produces recruiter-facing sections: positioning, CV bullets, LinkedIn summary, interview talking points, and limitations.
- Uses cautious, evidence-based wording (demonstrates, shows evidence of, supports, portfolio evidence).
- Does not invent deployment, SaaS status, production users, integrations, or automation. Sprint 124C manually refreshed the recruiter pack to include only verified post-Sprint-124B AI engineering evidence.

### Evidence-only rules for recruiter wording

- Every claim must trace to README, V1, or V2 content; do not add new product claims.
- Avoid exaggerated phrases (e.g. enterprise-grade, production-scale, fully automated, commercial SaaS, real users, deployed platform).
- Keep deployment, API, and integration limitations visible in **Evidence Limitations**.
- Re-run V1 and V2 before V3 when repository evidence changes materially.

### General evidence rules

- Every **Repository Evidence** cell (V2) must point to files that exist in this repo.
- Use `Missing` when no supporting path is found; do not guess.
- Do not claim production usage, live demos, Gmail/Calendar automation, scraping, auto-apply, autonomous agents, enterprise RAG, production vector databases, production AI reliability, or public REST APIs unless verified in the repository. CareerFunnel's controlled AI engineering layer may be claimed only with its documented qualifications.

## Run tool tests

```bash
python -m unittest tests.test_career_evidence_audit tests.test_career_job_fit_matrix tests.test_career_recruiter_pack -v
```

Or:

```bash
python manage.py test tests.test_career_evidence_audit tests.test_career_job_fit_matrix tests.test_career_recruiter_pack
```

## Portfolio project evidence

Portfolio-level reviews for the user's major GitHub projects live separately from the generated CareerFunnel V1-V3 reports above. They document implemented vs planned features, safe claims, and validation status per project without mixing other repositories into CareerFunnel's generated evidence.

- [portfolio_project_index.md](portfolio_project_index.md) -- priority table and claim-safety rules
- [portfolio_projects/](portfolio_projects/) -- one evidence review file per portfolio project

Recruiter/presentation materials (derived from portfolio evidence; manually refreshed in Sprint 124C and separate from the historical V1-V3 generators):

- [portfolio_presentation_pack.md](portfolio_presentation_pack.md) -- master recruiter-facing portfolio pack
- [github_pinned_repo_strategy.md](github_pinned_repo_strategy.md) -- GitHub pin order and repo descriptions
- [cv_project_bullet_bank.md](cv_project_bullet_bank.md) -- CV-ready bullets by project and role
- [linkedin_featured_project_order.md](linkedin_featured_project_order.md) -- LinkedIn Featured order and wording
- [interview_project_talking_points.md](interview_project_talking_points.md) -- interview scripts and STAR examples

## Principles

- Count and cite only what exists in the repository.
- Summaries come from README or generated evidence files, not invented marketing copy.
- V1/V2/V3 generator tools are documentation tooling only and do not call live AI providers.
- CareerFunnel's controlled AI engineering layer is separate from those generators and must retain its claim-safety qualifications.
- Use `controlled AI engineering layer`, `LLM-assisted`, or `AI-assisted, advisory and human-reviewed` rather than unqualified `AI-powered`.

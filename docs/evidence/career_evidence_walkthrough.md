# Career Evidence OS -- Reviewer Walkthrough

## Purpose

This walkthrough explains the **Career Evidence OS** delivered in Sprint 23 (23A-23F). It helps reviewers, recruiters, and interviewers inspect repository-derived portfolio evidence without overstating product maturity.

CareerFunnel Tracker remains a **local Django portfolio project**. This layer packages existing repo proof--documentation, tests, analytics modules, and screenshots--into structured markdown, dashboard pages, and optional metadata sync.

---

## What the reviewer should inspect

1. **Walkthrough and index**
   - This file: `docs/evidence/career_evidence_walkthrough.md`
   - Sprint index: `docs/evidence/evidence_index.md` (Sprint 23 section)
   - Tooling guide: `docs/career_evidence/README.md`

2. **Generated markdown (V1-V3)**
   - `docs/career_evidence/01_project_evidence_report.md` -- repository inventory
   - `docs/career_evidence/02_job_fit_matrix.md` -- requirement-to-evidence mapping
   - `docs/career_evidence/03_recruiter_evidence_pack.md` -- recruiter-facing summary traced to V1/V2

3. **Dashboard UI (V4)** -- local dev only, login required
   - Overview: `/dashboard/career-evidence/`
   - Project Evidence: `/dashboard/career-evidence/project-evidence/`
   - Job-Fit Matrix: `/dashboard/career-evidence/job-fit-matrix/`
   - Recruiter Pack: `/dashboard/career-evidence/recruiter-pack/`

4. **Screenshot evidence (V5)**
   - `docs/screenshots/career_evidence/` (four PNGs; see `docs/screenshots/career_evidence/README.md`)

5. **Optional Notion metadata (V6)**
   - `docs/notion/README.md` -- metadata/status sync only; not required to assess the project

6. **Core tracker context** (recommended before or after Career Evidence)
   - README Five-Minute Reviewer Path (dashboard, funnel metrics, data quality)
   - Curated screenshots: `docs/screenshots/curated/`
   - Analytics docs: `docs/analytics/metric_definitions.md`, `docs/analytics/analytics_lineage.md`

---

## V1-V6 evidence flow

| Step | Version | Sprint | Artifact | How it is produced |
| --- | --- | --- | --- | --- |
| 1 | V1 | 23A | Project Evidence Report | `python tools/career_evidence_audit.py` -> `01_project_evidence_report.md` |
| 2 | V2 | 23B | Job-Fit Matrix | Edit `sample_job_description.txt`, then `python tools/career_job_fit_matrix.py` -> `02_job_fit_matrix.md` |
| 3 | V3 | 23C | Recruiter Evidence Pack | `python tools/career_recruiter_pack.py` -> `03_recruiter_evidence_pack.md` (after V1/V2) |
| 4 | V4 | 23D | Dashboard UI | Django renders V1-V3 markdown at `/dashboard/career-evidence/` |
| 5 | V5 | 23E | Playwright screenshots | `scripts/capture_career_evidence_screenshots.py` -> `docs/screenshots/career_evidence/*.png` |
| 6 | V6 | 23F | Notion metadata sync (optional) | `scripts/notion_sync_career_evidence.py` per `docs/notion/README.md` |

**Recommended order:** V1 -> V2 -> V3 -> review in V4 -> refresh V5 when UI or markdown changes -> run V6 only if you maintain a Notion evidence tracker.

---

## What this proves (Data Analyst / BI Analyst / Analytics Engineer)

- **Evidence discipline:** Metrics, features, and job-fit rows cite real repository paths; strength labels (`Strong` / `Partial` / `Missing`) are explicit.
- **Reporting mindset:** V1 inventories what exists; V2 maps role requirements to implemented work; V3 translates that into recruiter-readable language with limitations visible.
- **Analytics engineering patterns:** The core tracker already uses governed metrics, data-quality propagation, and lineage docs; Career Evidence OS extends that honesty to **portfolio packaging**.
- **Tooling and testability:** V1-V3 generators and V4-V6 supporting scripts have dedicated tests under `tests/test_career_*` and `tests/test_notion_sync_config.py`.
- **BI-style presentation:** V4 dashboard and V5 screenshots give reviewers a browser-native path without claiming a hosted SaaS product.

---

## What is not claimed

- No verified **live deployment**, production users, or paying customers.
- No **external AI**, LLM APIs, scraping, auto-apply, **Gmail**, **Calendar**, or background automation.
- V2 does not guarantee job offers or perfect role fit; it maps a sample job description to **repository evidence only**.
- V5 screenshots are **local Playwright captures**, not production monitoring or CI browser farms unless you add that yourself.
- V6 syncs **metadata only** to Notion; it does not upload full reports or screenshots as the source of truth.
- Career Evidence does not replace the core tracker's analytics; it documents and presents what the repo already implements.

---

## Suggested interview explanation

> "Sprint 23 added a Career Evidence OS on top of the Django tracker. I generate a project inventory (V1), map a target job description to real files in the repo with explicit strength labels (V2), and produce a recruiter pack that only repeats what V1 and V2 support (V3). I review that in local dashboard pages (V4) and refresh Playwright screenshots for portfolios (V5). Notion sync is optional metadata only (V6). The point is auditable evidence for analytics roles--not a live SaaS or AI product."

Keep answers anchored to **paths, tests, and screenshots** the interviewer can open in the repository.

---

## Quick verification (local)

```bash
python tools/career_evidence_audit.py
python tools/career_job_fit_matrix.py
python tools/career_recruiter_pack.py
python manage.py test tests.test_career_evidence_audit tests.test_career_job_fit_matrix tests.test_career_recruiter_pack tests.test_career_evidence_views tests.test_career_evidence_screenshot_config tests.test_notion_sync_config
```

For V4/V5: start `python manage.py runserver`, log in locally, open `/dashboard/career-evidence/`, then follow `docs/screenshots/career_evidence/README.md` if regenerating PNGs.

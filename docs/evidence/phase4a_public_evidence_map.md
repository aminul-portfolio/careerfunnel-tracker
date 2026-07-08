# Phase 4A — Public Evidence Map

## Purpose

Single map for reviewers tracing CareerFunnel Tracker public portfolio evidence: where to look, what is strong, what remains unverified, and the next safe action.

---

## Where README Evidence Lives

| Evidence type | Location |
| --- | --- |
| Project overview and claim boundaries | `README.md` — top sections, "How to review", "What Is Not Claimed" |
| Curated screenshot gallery (embedded images) | `README.md` → "Curated Screenshot Gallery"; files in `docs/screenshots/curated/` |
| Career Intelligence screenshot index | `README.md` → "Career Intelligence Screenshot Evidence"; files in `docs/screenshots/intelligence/` |
| Five-minute reviewer path | `README.md` → "Five-Minute Reviewer Path" |
| Career Evidence OS summary | `README.md` → "Career Evidence OS" |
| Verification commands | `README.md` → "Evidence And Verification" |
| Phase 4A hardening pack (this sprint) | `docs/evidence/phase4a_*.md` (linked from README Evidence section) |
| Portfolio-wide project index | `docs/career_evidence/portfolio_project_index.md` |
| Recruiter presentation pack | `docs/career_evidence/portfolio_presentation_pack.md` |

---

## Where Test-Log Evidence Lives

| Evidence type | Location |
| --- | --- |
| **Current public test log (Phase 4A)** | `docs/evidence/phase4a_current_public_test_log.md` |
| README baseline mention | `README.md` — "900+ validated tests" (historical README baseline; may lag local count) |
| Sprint-level test counts | `docs/evidence/evidence_index.md` and per-sprint `docs/evidence/sprint_*.md` files |
| CI workflow definition | `.github/workflows/django-ci.yml` |
| Local reproduction | `python manage.py check` and `python manage.py test` (see Phase 4A test log for latest verified run) |

---

## Where Screenshots Should Live

| Set | Path | Used for |
| --- | --- | --- |
| Curated recruiter gallery | `docs/screenshots/curated/` | README front-door proof |
| Career Intelligence pipeline | `docs/screenshots/intelligence/` | Sprints 53–59 workflow |
| Career Evidence dashboard (V5) | `docs/screenshots/career_evidence/` | Career Evidence OS browser proof |
| Sprint historical captures | `docs/evidence/screenshots/` | Sprint closure cross-reference |
| Phase 4A new captures (optional) | `docs/screenshots/phase4a/` | Future dated refreshes |

Safety gate: `docs/evidence/phase4a_screenshot_safety_checklist.md`

---

## Where CI Proof Should Be Referenced

| Item | How to reference claim-safely |
| --- | --- |
| Workflow file | `.github/workflows/django-ci.yml` — defines Ruff, Django check, migration check, full test run |
| GitHub Actions UI | Repository → Actions → "Django CI" workflow runs |
| Safe wording | "CI workflow is defined to run Ruff, Django checks, migration check, and the full test suite on push/PR." |
| Unsafe wording | "CI is green" or "all checks pass on GitHub" without verifying the latest run |

**Current session status:** latest Actions run result is **[UNKNOWN]** (not queried via GitHub API/UI during Phase 4A).

---

## What Is Strong Evidence

| Strength | Evidence | Why it is strong |
| --- | --- | --- |
| **High** | Local test log with 1977 passing tests (Phase 4A) | Reproducible, timestamped, command-backed |
| **High** | Broad sprint evidence index | `docs/evidence/evidence_index.md` — traceable delivery history |
| **High** | Analytics governance docs | `docs/analytics/metric_definitions.md`, `docs/analytics/analytics_lineage.md` |
| **High** | README claim-control sections | Explicit "What Is Not Claimed" boundaries |
| **High** | Curated + intelligence screenshot sets | Visual proof aligned to documented routes |
| **High** | Career Evidence OS (V1–V4 markdown + dashboard) | Repo-derived, reviewer walkthrough |
| **High** | CI workflow in repo | Shows intended quality gates even when run status is unknown |
| **Medium** | Per-sprint closure docs | Point-in-time test counts; useful but may be stale vs current suite |
| **Medium** | Tableau local workbook + screenshots | Strong for BI narrative; not a verified public URL |

---

## What Remains [UNKNOWN]

| Item | Status |
| --- | --- |
| Latest GitHub Actions pass/fail for `main` | **[UNKNOWN]** |
| Latest GitHub Actions pass/fail for `feature/phase4a-careerfunnel-public-evidence-hardening` | **[UNKNOWN]** |
| Whether branch is pushed to remote | **[UNKNOWN]** |
| Verified live deployment URL | **[UNKNOWN]** — README explicitly says deployment is conditional and not verified |
| Verified Tableau Public URL | **[UNKNOWN]** |
| Whether all screenshot files on disk match README references | **[UNKNOWN]** — verify before external publish |
| Ruff / migration-check pass on local machine during Phase 4A | **[UNKNOWN]** — not run in Phase 4A validation (included in CI workflow) |

---

## Next Safe Evidence Action

1. **Push branch and confirm GitHub Actions** — then update Phase 4A test log CI table with run URL/status (still no unsupported claims).
2. **Refresh stale screenshots** only after running `phase4a_screenshot_safety_checklist.md`; store under `docs/screenshots/curated/` or `docs/screenshots/phase4a/`.
3. **Link this map from pinned repo description** or portfolio index — one line pointing to `docs/evidence/phase4a_public_evidence_map.md`.
4. **Before recruiter send:** run `python manage.py check` and `python manage.py test` locally; append dated entry to test log if counts change.
5. **Do not add** live-demo, SaaS, revenue, or production-user claims until separately verified.

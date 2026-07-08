# Phase 4A — Screenshot Safety Checklist

## Purpose

Guide for capturing, storing, and publishing CareerFunnel Tracker screenshots in a portfolio-safe way. Use this before adding screenshots to GitHub, LinkedIn, CV annexes, or interview decks.

---

## Screenshot Categories Safe for Public Portfolio Use

These surfaces use demo/synthetic or portfolio-scoped data and are generally safe when captured from a local dev server with seeded demo data:

| Category | Example paths / surfaces | Notes |
| --- | --- | --- |
| Dashboard overview | `/dashboard/` | Reviewer walkthrough note, pipeline health, today signals |
| Evaluation Queue | Evaluation queue list views | Company names from seed data only |
| Funnel Metrics | Funnel metrics pages, weekly trend charts | Synthetic/demo aggregates |
| Premium reporting | Source performance, CV version, rejection patterns, weekly trend | Directional analytics evidence |
| Data Quality Report | Data quality / impact reporting | Governance and completeness messaging |
| Skill Intelligence Dashboard | `/skill-gaps/` | Read-only advisory sections |
| Career Intelligence pipeline | `/skills/*` routes (Sprints 53–59) | Rule-based, portfolio-baseline inputs |
| Career Evidence dashboard | `/dashboard/career-evidence/` | Renders repo-derived markdown evidence |
| Curated recruiter gallery | `docs/screenshots/curated/` | Already intended for README embedding |
| Intelligence screenshot set | `docs/screenshots/intelligence/` | Sprint 53–59 pipeline evidence |
| Sprint historical screenshots | `docs/evidence/screenshots/` | Legacy sprint proof (verify content before reuse) |
| UI shell / navigation | Navbar, sidebar, responsive drawer | No sensitive data if background pages are safe |
| Empty states / form chrome | Add/edit forms before save | Fields blank or with obvious demo placeholders |

---

## Screenshot Categories Requiring Redaction

Review carefully before publishing; redact or recapture if any item below appears:

| Category | Risk | Action |
| --- | --- | --- |
| Login / auth screens showing real email or username | Identity exposure | Crop or use generic demo account label only |
| Application detail with real employer correspondence | PII / confidential comms | Blur email body, sender address, phone numbers |
| Recruiter email import fields | Email content, names | Use demo text only; redact real threads |
| Notes / interview prep free text | Personal or employer-confidential content | Replace with synthetic demo notes |
| Export downloads showing filesystem paths | Local machine paths | Crop OS path bars if they reveal username/machine |
| Browser devtools / terminal in frame | Env vars, secrets, API keys | Exclude from portfolio captures |
| Database admin or raw SQLite viewers | Real record dumps | Do not publish |
| `.env`, settings, or credential files | Secrets | Never screenshot |
| Error tracebacks with local paths | Path/username leakage | Crop or use sanitized repro |

---

## Data That Must Never Appear Publicly

- API keys, tokens, passwords, or OAuth client secrets
- `.env` contents or `SECRET_KEY` values
- Real recruiter/hiring manager email addresses or phone numbers
- Real salary negotiations, offer details, or rejection reasons tied to identifiable people
- `db.sqlite3` contents from a non-demo database
- Gmail or calendar integration screens (not implemented; do not imply they exist)
- Production/hosting credentials, SSH keys, or cloud console access
- Third-party Notion workspace URLs with live private content (V6 is optional metadata sync only)

---

## Suggested Screenshot Filenames

Use stable, sortable names. Prefer existing conventions where present.

**Curated README gallery (existing):**

```text
docs/screenshots/curated/01-dashboard-overview.png
docs/screenshots/curated/02-evaluation-queue.png
docs/screenshots/curated/03-job-posting-analyzer-conversion.png
docs/screenshots/curated/04-funnel-metrics-weekly-trend.png
docs/screenshots/curated/05-save-quality-warnings.png
docs/screenshots/curated/06-data-quality-impact-report.png
docs/screenshots/curated/07-visual-analytics-dashboard.png
docs/screenshots/curated/08-interview-evidence-workspace.png
```

**Career Intelligence pipeline (existing):**

```text
docs/screenshots/intelligence/01-ai-capability-framework.png
docs/screenshots/intelligence/02-ai-readiness-report.png
docs/screenshots/intelligence/03-job-ai-capability-match.png
docs/screenshots/intelligence/04-learning-recommendations.png
docs/screenshots/intelligence/05-career-readiness-dashboard.png
docs/screenshots/intelligence/06-career-strategy-action-plan.png
docs/screenshots/intelligence/07-final-career-intelligence-workflow.png
```

**Career Evidence dashboard (existing README in folder):**

```text
docs/screenshots/career_evidence/<surface-name>.png
```

**New Phase 4A captures (if added later):**

```text
docs/screenshots/phase4a/YYYYMMDD-<surface-slug>.png
```

---

## Local Screenshot Storage Paths

| Purpose | Path |
| --- | --- |
| Curated recruiter-facing set | `docs/screenshots/curated/` |
| Career Intelligence pipeline | `docs/screenshots/intelligence/` |
| Career Evidence OS (V5) | `docs/screenshots/career_evidence/` |
| Sprint historical evidence | `docs/evidence/screenshots/` |
| Recommended Phase 4A additions | `docs/screenshots/phase4a/` (create when needed) |

Keep captures in-repo under `docs/screenshots/` or `docs/evidence/screenshots/` only. Do not commit raw captures from Desktop/Downloads without renaming and safety review.

---

## Public GitHub Screenshot Rules

1. **Prefer existing curated paths** already referenced by `README.md`.
2. **Use relative image links** in markdown (as README already does) — no hotlinking to private hosts.
3. **Re-capture after UI changes** that affect reviewer-critical surfaces; stale screenshots mislead reviewers.
4. **Do not embed screenshots that imply** live SaaS deployment, paying customers, Gmail sync, auto-apply, or external AI chat UIs unless that behaviour is implemented and claim-documented.
5. **Pair screenshots with evidence docs** — e.g. `docs/evidence/evidence_index.md`, sprint closure docs, and this Phase 4A pack.
6. **Run this checklist** before opening a PR that adds or replaces PNGs.
7. **File size:** prefer PNG for UI clarity; avoid committing duplicate near-identical captures.

---

## Claim-Safety Warnings

- Screenshots are **local portfolio evidence**, not proof of production deployment or live users.
- Career Intelligence screenshots show **rule-based, deterministic** reporting — not live LLM API calls.
- CV Tailoring / fit scoring may have **optional mocked-first Claude paths** in code; screenshots must not imply every request hits an external model.
- Tableau/workbook evidence is **local artefact + screenshot** unless a public URL is separately verified.
- Do not caption screenshots with "production", "enterprise", "SaaS customers", "revenue", or "live AI assistant" unless independently verified and documented.

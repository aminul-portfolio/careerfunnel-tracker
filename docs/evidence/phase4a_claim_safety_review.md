# Phase 4A — Claim Safety Review

## Purpose

Claim-safe language guide for CareerFunnel Tracker public portfolio use (GitHub, CV, LinkedIn, interviews). Aligns with `README.md`, `CLAUDE.md`, and verified Phase 4A test evidence.

---

## Safe Claims

These are supported by the repository structure, documentation, and/or Phase 4A local validation:

- Django job-search analytics and decision-support **portfolio project** for a single user context.
- **Manual, advisory, rule-based** workflows for tracking applications, funnel metrics, data-quality warnings, and evidence exports.
- **Service-layer analytics** with metric definitions and analytics lineage documentation.
- **Sprint-based, evidence-first delivery** with indexed docs under `docs/evidence/`.
- **Local SQLite** database for portfolio-scale demonstration.
- **Test-backed development** — Phase 4A verified: **1977** tests pass locally (`python manage.py test`, 2026-07-08).
- **Django system check clean** — Phase 4A verified: `python manage.py check` reports no issues.
- **CI workflow defined** in `.github/workflows/django-ci.yml` (Ruff, check, migration check, tests).
- **Career Intelligence pipeline (Sprints 53–59)** as deterministic, read-only, rule-based reporting on portfolio baseline inputs.
- **Career Evidence OS** as repo-derived markdown + authenticated dashboard viewer.
- **Optional mocked-first / fallback Claude paths** in code for some advisory features — not universal runtime dependency.
- **Application Document Pack** stores/references externally generated documents and rule-based draft notes; manual review before use.
- **Screenshot and export evidence** for reviewer walkthroughs (local captures, not production monitoring).

---

## Claims to Avoid

Do not state or imply:

| Avoid | Why |
| --- | --- |
| Live SaaS product with paying customers | Not implemented; README denies |
| Production deployment / public demo URL (unless verified) | README: deployment conditional and not verified |
| Gmail, Calendar, OAuth, inbox sync | Not implemented |
| Auto-apply, auto-send, background polling | Not implemented |
| Scraping job boards at runtime | Not implemented |
| External AI/LLM on every request | Mocked-first / optional; rule-based fallback |
| Final CV or cover letter body generation by the app | Claim safety rules — angles/themes only |
| Scientific A/B testing of CV versions | Directional reporting only |
| Financial ROI calculation | "Source ROI" means channel outcome performance |
| Enterprise clients, revenue, subscriptions, billing | No commercial operation |
| "CI is green" without checking Actions | Phase 4A: CI run status **[UNKNOWN]** |
| Invented test counts | Use only verified logs (e.g. Phase 4A: 1977) |
| Power BI implementation | README: not claimed yet |
| Real user base / multi-tenant production | Single-user portfolio scope |

---

## AI / LLM Claims Status

| Topic | Status |
| --- | --- |
| External OpenAI/Anthropic calls in production | **Not claimed** — mocked-first; tests mock external APIs |
| Sprint 53–59 Career Intelligence | **Rule-based only** — no external AI APIs |
| CV Tailoring Advisor (`CVTailoringAdvisorResult`) | **Advisory angles and evidence pointers** — no full CV text generation |
| Optional Claude semantic path (Sprint 34) | **Optional when configured** — falls back to rule-based logic |
| Fit scoring Claude provider (Sprint 33) | **Mocked-first pattern** |
| Safe wording | "Deterministic rule-based advisory with optional, mocked-first LLM enhancement paths in code; no claim that external AI runs on every request." |

---

## Deployment Claims Status

| Topic | Status |
| --- | --- |
| Live hosted demo | **Not verified** — README explicit |
| `DEBUG`, `SECRET_KEY`, hosting config | Local dev only in docs |
| Safe wording | "Local Django portfolio project; deployment not verified." |

---

## Production / User / Client / Revenue Claims Status

| Topic | Status |
| --- | --- |
| Production users | **None claimed** — single-user portfolio |
| Paying clients / customers | **None claimed** |
| Revenue / ARR / subscriptions | **None claimed** |
| Enterprise rollout | **None claimed** |
| Safe wording | "Personal portfolio analytics project for my own job search; not a commercial product." |

---

## CV-Safe Wording

**Project title line:**

> CareerFunnel Tracker — Django job-search analytics portfolio (funnel metrics, data quality, evidence exports)

**Bullet examples:**

- Built a Django analytics application that turns manually logged applications into funnel metrics, source/CV performance views, and data-quality governance warnings.
- Documented metric definitions and analytics lineage; delivered sprint evidence, screenshots, and a **1977-test** local suite (verified 2026-07-08).
- Implemented rule-based decision support (fit review, follow-ups, interview prep handoffs) without auto-apply or inbox automation.
- Added a Career Intelligence read-only reporting pipeline and Career Evidence OS for reviewer-ready portfolio proof.

**Avoid on CV:** "SaaS platform", "live product", "AI-powered job automation", "Gmail integration".

---

## LinkedIn-Safe Wording

**Short project blurb:**

> CareerFunnel Tracker is my Django portfolio project for job-search analytics: funnel metrics, data-quality signals, exports, and reviewer-ready evidence. Manual workflows only — no auto-apply or live SaaS claims. Code, tests, and docs on GitHub.

**Featured skills to tag:** Django, Python, SQL/SQLite, data quality, reporting, analytics documentation, software testing.

**Avoid on LinkedIn:** "Founded a startup", "paying users", "production AI assistant", "deployed SaaS".

---

## Interview-Safe Explanation

**30-second version:**

> CareerFunnel Tracker is a Django portfolio project I built to practice analytics engineering on my own job search data. It tracks applications manually, computes funnel and quality metrics in service layers, surfaces governance warnings, and exports evidence for review. It's tested — about two thousand tests locally — and heavily documented, but it's not a live commercial product.

**If asked about AI:**

> Most of the product is rule-based and deterministic. Some modules have optional Claude integration paths that are mocked in tests and fall back to rules when not configured. I don't claim external AI runs on every request.

**If asked about deployment:**

> I run it locally for demonstration. I haven't verified a public deployment URL, and the README is explicit about that boundary.

**If asked about tests:**

> On 2026-07-08 I ran the full suite locally: 1977 tests, all passing, plus a clean Django system check. CI is configured in GitHub Actions; I'd confirm the latest run on Actions before citing CI green status.

---

## Cross-References

- Phase 4A test log: `docs/evidence/phase4a_current_public_test_log.md`
- Screenshot safety: `docs/evidence/phase4a_screenshot_safety_checklist.md`
- Evidence map: `docs/evidence/phase4a_public_evidence_map.md`
- README claim boundaries: `README.md` → "What Is Not Claimed"
- Master evidence index: `docs/evidence/evidence_index.md`

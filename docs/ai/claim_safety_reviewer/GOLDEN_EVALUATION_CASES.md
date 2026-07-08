# Claim-Safety Reviewer — Golden Evaluation Cases

## Status

Specification test fixtures for Phase 5B unit tests. Expected behaviour defined here; not executed by runtime in Phase 5A.

**Evidence baseline for testing claims:** Phase 4A test log (`docs/evidence/phase4a_current_public_test_log.md`) documents **1977** passing tests on **2026-07-08** when cited in `evidence_context`. Cases without that context must treat numbers as unverified.

---

## Case Format

Each case includes: input claim, evidence provided, expected verdict, expected risk level, expected warning(s), expected safe rewrite (substance; minor punctuation variance allowed in 5B tests).

---

## Case 01 — Safe analytics claim (portfolio scope)

| Field | Value |
| --- | --- |
| **Input claim** | Built a Django portfolio application that turns manually logged job applications into funnel metrics and data-quality warnings. |
| **Evidence provided** | README "What The Platform Does"; `docs/analytics/metric_definitions.md` referenced |
| **Expected verdict** | `safe` |
| **Expected risk level** | `low` |
| **Expected warning** | _(none)_ |
| **Expected safe rewrite** | Built a Django portfolio application that turns manually logged job applications into funnel metrics, data-quality signals, and reviewer-ready evidence exports. |

---

## Case 02 — Unsupported production claim

| Field | Value |
| --- | --- |
| **Input claim** | CareerFunnel Tracker is a live production SaaS platform serving hundreds of daily active users. |
| **Evidence provided** | README "What Is Not Claimed" — no production users |
| **Expected verdict** | `unsafe` |
| **Expected risk level** | `high` |
| **Expected warning** | `forbidden_production_claim`, `commercial_overclaim` |
| **Expected safe rewrite** | CareerFunnel Tracker is a local Django portfolio project for my own job-search analytics; it is not a live SaaS product with production users. |

---

## Case 03 — Unsupported AI/LLM claim

| Field | Value |
| --- | --- |
| **Input claim** | Every feature is powered by GPT-4 in real time, including auto-apply and email drafting. |
| **Evidence provided** | README denies auto-apply, Gmail, external AI on every request; CLAUDE.md mocked-first note |
| **Expected verdict** | `unsafe` |
| **Expected risk level** | `high` |
| **Expected warning** | `ai_automation_overclaim`, `integration_overclaim` |
| **Expected safe rewrite** | Most workflows are rule-based and manual. Some modules have optional mocked-first LLM paths with rule-based fallback; the app does not auto-apply or send email. |

---

## Case 04 — Unsupported user/revenue claim

| Field | Value |
| --- | --- |
| **Input claim** | Generated £50k ARR from enterprise subscriptions in the first quarter. |
| **Evidence provided** | README — no billing, subscriptions, or revenue claims |
| **Expected verdict** | `unsafe` |
| **Expected risk level** | `high` |
| **Expected warning** | `commercial_overclaim` |
| **Expected safe rewrite** | Personal portfolio project with no commercial revenue, subscriptions, or paying customers. |

---

## Case 05 — Unsupported deployment claim

| Field | Value |
| --- | --- |
| **Input claim** | Try the live demo at our production URL — deployed on AWS with 99.9% uptime. |
| **Evidence provided** | README "Live Demo Status" — deployment not verified |
| **Expected verdict** | `unsafe` |
| **Expected risk level** | `high` |
| **Expected warning** | `forbidden_production_claim`, `unverified_deployment_url` |
| **Expected safe rewrite** | Local Django project for portfolio review; no verified public deployment URL is claimed. |

---

## Case 06 — Mixed safe/unsafe claim

| Field | Value |
| --- | --- |
| **Input claim** | Django analytics app with SQLite and 1977 passing tests, currently used by 500 companies worldwide. |
| **Evidence provided** | Phase 4A test log excerpt: `Ran 1977 tests ... OK` (2026-07-08) |
| **Expected verdict** | `unsafe` |
| **Expected risk level** | `high` |
| **Expected warning** | `commercial_overclaim`, `forbidden_production_claim` |
| **Expected safe rewrite** | Django analytics portfolio app using SQLite, with 1977 passing tests verified locally on 2026-07-08; single-user portfolio scope, not used by external companies. |

---

## Case 07 — Unknown evidence case

| Field | Value |
| --- | --- |
| **Input claim** | CI is green on every push and the test suite has exactly 3000 tests. |
| **Evidence provided** | `.github/workflows/django-ci.yml` referenced only (workflow definition, no run result) |
| **Expected verdict** | `needs_evidence` |
| **Expected risk level** | `medium` |
| **Expected warning** | `unverified_test_count`, `unverified_ci_status` |
| **Expected safe rewrite** | CI workflow is defined in the repository; latest run status and exact test count should be cited from a dated test log or verified Actions run — otherwise mark as [UNKNOWN]. |

---

## Case 08 — CV-safe wording case

| Field | Value |
| --- | --- |
| **Input claim** | Shipped enterprise AI platform replacing recruiters with autonomous agents. |
| **Evidence provided** | `docs/evidence/phase4a_claim_safety_review.md` CV-safe examples |
| **Expected verdict** | `unsafe` |
| **Expected risk level** | `high` |
| **Expected warning** | `ai_automation_overclaim`, `commercial_overclaim` |
| **Expected safe rewrite** | Built a Django job-search analytics portfolio with rule-based decision support, documented sprint evidence, and a broad local test suite; manual workflows only. |

---

## Case 09 — README-safe wording case

| Field | Value |
| --- | --- |
| **Input claim** | Optional Claude semantic path for CV Tailoring Advisor when configured; falls back to rule-based logic. No external AI on every request. |
| **Evidence provided** | README "Technical Decisions" §1; Sprint 34 evidence doc path |
| **Expected verdict** | `safe` |
| **Expected risk level** | `low` |
| **Expected warning** | _(none)_ |
| **Expected safe rewrite** | Optional mocked-first Claude path for CV Tailoring Advisor when configured, with rule-based fallback; external AI is not claimed on every request. |

---

## Case 10 — LinkedIn-safe wording case

| Field | Value |
| --- | --- |
| **Input claim** | Just launched my AI startup — sign up for our freemium plan! |
| **Evidence provided** | Phase 4A LinkedIn-safe wording section |
| **Expected verdict** | `unsafe` |
| **Expected risk level** | `high` |
| **Expected warning** | `commercial_overclaim`, `forbidden_production_claim` |
| **Expected safe rewrite** | CareerFunnel Tracker is my Django portfolio project for job-search analytics: funnel metrics, data-quality signals, and evidence docs on GitHub. Manual workflows only — not a commercial SaaS launch. |

---

## Case 11 — Interview answer case

| Field | Value |
| --- | --- |
| **Input claim** | We integrated Gmail and the system automatically replies to recruiters for me. |
| **Evidence provided** | README — Gmail/OAuth not implemented; recruiter workflow is manual import only |
| **Expected verdict** | `unsafe` |
| **Expected risk level** | `high` |
| **Expected warning** | `integration_overclaim`, `ai_automation_overclaim` |
| **Expected safe rewrite** | Recruiter email workflow is manual import and rule-based advisory only. There is no Gmail integration, OAuth, or automatic sending. |

---

## Case 12 — Job application answer case

| Field | Value |
| --- | --- |
| **Input claim** | In CareerFunnel I designed service-layer analytics with metric governance and verified 1977 local tests; I run it locally and do not claim production deployment. |
| **Evidence provided** | Phase 4A test log (1977, 2026-07-08); README metric governance section |
| **Expected verdict** | `safe` |
| **Expected risk level** | `low` |
| **Expected warning** | _(none)_ |
| **Expected safe rewrite** | In CareerFunnel Tracker I implemented Django service-layer analytics with metric definitions, data-quality propagation, and sprint evidence; 1977 tests passed locally on 2026-07-08. I demonstrate it locally and do not claim a verified production deployment. |

---

## Parametrisation Notes for Phase 5B

- Implement as `@pytest.mark.parametrize` or Django `subTest` over fixture dicts
- Allow normalised string comparison on `safe_rewrite` (collapse whitespace)
- `warnings` may be superset-checked (expected warnings must appear)
- `unknowns` required non-empty for Case 07
- Do not call external APIs in golden tests

---

## Coverage Matrix

| Category | Cases |
| --- | --- |
| Safe claim | 01, 09, 12 |
| Unsupported production | 02, 05 |
| Unsupported AI/LLM | 03 |
| Unsupported user/revenue | 04 |
| Unsupported deployment | 05 |
| Mixed safe/unsafe | 06 |
| Unknown evidence | 07 |
| CV-safe | 08 |
| README-safe | 09 |
| LinkedIn-safe | 10 |
| Interview | 11 |
| Job application | 12 |

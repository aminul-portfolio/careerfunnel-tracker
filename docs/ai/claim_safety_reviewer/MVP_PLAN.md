# Claim-Safety Reviewer — MVP Plan (Phase 5A)

## Status

**Phase:** 5A — planning and specification only  
**Implementation:** not started  
**Live LLM provider:** not in scope for MVP or Phase 5B–5D

This document defines a future **Claim-Safety Reviewer** feature for CareerFunnel Tracker. Phase 4A hardened public portfolio evidence manually (`docs/evidence/phase4a_*.md`). Phase 5A plans a reproducible, testable reviewer that can later support mocked-first and optional provider-backed paths without changing product behaviour in this sprint.

---

## Problem Statement

Portfolio and job-application materials for CareerFunnel Tracker are easy to overstate. README sections, CV bullets, LinkedIn posts, interview answers, and recruiter messages can drift into unsupported claims about:

- production deployment and live users
- external AI/LLM usage at runtime
- commercial SaaS operation, revenue, or enterprise clients
- integrations that are not implemented (Gmail, auto-apply, scraping)

Today, claim safety relies on static markdown guides and human discipline. There is no structured, validated service that takes a draft claim plus evidence context and returns a schema-bound review with safe rewrites and explicit `[UNKNOWN]` handling.

---

## User Value

For the single portfolio user (Aminul Islam, Data Analyst job seeker):

1. **Before publishing** — paste or select draft wording; receive verdict, risk level, and evidence gaps.
2. **Before interviews** — rehearse answers with claim-safe framing tied to repo evidence.
3. **Before CV/LinkedIn updates** — get channel-specific safe rewrites without inventing metrics.
4. **During sprint closure** — verify new README or evidence docs do not introduce forbidden overclaims.

The reviewer is **advisory only**. It does not auto-publish, auto-apply, or mutate application records without explicit user action.

---

## Why This Supports AI Application Engineer Positioning

This MVP plan demonstrates AI-application engineering practices without requiring a live model in Phase 5A:

| Practice | How this feature embodies it |
| --- | --- |
| Schema-first outputs | `RESPONSE_SCHEMA_DRAFT.md` — structured, validatable responses |
| Golden evaluation cases | `GOLDEN_EVALUATION_CASES.md` — deterministic expected behaviour |
| Mocked-first delivery | Rule-based reviewer before any provider integration |
| Evidence boundaries | Compares claims to repo docs, test logs, and explicit unknowns |
| Fail-safe fallbacks | Unknown evidence → `unknown` verdict, not confident unsafe/safe |
| Claim safety by design | Core product constraint, not an afterthought |

Interview narrative (planning stage):

> "I designed a Claim-Safety Reviewer with a JSON schema, golden cases, and mocked-first architecture so portfolio claims stay aligned with verifiable evidence before any LLM provider is added."

---

## MVP Input

Minimum input payload (conceptual; not implemented in 5A):

```text
claim_text          — free text to review (CV bullet, README sentence, interview answer, etc.)
channel             — cv | linkedin | github_readme | interview | job_application | general
evidence_context    — optional structured hints (paths, test log excerpts, doc references)
repo_snapshot_refs  — optional list of evidence file paths the user asserts support the claim
strict_mode         — boolean; when true, downgrade unverified numbers to [UNKNOWN]
```

**Evidence context sources (read-only, no runtime fetch in MVP spec):**

- `docs/evidence/phase4a_current_public_test_log.md`
- `docs/evidence/phase4a_claim_safety_review.md`
- `docs/evidence/evidence_index.md`
- `README.md` "What Is Not Claimed" section
- User-supplied verbatim excerpts only (no invented CI/deployment facts)

---

## MVP Output

Schema-bound review per `RESPONSE_SCHEMA_DRAFT.md`:

- `overall_verdict` — safe | needs_evidence | unsafe | unknown
- `risk_level` — low | medium | high | unknown
- `reviewed_claims` — atomic claims extracted from input
- `unsupported_claims` — claims lacking evidence
- `evidence_required` — what proof would be needed to upgrade verdict
- `safe_rewrite` — channel-appropriate alternative wording
- `warnings` — specific overclaim or ambiguity flags
- `unknowns` — items that cannot be verified from provided context
- `reviewer_notes` — short human-readable rationale (no full CV/cover letter generation)

---

## Non-Goals (MVP and Phase 5B–5D)

- Live OpenAI, Anthropic, Gemini, or other external LLM calls
- API key storage or environment-based provider configuration UI
- Automatic rewriting of README, CV files, or LinkedIn via API
- Notion sync, GitHub Actions bots, or Hermes automation
- Multi-user SaaS deployment or billing
- Scraping GitHub Actions for CI status without explicit user-provided run evidence
- Generating full CV text, cover letter bodies, or professional summaries
- Replacing human judgment for final publish decisions

---

## Out-of-Scope Items

| Item | Reason |
| --- | --- |
| Gmail / Calendar / OAuth claim validation against live APIs | Not implemented in product |
| Real-time deployment health checks | No verified live URL |
| Competitor or market sizing claims | Outside repo evidence |
| Legal/compliance certification language | Not evidenced |
| Automatic job application submission review | Auto-apply not implemented |
| Training or fine-tuning custom models | Portfolio scope |
| Agentic multi-step workflows | Deferred beyond MVP |

---

## Success Criteria

### Phase 5A (this sprint — documentation)

- [x] MVP plan, architecture, schema, golden cases, rules, roadmap, and risk review documented
- [x] No Python/Django/runtime changes
- [x] All `[UNKNOWN]` handling rules explicit
- [x] At least 12 golden cases with expected verdicts

### Phase 5B (future — mocked service)

- [ ] `ClaimSafetyReviewerResult` frozen dataclass matching schema
- [ ] Rule-based `review_claim()` in `apps/ai_agents/services.py` (or dedicated module per sprint instruction)
- [ ] Schema validator rejects malformed outputs
- [ ] Unit tests cover all golden cases
- [ ] Zero network calls; zero API keys

### Phase 5C (future — optional UI)

- [ ] Authenticated internal review page or admin-adjacent form
- [ ] Displays verdict + safe rewrite; copy-only export
- [ ] Still mocked-first; no external provider

### Phase 5D (future — evaluation proof)

- [ ] Golden-case test module named in evidence docs
- [ ] Failure handling documented and tested (empty input, ambiguous channel)
- [ ] README evidence link updated with verified test count from that sprint's log

---

## Evidence Requirements

Any claim the reviewer marks `safe` must map to at least one of:

1. **Verified test log** — dated `python manage.py test` output in `docs/evidence/`
2. **README explicit statement** — especially "What Is Not Claimed" negations
3. **Sprint evidence doc** — `docs/evidence/sprint_*.md` with traceable scope
4. **Analytics docs** — `docs/analytics/metric_definitions.md`, `analytics_lineage.md`
5. **CI workflow file** — `.github/workflows/django-ci.yml` (workflow *definition* only; run status needs separate proof)

Items that default to `[UNKNOWN]` unless user supplies proof:

- Latest GitHub Actions green/red status
- Live deployment URL availability
- External LLM usage on every request
- Current test count if not from a cited log in the same review session

**Phase 4A baseline (reference only, not re-verified in 5A planning):**

- Local test log documents **1977** passing tests on 2026-07-08
- CI run status marked **[UNKNOWN]** in Phase 4A docs

---

## Later Implementation Phases

See `IMPLEMENTATION_ROADMAP.md` for full detail.

| Phase | Focus |
| --- | --- |
| **5A** | Planning docs only (this folder) |
| **5B** | Mocked rule-based service + schema validator + golden tests |
| **5C** | Optional authenticated UI route; still no live provider |
| **5D** | Evaluation proof, failure handling, README evidence update |
| **Deferred** | Live LLM provider abstraction, API keys, Notion, automation |

---

## Related Documents

- `MOCKED_FIRST_ARCHITECTURE.md`
- `RESPONSE_SCHEMA_DRAFT.md`
- `GOLDEN_EVALUATION_CASES.md`
- `CLAIM_SAFETY_RULES.md`
- `IMPLEMENTATION_ROADMAP.md`
- `RISK_REVIEW.md`
- Phase 4A evidence: `docs/evidence/phase4a_claim_safety_review.md`

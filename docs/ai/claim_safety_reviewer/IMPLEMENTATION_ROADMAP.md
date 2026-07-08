# Claim-Safety Reviewer — Implementation Roadmap

## Status

Forward plan only. Phase 5A delivers this document; no code changes until explicit Sprint 5B instruction.

---

## Phase 5A — MVP Planning (Current)

**Deliverables:**

- [x] `docs/ai/claim_safety_reviewer/` specification pack
- [x] MVP plan, architecture, schema, golden cases, rules, risk review
- [x] Minimal README link under Evidence section

**Constraints:**

- Documentation only
- No Django/Python changes
- No commits required in task spec (user reviews first)

**Exit criteria:**

- Reviewer can read folder and understand 5B scope without ambiguity
- Golden cases ≥ 12 with expected verdicts
- Deferred items explicitly separated from 5B–5D

---

## Phase 5B — Mocked Service Implementation

**Goal:** Rule-based `review_claim()` with schema validation and golden tests. Zero live API.

### Scope

| Item | Detail |
| --- | --- |
| Service function | e.g. `review_claim_safety(user, request) -> ClaimSafetyReviewerResult` |
| Location | `apps/ai_agents/` per project conventions (exact file per sprint brief) |
| Return type | `@dataclass(frozen=True)` matching `RESPONSE_SCHEMA_DRAFT.md` |
| Logic | Pattern buckets from `CLAIM_SAFETY_RULES.md` + evidence_context matching |
| Schema validator | `validate_claim_safety_response(dict)` — raises or returns errors in tests |
| Tests | `tests/test_claim_safety_reviewer.py` — all 12 golden cases parametrized |
| Fallbacks | Empty input, validation failure, strict_mode |
| Network | None |
| API keys | None |
| Migrations | None |
| Routes | None (service-only acceptable for 5B) |

### Suggested test commands

```bash
python manage.py test tests.test_claim_safety_reviewer
python manage.py check
```

### Evidence on completion

- New sprint doc: `docs/evidence/sprint_5b_claim_safety_reviewer_mocked.md`
- Update test log with verified count from that sprint's terminal output
- Do not claim live LLM

### Out of scope for 5B

- UI, templates, URLs
- Provider abstraction
- Reading filesystem evidence at runtime (use passed context + embedded rule constants; optional fixture loader in tests only)

---

## Phase 5C — Optional UI / Internal Review Route

**Goal:** Authenticated surface for paste-in claim review. Still mocked-first.

### Scope

| Item | Detail |
| --- | --- |
| Route | e.g. `/ai-agents/claim-safety/` or under existing ai_agents namespace |
| View | Thin — calls service, renders result |
| Template | Form + result panels: verdict, risk, warnings, safe_rewrite (copy button) |
| Auth | Login required; `user=user` scoping if persistence added later |
| Persistence | Optional `ClaimSafetyReview` model — **only if explicit sprint allows migrations** |
| Provider | Still none |

### UX principles

- Advisory banner: "Suggested wording only — verify before publishing"
- No auto-write to README/CV
- Display `unknowns` prominently

### Out of scope for 5C

- External API endpoints
- Webhooks, Notion, GitHub bots

---

## Phase 5D — Evaluation Proof and Evidence Closure

**Goal:** Demonstrate engineering rigour for portfolio reviewers.

### Scope

| Item | Detail |
| --- | --- |
| Golden suite | Named in README evidence section |
| Failure handling tests | Malformed evidence JSON, oversized input, secret-like patterns |
| Negative tests | Ensure unsafe claims never return `safe` |
| Regression gate | Golden cases run in CI via existing `django-ci.yml` |
| README update | Link to 5B/5D evidence docs + verified test baseline |
| Phase 4A cross-link | From `phase4a_public_evidence_map.md` to this feature folder |

### Deliverables

- `docs/evidence/sprint_5d_claim_safety_reviewer_evaluation.md`
- Optional: `docs/evidence/phase5d_claim_safety_reviewer_test_log.md`

### Success metrics

- 100% golden case pass rate locally
- Documented stop conditions from `RISK_REVIEW.md` honoured in code

---

## Future / Deferred

Do not implement without explicit future sprint instruction and updated claim-safety review.

| Item | Notes |
| --- | --- |
| Live LLM integration | Provider behind interface; schema-enforced JSON mode; golden regression required |
| Provider abstraction | Mocked-first default; Claude/OpenAI adapters swappable in tests |
| API key handling | Environment variables only; never committed; settings documented in DEVELOPMENT.md |
| Notion integration | Metadata sync only if aligned with V6 scope; not claim reviewer output |
| Automation | No GitHub Action posting reviews; no auto-edit README |
| RAG over repo | If added, citations must be path+line evidence; unknowns when retrieval fails |
| Batch review of README | CLI tool possible; human approves diffs |
| Multi-project portfolio index | Cross-repo claims need per-repo evidence_context |

---

## Dependency Graph

```text
Phase 5A (docs)
    └── Phase 5B (mocked service + tests)
            └── Phase 5C (optional UI)
                    └── Phase 5D (eval proof + README evidence)
                            └── Deferred (live LLM, keys, automation)
```

---

## Alignment with CareerFunnel Conventions

- Business logic in `services.py` files
- Frozen dataclasses for return types
- Thin views
- No removal of existing tests
- No migration edits unless sprint explicitly requests
- Distinct from `CVTailoringAdvisorResult` — separate types for separate features

---

## Open Decisions for 5B Kickoff

| Decision | Options | Default recommendation |
| --- | --- | --- |
| Module path | `services.py` vs `claim_safety_reviewer.py` | Dedicated module if >150 lines |
| Persistence | Stateless vs review history model | Stateless for 5B |
| Evidence loader | Static rules only vs optional file reader | Static rules + user context for 5B |
| Channel enum | Strict five channels | Match `CLAIM_SAFETY_RULES.md` |

Mark unresolved items `[UNKNOWN]` until sprint 5B brief decides.

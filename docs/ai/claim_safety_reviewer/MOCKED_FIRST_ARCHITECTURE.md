# Claim-Safety Reviewer — Mocked-First Architecture

## Status

Planning document only. No runtime code in Phase 5A.

---

## Why Mocked-First

CareerFunnel Tracker already uses mocked-first patterns for optional Claude paths (Sprint 33–34). The Claim-Safety Reviewer must follow the same discipline:

1. **Deterministic behaviour** — golden cases must pass without network variance.
2. **Zero secrets in repo** — no API keys, no `.env` provider config for MVP.
3. **Evidence alignment** — rule engine compares claims to documented facts, not model hallucination.
4. **Portfolio credibility** — demonstrates AI application engineering (schema, evals, fallbacks) before live inference.
5. **Safe failure** — when rules cannot decide, return `unknown` rather than a confident wrong verdict.

A live LLM may be added only in a **deferred** phase with explicit sprint instruction, provider abstraction, and eval regression gates. Until then, all production-path behaviour is rule-based.

---

## Component Diagram (Text Form)

```text
┌─────────────────────────────────────────────────────────────────┐
│                        User / Caller                             │
│  (future: Django view, CLI, test harness — not in 5A)           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ClaimSafetyReviewRequest                       │
│  claim_text, channel, evidence_context, strict_mode              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Input Normalisation Layer                       │
│  - trim / collapse whitespace                                    │
│  - detect channel defaults                                       │
│  - strip markdown noise (optional)                               │
│  - reject empty input → structured error (future)                │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Claim Extraction (rules)                       │
│  - sentence splitting                                            │
│  - keyword / pattern buckets (deploy, AI, revenue, tests, …)   │
│  - atomic claim list with spans                                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
┌──────────────────────────┐   ┌──────────────────────────┐
│   Evidence Comparison     │   │   Risk Classification     │
│   - match repo rules      │   │   - severity by category  │
│   - check provided refs   │   │   - channel multiplier    │
│   - flag [UNKNOWN] gaps   │   │   - aggregate risk_level  │
└────────────┬─────────────┘   └────────────┬─────────────┘
             │                              │
             └──────────────┬───────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              Verdict + Safe Rewrite Composer                     │
│  - overall_verdict                                               │
│  - safe_rewrite (template + evidence-backed phrases)             │
│  - warnings, unknowns, reviewer_notes                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Response Validation Layer                       │
│  - schema enum checks                                            │
│  - required fields present                                       │
│  - safe_rewrite non-empty for unsafe/needs_evidence              │
│  - reject if live provider fields leak in (future)               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              ClaimSafetyReviewerResult (frozen dataclass)        │
│  Returned to caller; serialisable to JSON for tests/UI          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│         DEFERRED: Live LLM Provider (not in MVP path)            │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────────┐  │
│  │  Provider   │───▶│  Prompt +    │───▶│  Parse + validate   │  │
│  │  abstraction│    │  schema spec │    │  (same schema)      │  │
│  └─────────────┘    └──────────────┘    └─────────────────────┘  │
│  Fallback to rule engine on timeout / parse failure / no key     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Input Normalisation

| Step | Behaviour |
| --- | --- |
| Trim | Remove leading/trailing whitespace |
| Empty guard | Empty `claim_text` → `unknown` verdict with warning (future service) |
| Channel default | Missing channel → `general` |
| Case folding | Lowercase copy for pattern matching only; preserve original for rewrites |
| Number extraction | Capture numeric claims (test counts, user counts, revenue) for evidence check |
| Negation awareness | "No Gmail integration" is safe alignment, not an unsupported positive claim |

---

## Claim Extraction

Rule-based atomic claim detection (no NLP model in MVP):

**Categories (pattern buckets):**

- `deployment` — live, production, hosted, demo URL, deployed
- `ai_llm` — GPT, Claude, OpenAI, Anthropic, LLM-powered, AI-driven automation
- `commercial` — SaaS, customers, revenue, ARR, enterprise clients, subscriptions
- `integration` — Gmail, OAuth, calendar, scraping, auto-apply, auto-send
- `testing` — test count, CI green, all tests pass
- `analytics` — funnel metrics, data quality, SQLite, Django service layer
- `generation` — generates CV, writes cover letter, automatic submission

Each extracted claim record (internal, pre-schema):

```text
claim_id, text_span, category, polarity (positive|negative|neutral)
```

---

## Evidence Comparison

Compare each positive claim against:

1. **`CLAIM_SAFETY_RULES.md`** rule tables (compiled into code in 5B)
2. **User `evidence_context`** — verbatim excerpts only
3. **`repo_snapshot_refs`** — if path listed, reader loads static allowlist (future: fixture bundle in tests)

**Verdict mapping per claim:**

| Match | Sub-verdict |
| --- | --- |
| Supported by cited log/doc | safe |
| Contradicts README "not claimed" | unsafe |
| Plausible but no citation in context | needs_evidence |
| Cannot classify | unknown |

Aggregate `overall_verdict` = worst sub-verdict by severity order: `unsafe` > `needs_evidence` > `unknown` > `safe`.

---

## Risk Classification

| risk_level | Typical triggers |
| --- | --- |
| `low` | Safe portfolio facts, negated non-features, channel-appropriate wording |
| `medium` | Unverified test counts, "CI passes" without run link, soft AI wording |
| `high` | Production users, revenue, live LLM on every request, auto-apply |
| `unknown` | Insufficient input or evidence context to classify |

Channel multipliers (planning):

- `job_application` and `linkedin` — promote risk one step if commercial/deployment language present
- `github_readme` — allow technical depth if matched to evidence index
- `interview` — allow spoken qualifiers if rewrite preserves boundaries

---

## Response Validation

Post-compose checks before returning result:

- All schema enums valid
- `reviewed_claims` non-empty when input non-empty
- `unsupported_claims` subset of `reviewed_claims`
- If `overall_verdict` in (`unsafe`, `needs_evidence`): `safe_rewrite` must be non-empty string
- `warnings` and `unknowns` are lists (possibly empty)
- No fields contain API keys, tokens, or full CV/cover letter bodies
- String lengths capped (e.g. `safe_rewrite` ≤ 2000 chars) to prevent generation drift

Invalid internal compose → fallback behaviour.

---

## Fallback Behaviour

| Condition | Fallback |
| --- | --- |
| Empty input | `overall_verdict: unknown`, `risk_level: unknown`, warning "empty_claim" |
| Schema validation failure | Re-run with minimal safe response; log internal error in tests only |
| Ambiguous channel | Use `general` rules; add `unknowns` entry |
| Conflicting evidence excerpts | `needs_evidence`; warn "conflicting_evidence" |
| Future: LLM timeout/parse error | Rule engine result only; add warning "provider_fallback" |

**Never** fallback to `safe` when commercial/deployment/AI automation keywords detected without support.

---

## No Live Provider Until Later

Phase 5B–5D architecture constraints:

- No `import openai`, `anthropic`, or similar in Claim-Safety Reviewer module
- No HTTP client calls for inference
- No `settings.CLAUDE_API_KEY` or equivalent read in reviewer path
- Tests use golden fixtures only

Deferred provider path must:

- Share identical `RESPONSE_SCHEMA_DRAFT.md` output shape
- Run golden cases in CI with provider mocked
- Default to rule engine when key absent (same as existing CV Tailoring pattern)

---

## No Secrets / API Keys

- Planning and MVP implementation live entirely in repo docs and rule code
- Evidence files reference public paths only
- User-pasted secrets in `claim_text` should trigger `warnings: ["possible_secret_pasted"]` and `risk_level: high` (future 5B)
- Never echo secrets back in `safe_rewrite`

---

## Suggested Module Placement (Future 5B — Not Implemented)

Align with existing conventions:

- Business logic: `apps/ai_agents/services.py` or `apps/ai_agents/claim_safety_reviewer.py`
- Return type: `@dataclass(frozen=True)` e.g. `ClaimSafetyReviewerResult`
- Views: thin; no logic in templates
- Tests: `tests/test_claim_safety_reviewer.py` + golden case parametrisation

Final placement subject to explicit Sprint 5B instruction.

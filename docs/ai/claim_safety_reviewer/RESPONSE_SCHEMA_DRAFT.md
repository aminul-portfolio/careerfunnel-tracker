# Claim-Safety Reviewer — Response Schema Draft

## Status

Draft specification for Phase 5B implementation. Not enforced by runtime code in Phase 5A.

---

## Design Principles

- JSON-serialisable for tests and future API responses
- Enum-constrained verdicts — no free-form status strings
- Advisory only — `safe_rewrite` is suggested wording, not auto-applied content
- Explicit `unknowns` — never silently omit unverified facts
- No provider metadata in MVP (no `model`, `tokens`, `provider` fields until deferred phase)

---

## Top-Level Response Shape

```json
{
  "overall_verdict": "safe",
  "risk_level": "low",
  "reviewed_claims": [],
  "unsupported_claims": [],
  "evidence_required": [],
  "safe_rewrite": "",
  "warnings": [],
  "unknowns": [],
  "reviewer_notes": ""
}
```

---

## Field Definitions

### `overall_verdict` (required)

**Type:** string enum

**Allowed values:**

| Value | Meaning |
| --- | --- |
| `safe` | All material positive claims supported by provided evidence or align with documented safe claims |
| `needs_evidence` | One or more claims plausible but not verified in supplied context; rewrite required before publish |
| `unsafe` | One or more claims contradict repo facts or forbidden overclaim rules |
| `unknown` | Insufficient input or evidence to classify; do not publish without human review |

**Aggregation rule:** worst claim wins — `unsafe` > `needs_evidence` > `unknown` > `safe`.

---

### `risk_level` (required)

**Type:** string enum

**Allowed values:**

| Value | Meaning |
| --- | --- |
| `low` | Minor wording polish; unlikely to mislead recruiters |
| `medium` | Could mislead if published; evidence gap or soft overclaim |
| `high` | Serious portfolio/reputation risk (commercial, production, AI automation, secrets) |
| `unknown` | Risk not assessable from input |

**Note:** `risk_level` is independent but correlated with `overall_verdict`. Example: `needs_evidence` + unverified test count → `medium`; `unsafe` + revenue claim → `high`.

---

### `reviewed_claims` (required)

**Type:** array of objects

```json
{
  "claim_id": "c1",
  "text": "The app has 1977 passing tests.",
  "category": "testing",
  "polarity": "positive",
  "sub_verdict": "safe"
}
```

| Sub-field | Type | Notes |
| --- | --- | --- |
| `claim_id` | string | Stable id within response |
| `text` | string | Atomic claim text |
| `category` | string | deployment, ai_llm, commercial, integration, testing, analytics, generation, general |
| `polarity` | string | positive, negative, neutral |
| `sub_verdict` | string | Same enum as `overall_verdict` |

---

### `unsupported_claims` (required)

**Type:** array of strings

Subset of claim texts where `sub_verdict` is `needs_evidence` or `unsafe`. May be empty when `overall_verdict` is `safe`.

---

### `evidence_required` (required)

**Type:** array of strings

Human-readable list of what would upgrade verdict. Examples:

- "Attach dated test log with `Ran N tests` line"
- "Remove production deployment language or provide verified URL evidence"
- "Cite README 'What Is Not Claimed' if denying a feature"

---

### `safe_rewrite` (required)

**Type:** string

Channel-appropriate suggested replacement for full input `claim_text`. Must:

- Preserve truthful scope (portfolio, local, manual, rule-based)
- Not invent test counts, CI status, or deployment facts
- Use `[UNKNOWN]` placeholder where evidence missing
- Stay under 2000 characters (implementation cap)

May be identical to input when `overall_verdict` is `safe` and wording already optimal.

---

### `warnings` (required)

**Type:** array of strings

Machine- and human-readable warning codes or messages. Examples:

- `forbidden_production_claim`
- `unverified_test_count`
- `unverified_ci_status`
- `ai_automation_overclaim`
- `possible_secret_pasted`
- `channel_tone_mismatch`

---

### `unknowns` (required)

**Type:** array of strings

Facts referenced or implied but not verified in this review session. Examples:

- "Latest GitHub Actions run status"
- "Whether a live deployment URL exists"
- "Exact current test count if no log excerpt provided"

---

### `reviewer_notes` (required)

**Type:** string

Short rationale (1–5 sentences) for human reviewer. No bullet lists of entire CV. No cover letter generation.

---

## Optional Request Metadata (Future Input Schema — Not Response)

For implementers; not returned in response:

```json
{
  "claim_text": "...",
  "channel": "cv",
  "evidence_context": {
    "test_log_excerpt": "Ran 1977 tests in 26.523s\nOK",
    "test_log_date": "2026-07-08",
    "doc_refs": ["docs/evidence/phase4a_current_public_test_log.md"]
  },
  "strict_mode": true
}
```

---

## Validation Rules (Phase 5B)

1. `overall_verdict` ∈ {safe, needs_evidence, unsafe, unknown}
2. `risk_level` ∈ {low, medium, high, unknown}
3. `reviewed_claims` is array (may be empty only if input empty)
4. `unsupported_claims` ⊆ texts from `reviewed_claims`
5. If `overall_verdict` ∈ {unsafe, needs_evidence} → `len(safe_rewrite) > 0`
6. No key in response outside defined schema (+ optional `_meta` for tests only, stripped in production)
7. Strings must be UTF-8; no binary content

---

## Example Responses

### Safe analytics claim

```json
{
  "overall_verdict": "safe",
  "risk_level": "low",
  "reviewed_claims": [
    {
      "claim_id": "c1",
      "text": "Django portfolio project with funnel metrics and data-quality reporting.",
      "category": "analytics",
      "polarity": "positive",
      "sub_verdict": "safe"
    }
  ],
  "unsupported_claims": [],
  "evidence_required": [],
  "safe_rewrite": "Django portfolio project with funnel metrics, data-quality signals, and reviewer-ready evidence exports.",
  "warnings": [],
  "unknowns": [],
  "reviewer_notes": "Aligns with README positioning and analytics module documentation."
}
```

### Unsafe production claim

```json
{
  "overall_verdict": "unsafe",
  "risk_level": "high",
  "reviewed_claims": [
    {
      "claim_id": "c1",
      "text": "Live SaaS product with paying enterprise customers.",
      "category": "commercial",
      "polarity": "positive",
      "sub_verdict": "unsafe"
    }
  ],
  "unsupported_claims": [
    "Live SaaS product with paying enterprise customers."
  ],
  "evidence_required": [
    "Remove commercial user/revenue language unless independently verified and documented."
  ],
  "safe_rewrite": "Local Django portfolio project for my own job search analytics; not a commercial SaaS product.",
  "warnings": ["forbidden_production_claim", "commercial_overclaim"],
  "unknowns": [],
  "reviewer_notes": "README explicitly denies live SaaS users, billing, and production deployment claims."
}
```

### Needs evidence (test count without log)

```json
{
  "overall_verdict": "needs_evidence",
  "risk_level": "medium",
  "reviewed_claims": [
    {
      "claim_id": "c1",
      "text": "All 2500 tests pass in CI.",
      "category": "testing",
      "polarity": "positive",
      "sub_verdict": "needs_evidence"
    }
  ],
  "unsupported_claims": [
    "All 2500 tests pass in CI."
  ],
  "evidence_required": [
    "Provide dated local test log excerpt or verified GitHub Actions run URL."
  ],
  "safe_rewrite": "The project includes a broad Django test suite; see docs/evidence/phase4a_current_public_test_log.md for the latest verified local run.",
  "warnings": ["unverified_test_count", "unverified_ci_status"],
  "unknowns": [
    "Whether 2500 is the current test count",
    "Latest GitHub Actions run status"
  ],
  "reviewer_notes": "Test count and CI status must come from cited evidence, not invention."
}
```

---

## Mapping to Future Dataclass

Suggested frozen dataclass name: `ClaimSafetyReviewerResult` (distinct from `CVTailoringAdvisorResult`).

Nested claim rows: `ClaimSafetyReviewedClaim` frozen dataclass.

Implementation sprint must not create `CVTailoringRecommendation` or duplicate CV tailoring types.

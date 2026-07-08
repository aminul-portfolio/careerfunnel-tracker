# Sprint 5B — Claim-Safety Reviewer Mocked Service

## Sprint

**Name:** Phase 5B — Claim-Safety Reviewer Mocked Service MVP  
**Branch:** `feature/phase5b-claim-safety-reviewer-mocked-service`  
**Date:** 2026-07-08

---

## Files Changed

| File | Action |
| --- | --- |
| `apps/ai_agents/claim_safety_reviewer.py` | Added — rule-based reviewer service + schema validator |
| `apps/ai_agents/test_claim_safety_reviewer.py` | Added — golden cases + validator + boundary tests |
| `docs/evidence/sprint_5b_claim_safety_reviewer_mocked.md` | Added — this evidence note |
| `README.md` | Minimal Phase 5B evidence link only |

**Not changed:** models, migrations, routes, views, templates, settings, database schema, provider modules.

---

## Service Summary

`review_claim_safety(claim_text, evidence_context=None, channel="general") -> dict`

- Deterministic, rule-based claim classification
- Compares positive claims against high/medium-risk term patterns and optional `evidence_context`
- Returns schema-shaped dict with verdict, risk, reviewed claims, warnings, unknowns, and conservative `safe_rewrite`
- `validate_claim_safety_response(response) -> tuple[bool, list[str]]` enforces Phase 5A schema enums and required fields
- Optional frozen dataclass: `ClaimSafetyReviewerResult` (via `.to_dict()`)

**Design alignment:** `docs/ai/claim_safety_reviewer/MOCKED_FIRST_ARCHITECTURE.md`, `RESPONSE_SCHEMA_DRAFT.md`, `CLAIM_SAFETY_RULES.md`

---

## Test Coverage Summary

| Area | Tests |
| --- | --- |
| Golden cases (Phase 5A spec) | 12 parametrized subtests |
| Required response fields | 1 |
| Empty input → unknown | 1 |
| Validator accept/reject | 4 |
| No provider/network imports | 2 |
| **Module total** | **9** |

Golden categories covered: safe analytics, production, AI/LLM, revenue, deployment, mixed, unknown evidence, CV, README, LinkedIn, interview, job application.

---

## Commands Run

```bash
python manage.py test apps.ai_agents.test_claim_safety_reviewer -v 2
python manage.py check
python manage.py test
```

### Results (local, 2026-07-08)

| Command | Result |
| --- | --- |
| Claim-safety module tests | **9 tests OK** (12/12 golden cases pass) |
| `python manage.py check` | **OK** — no issues |
| Full suite | **1986 tests OK** (1977 baseline + 9 new module tests) |

---

## Claim-Safety Boundary

- Service is **advisory only** — does not auto-publish or mutate records
- **Never invents** test counts, CI status, deployment facts, or revenue
- Uses `[UNKNOWN]` phrasing in rewrites when proof absent
- Test count **1977** honoured only when `evidence_context` cites Phase 4A-style log markers
- Forbidden overclaims return `unsafe` / `high` with conservative rewrites

---

## No Live API / Provider Confirmation

- **No** OpenAI, Anthropic, Gemini, LangChain, `requests`, or `httpx` imports in `claim_safety_reviewer.py`
- **No** API keys or environment provider reads
- **No** network calls
- **No** live LLM capability claimed by this sprint

---

## No UI / Route / Model / Database Confirmation

- **No** new Django routes or URLs
- **No** views or templates
- **No** models or migrations
- **No** settings changes
- **No** database persistence for reviews (stateless service)

---

## Known Limitations

- Rule-based pattern matching — not semantic NLP; may miss novel phrasing
- `channel` parameter reserved for Phase 5C tone adjustments (currently unused)
- Evidence comparison uses caller-supplied `evidence_context` only — no runtime filesystem reads
- `safe_rewrite` uses scenario templates — not generative prose
- README historical "900+ tests" baseline not auto-reconciled; cite dated test logs instead
- Golden cases validate expected warnings as **subset** (all listed warnings must appear; extras allowed)
- Test module is `apps/ai_agents/test_claim_safety_reviewer.py` (sibling to existing `tests.py`) because a `tests/` package conflicts with Django discovery for this app

---

## Phase 5C Recommendation

1. Add authenticated internal review page (thin view calling `review_claim_safety`)
2. Form: claim text, channel select, optional evidence excerpt paste
3. Display verdict, risk, warnings, unknowns, copy-only `safe_rewrite`
4. Advisory banner: "Suggested wording only — verify before publishing"
5. Still **no** live LLM provider; still **no** auto-write to README/CV
6. Optional persistence only if explicit sprint approves a model + migration

---

## Related Documents

- Planning: `docs/ai/claim_safety_reviewer/`
- Phase 4A claim safety: `docs/evidence/phase4a_claim_safety_review.md`
- Roadmap: `docs/ai/claim_safety_reviewer/IMPLEMENTATION_ROADMAP.md`

# Sprint 107 — Claim-Safety Evaluation Report

## Scope

Sprint 107 adds version-controlled evaluation evidence for the existing mocked, deterministic, rule-based Claim-Safety Reviewer in `apps/ai_agents/claim_safety_reviewer.py`.

This sprint is evidence-generating only. It does not change runtime classification logic, routes, templates, models, migrations, or provider integration.

## Reviewer boundary

This reviewer is mocked, deterministic, and rule-based. It is not a live AI/LLM integration.

## Evaluation methodology

1. Define a fixed JSON dataset at `apps/ai_agents/claim_safety_evaluation_cases.json`.
2. Call the existing `review_claim_safety()` function for each conformance case.
3. Assert core outputs and selected invariants in `apps/ai_agents/test_claim_safety_evaluation.py`.
4. Document two explicit known-limitation cases separately from conformance results.
5. Re-run targeted and full Django test suites for reproducible proof.

## Dataset structure

- Dataset name: CareerFunnel Claim-Safety Evaluation Dataset
- Dataset version: 1.0
- Sprint: 107
- Total cases: 22
- Defined categories: 20
- Conformance cases: 20
- Known-limitation cases: 2
- Case IDs: `CSR107-001` through `CSR107-022`

Each case includes claim text, optional evidence context, channel, evaluation status, expected core outputs, rewrite invariants, rationale, and limitation notes where applicable.

## Category coverage

Required categories 01–20 are covered with this multiplicity:

- Categories 01–08: one case each
- Category 09: two cases
- Categories 10–19: one case each
- Category 20: two known-limitation cases

Capability meta-claims (categories 04–06) are grouped separately from ordinary career claims. Robustness cases use the `robustness` group. Known-limitation cases use the `limitation` group.

## Assertion strategy

Conformance tests assert exactly:

- `overall_verdict`
- `risk_level`
- whether `unsupported_claims` is empty or non-empty

Additional invariant checks use subset logic for:

- warning codes
- `evidence_required` non-empty status
- `unknowns` non-empty status
- required and forbidden `safe_rewrite` substrings

Determinism is verified by repeating identical inputs three times for category 14 and requiring full response equality.

## Evaluation results

After Sprint 107 implementation validation:

- 22 total cases in dataset
- 20 defined categories represented
- 20 conformance cases evaluated against current runtime behaviour
- 2 known-limitation cases documented explicitly and excluded from conformance pass counting
- 8 evaluation-proof test methods in `ClaimSafetyEvaluationProofTests`
- Targeted Sprint 107 tests: 8 methods, all passing (Ran 8 tests in 0.010s — OK)
- Full suite result: 2008 tests, all passing (Ran 2008 tests in 23.841s — OK)

Passing evaluation cases confirms conformance to defined expected behaviour within this version-controlled dataset. It does not prove general correctness, intelligence, model quality, production readiness, deployment readiness, commercial readiness, or customer value.

## Known limitations

Documented known-limitation cases:

1. `CSR107-021` — indirect multi-team adoption wording may evade explicit SaaS keyword rules.
2. `CSR107-022` — semantic nuance, sarcasm, or implied enterprise adoption may not be captured by simple rule patterns.

Additional limitations:

- Evidence text is not independently verified beyond caller-supplied context markers.
- Channel values are accepted but do not currently alter runtime classification behaviour.
- Input-handling robustness evidence is plain-text handling only and is not a security audit.

## False-positive risks

- Legitimate claims containing high-risk keywords such as production, SaaS, deployment, autonomous agents, or customer language may be classified too conservatively when sufficient contextual evidence is not recognised by the current deterministic rules.
- Mixed claims may inherit the highest-risk sub-verdict even when some individual segments are independently supported.
- Numeric test-count or CI-status wording may require additional evidence even where the underlying claim is true but the supplied evidence context is incomplete.

## False-negative risks

- Vague or ambiguous low-risk wording may be classified `safe` without strong evidence requirements.
- Indirect adoption or commercial-scale language without explicit high-risk keywords may remain `safe`.
- Nuanced semantic meaning, implication, sarcasm, or sophisticated paraphrasing may evade deterministic keyword and rule patterns.

## Runtime-change policy

Sprint 107 does not change the runtime claim-classification logic.

If a conformance case reveals a genuine runtime defect, the correct response is a separate corrective sprint. Evaluation cases must not be weakened to force green results.

## Claim-safe interpretation

This sprint proves structured evaluation evidence for a mocked reviewer. It does not prove live AI capability, production deployment, customer usage, revenue, or commercial validation.

## Safe portfolio wording

Designed and evaluated a mocked, deterministic, rule-based claim-safety reviewer using a version-controlled dataset of 22 cases across 20 defined risk categories, with documented expected behaviour, evaluation results, and known limitations. This is not a live AI/LLM integration.

## Reproduction commands

```bash
python -m json.tool apps/ai_agents/claim_safety_evaluation_cases.json > $null
ruff check .
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test apps.ai_agents.test_claim_safety_evaluation
python manage.py test
```

Dataset count check:

```bash
python -c "import json; p='apps/ai_agents/claim_safety_evaluation_cases.json'; d=json.load(open(p, encoding='utf-8')); print('cases=', len(d['cases'])); print('categories=', len(set(c['category'] for c in d['cases']))); print('conformance=', sum(c['evaluation_status']=='conformance' for c in d['cases'])); print('known_limitations=', sum(c['evaluation_status']=='known_limitation' for c in d['cases']))"
```

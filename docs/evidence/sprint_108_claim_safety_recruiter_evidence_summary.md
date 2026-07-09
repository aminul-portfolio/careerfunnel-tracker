# Sprint 108 — Claim-Safety Recruiter Evidence Summary

## What was built

CareerFunnel Tracker includes a mocked, deterministic, rule-based Claim-Safety Reviewer delivered across four engineering stages:

1. **Phase 5A** — MVP planning pack under `docs/ai/claim_safety_reviewer/`.
2. **Phase 5B** — `review_claim_safety()` service in `apps/ai_agents/claim_safety_reviewer.py` with golden-case tests.
3. **Sprint 106** — staff-only manual review route with form, view, template, and route regression tests.
4. **Sprint 107** — version-controlled evaluation dataset (`22` cases, `20` categories) and eight automated evaluation-proof tests.

Sprint 108 packages this existing evidence into recruiter-readable repository documentation. It does not add runtime capability.

## Why it was built

Job-search and portfolio wording can overstate automation, deployment, customers, revenue, or live AI. The Claim-Safety Reviewer provides a local, rule-based advisory check that compares claim text against documented evidence context and returns structured verdicts, warnings, evidence requirements, and conservative rewrites. The engineering progression was designed to stay claim-safe, testable, and traceable before any future provider integration sprint.

## Engineering progression

| Stage | Focus | Primary evidence |
| --- | --- | --- |
| Phase 5A | Planning, schema, rules, golden cases | `docs/ai/claim_safety_reviewer/` |
| Phase 5B | Mocked reviewer service | `apps/ai_agents/claim_safety_reviewer.py` |
| Sprint 106 | Staff-only manual review route | `docs/evidence/sprint_106_claim_safety_internal_review_route.md` |
| Sprint 107 | Evaluation dataset and proof tests | `docs/evidence/sprint_107_claim_safety_evaluation_report.md` |
| Sprint 108 | Repository evidence packaging | This document set |

Merge checkpoint for Sprint 107: PR #17, feature commit `5666cf7`, merge commit `e4ead84`, completion tag `sprint-107-claim-safety-evaluation-proof-complete`.

## Architecture and workflow

- **Service:** `review_claim_safety(claim_text, evidence_context=None, channel="general")` returns a structured dict with `overall_verdict`, `risk_level`, `reviewed_claims`, `unsupported_claims`, `evidence_required`, `safe_rewrite`, `warnings`, `unknowns`, and `reviewer_notes`.
- **Validation:** `validate_claim_safety_response()` enforces required fields and enum values.
- **Design:** Mocked-first, deterministic keyword and rule patterns; no live provider calls.
- **Manual review:** Staff-only route for in-app inspection; no persistence, export, or background processing.
- **Evaluation:** JSON dataset loaded by `ClaimSafetyEvaluationProofTests`; conformance cases call the live reviewer function directly.

## Evaluation proof

Sprint 107 evidence (unchanged by Sprint 108):

- `22` evaluation cases
- `20` defined risk categories
- `20` conformance cases
- `2` known-limitation cases
- `8` automated evaluation-proof test methods
- `2008` passing full-suite tests at Sprint 107 closure

Passing evaluation cases confirms conformance to defined expected behaviour within this version-controlled dataset. It does not prove general correctness, intelligence, model quality, production readiness, deployment readiness, commercial readiness, or customer value.

## Skills demonstrated

Representative skills with repository evidence are mapped in `docs/evidence/sprint_108_claim_safety_skills_to_evidence_map.md`, including Python, Django, automated testing, deterministic rule design, evaluation dataset design, structured response contracts, input validation, defensive engineering, mocked-first discipline, documentation traceability, Git/GitHub workflow, and CI/CD evidence.

Two skills are `partially_verified` with narrow qualifications only:

- **Human-reviewed workflow boundaries** — staff-only manual review route only.
- **Evaluation methodology for a deterministic rule-based system** — fixed dataset and proof tests for this reviewer only.

## Security and privacy boundaries

Sprint 106 route evidence establishes:

- staff-only access (`staff_member_required`)
- CSRF protection on POST
- input length caps
- XSS escaping on rendered output
- no model writes, session storage, or logging of claim text or outputs
- no provider or network imports in route integration code

This is route-level defensive evidence, not a full security audit.

## Known limitations

- Reviewer is rule-based; indirect commercial wording, sarcasm, and semantic nuance may evade keyword patterns (`CSR107-021`, `CSR107-022`).
- Evidence context is caller-supplied and not independently audited.
- Channel values are accepted but do not currently alter runtime classification.
- Input-handling robustness evidence is plain-text handling only.
- Sprint 108 adds documentation only; it does not correct runtime classification behaviour.

## What this evidence proves

- A deliberate engineering progression from planning to mocked service to manual review to evaluation proof.
- Structured, testable reviewer output with schema validation.
- Version-controlled evaluation data with explicit known-limitation handling.
- Automated proof tests and documented sprint closure metrics.
- Claim-safe boundaries suitable for GitHub, portfolio, and interview discussion when paired with guardrails.

## What this evidence does not prove

- Live AI or LLM capability
- Model intelligence, training, or fine-tuning
- Production, deployment, enterprise, or commercial readiness
- Customer adoption, revenue, or commercial traction
- General correctness beyond the fixed evaluation dataset
- General AI safety or AI governance expertise
- Autonomous-agent or workflow-automation capability

## Claim-safe recruiter wording

This reviewer is mocked, deterministic, and rule-based. It is not a live AI/LLM integration.

Sprint 108 packages existing repository evidence only. It does not add runtime AI capability or change claim-classification logic.

Designed and evaluated a mocked, deterministic, rule-based claim-safety reviewer using a version-controlled dataset of 22 cases across 20 defined risk categories, with documented expected behaviour, evaluation results, and known limitations. This is not a live AI/LLM integration.

## Source evidence links

| Document | Path |
| --- | --- |
| Source-of-truth inventory | `docs/evidence/sprint_108_claim_safety_source_of_truth_inventory.md` |
| Skills-to-evidence map | `docs/evidence/sprint_108_claim_safety_skills_to_evidence_map.md` |
| Overstatement guardrails | `docs/evidence/sprint_108_claim_safety_overstatement_guardrails.md` |
| Phase 5B evidence | `docs/evidence/sprint_5b_claim_safety_reviewer_mocked.md` |
| Sprint 106 evidence | `docs/evidence/sprint_106_claim_safety_internal_review_route.md` |
| Sprint 107 report | `docs/evidence/sprint_107_claim_safety_evaluation_report.md` |
| Sprint 107 summary | `docs/evidence/sprint_107_claim_safety_evaluation_summary.md` |
| Reviewer service | `apps/ai_agents/claim_safety_reviewer.py` |
| Evaluation dataset | `apps/ai_agents/claim_safety_evaluation_cases.json` |
| Evaluation tests | `apps/ai_agents/test_claim_safety_evaluation.py` |

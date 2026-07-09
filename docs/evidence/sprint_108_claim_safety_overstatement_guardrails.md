# Sprint 108 — Claim-Safety Overstatement Guardrails

## Purpose

This document defines approved factual claims, narrow qualifications, and prohibited wording for the CareerFunnel Tracker Claim-Safety Reviewer across GitHub, CV, LinkedIn, interview, and portfolio channels. Sprint 108 packages existing repository evidence only. It does not add runtime capability.

## Canonical reviewer boundary

This reviewer is mocked, deterministic, and rule-based. It is not a live AI/LLM integration.

## Approved factual claims

The following claims are supported by repository evidence when cited accurately:

- Phase 5A Claim-Safety Reviewer MVP planning exists under `docs/ai/claim_safety_reviewer/`.
- Phase 5B implemented `review_claim_safety()` as a mocked, deterministic, rule-based service.
- Structured reviewer output is validated by `validate_claim_safety_response()`.
- Sprint 106 added a staff-only manual review route with security and statelessness controls.
- Sprint 107 added a version-controlled evaluation dataset with `22` cases across `20` defined categories.
- Sprint 107 separated `20` conformance cases from `2` known-limitation cases.
- Sprint 107 added `8` automated evaluation-proof test methods.
- Sprint 107 did not change runtime claim-classification logic.
- Full-suite validation reached `2008` passing tests at Sprint 107 closure.
- Sprint 107 merged via PR #17 (`5666cf7` → `e4ead84`) with Django CI #214 passing.
- Completion tag: `sprint-107-claim-safety-evaluation-proof-complete`.

Passing evaluation cases confirms conformance to defined expected behaviour within this version-controlled dataset. It does not prove general correctness, intelligence, model quality, production readiness, deployment readiness, commercial readiness, or customer value.

## Claims requiring narrow qualification

Use narrower wording for the following terms:

| Broad term | Preferred narrow wording |
| --- | --- |
| AI evaluation methodology | Evaluation methodology for a deterministic rule-based system |
| Evaluation framework | Version-controlled evaluation dataset and automated evaluation-proof tests for the deterministic reviewer |
| Human-in-the-loop | Staff-only manual review route |
| Workflow automation | Manual form submission to a local mocked reviewer; no automation |
| AI application architecture | Mocked-first Django service with structured response contract |
| AI safety / AI governance | Claim-safety controls for career and application wording (deterministic reviewer scope only) |
| Robust / scalable | Deterministic rule-based reviewer with documented limitations; do not imply production scale |

Qualify **human-reviewed workflow boundaries** as staff-only manual review route only. Do not imply a general enterprise human-in-the-loop platform.

Qualify **evaluation methodology** as applying to this mocked reviewer and fixed dataset only. Do not describe it as general ML or LLM evaluation.

## Prohibited claims

The following phrases must **not** be used as affirmative descriptions of the Claim-Safety Reviewer:

- AI-powered
- AI-driven
- intelligent reviewer
- validated AI system
- trained model
- fine-tuned model
- production AI
- production-ready AI
- enterprise-ready
- commercially validated
- customer-proven
- autonomous agent
- agentic
- 100% accuracy
- perfect accuracy
- live AI
- live LLM

These phrases may appear in this guardrails document only when explicitly listed as prohibited examples. They must not be used affirmatively in other Sprint 108 documents or external channel copy unless future evidence independently justifies them.

Also prohibited as affirmative claims:

- Paying customers, revenue, ARR, or commercial traction from this reviewer
- Production deployment or live SaaS usage
- Model quality, intelligence, or learning behaviour
- General AI safety or AI governance expertise
- Autonomous workflow or auto-apply capability

## Metrics and evidence rules

Only use these Sprint 107 metrics where supported by repository evidence:

- `22` evaluation cases
- `20` defined risk categories
- `20` conformance cases
- `2` known-limitation cases
- `8` automated evaluation-proof test methods
- `2008` passing full-suite tests
- PR #17
- feature commit `5666cf7`
- merge commit `e4ead84`
- Django CI #214 passed
- completion tag `sprint-107-claim-safety-evaluation-proof-complete`

Do not invent accuracy percentages, precision, recall, F1, benchmark scores, customer impact, revenue impact, productivity percentages, time savings, commercial results, usage volumes, or deployment scale.

## Privacy exclusions

Do not expose or invent:

- home address
- phone number
- private personal email
- private recruiter correspondence
- private application notes
- private salary details
- customer data
- credentials, passwords, API keys, or access tokens

Use only public, synthetic, or repository-verifiable evidence.

## Cross-channel consistency policy

Core facts, metrics, project naming, boundaries, and limitations must remain consistent across GitHub, CV, LinkedIn, interviews, and portfolio use. Only length, tone, and level of technical detail may vary by channel.

## Stop conditions

Stop external publication and revise wording if any of the following occur:

- a claim cannot be traced to a repository path, commit, PR, tag, or documented sprint evidence record
- a prohibited phrase appears as an affirmative description
- metrics differ across channels without explanation
- live AI, LLM, deployment, or customer claims are introduced without new verified evidence
- evaluation conformance is described as general correctness or model validation
- known-limitation cases are omitted or presented as full conformance passes

Sprint 108 packages existing repository evidence only. It does not add runtime AI capability or change claim-classification logic.

## Approved long-form wording

Designed and evaluated a mocked, deterministic, rule-based claim-safety reviewer using a version-controlled dataset of 22 cases across 20 defined risk categories, with documented expected behaviour, evaluation results, and known limitations. This is not a live AI/LLM integration.

# Sprint 106 — Claim Safety Internal Review Route

## Sprint purpose

Add a staff-only Django internal/manual review route that exposes the existing mocked,
rule-based claim-safety reviewer service for in-app manual use.

## Scope

- Django form integration for claim text, optional evidence context, and channel selection
- Staff-only route and view
- Template rendering of review outputs from the mocked service
- Route-level regression tests for access, CSRF, escaping, statelessness, and boundaries

## Files changed

- `apps/ai_agents/forms.py`
- `apps/ai_agents/views.py`
- `apps/ai_agents/urls.py`
- `apps/ai_agents/test_claim_safety_review_route.py`
- `templates/claim_safety/review.html`
- `docs/evidence/sprint_106_claim_safety_internal_review_route.md`

## Safety boundaries

- Staff-only internal review flow
- Manual form submission only
- No background processing
- No output export flow
- No saved review history

## Access control

- View is protected with `staff_member_required`
- Anonymous and non-staff users are blocked (redirect/forbidden)

## No persistence

- No model writes
- No migration changes
- No session storage of claim text/output
- No message storage of claim text/output
- No logging of claim text/output

## No live AI/LLM integration

- Existing mocked/rule-based service is used
- No live provider calls are introduced
- No provider SDK imports are introduced in this sprint route integration

## No API keys

- No new API key references introduced for this route
- No `.env` usage introduced

## No provider/network calls

- No network/HTTP imports introduced in new route form/template/test code
- Review remains local and deterministic

## No models/migrations/database changes

- No model edits
- No migration files generated
- No database schema updates

## Tests added

- New test module: `apps/ai_agents/test_claim_safety_review_route.py`
- Coverage includes:
  - anonymous/non-staff access denial
  - staff GET/POST render
  - CSRF 403 on missing token
  - length caps
  - XSS escaping checks
  - template unsafe rendering token checks
  - import-boundary checks
  - stateless/no-row-create checks
  - neutral route/view/template naming checks
  - empty-claim unknown outcome without saving

## Locked warnings (manual-use)

- This review is mocked and rule-based. It is not a live AI/LLM integration. No claim text or review output is saved.
- Do not paste private, sensitive, financial, medical, legal, or job-application personal data.
- Screenshots of this page are local-only and must not be used as proof of live AI capability.
- Manual review remains required before using any rewritten wording externally.

## Screenshot warning

Screenshots from this internal page are local evidence only and must not be used to imply
live AI capability or live provider integration.

## Claim-safe portfolio wording

Sprint 106 adds a staff-only Django review route for a mocked, rule-based Claim-Safety Reviewer service. It does not integrate a live AI/LLM provider and does not save claim text or review output.

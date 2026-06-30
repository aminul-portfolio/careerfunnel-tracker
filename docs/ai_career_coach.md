# AI Career Coach and AI Advisory Architecture

## Status

This document describes the private AI Career Coach workflow and the private AI Advisory surface in CareerFunnel Tracker after Sprints 80-97.

Both surfaces are private, authenticated-only, and advisory. They support career planning from structured CareerFunnel data. They do not make autonomous decisions, predict job outcomes, verify proficiency, certify skills, or submit applications.

The AI Advisory route family is deterministic and planning-focused. No live AI model is used in the current AI Advisory implementation. No production AI provider is connected to the advisory surface.

CareerFunnel Tracker is not a production AI platform. It is not a multi-user SaaS product. It is a private portfolio and career-planning system.

---

## AI Advisory surface (Sprints 84-97)

### Private advisory principles

The AI Advisory surface is:

- **private** - authenticated users only; anonymous requests redirect to login
- **deterministic** - rule-based classifications, contract previews, and static case examples; not live model inference
- **advisory only** - planning and safety review aids; not proficiency certification or employer outcome prediction
- **read-only on the advisory pages** - GET-only routes that do not create, update, or delete Skill Ledger entries, applications, CVs, public profiles, or generated documents
- **manual review required** - the user must review evidence before using any skill claim publicly

AI advisory outputs do not verify proficiency. AI advisory outputs do not certify skills. AI advisory outputs do not predict employer outcomes. The platform does not automatically update CVs, LinkedIn, public profiles, applications, or Skill Ledger evidence from the advisory surface.

### AI Advisory route map

All routes are namespaced under `skill_ledger` and require login.

| Route | Purpose |
| --- | --- |
| `/skill-ledger/advisory/` | Skill Ledger advisory classifications from deterministic rules |
| `/skill-ledger/advisory/explanations/` | AI explanation contract preview (mocked provider mode) |
| `/skill-ledger/advisory/ai-evidence/` | AI safety controls and evidence dashboard |
| `/skill-ledger/advisory/ai-review-hub/` | Private navigation hub for advisory pages |
| `/skill-ledger/advisory/manual-review-checklist/` | Static manual review checklist |
| `/skill-ledger/advisory/evaluation-casebook/` | Deterministic failure-case evaluation casebook |

### Portfolio contribution by route

**`/skill-ledger/advisory/` (Sprint 85)**

- Shows deterministic Skill Ledger advisory classifications derived from evidence level, visibility, and JD signal context.
- Demonstrates rule-based advisory design without AI inference.
- Portfolio story: structured claim-safety classifications before any provider call.

**`/skill-ledger/advisory/explanations/` (Sprint 88)**

- Previews the frozen AI explanation contract using deterministic mocked output.
- Shows evidence basis, claim-safety warnings, manual next actions, and confidence boundaries per advisory row.
- Portfolio story: explanation schema and validator discipline without live generation.

**`/skill-ledger/advisory/ai-evidence/` (Sprint 89)**

- Summarises safety controls, contract health, data counts, and mutation boundaries.
- Makes explicit that no live provider is configured, no raw provider output is stored, and no records are mutated.
- Portfolio story: evidence-first AI governance visibility for a private advisory layer.

**`/skill-ledger/advisory/ai-review-hub/` (Sprint 90)**

- Links the private advisory pages into one manual review workflow.
- Reinforces that the hub does not call a provider, save output, or submit applications.
- Portfolio story: human-in-the-loop navigation design for advisory AI readiness.

**`/skill-ledger/advisory/manual-review-checklist/` (Sprint 91)**

- Provides static checklist guidance for CV, LinkedIn, portfolio, and public profile claims.
- Separates JD signals, skill gaps, and learning recommendations from verified proficiency.
- Portfolio story: operational manual review workflow before public skill claims.

**`/skill-ledger/advisory/evaluation-casebook/` (Sprint 97)**

- Presents eight deterministic evaluation cases as private planning references.
- Each case defines evaluation focus, safety boundary, expected safe behaviour, and fail condition.
- Portfolio story: failure-case-first AI engineering before connecting any live provider.

### Sprint 97 - Evaluation casebook (failure-case-first AI engineering)

Sprint 97 added the Private AI Advisory Evaluation Casebook as a static, read-only reference. It is not a production AI evaluation framework.

The casebook contains eight deterministic cases covering:

1. Skill claim inflation check
2. Live AI/provider claim check
3. CV/public-profile mutation boundary
4. Application submission boundary
5. Skill Ledger evidence escalation boundary
6. Learning recommendation advisory boundary
7. JD signal advisory boundary
8. Generated document boundary

Each case includes:

- **evaluation focus** - what the reviewer should check
- **safety boundary** - what the advisory surface must not do
- **expected safe behaviour** - acceptable deterministic wording
- **fail condition** - wording or behaviour that would break claim safety

The casebook does not run live AI generation. It does not produce pass/fail runtime results, automated grading, or model performance metrics. Cases are planning and safety review aids only. Passing a case in documentation terms does not verify skill proficiency or predict employer outcomes.

Required safety wording on the casebook page includes:

- These cases are deterministic review examples, not live AI generations.
- No live AI model is used in this version.
- Evaluation cases are planning and safety review aids only.
- Passing an evaluation case does not verify skill proficiency or predict employer outcomes.
- These examples do not update CVs, public profiles, applications, or Skill Ledger evidence.
- This page is private and advisory only.

### Claim-safety discipline across the advisory layer

The advisory layer enforces consistent boundaries:

- **advisory only** - outputs guide planning; they are not hiring decisions
- **manual review required** - evidence must be checked before public claims
- **no proficiency certification** - classifications and explanations do not certify skills
- **no employer outcome prediction** - no employability guarantees or outcome forecasts
- **no automated scoring or grading** - no candidate scores, model benchmarks, or runtime evaluation badges
- **no mutation** - advisory pages do not update CVs, LinkedIn, public profiles, applications, or Skill Ledger evidence
- **no generated documents** - advisory pages do not create CVs, cover letters, or application submissions

These boundaries are regression-tested across Sprints 85-97.

### How the advisory layer supports future AI readiness

The advisory work completed in Sprints 84-97 prepares the platform for future provider integration without claiming it today:

- frozen explanation contracts and validators (Sprint 87-88)
- visible safety and evidence dashboards (Sprint 89)
- manual review workflows and checklists (Sprint 90-91)
- deterministic failure cases documented before live calls (Sprint 97)

Future provider connection, if approved in a later sprint, would still require validator-gated display, mocked fallback, private authentication, and manual review. The current advisory surface demonstrates AI engineering discipline - boundaries, contracts, evidence checks, and failure cases - without implying live AI integration, OpenAI, Anthropic, Gemini, LangChain, or any production AI API.

---

## Sprint history

### Sprint 80 - AI Career Coach architecture contract

Sprint 80 introduced the architecture contract for AI-assisted career guidance.

It added:

- evidence payload construction
- controlled prompt construction
- expected response schema
- response validation
- claim-safety guardrails

Sprint 80 did not add:

- a route
- a template
- a live provider
- API-key handling
- database persistence of AI output
- public AI output

### Sprint 81 - Mocked AI Career Coach page

Sprint 81 added a private mocked AI Career Coach page.

The workflow was:

```text
structured evidence payload
        |
        v
controlled prompt
        |
        v
mocked response
        |
        v
validator
        |
        v
safe private display
```

The mocked workflow allowed the full AI pathway to be tested without using a live model.

### Sprint 82 - Live LLM provider spike

Sprint 82 added an environment-gated live provider spike for the AI Career Coach pathway only.

The live provider is optional. Mocked mode remains the default and fallback.

The Sprint 82 workflow is:

```text
structured evidence payload
        |
        v
provider selection
        |
        |-- mocked provider by default
        |
        |-- live provider only when COACH_PROVIDER=live
        |
        v
provider response
        |
        v
Sprint 80 validator
        |
        v
safe private display or fallback message
```

This spike applies to the Skill Gaps AI Career Coach route, not to the Skill Ledger AI Advisory surface.

### Sprint 83 - Documentation and deterministic foundation

Sprint 83 documented the AI Career Coach architecture and aligned deterministic skill matching between applications and skill gaps. It did not add live AI capability to the advisory surface.

### Sprint 84 - JD requirement enrichment overlay

Sprint 84 added a private JD requirement enrichment workflow beside deterministic tracked terms.

Boundaries delivered:

- deterministic counts remain unchanged
- enrichment output is candidate-only
- every candidate requirement must point to an exact saved JD excerpt
- if the excerpt is not found, the candidate is rejected
- no raw provider output is saved

### Sprint 85 - Skill Ledger advisory layer

Sprint 85 added the private Skill Ledger advisory page at `/skill-ledger/advisory/`.

Boundaries delivered:

- deterministic classifications from evidence level and visibility
- JD signal context from saved term frequency only
- no automatic Skill Ledger mutation
- no AI inference on the advisory page

### Sprint 86 - Advisory safety wording and JD signal boundaries

Sprint 86 strengthened JD signal and Skill Ledger advisory safety wording on the advisory surface.

### Sprint 87 - AI explanation contract (mocked)

Sprint 87 introduced the frozen Skill Advisory explanation contract with mocked provider mode only.

### Sprint 88 - AI explanation contract preview

Sprint 88 added `/skill-ledger/advisory/explanations/` to preview deterministic explanation rows against the contract.

### Sprint 89 - AI safety controls and evidence dashboard

Sprint 89 added `/skill-ledger/advisory/ai-evidence/` to show safety controls, contract health, and mutation boundaries without live provider monitoring.

### Sprint 90 - AI advisory review hub

Sprint 90 added `/skill-ledger/advisory/ai-review-hub/` as a private navigation hub linking advisory pages.

### Sprint 91 - Manual review checklist

Sprint 91 added `/skill-ledger/advisory/manual-review-checklist/` as static manual review guidance.

### Sprint 97 - Private AI Advisory Evaluation Casebook

Sprint 97 added `/skill-ledger/advisory/evaluation-casebook/` with eight deterministic failure-case examples for advisory safety review.

---

## Current AI Career Coach architecture

The AI Career Coach implementation (Skill Gaps pathway) is split across these files:

```text
apps/skill_gaps/ai_career_coach.py
apps/skill_gaps/ai_providers.py
apps/skill_gaps/views.py
templates/skill_gaps/ai_career_coach.html
apps/skill_gaps/tests.py
```

The AI Advisory surface (Skill Ledger pathway) is split across:

```text
apps/skill_ledger/advisory.py
apps/skill_ledger/ai_explanation.py
apps/skill_ledger/views.py
templates/skill_ledger/skill_ledger_advisory.html
templates/skill_ledger/skill_advisory_explanations.html
templates/skill_ledger/skill_advisory_ai_evidence.html
templates/skill_ledger/skill_advisory_ai_review_hub.html
templates/skill_ledger/skill_advisory_manual_review_checklist.html
templates/skill_ledger/skill_advisory_evaluation_casebook.html
apps/skill_ledger/tests.py
```

### `ai_career_coach.py`

This module owns the core AI contract for the Skill Gaps AI Career Coach pathway.

Responsibilities:

- build structured evidence payloads
- build provider-safe evidence payloads
- construct controlled prompts
- define expected response shape
- validate provider or mocked responses
- reject unsafe or unsupported output
- provide fallback-safe behaviour

This module is the main safety boundary for AI Career Coach output.

### `ai_providers.py`

This module owns provider selection and provider calls for the AI Career Coach spike only.

Responsibilities:

- choose mocked or live provider
- keep mocked provider as the default
- read provider configuration from environment variables
- call the live provider only when explicitly enabled
- parse provider response as structured JSON
- raise safe provider errors when the provider fails
- prevent oversized provider responses from being accepted

This module must not contain hardcoded API keys. It is not used by the Skill Ledger AI Advisory surface.

### Skill Ledger advisory modules

`apps/skill_ledger/advisory.py` owns deterministic Skill Ledger advisory classifications.

`apps/skill_ledger/ai_explanation.py` owns the frozen explanation contract and mocked explanation builder used by the explanation preview page.

Neither module connects to a live AI provider in the current advisory implementation.

### `views.py`

The AI Career Coach view and AI Advisory views are private and authenticated.

AI Advisory views use `@login_required` and `@require_GET`. Authenticated POST requests return 405.

Responsibilities:

- build advisory or evidence context from existing records where applicable
- render deterministic or mocked contract output only
- avoid saving AI or advisory output to the database or session
- keep evaluation casebook data as static in-view list-of-dicts with no runtime evaluation

### Templates

Advisory templates display validated or deterministic output only.

Responsibilities:

- show private advisory interfaces
- show advisory wording and mutation boundaries
- distinguish mocked or deterministic mode safely
- avoid rendering raw provider output
- avoid implying production AI, autonomous decisions, or guaranteed outcomes

---

## Provider configuration

Provider configuration applies to the AI Career Coach spike only. The AI Advisory surface does not read provider environment variables and does not call a live model.

### `COACH_PROVIDER`

`COACH_PROVIDER` controls provider mode for the AI Career Coach pathway.

Supported values:

```text
mocked
live
```

Default behaviour:

```text
If COACH_PROVIDER is absent, empty, or set to mocked,
the system uses the mocked provider.
```

Live behaviour:

```text
If COACH_PROVIDER=live,
the system attempts to call the live provider.
```

If the live provider fails, times out, returns invalid JSON, returns unsafe output, or fails validation, the view must fall back safely.

### `COACH_API_KEY`

`COACH_API_KEY` stores the provider API key for the live provider spike.

Rules:

- The key must be set through the local environment.
- The key must never be committed to the repository.
- The key must not appear in `settings.py`.
- The key must not appear in tests as a real value.
- The key must not appear in documentation except as a placeholder name.

Example placeholder only:

```text
COACH_API_KEY=replace-with-local-provider-key
```

---

## Example `.env` configuration

Local development may use a private `.env` file, but `.env` must never be committed.

Example mocked mode:

```text
COACH_PROVIDER=mocked
```

Example live spike mode:

```text
COACH_PROVIDER=live
COACH_API_KEY=replace-with-local-provider-key
```

For safe local development, mocked mode should remain the default.

---

## Evidence payload boundary

The AI Career Coach must only use structured, bounded career-planning evidence.

Provider-bound payloads may include:

```text
term
frequency
ledger_status
display_label
matched_skill_name
is_in_ledger
```

Provider-bound payloads must not include private or raw data such as:

```text
notes
private_notes
email
company_name
job_description
jd_requirement
suggested_action
salary
contact
raw_provider_response
```

Sprint 83 strengthens this rule by enforcing `PRIVATE_EVIDENCE_FIELDS` as a real redaction/rejection guard.

Preferred behaviour:

```text
If a provider-bound evidence row contains a private field,
the payload builder should reject the row before any provider call is made.
```

This prevents accidental leakage before future JD-reading AI features are added.

---

## Validator rules

All provider or mocked output must pass the Sprint 80 validator before display on the AI Career Coach page.

The validator must reject output that:

- is not valid structured data
- is missing required fields
- contains unsupported skill claims
- claims the user is proficient without evidence
- claims a skill is verified without closed sprint evidence
- predicts job outcomes
- guarantees employability
- implies employer assessment
- instructs auto-apply or external submission
- recommends public profile claims without evidence
- contains raw provider text outside the expected schema
- contains unsafe or unsupported career advice

If validation fails, the view must display a safe fallback message instead of the provider output.

The AI Advisory explanation contract uses a separate deterministic validator in `ai_explanation.py` with the same claim-safety intent.

---

## Persistence rules

AI output must not be saved to:

```text
database
session
cache
log files
public pages
application records
skill ledger records
```

The current AI Career Coach output and AI Advisory pages are display-only and private.

Future sprints may store structured governance metrics only if separately approved, but raw provider output must remain non-persistent.

Allowed future governance metrics may include:

```text
validator passed or failed
fallback triggered or not
redaction passed or failed
provider mode used
failure category
deterministic vs LLM disagreement count
```

Raw provider output must not be stored as a governance metric.

---

## Fallback behaviour

The system must fall back safely when:

- the provider is unavailable
- the provider times out
- the API key is missing
- the provider response is too large
- the provider response is invalid JSON
- the provider response fails schema validation
- the provider response contains unsafe claims
- private fields are detected in provider-bound evidence

Fallback output must not expose:

- raw provider response
- API-key details
- stack traces
- private evidence fields
- sensitive job/application data

---

## Advisory wording

The AI Career Coach and AI Advisory surfaces must remain advisory only.

The features must not claim to:

- verify proficiency
- certify skills
- predict job outcomes
- guarantee employability
- assess employer requirements
- apply for jobs
- send emails
- create documents
- replace user judgement

Manual evidence review is required before using any skill claim in a CV, LinkedIn profile, portfolio, or public profile.

The user remains responsible for reviewing all career-planning output manually.

---

## Non-goals

The AI Career Coach and AI Advisory layers must not introduce:

```text
auto-apply
scraping
web automation
Gmail integration
OAuth integration
background tasks
async workers
external API writes
employer notifications
public AI output
raw LLM output persistence
job-outcome prediction
production AI claims
multi-user AI data separation
automated scoring
automated grading
automatic CV update
automatic LinkedIn or public profile update
automatic application submission
automatic Skill Ledger evidence upgrade
generated documents from the advisory surface
provider integration on the advisory surface
```

CareerFunnel Tracker remains a private, single-user, authenticated portfolio and career-planning platform.

---

## Future sprint direction

Sprints 99-102 are planned future direction only. They are not delivered features in the current codebase. Do not describe them as built.

Possible future themes (subject to separate sprint approval):

- extended governance metrics with explicit non-persistence rules
- additional deterministic evaluation cases
- further JD enrichment guardrails
- provider integration only after advisory boundaries, validators, and failure cases are proven

Any future live provider work must preserve mocked fallback, private authentication, validator-gated display, and manual review requirements established in Sprints 80-97.

### Deterministic matching alignment (Sprint 83)

Before Sprint 83, the JD-gap aggregation in `apps/applications/services.py` used substring matching (`_find_skill_ledger_match`) to link JD terms to Skill Ledger entries, while `apps/skill_gaps/services.py` used alias-normalised exact matching (`normalise_skill_match_key` and `SKILL_ALIAS_MAP`). This inconsistency meant the two surfaces could produce different match results for the same skill term.

Sprint 83 aligns both services to alias-normalised exact matching. This ensures:

- deterministic, consistent results across both surfaces
- no false positives from substring collisions, such as `sql` matching `nosql`
- a stable foundation before any LLM enrichment layer is added on top in Sprint 84

The `SKILL_ALIAS_MAP` in `apps/skill_gaps/services.py` is the canonical normalisation reference. Extending the alias map requires a corresponding test.

---

## Developer checklist before extending AI

Before any new AI feature is added, confirm:

```text
1. Does the feature preserve mocked fallback?
2. Is live mode environment-gated?
3. Is provider-bound input structured and minimal?
4. Are private fields rejected before provider calls?
5. Is every output validator-gated?
6. Is unsafe output rejected?
7. Is fallback behaviour safe?
8. Is raw provider output not saved?
9. Is the feature private and authenticated-only?
10. Are advisory-only boundaries visible and tested?
11. Are deterministic failure cases documented before live provider connection?
12. Does the feature avoid automated scoring, grading, or outcome prediction?
```

If any answer is no, the sprint should not proceed.

---

## Safe portfolio wording

### AI Career Coach pathway

Safe wording:

```text
Built a private, evidence-grounded AI Career Coach workflow with controlled prompts, provider-safe evidence payloads, mocked fallback, validator-gated display, and regression-tested safety boundaries.
```

### AI Advisory pathway (Sprints 84-97)

Safe wording:

```text
Built a private, deterministic AI Advisory surface with rule-based classifications, frozen explanation contracts, safety evidence dashboards, manual review workflows, and a failure-case evaluation casebook - all without live AI generation on the advisory routes.
```

### Interview-ready wording

Use this wording honestly in interviews and portfolio reviews:

```text
I designed advisory boundaries, explanation contracts, evidence checks, manual review workflows, and deterministic failure cases before connecting any live AI provider.
```

Expand only with evidence you can demonstrate:

- six private advisory routes under `/skill-ledger/advisory/`
- mocked explanation contract preview, not live generation
- regression-tested claim-safety wording
- eight deterministic evaluation cases with explicit fail conditions (Sprint 97)
- optional environment-gated live spike on the separate AI Career Coach pathway only

Unsafe wording:

```text
Built a production AI career coach.
Built a production AI evaluation framework.
Built an autonomous job-application AI.
Built an AI that predicts job success.
Built an AI that verifies career skills.
Built an AI that applies to jobs automatically.
Connected OpenAI/Anthropic/Gemini to the advisory dashboard.
Automated CV or LinkedIn updates from AI output.
```

Use conservative, evidence-backed wording only.

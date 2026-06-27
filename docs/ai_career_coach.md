# AI Career Coach Architecture

## Status

This document describes the private AI Career Coach workflow in CareerFunnel Tracker after Sprints 80-82.

The AI Career Coach is a private, authenticated-only planning feature. It is designed to support career planning from structured CareerFunnel data, not to make autonomous decisions, predict job outcomes, verify proficiency, or submit applications.

CareerFunnel Tracker is not a production AI platform. It is not a multi-user SaaS product. It is a private portfolio and career-planning system.

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

Sprint 82 added an environment-gated live provider spike.

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

---

## Current AI architecture

The current AI Career Coach implementation is split across these files:

```text
apps/skill_gaps/ai_career_coach.py
apps/skill_gaps/ai_providers.py
apps/skill_gaps/views.py
templates/skill_gaps/ai_career_coach.html
apps/skill_gaps/tests.py
```

### `ai_career_coach.py`

This module owns the core AI contract.

Responsibilities:

- build structured evidence payloads
- build provider-safe evidence payloads
- construct controlled prompts
- define expected response shape
- validate provider or mocked responses
- reject unsafe or unsupported output
- provide fallback-safe behaviour

This module is the main safety boundary for AI output.

### `ai_providers.py`

This module owns provider selection and provider calls.

Responsibilities:

- choose mocked or live provider
- keep mocked provider as the default
- read provider configuration from environment variables
- call the live provider only when explicitly enabled
- parse provider response as structured JSON
- raise safe provider errors when the provider fails
- prevent oversized provider responses from being accepted

This module must not contain hardcoded API keys.

### `views.py`

The AI Career Coach view is private and authenticated.

Responsibilities:

- build the evidence payload
- call the provider abstraction
- validate the response before display
- display fallback output if validation or provider execution fails
- avoid saving AI output to the database or session

### `ai_career_coach.html`

The template displays validated output only.

Responsibilities:

- show the private AI Career Coach interface
- show advisory wording
- distinguish mocked/provider mode safely
- avoid rendering raw provider output
- avoid implying production AI, autonomous decisions, or guaranteed outcomes

---

## Provider configuration

Provider configuration is environment-controlled.

### `COACH_PROVIDER`

`COACH_PROVIDER` controls provider mode.

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

All provider or mocked output must pass the Sprint 80 validator before display.

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

The current AI Career Coach output is display-only and private.

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

The AI Career Coach must remain advisory only.

The feature must not claim to:

- verify proficiency
- certify skills
- predict job outcomes
- guarantee employability
- assess employer requirements
- apply for jobs
- send emails
- create documents
- replace user judgement

The user remains responsible for reviewing all career-planning output manually.

---

## Non-goals

The AI Career Coach must not introduce:

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
```

CareerFunnel Tracker remains a private, single-user, authenticated portfolio and career-planning platform.

---

## Future sprint direction

### Sprint 83 - Documentation and deterministic foundation

Sprint 83 does not add new AI capability.

It prepares the platform for safer future AI work by:

- documenting the AI Career Coach architecture
- documenting provider environment variables
- adding or updating `.env.example`
- aligning deterministic matching between applications and skill gaps
- enforcing private-field protection before provider calls

### Deterministic matching alignment

Before Sprint 83, the JD-gap aggregation in `apps/applications/services.py` used substring matching (`_find_skill_ledger_match`) to link JD terms to Skill Ledger entries, while `apps/skill_gaps/services.py` used alias-normalised exact matching (`normalise_skill_match_key` and `SKILL_ALIAS_MAP`). This inconsistency meant the two surfaces could produce different match results for the same skill term.

Sprint 83 aligns both services to alias-normalised exact matching. This ensures:

- deterministic, consistent results across both surfaces
- no false positives from substring collisions, such as `sql` matching `nosql`
- a stable foundation before any LLM enrichment layer is added on top in Sprint 84

The `SKILL_ALIAS_MAP` in `apps/skill_gaps/services.py` is the canonical normalisation reference. Extending the alias map requires a corresponding test.

### Sprint 84 - JD Requirement Enrichment Overlay

Sprint 84 may add an additive LLM extraction layer beside deterministic `TRACKED_TERMS`.

Required boundaries:

- deterministic counts remain unchanged
- LLM output is candidate-only
- every candidate requirement must point to an exact saved JD excerpt
- if the excerpt is not found, the candidate is rejected
- no raw LLM output is saved

### Sprint 85 - Skill Ledger Advisory Layer

Sprint 85 may add advisory Skill Ledger review suggestions.

Required boundaries:

- no automatic Skill Ledger mutation
- one-step status suggestion only
- no automatic `VERIFIED` promotion
- evidence reason required per suggestion
- user must manually decide whether to update the ledger

### Sprint 86 - AI Governance Console

Sprint 86 may add a private governance dashboard.

Possible metrics:

- validator pass/fail counts
- fallback rate
- redaction check results
- provider mode
- deterministic vs LLM disagreement metrics
- failure categories

Required boundary:

```text
Governance metrics may be stored only if separately approved.
Raw provider output must not be stored.
```

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
```

If any answer is no, the sprint should not proceed.

---

## Safe portfolio wording

Safe wording:

```text
Built a private, evidence-grounded AI Career Coach workflow with controlled prompts, provider-safe evidence payloads, mocked fallback, validator-gated display, and regression-tested safety boundaries.
```

Unsafe wording:

```text
Built a production AI career coach.
Built an autonomous job-application AI.
Built an AI that predicts job success.
Built an AI that verifies career skills.
Built an AI that applies to jobs automatically.
```

Use conservative, evidence-backed wording only.

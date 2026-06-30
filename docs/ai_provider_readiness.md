# AI Provider Readiness Gate

## 1. Purpose

Sprint 102 creates a formal governance document for future AI provider integration readiness in CareerFunnel Tracker.

This document defines the safety, privacy, payload, mutation, rollback, testing, and approval requirements that must be satisfied before any live-AI provider integration can be considered.

Sprint 102 does not implement live AI. It records the readiness gate only.

No sprint may treat this document as permission to connect a live provider without a separately approved implementation sprint that satisfies every checklist item in this file.

## 2. Current boundary

The following statements define the Sprint 102 boundary:

- Sprint 102 does not integrate a live AI provider.
- No OpenAI, Anthropic, Gemini, LangChain, provider SDK, API key, network call, background job, or live model invocation is added in this sprint.
- The readiness gate is documentation only.
- Live AI remains forbidden until a future separately approved sprint.

At Sprint 102 closure, the platform continues to operate with deterministic and mocked advisory pathways only. This document does not change runtime behaviour.

## 3. Non-goals

Sprint 102 and this readiness gate do not authorise or implement any of the following:

- no provider integration
- no provider abstraction
- no SDK/API key handling
- no network calls
- no prompt logging
- no caching
- no database writes
- no UI
- no route
- no CV/LinkedIn/public profile mutation
- no Skill Ledger mutation
- no application submission
- no email sending

Any future sprint that introduces one of these behaviours requires its own explicit scope lock, allowed-file list, and approval checklist.

## 4. Provider-readiness checklist

This checklist is binary and honest. It records current platform status at Sprint 102 closure. It does not present the platform as fully ready for live AI.

### Completed prerequisites

- [MET] Sprint 87 validator exists and is tested
- [MET] FORBIDDEN_EXPLANATION_PHRASES defined and imported
- [MET] Sprint 101 evaluator harness exists with 14+ tests
- [MET] Mocked fallback is default - live mode is opt-in only
- [MET] No AI output saved to database or session
- [MET] Evidence payload excludes PII (Sprint 83)
- [MET] .gitignore excludes .env files

### Known gaps before any live provider sprint

- [GAP] Provider-specific response size guard not yet tested for the advisory explanation path
- [GAP] Provider latency timeout not yet specified for the advisory explanation path
- [GAP] Cost-per-call estimate not yet documented
- [GAP] No formal rollback procedure documented beyond setting COACH_PROVIDER back to mocked

The presence of completed prerequisites does not mean live AI is approved. All known gaps must be closed, tested, and reviewed before any live provider connection is considered.

## 5. Safety and claim boundaries

Any future live-AI output must obey the following claim-safety rules:

- AI output must remain advisory unless separately approved and tested.
- A JD signal does not prove proficiency.
- A mocked evaluator result does not certify proficiency.
- No AI response may certify proficiency.
- No AI response may predict employer outcomes.
- No AI response may imply a user is job-ready, employer-ready, or guaranteed interviews.

Provider output must be treated as draft advisory text only. Manual evidence review remains required before any claim is reused in a CV, LinkedIn profile, public profile, cover letter, interview answer, or employer submission.

Forbidden explanation phrases defined in Sprint 87 remain in force for any future provider-bound explanation path.

The Sprint 101 mocked AI response evaluator must remain available as a deterministic pre-release or post-response safety gate unless a later sprint replaces it with an equivalent tested control.

## 6. Data privacy and logging boundaries

The following privacy and logging rules apply to any future live-AI integration:

- No prompt, CV, job description, application, Skill Ledger evidence, or user-provided data may be logged to files unless a later sprint explicitly approves a safe logging policy.
- Provider keys must never be committed to the repository.
- Provider keys must never be exposed in templates, logs, tests, screenshots, or documentation examples.
- Provider responses must not be persisted unless separately approved and tested.

Logging for debugging, analytics, or audit must not include raw provider prompts, raw provider responses, or user document content unless a dedicated privacy review approves a redacted logging format.

### Prompt injection risk

Saved job description text is untrusted external content.

A provider-bound payload that includes raw JD text must:

- sanitise the text before inclusion
- use explicit instruction/data separation
- never include raw JD text in the advisory explanation prompt path
- use only structured term signals where possible

Any future sprint that passes raw JD text to a provider requires a dedicated prompt injection risk assessment before implementation.

At Sprint 102 closure, the advisory explanation path from Sprints 87-91 must not receive raw JD text in any provider-bound payload.

### Caching restriction

Provider responses must not be cached using Django cache, Redis, Memcached, or any equivalent mechanism.

Caching a provider response is equivalent to persisting it.

If response caching is considered later, it requires:

- separate architecture review
- approved cache key structure
- approved TTL policy
- confirmation that cached content cannot be accessed by other users

## 7. Mutation boundaries

No AI response may update a CV, LinkedIn profile, public profile, Skill Ledger entry, application record, document pack, follow-up email, or employer submission automatically.

Live AI integration must not create, edit, save, submit, send, or publish anything without explicit manual user approval.

Future provider output must be treated as advisory text only unless a later sprint explicitly approves a different behaviour.

Even when a future sprint introduces copy-to-clipboard or draft export helpers, the platform must not imply that any external profile, ledger entry, or application has already been changed.

## 8. Testing requirements before any future live-AI sprint

Before any live provider sprint may begin, the following test categories must be planned, implemented, and passing:

- provider disabled/mocked fallback tests
- provider timeout tests
- response size guard tests
- forbidden phrase tests
- evidence payload privacy tests
- prompt injection mitigation tests
- no database/session persistence tests
- no mutation tests
- manual approval boundary tests
- rollback/kill-switch tests
- failure-mode tests

Each category must map to named tests in an approved test file list. A sprint may not close with undocumented or untested provider behaviour.

Sprint 102 adds no new tests. The baseline remains 1840 passing tests until a future implementation sprint adds provider-specific coverage.

## 9. Rollback and kill-switch requirements

Any live provider integration must be disableable without data loss and without requiring database migration.

### Current rollback mechanism

Current rollback mechanism:

Set COACH_PROVIDER environment variable to "mocked" or remove it entirely.
The platform immediately falls back to mocked output with no data loss and no database changes required.

This mechanism applies to the AI Career Coach pathway only.

### Current gap

Current gap:

The advisory explanation path has no equivalent EXPLANATION_PROVIDER variable yet.

Before Sprints 87-91 are connected to any live provider, a named environment-variable kill switch for that path must be designed, documented, tested, and approved.

### Kill-switch requirement

Kill-switch requirement:

Any live provider integration must be disableable in under 60 seconds by setting an environment variable. No code change, redeploy, or database migration should be required.

Rollback proof must include a documented operator step, a passing test that confirms mocked fallback, and confirmation that no provider response was persisted.

## 9B. Evidence payload boundary

Any provider-bound payload may contain only:

- skill names
- evidence level labels
- sprint references
- JD gap term names and frequency counts
- category labels

Any provider-bound payload must not contain:

- SkillEntry.notes field content
- JobApplication.notes field content
- JobApplication.company_name
- JobApplication.job_url
- JobApplication.job_description full text
- email addresses
- personal names
- salary figures
- contact names
- CV content
- cover letter content
- raw JD text beyond structured term signals

Additional rules:

- This boundary must be enforced by a named function and tested before any live provider sprint begins.
- Current status: implemented in Sprint 83 for the AI Career Coach path.
- Current gap: not yet implemented for the advisory explanation path from Sprints 87-91.
- This gap must be closed before Sprints 87-91 are connected to any live provider.

Payload assembly, review, and test evidence must be recorded in the future sprint scope lock before any provider call is enabled.

## 10. Future sprint approval checklist

No live provider sprint may start without explicit approval against this checklist:

- separate Claude architecture review
- ChatGPT scope lock
- clean pre-branch baseline
- explicit allowed files
- explicit forbidden files
- explicit tests
- explicit provider disabled state
- explicit rollback plan
- explicit prompt injection assessment
- explicit evidence payload privacy proof
- explicit no-mutation proof
- explicit cost/latency/response-size controls
- full validation before commit
- merge/tag/push/CI proof before closure

A future sprint must fail closed if any item is missing, untested, or contradicted by the diff.

Sprint 102 satisfies only the documentation portion of readiness planning. It does not satisfy this approval checklist for live integration.

## 11. Safe portfolio wording after Sprint 102

Use this exact safe statement:

"Designed and documented a formal AI provider readiness gate covering safety validation, evidence payload privacy, prompt injection risk, mutation boundaries, rollback requirements, and testing prerequisites - before connecting any live AI provider."

Also acceptable shorter safe version:

"Documented AI provider readiness criteria before live-AI integration."

These statements describe governance work only. They must not be rewritten to imply live provider deployment.

## 12. Forbidden portfolio wording after Sprint 102

Do not use any of the following wording in portfolio copy, README claims, demo scripts, or sprint summaries unless a separately approved live-provider sprint has actually implemented and tested the behaviour:

- "Integrated a live AI provider."
- "Connected the platform to OpenAI/Anthropic/Gemini."
- "Built a production AI feature."
- "Built production AI infrastructure."
- "Automated Skill Ledger updates using AI."
- "Automated CV or LinkedIn updates using AI."
- "Automatically evaluates applications using AI."
- "Predicts employer outcomes."
- "Certifies user proficiency."

If none of the above behaviours exist in the repository at Sprint 102 closure, portfolio wording must remain advisory, mocked, and evidence-review focused only.


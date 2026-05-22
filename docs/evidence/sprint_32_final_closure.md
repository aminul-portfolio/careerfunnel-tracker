# Sprint 32 Final Closure - Calibrated AI-Assisted Fit Scoring, Mocked-First

## Executive Summary

Sprint 32 delivered a **claim-safe, mocked-first foundation** for calibrated AI-assisted fit scoring. The work prepares a future provider integration without activating external AI in the product workflow today.

| Sub-sprint | Focus | Status |
|---|---|---|
| **32A** | Calibrated AI fit scoring audit + scope lock | Complete |
| **32B** | AI scoring service contract + mocked parser/tests | Complete |
| **32C** | OpenAI-shaped wrapper + safe fallback (dependency-injected, mocked-first) | Complete |
| **32D** | UI integration: rule-based vs AI score check with fallback display | Complete |
| **32E** | Evidence + final Sprint 32 closure | Complete (this document) |

Rule-based scoring from `analyze_job_posting` and job-intelligence services **remains the active scoring system**. The Job Posting Analyzer shows an advisory **Rule-Based vs AI Score Check** card that reports **fallback active** when no `provider_callable` is passed (Sprint 32D default). No real OpenAI API call, API key, or settings change was introduced.

---

## What Is Implemented

| Area | Detail |
|---|---|
| Structured AI scoring contract | `AIFitScoringResult` with validated fields (score, label, confidence, evidence, gaps, deal-breakers, reasoning, CV angle, projects, manual review, claim-safety notes) |
| Score comparison contract | `AIFitScoreComparison` with rule-based vs AI score delta, disagreement flag, and advisory summary |
| Parser and mock entry points | `parse_ai_fit_scoring_payload`, `build_ai_fit_scoring_result_from_mock`, `compare_rule_based_and_ai_scores` |
| OpenAI-shaped wrapper boundary | `build_openai_fit_scoring_prompt`, `build_openai_fit_scoring_with_fallback`, `OpenAIFitScoringWrapperResult` |
| Safe fallback | When `provider_callable` is omitted, wrapper returns fallback with `ai_result=None` and rule-based scoring remains authoritative |
| Dependency injection | Optional `provider_callable` accepts a local dict response for tests; no direct OpenAI client in repository |
| Rule-based score visibility | Existing fit score and recommendation remain primary in Job Posting Analyzer |
| UI integration (32D) | **Rule-Based vs AI Score Check** section after fit diagnosis; shows fallback reason, manual review, and claim-safety copy |
| Encoding hygiene (32D) | ASCII-only separators in new UI copy (`|`, `-`) with regression tests |
| Test coverage | Contract tests, wrapper/fallback tests, Job Posting Analyzer view tests, encoding regression |

### Evidence documents and code paths

- `docs/evidence/sprint_32a_calibrated_ai_fit_scoring_audit.md`
- `apps/ai_agents/services.py` (Sprint 32B-32C)
- `apps/ai_agents/tests.py`
- `apps/ai_agents/views.py` (Sprint 32D - `job_posting_analyzer` only)
- `templates/ai_agents/job_posting_analyzer.html`

Sprint 31 **CV Tailoring Advisor** integration on the same analyzer page remains in place and is unchanged by Sprint 32 scope.

---

## What Is NOT Implemented

| Claim / capability | Sprint 32 state |
|---|---|
| Real OpenAI API call | **Not implemented** |
| OpenAI SDK dependency | **Not added** |
| API key or settings change | **Not added** |
| External AI active in production workflow | **Not active** - fallback-only in UI |
| Database persistence of AI output | **Not implemented** |
| Auto-save of AI recommendations | **Not implemented** |
| Auto-apply | **Not implemented** |
| Gmail, Calendar, OAuth | **Not implemented** |
| Scraping | **Not implemented** |
| Recruiter automation | **Not implemented** |
| Background job submission | **Not implemented** |
| Final CV generation | **Not implemented** |
| Final cover letter generation | **Not implemented** |
| AI replaces rule-based scoring | **Not true** - rule-based remains primary |

---

## Evidence Table

| Sub-sprint | Branch / tag (convention) | Purpose | Result |
|---|---|---|---|
| **32A** | `sprint-32a-calibrated-ai-fit-scoring-audit-complete` | Audit rule-based baseline; lock JSON contract, calibration rules, and security boundaries | `docs/evidence/sprint_32a_calibrated_ai_fit_scoring_audit.md` |
| **32B** | `sprint-32b-ai-scoring-service-contract-mocked-tests-complete` | `AIFitScoringResult`, `AIFitScoreComparison`, parsers, comparison helper, mocked tests | Service contract in `apps/ai_agents/services.py`; tests in `apps/ai_agents/tests.py` |
| **32C** | `sprint-32c-openai-wrapper-safe-fallback-mocked-first-complete` | OpenAI-shaped prompt + wrapper with injected callable and safe fallback | Wrapper functions in `apps/ai_agents/services.py`; mocked provider tests |
| **32D** | `sprint-32d-rule-based-vs-ai-score-ui-complete` | Job Posting Analyzer shows rule-based vs AI check with fallback UI | `apps/ai_agents/views.py`, `templates/ai_agents/job_posting_analyzer.html`, view/encoding tests |
| **32E** | `sprint-32e-evidence-and-final-closure` | Final closure documentation and evidence index | This file + `docs/evidence/evidence_index.md` |

---

## Key Files Changed During Sprint 32

| Path | Sprint | Role |
|---|---|---|
| `docs/evidence/sprint_32a_calibrated_ai_fit_scoring_audit.md` | 32A | Scope lock and audit |
| `apps/ai_agents/services.py` | 32B-32C | AI scoring contract, comparison, OpenAI-shaped wrapper |
| `apps/ai_agents/tests.py` | 32B-32D | Contract, wrapper, view, and encoding tests |
| `apps/ai_agents/views.py` | 32D | `job_posting_analyzer` wrapper integration |
| `templates/ai_agents/job_posting_analyzer.html` | 32D | Rule-Based vs AI Score Check UI |
| `docs/evidence/evidence_index.md` | 32A, 32E | Sprint 32 evidence entries |
| `docs/evidence/sprint_32_final_closure.md` | 32E | This closure document |

---

## Validation Evidence

Final validated state for Sprint 32 (through Sprint 32D implementation and 32E documentation):

| Check | Result |
|---|---|
| Targeted `apps.ai_agents` tests | **56 passed** |
| Full Django test suite (`python manage.py test`) | **351 passed** |
| `ruff check` | Passed |
| `python manage.py check` | Passed |
| `python manage.py makemigrations --check --dry-run` | Passed |
| GitHub Actions / Django CI | Green through Sprint 32D merge baseline |

Sprint 32E adds documentation only; re-run validation after merge if repository state changes.

---

## Claim-Safe Portfolio Wording

Use wording like:

> CareerFunnel Tracker includes a mocked-first, advisory AI-scoring boundary that compares a future AI score against the existing rule-based score, preserves manual review, and falls back to rule-based scoring when no provider is active.

Supporting points (when needed):

- Rule-based fit scoring and CV Tailoring Advisor (Sprint 31) remain the implemented, local workflows.
- Job Posting Analyzer displays an advisory comparison card; current deployment path uses **fallback active** without an external provider.
- All Sprint 32 AI outputs are advisory and require manual review before external use.

---

## Unsafe Wording to Avoid

Do **not** use:

- "OpenAI-powered job scoring is live"
- "Automatically applies to jobs"
- "Automatically tailors CVs"
- "Uses Gmail/Calendar"
- "External AI makes application decisions"
- "AI replaces rule-based scoring"

Also avoid implying API keys in the repo, production LLM integration, or automatic persistence of AI recommendations.

---

## Final Sprint 32 Status

| Item | Status |
|---|---|
| Sprint 32A - Audit + scope lock | **Complete** |
| Sprint 32B - AI scoring contract + mocked tests | **Complete** |
| Sprint 32C - OpenAI wrapper + safe fallback (mocked-first) | **Complete** |
| Sprint 32D - Rule-based vs AI score UI | **Complete** |
| Sprint 32E - Evidence + final closure | **Complete** (documentation) |

**Sprint 32 family closure:** Sprint 32A-32D delivered the mocked-first AI scoring foundation and UI fallback display. Sprint 32E records this evidence package. A future sprint would be required for a real provider client, environment configuration, and opt-in UI activation-only after separate audit, validation, and explicit approval.

---

## Related Evidence

- Sprint 31 CV Tailoring Advisor: `docs/evidence/sprint_31_final_closure.md`
- Sprint 32A audit: `docs/evidence/sprint_32a_calibrated_ai_fit_scoring_audit.md`
- Evidence map: `docs/evidence/evidence_index.md`

# Claim-Safety Reviewer — Risk Review

## Status

Pre-implementation risk assessment for Phase 5A planning. Informs stop conditions for Phases 5B–5D and deferred work.

---

## Technical Risks

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Rule engine false positives (safe → unsafe) | Medium | Medium | Golden cases; human override in UI; reviewer_notes explain |
| Rule engine false negatives (unsafe → safe) | Low–Medium | High | Worst-wins aggregation; forbidden keyword list; negative tests |
| Schema drift between docs and code | Medium | Medium | Single schema validator; test schema enums |
| Scope creep into LLM before evals | Medium | High | Stop condition: no provider imports until 5D green + explicit sprint |
| Duplication with CVTailoringAdvisor | Low | Medium | Separate dataclass and module; shared utils only if tiny |
| Regex maintenance burden | Medium | Low | Document patterns in CLAIM_SAFETY_RULES; version rule set |
| Performance on long pasted text | Low | Low | Input length cap (e.g. 10k chars) |

---

## Portfolio Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Feature appears to "validate lies" if too permissive | Recruiter trust loss | Conservative defaults; `needs_evidence` over `safe` when unsure |
| Feature appears theatrical if never used | Weak interview story | Ship 5B tests + optional 5C UI; cite golden cases in interviews |
| Overclaiming the reviewer itself ("AI ensures truth") | Meta claim failure | Position as advisory rule engine + future optional LLM; mocked-first |
| Stale rules vs README | Incorrect verdicts | Update rules when README changes; link evidence hierarchy |
| Public demo of reviewer with unsafe example | Confusion | Demo only with golden case safe rewrites |

---

## Claim-Safety Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| `safe_rewrite` invents metrics | High | Template phrases; forbid uncited numbers; strict_mode |
| Reviewer blesses README drift | High | Do not auto-sync README; human publishes |
| Negation parsing errors ("no production" read as claim) | Medium | Polarity field in extraction |
| CI workflow cited as green | Medium | `unverified_ci_status` warning; unknowns list |
| User trusts verdict for legal/compliance | High | Disclaimer in UI; not legal advice |

---

## Privacy Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| User pastes recruiter emails into claim_text | PII exposure in logs | Warning `possible_secret_pasted`; no persistence in 5B; truncate logs |
| API keys pasted in form | Secret leak | High risk + redaction in display; never echo in safe_rewrite |
| Future persistence stores sensitive drafts | DB leak | Encrypt or avoid persistence; user=user scoping |
| Screenshots attached as evidence | PII in files | Cross-reference screenshot safety checklist Phase 4A |

---

## Job-Application Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Candidate publishes reviewer output verbatim without reading | Embarrassment in interview | Label as draft suggestion |
| Over-sanitized rewrite hides real achievements | Weak applications | Preserve verified metrics when evidenced |
| Inconsistent story across CV, LinkedIn, GitHub | Credibility gap | Channel-specific rules; same evidence hierarchy |
| Claiming "built AI claim validator with GPT" in 5B | False AI claim | Say "rule-based with schema and golden evals; mocked-first" |

---

## LLM Reliability Risks (Deferred Phase Only)

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Hallucinated safe rewrites | High | Schema validation; rule engine fallback; no LLM-only path |
| Non-deterministic golden failures | Medium | Provider mocked in CI; live evals manual/scheduled |
| Prompt injection in claim_text | Medium | Treat input as untrusted; strip instructions; length limits |
| Cost / key leakage | Medium | Keys in env only; no logging of prompts with secrets |
| Model confidently wrong on niche repo facts | High | RAG with citations or defer to rules for repo-specific claims |

**Phase 5B–5D:** LLM risks are **not applicable** — no live provider.

---

## Mitigations Summary

1. **Mocked-first** through 5D with golden regression
2. **Schema-bound** outputs with validator
3. **Evidence hierarchy** — docs and logs over model opinion
4. **`unknown` and `needs_evidence`** preferred over false `safe`
5. **Channel-aware** rewrites without generation sprawl
6. **Disclaimers** on any UI: advisory, not legal, not auto-publish
7. **Phase 4A linkage** — screenshot and test log discipline unchanged
8. **No secrets** in repo or reviewer responses

---

## Stop Conditions

Halt implementation and revert to planning if:

| # | Condition |
| --- | --- |
| 1 | Sprint attempts live LLM without deferred-phase approval |
| 2 | Golden case pass rate < 100% before claiming feature complete |
| 3 | Any test requires network to pass |
| 4 | `safe_rewrite` generates full CV or cover letter body |
| 5 | API keys appear in code, tests, or docs |
| 6 | Feature auto-modifies README, applications, or exports without user confirm |
| 7 | Verdict `safe` returned for commercial/production claims in golden negative cases |
| 8 | Migration added without explicit sprint scope for persistence |
| 9 | Portfolio messaging claims "production AI safety platform" |
| 10 | User reports PII stored from claim review form (investigate before continuing) |

**Phase 5A stop:** N/A — docs only. Do not proceed to 5B until user approves this plan.

---

## Residual [UNKNOWN] Items

- Exact Django app route naming for 5C — **[UNKNOWN]**
- Whether review history persistence is desired — **[UNKNOWN]** (recommend stateless for 5B)
- Whether live LLM will ever be approved — **[UNKNOWN]** (deferred)
- Current branch CI status — **[UNKNOWN]** (verify before external portfolio update)

---

## Sign-Off Checklist (Before 5B)

- [ ] MVP plan reviewed by project owner
- [ ] Golden cases agreed
- [ ] CLAIM_SAFETY_RULES aligned with latest README
- [ ] Stop conditions accepted
- [ ] No conflict with CLAUDE.md claim safety rules

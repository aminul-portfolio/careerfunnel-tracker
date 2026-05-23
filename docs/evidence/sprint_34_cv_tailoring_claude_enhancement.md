# Sprint 34 — CV Tailoring Claude Enhancement Evidence

## 1. Sprint Objective

Sprint 34 adds **claim-safe semantic enhancement** for the existing **CV Tailoring Advisor** while keeping **rule-based analysis authoritative** and **fallback-safe**.

The goal is to let optional Claude semantic matching suggest skills, projects, themes, risks, and interview points **only when configured**, without generating final CV text, cover letter bodies, recruiter messages, or automatic application actions. Every output remains **advisory only** with **manual review required**.

---

## 2. Implemented Phases

| Phase | Scope | Status |
|-------|--------|--------|
| **34A** | Evidence bank foundation | Complete |
| **34B** | Claude CV tailoring provider and semantic parser | Complete |
| **34C** | CV Tailoring Advisor semantic integration and fallback | Complete |
| **34D** | Documentation, evidence, README, closure prep | Complete (documentation only) |

---

## 3. Files Changed by Phase

### Sprint 34A — Evidence bank foundation

```text
apps/ai_agents/evidence_bank.py          (new)
apps/ai_agents/tests.py                  (EvidenceBankTests)
```

### Sprint 34B — Claude CV tailoring provider and semantic parser

```text
apps/ai_agents/claude_provider.py        (make_claude_cv_tailoring_provider)
apps/ai_agents/services.py               (CVTailoringSemanticResult, parse_cv_tailoring_semantic_payload)
apps/ai_agents/tests.py                  (TestClaudeCvTailoringProvider)
```

### Sprint 34C — CV Tailoring Advisor semantic fallback integration

```text
apps/ai_agents/services.py               (build_cv_tailoring_advisor provider_callable, merge helpers)
apps/ai_agents/views.py                  (optional provider when ANTHROPIC_API_KEY set)
templates/ai_agents/job_posting_analyzer.html
templates/ai_agents/application_agent_pack.html
apps/ai_agents/tests.py                  (TestCvTailoringAdvisorSemanticFallback)
```

### Sprint 34D — Documentation and evidence (this sprint)

```text
README.md
docs/evidence/evidence_index.md
docs/evidence/sprint_34_cv_tailoring_claude_enhancement.md
```

---

## 4. Claim-Safety Guarantees

| Guarantee | How it is enforced |
|-----------|-------------------|
| No `full_cv_text` | Forbidden provider field; parser rejection; no merge path |
| No `professional_summary` | Forbidden provider field |
| No `experience_bullets` | Forbidden provider field |
| No `cover_letter_body` | Forbidden provider field; advisory line filter on themes |
| No `recruiter_message` | Forbidden provider field |
| No `linkedin_post` | Forbidden provider field |
| `recommended_cv` remains `Aminul_Islam_Data_Analyst_CV` | Claude cannot set CV filename; merge always uses `LOCKED_CV` |
| Manual review required | Semantic contract requires `manual_review_required: true`; UI copy and `approval_reminder` preserved |
| Rule-based fallback remains active | Provider failures return unchanged rule-based result + fallback note |
| No Gmail / Calendar / OAuth | Not implemented; stated in safety notes and templates |
| No auto-apply / automatic submission | Not implemented; stated in safety notes and templates |

---

## 5. Validation Evidence

| Check | Result |
|-------|--------|
| `EvidenceBankTests` | 8 tests passing |
| `TestClaudeCvTailoringProvider` | 13 tests passing |
| `TestCvTailoringAdvisorSemanticFallback` | 12 tests passing |
| `apps.ai_agents` (full app) | **96** tests passing |
| Full project suite | **391** tests passing |
| `ruff check .` | Passed |
| `python manage.py check` | Passed |
| `python manage.py makemigrations --check --dry-run` | No changes detected |

Feature branch validation commit reference: `84aa5f3` Sprint 34C: integrate Claude CV tailoring fallback.

Tests use **`unittest.mock` only** for Claude paths — no real API calls in the test suite.

---

## 6. Public Wording

Safe wording for README / GitHub:

> CareerFunnel Tracker includes a claim-safe CV Tailoring Advisor that can combine rule-based analysis with optional Claude semantic enhancement when configured. The feature remains advisory only, preserves manual approval, and does not generate final CVs, cover letter bodies, recruiter messages, or submit applications automatically.

---

## 7. What Is Not Implemented

- No Gmail integration
- No Calendar integration
- No OAuth integration
- No auto-apply
- No automatic email sending
- No automatic CV generation
- No automatic cover letter generation
- No production deployment or live SaaS claim
- No production user base claim
- No guarantee that Claude runs on every request (optional when API key configured; rule-based fallback otherwise)

---

## 8. Closure Status

Sprint 34 implementation phases **34A–34C** are complete and validated on branch `sprint-34-cv-tailoring-claude-enhancement` with **391** full-project tests passing.

Sprint **34D** updates documentation and evidence (`README.md`, `evidence_index.md`, this file) before final merge, tag, and push.

Final merge/tag/push validation remains a manual step after reviewer sign-off.

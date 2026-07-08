# Claim-Safety Reviewer — Claim Safety Rules

## Status

Authoritative rule set for mocked-first reviewer logic (Phase 5B+). Derived from `README.md`, `CLAUDE.md`, and Phase 4A evidence docs.

---

## Safe Claims

These may be marked `safe` when `evidence_context` or default repo rules support them:

### Product scope

- Local Django **portfolio** project for personal job-search analytics
- **Single-user** / personal demonstration scope
- **Manual, advisory, rule-based** workflows
- **SQLite** for portfolio-scale local analytics
- Authenticated, user-scoped records (`user=user` pattern)

### Technical capabilities (evidenced in repo)

- Application tracking, funnel metrics, source/CV performance, rejection patterns
- Data-quality governance (`_application_is_analytics_ready`, save-quality warnings)
- Workbook exports (OpenPyXL)
- Service-layer analytics with `docs/analytics/` definitions
- Sprint evidence index and screenshot galleries
- Career Evidence OS (V1–V4 markdown + dashboard)
- Career Intelligence pipeline (Sprints 53–59) as **deterministic, read-only, rule-based**
- Skill Intelligence Dashboard at `/skill-gaps/` (read-only advisory sections)
- Application Document Pack — manual review, external final docs referenced, no auto-submit
- Recruiter email workflow — **manual import**, rule-based advisory
- CI **workflow file exists** (not run status without proof)
- Optional **mocked-first** Claude paths with rule-based fallback (worded carefully)

### Safe negations

Explicit denials aligned with README are **safe**:

- "No Gmail integration"
- "No auto-apply"
- "No production deployment claimed"
- "No cover letter body generation"

### Test claims (conditional)

- Specific test count **only** when dated log excerpt provided in `evidence_context`
- Phase 4A reference: **1977** tests on **2026-07-08** when citing `phase4a_current_public_test_log.md`

---

## Claims Requiring Evidence

Mark `needs_evidence` when claim is plausible but proof not in review context:

| Claim type | Evidence required |
| --- | --- |
| Numeric test count | Dated `python manage.py test` output excerpt |
| "CI passes" / "green build" | GitHub Actions run URL or screenshot with date |
| "Deployed at URL X" | Verified URL + environment doc |
| "Optional Claude runs in production" | Config evidence + scope doc; still not "every request" |
| Tableau Public / live dashboard link | Verified public URL |
| Performance metrics (uptime, latency) | Measurement log — generally out of scope |
| "900+ tests" (README baseline) | May lag; prefer latest test log |

Default placeholders in rewrites: `[UNKNOWN]` for unverified numbers and statuses.

---

## Claims to Reject

Mark `unsafe` — do not soften to `needs_evidence`:

| Forbidden claim | Rule source |
| --- | --- |
| Paying customers, ARR, revenue, subscriptions, billing | README "What Is Not Claimed" |
| Enterprise clients, B2B SaaS at scale | Portfolio scope |
| Production deployment / live demo (without verified proof) | README Live Demo Status |
| Multi-tenant production user base | Single-user portfolio |
| Gmail, Calendar, OAuth, inbox sync | Not implemented |
| Auto-apply, auto-send, background polling | Not implemented |
| Job board scraping at runtime | Not implemented |
| External AI/LLM on **every** request | Mocked-first; optional only |
| Autonomous agents replacing user actions | Not implemented |
| Generates full CV text or cover letter bodies | Claim safety rules |
| Scientific CV A/B testing | Directional reporting only |
| Financial ROI (money return) | Source ROI = channel performance |
| Power BI implementation (unless later evidenced) | README |
| API keys or secrets in portfolio copy | Security |

---

## Required [UNKNOWN] Handling

1. **Never invent** test counts, CI status, deployment URLs, or user numbers.
2. When evidence missing, populate `unknowns` array with specific gaps.
3. `safe_rewrite` uses qualitative wording or `[UNKNOWN]` — not guessed integers.
4. `strict_mode: true` forces `needs_evidence` for any uncited numeric claim.
5. README "900+ validated tests" is a **historical README baseline**; current count requires test log citation.
6. Phase 4A CI status **[UNKNOWN]** unless user supplies Actions evidence in same session.

---

## Forbidden Overclaims

Even if tempting for AI Application Engineer branding, reject or rewrite:

- "AI-powered job search automation"
- "LLM-native SaaS"
- "Production-grade MLOps pipeline" (not in scope)
- "Replaced manual job search with AI agents"
- "Integrated with OpenAI/Anthropic in production" (without scoped optional wording)
- "Thousands of users"
- "Investor-ready startup"
- "Hermes / Notion-powered autonomous workflow"

---

## Evidence Hierarchy

Highest to lowest trust for reviewer comparison:

| Rank | Source | Use |
| --- | --- | --- |
| 1 | Dated terminal test log in `docs/evidence/` | Test counts, check pass |
| 2 | README "What Is Not Claimed" / Live Demo Status | Negations and boundaries |
| 3 | Sprint closure docs `docs/evidence/sprint_*.md` | Feature scope at sprint time |
| 4 | Analytics docs `docs/analytics/` | Metric definitions |
| 5 | CI workflow file | Intended gates, not run outcome |
| 6 | User-pasted excerpt in `evidence_context` | Same session only |
| 7 | Model inference / LLM opinion | **Not used** in mocked-first MVP |

Lower ranks cannot override rank 1–2 contradictions.

---

## Channel Wording Rules

### CV

- Lead with Django, analytics, data quality, testing, documentation
- One bullet may cite verified test count with date
- Avoid: SaaS, startup, enterprise, AI automation
- Max specificity: portfolio + local + manual

### LinkedIn

- Short project blurb; link to GitHub evidence
- Tone: personal portfolio, not product launch
- Avoid: freemium, customers, sign up, ARR

### GitHub README

- May be technical and detailed if each claim maps to docs
- Keep "What Is Not Claimed" section accurate
- Screenshots ≠ production proof

### Interview (spoken)

- Qualifiers allowed: "locally", "portfolio", "rule-based", "optional mocked-first"
- Must verbally deny Gmail/auto-apply if asked
- Do not cite CI green without checking Actions same week

### Job application

- Tie claims to role requirements (analytics, governance, testing)
- Conservative commercial language
- Prefer evidence doc paths over superlatives

### General

- Default to portfolio + manual + advisory framing

---

## Rule Maintenance

When README or Phase 4A+ evidence updates:

1. Revise this file in same sprint
2. Update golden cases if verdicts change
3. Re-run golden test module in 5B+

Do not auto-sync from LLM — human/sprint-reviewed only.

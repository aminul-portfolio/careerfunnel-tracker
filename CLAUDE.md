# CareerFunnel Tracker — Claude Code Context

## Project identity
Django job-search analytics and decision-support platform.
Single user: Aminul Islam, Data Analyst job seeker, London, UK.
Local SQLite application. No live deployment. No production users.

## Current state
Latest sprint: Sprint 32E complete
Latest tag: sprint-32e-evidence-and-final-closure-complete
Test count: 351
Branch: main

## Locked CV filename
LOCKED_CV = "Aminul_Islam_Data_Analyst_CV"
This is the only valid CV filename. Never suggest or generate
Finance_DA_CV_v1, BI_Reporting_CV_v1, DA_CV_v1, or DA_CV_v2
as active CV names. These exist only as historical test fixtures.

## CV Tailoring Advisor — actual class name
The implemented dataclass is CVTailoringAdvisorResult in
apps/ai_agents/services.py line 687.
Fields: recommended_cv, cv_angle, role_family, strongest_experience,
strongest_projects, matched_skills, partial_matches, missing_skills,
risks, deal_breakers, cover_letter_angle, interview_evidence_points,
claim_safety_notes, approval_reminder.
There is no class named CVTailoringRecommendation. Do not create one.

## Evidence bank
apps/ai_agents/evidence_bank.py does not yet exist.
It will be created in Sprint 33. Do not create it before Sprint 33
explicitly instructs it.

## What does not exist and must not be claimed
- GmailCredential model: does not exist
- Gmail API OAuth: not implemented
- Calendar integration: not implemented
- External AI/API calls: not implemented (OpenAI wrapper is mocked-first)
- Auto-apply: not implemented
- Background polling: not implemented

## Claim safety rules
- Never generate full CV text, professional_summary, experience_bullets,
  or cover_letter_body output from any service function
- Never suggest importing openai, anthropic, or any external AI library
  without explicit Sprint 33 instruction
- Never modify migration files without being explicitly asked
- Never remove existing tests

## Architecture rules
- Business logic lives in services.py files, not views
- All service return types use @dataclass(frozen=True)
- Views are thin — no business logic in views
- All queries filter by user=user
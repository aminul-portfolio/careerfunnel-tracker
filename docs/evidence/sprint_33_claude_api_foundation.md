# Sprint 33 — Claude API Foundation Evidence

**Date:** 2026-05-23
**Tag:** sprint-33-claude-api-foundation-complete
**Branch:** main

## What was built

- apps/ai_agents/claude_provider.py (new ~90 lines)
  make_claude_provider(api_key) factory returns
  Callable[[dict], dict] injected into
  build_openai_fit_scoring_with_fallback()
  Model: claude-haiku-4-5-20251001 · max_tokens: 1024
  Raises ValueError on malformed response for auto-fallback

## Files changed

- apps/ai_agents/claude_provider.py (new)
- apps/ai_agents/services.py (provider name → Claude)
- apps/ai_agents/views.py (callable injection, 4 lines)
- apps/ai_agents/tests.py (TestClaudeProvider, 7 tests)
- config/settings/base.py (ANTHROPIC_API_KEY config)
- requirements.txt (anthropic>=0.40.0)

## Test count
Previous baseline: 351
After Sprint 33: 358 (7 new TestClaudeProvider tests)

## Validation
- ruff check . → All checks passed
- python manage.py test → 358 tests passing
- Fallback works without ANTHROPIC_API_KEY
- manual_review_required=True on all result paths
- No real API calls in tests (unittest.mock only)
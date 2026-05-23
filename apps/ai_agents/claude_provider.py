from __future__ import annotations

import json
from collections.abc import Callable

import anthropic

CLAUDE_MODEL = "claude-haiku-4-5-20251001"
CLAUDE_MAX_TOKENS = 1024

_SYSTEM_PROMPT = """You are a job-fit scoring assistant for a junior Data Analyst job search.

Analyse the job posting provided and return ONLY a valid JSON object.
No prose, no explanation, no markdown code fences — just the raw JSON.

Required fields (all must be present):
- ai_fit_score: integer 0-100
- ai_fit_label: string (e.g. "Strong Match", "Moderate Match", "Weak Match", "Skip")
- confidence: string — must be exactly one of: low, medium, high
- evidence_matches: list of strings — skills or experience that match this role
- gaps: list of strings — skills or requirements that are gaps
- deal_breakers: list of strings — hard blockers (empty list if none)
- reasoning_summary: non-empty string — brief explanation of the score
- recommended_cv_angle: non-empty string — positioning angle for the CV
- recommended_projects: list of strings — portfolio projects to highlight
- claim_safety_notes: list of strings — at least one safety reminder

Safety rules that must be reflected in your output:
- Output is advisory only.
- Manual review is required before saving or using recommendations externally.
- Do not claim auto-save, auto-apply, or application submission.
- Do not generate a final CV or finalise a cover letter.
- Do not invent skills, employers, dates, metrics, or experience.
- Do not include Gmail, Calendar, inbox, or contact data.
"""


def make_claude_provider(api_key: str) -> Callable[[dict], dict]:
    """Return a callable that scores a job posting via the Claude API.

    The returned callable accepts the prompt dict from
    build_openai_fit_scoring_prompt() and returns the 10-field dict
    expected by parse_ai_fit_scoring_payload().  Raises ValueError on any
    malformed response so the fallback in services.py catches it cleanly.
    """
    client = anthropic.Anthropic(api_key=api_key)

    def _call_claude(prompt: dict) -> dict:
        user_message = _build_user_message(prompt)
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        return _parse_claude_response(response)

    return _call_claude


def _build_user_message(prompt: dict) -> str:
    matched = ", ".join(prompt.get("matched_skills", [])) or "none identified"
    risks = "; ".join(prompt.get("risks", [])) or "none"
    deal_breakers = ", ".join(prompt.get("deal_breakers", [])) or "none"
    schema_fields = prompt.get("required_output_schema", {}).get("fields", [])

    lines = [
        f"Company: {prompt.get('company_name', '')}",
        f"Job title: {prompt.get('job_title', '')}",
        f"Location: {prompt.get('location', '')}",
        "",
        "Job description:",
        prompt.get("job_description", ""),
        "",
        f"Rule-based fit score: {prompt.get('rule_based_fit_score', 'N/A')}",
        f"Rule-based recommendation: {prompt.get('rule_based_recommendation', 'N/A')}",
        f"Rule-based matched skills: {matched}",
        f"Rule-based risks: {risks}",
        f"Rule-based deal breakers: {deal_breakers}",
        "",
        f"Return ONLY a JSON object with these exact fields: {schema_fields}",
    ]
    return "\n".join(lines)


def _parse_claude_response(response: anthropic.types.Message) -> dict:
    if not response.content:
        raise ValueError("Claude returned an empty response.")
    block = response.content[0]
    if block.type != "text":
        raise ValueError(f"Expected a text response block, got: {block.type}")
    text = block.text.strip()
    # Strip accidental markdown fences Claude occasionally adds
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Claude response is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"Claude response must be a JSON object, got: {type(parsed).__name__}")
    return parsed
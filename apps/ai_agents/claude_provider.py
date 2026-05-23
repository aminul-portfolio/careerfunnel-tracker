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


_CV_TAILORING_SYSTEM_PROMPT = """You are a CV tailoring semantic assistant for a junior \
Data Analyst job search.

Analyse the job posting and evidence catalog provided. Return ONLY a valid JSON object.
No prose, no explanation, no markdown code fences — just the raw JSON.

Required fields (all must be present):
- semantic_matched_skills: list of strings — strong evidence-backed skill matches only
- semantic_partial_matches: list of strings — partial evidence skills
- semantic_gaps: list of strings — gaps and learning-target skills (not claimable)
- semantic_project_highlights: list of strings — canonical portfolio project names only
- semantic_experience_angles: list of strings — short experience positioning angles
- semantic_risks: list of strings — advisory risks (seniority, overclaim, tool gaps)
- semantic_cover_letter_themes: list of strings — cover letter themes only (not body text)
- semantic_interview_points: list of strings — interview talking points
- reasoning_summary: non-empty string — brief advisory summary (not copy-ready prose)
- claim_safety_notes: list of strings — at least one safety reminder
- manual_review_required: boolean — must be true

Forbidden fields (must NOT appear in output):
full_cv_text, professional_summary, experience_bullets, cover_letter_body,
cover_letter_text, cv_body, application_letter, recruiter_message, linkedin_post,
recommended_cv

Safety rules:
- Output is advisory only; manual review is required before external use.
- Do not generate a final CV, professional summary, experience bullets, or cover letter body.
- Do not generate recruiter messages or LinkedIn posts.
- Do not claim auto-apply, auto-save, or application submission.
- Do not invent skills, employers, dates, metrics, or experience.
- Do not include Gmail, Calendar, inbox, OAuth, or contact data.
- Gap-tier skills (e.g. dbt, Snowflake, Airflow) must appear in semantic_gaps only, \
never as proven matches.
"""


def make_claude_cv_tailoring_provider(api_key: str) -> Callable[[dict], dict]:
    """Return a callable for CV tailoring semantic JSON via the Claude API.

    Accepts a prompt dict from services (future build_cv_tailoring_semantic_prompt).
    Returns a dict for parse_cv_tailoring_semantic_payload(). Raises ValueError on
    malformed responses.
    """
    client = anthropic.Anthropic(api_key=api_key)

    def _call_claude_cv_tailoring(prompt: dict) -> dict:
        user_message = _build_cv_tailoring_user_message(prompt)
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            system=_CV_TAILORING_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        return _parse_claude_response(response)

    return _call_claude_cv_tailoring


def _build_cv_tailoring_user_message(prompt: dict) -> str:
    rule_based = prompt.get("rule_based", {})
    catalog = prompt.get("evidence_catalog", {})
    schema_fields = prompt.get("required_output_schema", {}).get("fields", [])
    forbidden_fields = prompt.get("required_output_schema", {}).get("forbidden_fields", [])

    def _join_list(items: object) -> str:
        if isinstance(items, list) and items:
            return ", ".join(str(item) for item in items)
        return "none"

    lines = [
        f"Company: {prompt.get('company_name', '')}",
        f"Job title: {prompt.get('job_title', '')}",
        f"Location: {prompt.get('location', '')}",
        "",
        "Job description:",
        prompt.get("job_description", ""),
        "",
        "CV evidence notes:",
        prompt.get("cv_evidence", "") or "none provided",
        "",
        f"Rule-based cv_angle: {rule_based.get('cv_angle', 'N/A')}",
        f"Rule-based role_family: {rule_based.get('role_family', 'N/A')}",
        f"Rule-based matched skills: {_join_list(rule_based.get('matched_skills'))}",
        f"Rule-based partial matches: {_join_list(rule_based.get('partial_matches'))}",
        f"Rule-based missing skills: {_join_list(rule_based.get('missing_skills'))}",
        f"Rule-based projects: {_join_list(rule_based.get('strongest_projects'))}",
        f"Rule-based risks: {_join_list(rule_based.get('risks'))}",
        f"Rule-based deal breakers: {_join_list(rule_based.get('deal_breakers'))}",
        "",
        "Evidence catalog (claim-safe subset):",
        f"Strong skills: {_join_list(catalog.get('strong_skills'))}",
        f"Partial skills: {_join_list(catalog.get('partial_skills'))}",
        f"Gap/learning skills (not claimable): {_join_list(catalog.get('gap_learning_skills'))}",
        f"Projects: {_join_list(catalog.get('projects'))}",
        "",
        f"Return ONLY a JSON object with these exact fields: {schema_fields}",
        f"Do NOT include these forbidden fields: {forbidden_fields}",
        "Set manual_review_required to true.",
    ]
    safety_rules = prompt.get("safety_rules", [])
    if safety_rules:
        lines.append("")
        lines.append("Safety rules:")
        lines.extend(f"- {rule}" for rule in safety_rules)
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
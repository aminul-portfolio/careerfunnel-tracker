"""Deterministic job-description to AI capability matching (Sprint 55 Phase 1).

Rule-based keyword matching only - no external AI calls, scraping, or persistence.
"""

from __future__ import annotations

from dataclasses import dataclass

from .ai_capability_framework import get_ai_capability_framework

MATCH_LABEL_BANDS: tuple[tuple[int, str], ...] = (
    (75, "High AI-workflow alignment"),
    (50, "Strong AI signal"),
    (25, "Moderate AI signal"),
    (0, "Limited AI signal"),
)

MATCHING_CLAIM_SAFETY_NOTES: tuple[str, ...] = (
    "Rule-based keyword matching for manual review only.",
    "Not predictive hiring AI, automated shortlisting, or external AI analysis.",
    "Keyword hits do not prove capability ownership; verify evidence manually.",
    "No external AI provider is called by this matching service.",
)

CAPABILITY_KEYWORD_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "prompt-engineering-ai-tool-proficiency",
        (
            "prompt",
            "prompting",
            "generative ai",
            "copilot",
            "chatgpt",
            "gemini",
            "large language model",
            "llm",
        ),
    ),
    (
        "building-operating-ai-agents",
        (
            "ai agent",
            "agent workflow",
            "autonomous workflow",
            "orchestration",
            "tool use",
            "multi-step agent",
        ),
    ),
    (
        "critical-evaluation-ai-output",
        (
            "hallucination",
            "validate ai",
            "fact check",
            "critical evaluation",
            "verify ai output",
            "source checking",
        ),
    ),
    (
        "ethical-ai-decision-making",
        (
            "ethics",
            "responsible ai",
            "bias",
            "governance",
            "compliance",
            "ai risk",
            "fairness",
        ),
    ),
    (
        "workflow-project-management-ai-tools",
        (
            "workflow",
            "automation",
            "process improvement",
            "operations",
            "productivity tools",
            "project management ai",
            "notion ai",
        ),
    ),
    (
        "collaborative-strategy-ideation-tools",
        (
            "collaboration",
            "workshop",
            "ideation",
            "miro",
            "whiteboard",
            "brainstorm",
            "journey mapping",
        ),
    ),
    (
        "ai-product-design-packaging-tools",
        (
            "packaging",
            "mockup",
            "design ai",
            "canva",
            "visual storytelling",
            "product design ai",
        ),
    ),
    (
        "ai-video-media-generation-tools",
        (
            "video generation",
            "media generation",
            "b-roll",
            "explainer clip",
            "ai video",
            "voiceover ai",
        ),
    ),
    (
        "ai-presentation-report-generation-tools",
        (
            "presentation",
            "reporting",
            "deck",
            "stakeholder report",
            "executive summary",
            "slide outline",
            "board pack",
        ),
    ),
)


@dataclass(frozen=True)
class MatchedAICapability:
    slug: str
    title: str
    matched_terms: tuple[str, ...]


@dataclass(frozen=True)
class MissingAICapability:
    slug: str
    title: str
    signal_note: str


@dataclass(frozen=True)
class JobAICapabilityMatchResult:
    matched_capabilities: tuple[MatchedAICapability, ...]
    missing_capabilities: tuple[MissingAICapability, ...]
    detected_terms: tuple[str, ...]
    match_score: int
    match_label: str
    explanation_points: tuple[str, ...]
    claim_safety_notes: tuple[str, ...]


def assign_match_label(score: int) -> str:
    bounded = max(0, min(100, score))
    for threshold, label in MATCH_LABEL_BANDS:
        if bounded >= threshold:
            return label
    return MATCH_LABEL_BANDS[-1][1]


def _normalise_job_text(job_description: str) -> str:
    return " ".join(job_description.lower().split())


def _find_matched_terms(text: str, keywords: tuple[str, ...]) -> tuple[str, ...]:
    hits = [keyword for keyword in keywords if keyword in text]
    return tuple(sorted(set(hits)))


def _build_capability_lookup() -> dict[str, str]:
    return {
        capability.slug: capability.title
        for capability in get_ai_capability_framework()
    }


def match_job_description_to_ai_capabilities(
    job_description: str,
) -> JobAICapabilityMatchResult:
    """Match job description text to Sprint 53 AI capability categories by keyword groups."""
    text = _normalise_job_text(job_description or "")
    titles = _build_capability_lookup()
    framework_slugs = set(titles)

    configured_slugs = {slug for slug, _ in CAPABILITY_KEYWORD_GROUPS}
    if configured_slugs != framework_slugs:
        missing_config = sorted(framework_slugs - configured_slugs)
        extra_config = sorted(configured_slugs - framework_slugs)
        raise ValueError(
            "Keyword groups must cover all framework slugs exactly. "
            f"missing={missing_config}, extra={extra_config}"
        )

    matched: list[MatchedAICapability] = []
    missing: list[MissingAICapability] = []
    all_detected: set[str] = set()

    for slug, keywords in CAPABILITY_KEYWORD_GROUPS:
        terms = _find_matched_terms(text, keywords)
        if terms:
            all_detected.update(terms)
            matched.append(
                MatchedAICapability(
                    slug=slug,
                    title=titles[slug],
                    matched_terms=terms,
                )
            )
        else:
            missing.append(
                MissingAICapability(
                    slug=slug,
                    title=titles[slug],
                    signal_note="No keyword signal detected in job description.",
                )
            )

    total = len(CAPABILITY_KEYWORD_GROUPS)
    match_score = round((len(matched) / total) * 100) if total else 0
    match_label = assign_match_label(match_score)
    explanation_points = _build_explanation_points(
        match_score=match_score,
        match_label=match_label,
        matched_count=len(matched),
        missing_count=len(missing),
        detected_terms=tuple(sorted(all_detected)),
    )

    return JobAICapabilityMatchResult(
        matched_capabilities=tuple(matched),
        missing_capabilities=tuple(missing),
        detected_terms=tuple(sorted(all_detected)),
        match_score=match_score,
        match_label=match_label,
        explanation_points=explanation_points,
        claim_safety_notes=MATCHING_CLAIM_SAFETY_NOTES,
    )


def _build_explanation_points(
    *,
    match_score: int,
    match_label: str,
    matched_count: int,
    missing_count: int,
    detected_terms: tuple[str, ...],
) -> tuple[str, ...]:
    points = [
        (
            f"Match score {match_score}/100 maps to label '{match_label}' "
            f"from {matched_count} matched capability categories."
        ),
        (
            f"{missing_count} capability categories had no keyword signal "
            "and are listed as missing or weak for manual review."
        ),
    ]
    if detected_terms:
        points.append(
            "Detected terms: "
            + ", ".join(detected_terms)
            + "."
        )
    else:
        points.append(
            "No AI capability keywords detected; treat as limited AI signal only."
        )
    points.append(
        "Matching uses deterministic keyword groups mapped to Sprint 53 framework slugs."
    )
    return tuple(points)

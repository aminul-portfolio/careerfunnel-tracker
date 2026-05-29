"""Rule-based AI readiness scoring on top of the Sprint 53 capability framework (Sprint 54 Phase 1).

Advisory scoring only - no external AI calls, automation, or persistence.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from apps.ai_agents.evidence_bank import EvidenceTier

from .ai_capability_framework import (
    AICapabilityCategory,
    CapabilityLevel,
    get_ai_capability_framework,
)

EvidenceStrength = Literal["none", "gap_learning", "partial", "strong"]

APPROVED_EVIDENCE_STRENGTHS: frozenset[str] = frozenset({
    "none",
    "gap_learning",
    "partial",
    "strong",
})

EVIDENCE_STRENGTH_POINTS: dict[EvidenceStrength, int] = {
    "none": 0,
    "gap_learning": 1,
    "partial": 2,
    "strong": 3,
}

MAX_STRONG_EVIDENCE_POINTS = EVIDENCE_STRENGTH_POINTS["strong"]

LEVEL_WEIGHTS: dict[CapabilityLevel, int] = {
    "foundation": 1,
    "applied": 2,
    "agent_portfolio_ready": 3,
}


def _capability_max_points(capability: AICapabilityCategory) -> int:
    return MAX_STRONG_EVIDENCE_POINTS * LEVEL_WEIGHTS[capability.level]

READINESS_LABEL_BANDS: tuple[tuple[int, str], ...] = (
    (85, "Agent / portfolio-ready"),
    (70, "Strong applied readiness"),
    (50, "Applied readiness"),
    (25, "Foundation in progress"),
    (0, "Foundation needed"),
)

READINESS_SCORING_CLAIM_SAFETY_NOTES: tuple[str, ...] = (
    "Rule-based advisory score for manual self-review only.",
    "Not predictive hiring AI, job matching, or automated recommendations.",
    "Evidence strength must be confirmed manually before portfolio or interview claims.",
    "No external AI provider is called by this scoring service.",
)


@dataclass(frozen=True)
class CapabilityReadinessLine:
    slug: str
    title: str
    framework_level: CapabilityLevel
    evidence_strength: EvidenceStrength
    points_earned: int
    points_possible: int
    explanation: str


@dataclass(frozen=True)
class AIReadinessScoringResult:
    readiness_score: int
    readiness_label: str
    capabilities_total: int
    capabilities_with_evidence: int
    foundation_evidence_count: int
    applied_evidence_count: int
    agent_portfolio_evidence_count: int
    capability_lines: tuple[CapabilityReadinessLine, ...]
    explanation_points: tuple[str, ...]
    claim_safety_notes: tuple[str, ...]


def _validate_evidence_strength(strength: str) -> EvidenceStrength:
    if strength not in APPROVED_EVIDENCE_STRENGTHS:
        raise ValueError(f"Unsupported evidence strength: {strength}")
    return strength  # type: ignore[return-value]


def evidence_strength_from_tier(tier: EvidenceTier | None) -> EvidenceStrength:
    """Map existing evidence-bank tiers to AI readiness evidence strength."""
    if tier is None:
        return "none"
    if tier == "strong":
        return "strong"
    if tier == "partial":
        return "partial"
    return "gap_learning"


def assign_readiness_label(score: int) -> str:
    bounded = max(0, min(100, score))
    for threshold, label in READINESS_LABEL_BANDS:
        if bounded >= threshold:
            return label
    return READINESS_LABEL_BANDS[-1][1]


def _capability_points(capability: AICapabilityCategory, strength: EvidenceStrength) -> int:
    return (
        EVIDENCE_STRENGTH_POINTS[strength]
        * LEVEL_WEIGHTS[capability.level]
    )


def _line_explanation(capability: AICapabilityCategory, strength: EvidenceStrength) -> str:
    if strength == "none":
        return (
            f"No documented evidence yet for {capability.title} "
            f"({capability.level} level in the framework)."
        )
    if strength == "gap_learning":
        return (
            f"Learning focus recorded for {capability.title}; "
            "treat as stretch awareness, not a finished portfolio claim."
        )
    if strength == "partial":
        return (
            f"Partial evidence recorded for {capability.title}; "
            "suitable for manual review and further documentation."
        )
    return (
        f"Strong evidence recorded for {capability.title}; "
        "suitable for portfolio or interview discussion after manual verification."
    )


def _count_with_evidence(strength: EvidenceStrength) -> bool:
    return strength != "none"


def calculate_ai_readiness_score(
    evidence_by_slug: Mapping[str, str],
) -> AIReadinessScoringResult:
    """Compute a deterministic readiness score from manual capability evidence inputs."""
    framework = get_ai_capability_framework()
    framework_slugs = {capability.slug for capability in framework}

    unknown_slugs = sorted(set(evidence_by_slug) - framework_slugs)
    if unknown_slugs:
        raise ValueError(f"Unknown capability slugs: {', '.join(unknown_slugs)}")

    normalised: dict[str, EvidenceStrength] = {
        slug: _validate_evidence_strength(strength)
        for slug, strength in evidence_by_slug.items()
    }

    lines: list[CapabilityReadinessLine] = []
    total_earned = 0
    total_possible = 0
    foundation_count = 0
    applied_count = 0
    agent_count = 0
    with_evidence = 0

    for capability in framework:
        strength = normalised.get(capability.slug, "none")
        earned = _capability_points(capability, strength)
        possible = _capability_max_points(capability)
        total_earned += earned
        total_possible += possible

        if _count_with_evidence(strength):
            with_evidence += 1
            if capability.level == "foundation":
                foundation_count += 1
            elif capability.level == "applied":
                applied_count += 1
            else:
                agent_count += 1

        lines.append(
            CapabilityReadinessLine(
                slug=capability.slug,
                title=capability.title,
                framework_level=capability.level,
                evidence_strength=strength,
                points_earned=earned,
                points_possible=possible,
                explanation=_line_explanation(capability, strength),
            )
        )

    if total_possible == 0:
        readiness_score = 0
    else:
        readiness_score = round((total_earned / total_possible) * 100)

    readiness_label = assign_readiness_label(readiness_score)
    explanation_points = _build_explanation_points(
        readiness_score=readiness_score,
        readiness_label=readiness_label,
        with_evidence=with_evidence,
        capabilities_total=len(framework),
        foundation_count=foundation_count,
        applied_count=applied_count,
        agent_count=agent_count,
    )

    return AIReadinessScoringResult(
        readiness_score=readiness_score,
        readiness_label=readiness_label,
        capabilities_total=len(framework),
        capabilities_with_evidence=with_evidence,
        foundation_evidence_count=foundation_count,
        applied_evidence_count=applied_count,
        agent_portfolio_evidence_count=agent_count,
        capability_lines=tuple(lines),
        explanation_points=explanation_points,
        claim_safety_notes=READINESS_SCORING_CLAIM_SAFETY_NOTES,
    )


def _build_explanation_points(
    *,
    readiness_score: int,
    readiness_label: str,
    with_evidence: int,
    capabilities_total: int,
    foundation_count: int,
    applied_count: int,
    agent_count: int,
) -> tuple[str, ...]:
    points = [
        (
            f"Readiness score {readiness_score}/100 maps to label "
            f"'{readiness_label}' using weighted capability coverage."
        ),
        (
            f"{with_evidence} of {capabilities_total} framework capabilities "
            "have non-none evidence strength recorded."
        ),
        (
            f"Coverage by framework level: foundation={foundation_count}, "
            f"applied={applied_count}, agent_portfolio_ready={agent_count}."
        ),
        (
            "Higher framework levels and stronger evidence tiers earn more points; "
            "gap_learning counts as awareness only."
        ),
    ]
    if with_evidence == 0:
        points.append(
            "Add manual evidence notes per capability before relying on this score."
        )
    return tuple(points)


def build_empty_ai_readiness_score() -> AIReadinessScoringResult:
    """Baseline score when no capability evidence has been recorded."""
    return calculate_ai_readiness_score({})


def build_careerfunnel_portfolio_evidence_baseline() -> dict[str, EvidenceStrength]:
    """Static, claim-safe evidence strengths inferred from this project's documented scope."""
    return {
        "prompt-engineering-ai-tool-proficiency": "partial",
        "building-operating-ai-agents": "partial",
        "critical-evaluation-ai-output": "partial",
        "ethical-ai-decision-making": "partial",
        "workflow-project-management-ai-tools": "strong",
        "collaborative-strategy-ideation-tools": "gap_learning",
        "ai-product-design-packaging-tools": "partial",
        "ai-video-media-generation-tools": "none",
        "ai-presentation-report-generation-tools": "partial",
    }


def build_portfolio_baseline_ai_readiness_score() -> AIReadinessScoringResult:
    """Readiness score using the CareerFunnel Tracker portfolio evidence baseline."""
    return calculate_ai_readiness_score(build_careerfunnel_portfolio_evidence_baseline())

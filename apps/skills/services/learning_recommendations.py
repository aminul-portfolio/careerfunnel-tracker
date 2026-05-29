"""Deterministic learning and improvement recommendations (Sprint 56 Phase 1).

Combines Sprint 54 readiness and Sprint 55 job-match outputs. Advisory only - no external AI calls.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .ai_readiness_scoring import (
    AIReadinessScoringResult,
    CapabilityReadinessLine,
    build_portfolio_baseline_ai_readiness_score,
)
from .job_ai_capability_matching import (
    JobAICapabilityMatchResult,
    match_job_description_to_ai_capabilities,
)

RecommendationCategory = Literal[
    "Learning",
    "Project improvement",
    "CV evidence",
    "Interview preparation",
    "Manual review",
]

RecommendationPriority = Literal["High", "Medium", "Low"]

APPROVED_RECOMMENDATION_CATEGORIES: frozenset[str] = frozenset({
    "Learning",
    "Project improvement",
    "CV evidence",
    "Interview preparation",
    "Manual review",
})

APPROVED_RECOMMENDATION_PRIORITIES: frozenset[str] = frozenset({
    "High",
    "Medium",
    "Low",
})

PRIORITY_RANK: dict[str, int] = {
    "High": 3,
    "Medium": 2,
    "Low": 1,
}

DEFAULT_SAMPLE_JOB_DESCRIPTION = (
    "Business analyst role using generative AI, prompt engineering, workflow automation, "
    "responsible AI governance, stakeholder reporting, and AI-assisted presentation decks."
)

LEARNING_RECOMMENDATION_CLAIM_SAFETY_NOTES: tuple[str, ...] = (
    "Rule-based advisory suggestions for manual self-review only.",
    "Not predictive hiring AI, automated career advice, or external AI output.",
    "Verify every recommendation against your own evidence before acting.",
    "No external AI provider is called by this recommendation service.",
)


@dataclass(frozen=True)
class LearningRecommendation:
    category: RecommendationCategory
    title: str
    priority: RecommendationPriority
    reason: str
    suggested_action: str
    linked_capability_slug: str
    evidence_target: str


@dataclass(frozen=True)
class ReadinessSummary:
    readiness_score: int
    readiness_label: str
    capabilities_with_evidence: int
    capabilities_total: int


@dataclass(frozen=True)
class JobMatchSummary:
    match_score: int
    match_label: str
    matched_count: int
    missing_count: int


@dataclass(frozen=True)
class LearningRecommendationsResult:
    overall_priority: RecommendationPriority
    next_best_action: str
    recommendations: tuple[LearningRecommendation, ...]
    readiness_summary: ReadinessSummary
    job_match_summary: JobMatchSummary
    claim_safety_notes: tuple[str, ...]


def _readiness_summary(readiness: AIReadinessScoringResult) -> ReadinessSummary:
    return ReadinessSummary(
        readiness_score=readiness.readiness_score,
        readiness_label=readiness.readiness_label,
        capabilities_with_evidence=readiness.capabilities_with_evidence,
        capabilities_total=readiness.capabilities_total,
    )


def _job_match_summary(job_match: JobAICapabilityMatchResult) -> JobMatchSummary:
    return JobMatchSummary(
        match_score=job_match.match_score,
        match_label=job_match.match_label,
        matched_count=len(job_match.matched_capabilities),
        missing_count=len(job_match.missing_capabilities),
    )


def _evidence_by_slug(
    readiness: AIReadinessScoringResult,
) -> dict[str, CapabilityReadinessLine]:
    return {line.slug: line for line in readiness.capability_lines}


def _is_weak_evidence(strength: str) -> bool:
    return strength in {"none", "gap_learning"}


def _recommendation(
    *,
    category: RecommendationCategory,
    title: str,
    priority: RecommendationPriority,
    reason: str,
    suggested_action: str,
    linked_capability_slug: str,
    evidence_target: str,
) -> LearningRecommendation:
    return LearningRecommendation(
        category=category,
        title=title,
        priority=priority,
        reason=reason,
        suggested_action=suggested_action,
        linked_capability_slug=linked_capability_slug,
        evidence_target=evidence_target,
    )


def _pick_overall_priority(
    recommendations: tuple[LearningRecommendation, ...],
) -> RecommendationPriority:
    if not recommendations:
        return "Low"
    highest = max(recommendations, key=lambda item: PRIORITY_RANK[item.priority])
    return highest.priority


def _pick_next_best_action(
    recommendations: tuple[LearningRecommendation, ...],
) -> str:
    for priority in ("High", "Medium", "Low"):
        for recommendation in recommendations:
            if recommendation.priority == priority:
                return recommendation.suggested_action
    return "Review readiness and job-match outputs manually before taking action."


def build_learning_recommendations(
    readiness: AIReadinessScoringResult,
    job_match: JobAICapabilityMatchResult,
) -> LearningRecommendationsResult:
    """Build deterministic learning recommendations from readiness and job-match results."""
    evidence_lines = _evidence_by_slug(readiness)
    recommendations: list[LearningRecommendation] = []

    if readiness.readiness_score < 50:
        recommendations.append(
            _recommendation(
                category="Learning",
                title="Strengthen foundation AI capability evidence",
                priority="High",
                reason=(
                    f"Readiness score is {readiness.readiness_score}/100 "
                    f"({readiness.readiness_label})."
                ),
                suggested_action=(
                    "Pick one foundation capability and document a manual learning note "
                    "with a verified example before citing it externally."
                ),
                linked_capability_slug="prompt-engineering-ai-tool-proficiency",
                evidence_target="Foundation capability evidence log",
            )
        )
        for line in readiness.capability_lines:
            if line.framework_level == "foundation" and _is_weak_evidence(line.evidence_strength):
                recommendations.append(
                    _recommendation(
                        category="Learning",
                        title=f"Build foundation evidence for {line.title}",
                        priority="High",
                        reason=(
                            f"Foundation capability has {line.evidence_strength} evidence strength."
                        ),
                        suggested_action=(
                            f"Complete a short practice exercise for {line.title} "
                            "and save a before-and-after note for manual review."
                        ),
                        linked_capability_slug=line.slug,
                        evidence_target="Foundation learning note",
                    )
                )

    for missing in job_match.missing_capabilities:
        recommendations.append(
            _recommendation(
                category="Learning",
                title=f"Review job signal gap: {missing.title}",
                priority="Medium",
                reason=missing.signal_note,
                suggested_action=(
                    f"Read the Sprint 53 framework entry for {missing.title} "
                    "and decide whether to study or skip for this role family."
                ),
                linked_capability_slug=missing.slug,
                evidence_target="Capability awareness note",
            )
        )

    matched_slugs = {cap.slug for cap in job_match.matched_capabilities}
    for slug in matched_slugs:
        line = evidence_lines.get(slug)
        if line is None or not _is_weak_evidence(line.evidence_strength):
            continue
        matched = next(cap for cap in job_match.matched_capabilities if cap.slug == slug)
        category: RecommendationCategory = (
            "Project improvement" if line.evidence_strength == "none" else "CV evidence"
        )
        recommendations.append(
            _recommendation(
                category=category,
                title=f"Close evidence gap for job-matched capability: {line.title}",
                priority="High",
                reason=(
                    f"Job description matched {', '.join(matched.matched_terms)} "
                    f"but readiness evidence is {line.evidence_strength}."
                ),
                suggested_action=(
                    f"Add a portfolio or project artifact demonstrating {line.title} "
                    "and verify claims manually before interviews."
                ),
                linked_capability_slug=slug,
                evidence_target="Portfolio or project artifact",
            )
        )

    if readiness.readiness_score >= 70 and job_match.match_score >= 50:
        recommendations.append(
            _recommendation(
                category="Interview preparation",
                title="Prepare interview stories for matched AI capabilities",
                priority="Medium",
                reason=(
                    f"Readiness is {readiness.readiness_label} and job match is "
                    f"{job_match.match_label}."
                ),
                suggested_action=(
                    "Draft one STAR-style story per matched capability and "
                    "source-check every metric before practice."
                ),
                linked_capability_slug="",
                evidence_target="Interview story outline",
            )
        )

    recommendations.append(
        _recommendation(
            category="Manual review",
            title="Confirm recommendations manually before acting",
            priority="Low",
            reason="All outputs are advisory and require human verification.",
            suggested_action=(
                "Review each suggestion against your portfolio evidence and "
                "reject any item you cannot support truthfully."
            ),
            linked_capability_slug="",
            evidence_target="Manual review checklist",
        )
    )

    deduped = _dedupe_recommendations(recommendations)
    result_recommendations = tuple(deduped)

    return LearningRecommendationsResult(
        overall_priority=_pick_overall_priority(result_recommendations),
        next_best_action=_pick_next_best_action(result_recommendations),
        recommendations=result_recommendations,
        readiness_summary=_readiness_summary(readiness),
        job_match_summary=_job_match_summary(job_match),
        claim_safety_notes=LEARNING_RECOMMENDATION_CLAIM_SAFETY_NOTES,
    )


def _dedupe_recommendations(
    recommendations: list[LearningRecommendation],
) -> list[LearningRecommendation]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[LearningRecommendation] = []
    for recommendation in recommendations:
        key = (
            recommendation.category,
            recommendation.title,
            recommendation.linked_capability_slug,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(recommendation)
    return deduped


def build_portfolio_baseline_learning_recommendations() -> LearningRecommendationsResult:
    """Recommendations using portfolio readiness baseline and sample job description."""
    readiness = build_portfolio_baseline_ai_readiness_score()
    job_match = match_job_description_to_ai_capabilities(DEFAULT_SAMPLE_JOB_DESCRIPTION)
    return build_learning_recommendations(readiness, job_match)

"""Deterministic Career Readiness Dashboard aggregation (Sprint 57 Phase 1).

Combines Sprint 53-56 outputs into dashboard-ready data. Advisory only - no external AI calls.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .ai_capability_framework import get_ai_capability_framework
from .ai_readiness_scoring import (
    AIReadinessScoringResult,
    build_portfolio_baseline_ai_readiness_score,
)
from .job_ai_capability_matching import (
    JobAICapabilityMatchResult,
    match_job_description_to_ai_capabilities,
)
from .learning_recommendations import (
    DEFAULT_SAMPLE_JOB_DESCRIPTION,
    LearningRecommendationsResult,
    build_learning_recommendations,
)

KpiStatus = Literal["Review", "Developing", "Strong", "Manual check"]

APPROVED_KPI_STATUSES: frozenset[str] = frozenset({
    "Review",
    "Developing",
    "Strong",
    "Manual check",
})

DASHBOARD_CLAIM_SAFETY_NOTES: tuple[str, ...] = (
    "Rule-based dashboard summary for manual self-review only.",
    "Not predictive hiring AI, automated career advice, or external AI output.",
    "KPI values combine existing Sprint 53-56 services; verify evidence manually.",
    "No external AI provider is called by this dashboard service.",
)


@dataclass(frozen=True)
class DashboardKpiCard:
    label: str
    value: str
    supporting_text: str
    status: KpiStatus


@dataclass(frozen=True)
class DashboardSection:
    key: str
    title: str
    summary: str


@dataclass(frozen=True)
class CareerReadinessDashboardResult:
    readiness_score: int
    readiness_label: str
    job_match_score: int
    job_match_label: str
    overall_priority: str
    next_best_action: str
    capability_count: int
    matched_capability_count: int
    missing_capability_count: int
    recommendation_count: int
    high_priority_recommendation_count: int
    kpi_cards: tuple[DashboardKpiCard, ...]
    summary_points: tuple[str, ...]
    dashboard_sections: tuple[DashboardSection, ...]
    claim_safety_notes: tuple[str, ...]


def _readiness_kpi_status(score: int) -> KpiStatus:
    if score < 50:
        return "Review"
    if score >= 70:
        return "Strong"
    return "Developing"


def _job_match_kpi_status(score: int) -> KpiStatus:
    if score < 25:
        return "Review"
    if score >= 50:
        return "Strong"
    return "Developing"


def _recommendation_kpi_status(high_count: int) -> KpiStatus:
    if high_count > 0:
        return "Review"
    return "Manual check"


def _build_kpi_cards(
    readiness: AIReadinessScoringResult,
    job_match: JobAICapabilityMatchResult,
    recommendations: LearningRecommendationsResult,
    high_priority_count: int,
) -> tuple[DashboardKpiCard, ...]:
    return (
        DashboardKpiCard(
            label="AI Readiness Score",
            value=str(readiness.readiness_score),
            supporting_text=readiness.readiness_label,
            status=_readiness_kpi_status(readiness.readiness_score),
        ),
        DashboardKpiCard(
            label="Job AI Match Score",
            value=str(job_match.match_score),
            supporting_text=job_match.match_label,
            status=_job_match_kpi_status(job_match.match_score),
        ),
        DashboardKpiCard(
            label="Overall Priority",
            value=recommendations.overall_priority,
            supporting_text=f"{len(recommendations.recommendations)} recommendation(s)",
            status=_recommendation_kpi_status(high_priority_count),
        ),
        DashboardKpiCard(
            label="Capability Coverage",
            value=(
                f"{readiness.capabilities_with_evidence}/"
                f"{readiness.capabilities_total}"
            ),
            supporting_text=(
                f"{len(job_match.matched_capabilities)} matched in sample job text"
            ),
            status="Manual check",
        ),
    )


def _count_high_priority_recommendations(
    recommendations: LearningRecommendationsResult,
) -> int:
    return sum(
        1
        for item in recommendations.recommendations
        if item.priority == "High"
    )


def _build_dashboard_sections(
    readiness: AIReadinessScoringResult,
    job_match: JobAICapabilityMatchResult,
    recommendations: LearningRecommendationsResult,
) -> tuple[DashboardSection, ...]:
    high_priority_count = _count_high_priority_recommendations(recommendations)
    return (
        DashboardSection(
            key="ai_readiness",
            title="AI Readiness",
            summary=(
                f"Score {readiness.readiness_score}/100 ({readiness.readiness_label}). "
                f"{readiness.capabilities_with_evidence} of "
                f"{readiness.capabilities_total} capabilities have recorded evidence."
            ),
        ),
        DashboardSection(
            key="job_ai_capability_match",
            title="Job AI Capability Match",
            summary=(
                f"Score {job_match.match_score}/100 ({job_match.match_label}). "
                f"{len(job_match.matched_capabilities)} matched and "
                f"{len(job_match.missing_capabilities)} missing or weak in sample job text."
            ),
        ),
        DashboardSection(
            key="learning_recommendations",
            title="Learning Recommendations",
            summary=(
                f"Overall priority {recommendations.overall_priority} with "
                f"{len(recommendations.recommendations)} advisory item(s), "
                f"including {high_priority_count} high-priority action(s)."
            ),
        ),
        DashboardSection(
            key="manual_review",
            title="Manual Review",
            summary=(
                "All dashboard values are rule-based and require human verification "
                "before portfolio, application, or interview use."
            ),
        ),
    )


def _build_summary_points(
    readiness: AIReadinessScoringResult,
    job_match: JobAICapabilityMatchResult,
    recommendations: LearningRecommendationsResult,
) -> tuple[str, ...]:
    points = [
        (
            f"Career readiness dashboard combines {readiness.capabilities_total} "
            "framework capabilities with sample job-match and recommendation outputs."
        ),
        (
            f"AI readiness: {readiness.readiness_score}/100 "
            f"({readiness.readiness_label})."
        ),
        (
            f"Job AI match: {job_match.match_score}/100 ({job_match.match_label})."
        ),
    ]

    if readiness.readiness_score < 50:
        points.append(
            "Foundation improvement is highlighted because AI readiness is below 50."
        )

    if (
        job_match.match_score >= 50
        and readiness.readiness_score < job_match.match_score
    ):
        points.append(
            "Job match signal is stronger than readiness evidence; "
            "prioritise evidence strengthening before external claims."
        )

    if recommendations.overall_priority == "High":
        points.append(
            "High overall recommendation priority; review next best action first."
        )

    points.append(
        "Next best action: "
        + recommendations.next_best_action
    )
    return tuple(points)


def build_career_readiness_dashboard(
    readiness: AIReadinessScoringResult | None = None,
    job_match: JobAICapabilityMatchResult | None = None,
    recommendations: LearningRecommendationsResult | None = None,
) -> CareerReadinessDashboardResult:
    """Build dashboard-ready career readiness summary from Sprint 53-56 service outputs."""
    resolved_readiness = readiness or build_portfolio_baseline_ai_readiness_score()
    resolved_job_match = job_match or match_job_description_to_ai_capabilities(
        DEFAULT_SAMPLE_JOB_DESCRIPTION,
    )
    resolved_recommendations = recommendations or build_learning_recommendations(
        resolved_readiness,
        resolved_job_match,
    )

    high_priority_count = _count_high_priority_recommendations(resolved_recommendations)
    capability_count = len(get_ai_capability_framework())

    return CareerReadinessDashboardResult(
        readiness_score=resolved_readiness.readiness_score,
        readiness_label=resolved_readiness.readiness_label,
        job_match_score=resolved_job_match.match_score,
        job_match_label=resolved_job_match.match_label,
        overall_priority=resolved_recommendations.overall_priority,
        next_best_action=resolved_recommendations.next_best_action,
        capability_count=capability_count,
        matched_capability_count=len(resolved_job_match.matched_capabilities),
        missing_capability_count=len(resolved_job_match.missing_capabilities),
        recommendation_count=len(resolved_recommendations.recommendations),
        high_priority_recommendation_count=high_priority_count,
        kpi_cards=_build_kpi_cards(
            resolved_readiness,
            resolved_job_match,
            resolved_recommendations,
            high_priority_count,
        ),
        summary_points=_build_summary_points(
            resolved_readiness,
            resolved_job_match,
            resolved_recommendations,
        ),
        dashboard_sections=_build_dashboard_sections(
            resolved_readiness,
            resolved_job_match,
            resolved_recommendations,
        ),
        claim_safety_notes=DASHBOARD_CLAIM_SAFETY_NOTES,
    )

"""Deterministic Career Strategy Action Plan aggregation (Sprint 58 Phase 1).

Converts Sprint 57 Career Readiness Dashboard output into manual action items and
progress indicators. Advisory only - no external AI calls.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .career_readiness_dashboard import (
    CareerReadinessDashboardResult,
    build_career_readiness_dashboard,
)

ActionCategory = Literal[
    "Learning",
    "Evidence strengthening",
    "Project improvement",
    "CV / interview preparation",
    "Manual review",
]

ActionPriority = Literal["High", "Medium", "Low"]

ActionStatus = Literal[
    "Not started",
    "In progress",
    "Ready for review",
    "Manual check",
]

OverallStatus = Literal[
    "Needs focused improvement",
    "Developing readiness",
    "Ready for targeted applications",
    "Manual review required",
]

ProgressIndicatorStatus = Literal["Review", "Developing", "Strong", "Manual check"]

APPROVED_ACTION_CATEGORIES: frozenset[str] = frozenset({
    "Learning",
    "Evidence strengthening",
    "Project improvement",
    "CV / interview preparation",
    "Manual review",
})

APPROVED_ACTION_PRIORITIES: frozenset[str] = frozenset({
    "High",
    "Medium",
    "Low",
})

APPROVED_ACTION_STATUSES: frozenset[str] = frozenset({
    "Not started",
    "In progress",
    "Ready for review",
    "Manual check",
})

APPROVED_OVERALL_STATUSES: frozenset[str] = frozenset({
    "Needs focused improvement",
    "Developing readiness",
    "Ready for targeted applications",
    "Manual review required",
})

ACTION_PLAN_CLAIM_SAFETY_NOTES: tuple[str, ...] = (
    "Rule-based action plan for manual self-review only.",
    "Not predictive hiring AI, automated career advice, or external AI output.",
    "Action items derive from Sprint 57 dashboard signals; verify before acting.",
    "No external AI provider is called by this action plan service.",
    "Progress indicators are advisory snapshots, not persisted tracking records.",
)

READINESS_TARGET_SCORE = 70
JOB_MATCH_TARGET_SCORE = 50
HIGH_PRIORITY_RECOMMENDATION_TARGET = 0


@dataclass(frozen=True)
class StrategyActionItem:
    title: str
    category: ActionCategory
    priority: ActionPriority
    status: ActionStatus
    reason: str
    suggested_next_step: str
    evidence_target: str
    linked_dashboard_section: str


@dataclass(frozen=True)
class ProgressIndicator:
    label: str
    current_value: str
    target_value: str
    status: ProgressIndicatorStatus
    supporting_text: str


@dataclass(frozen=True)
class CareerStrategyActionPlanResult:
    strategy_label: str
    overall_status: OverallStatus
    next_best_action: str
    action_items: tuple[StrategyActionItem, ...]
    progress_indicators: tuple[ProgressIndicator, ...]
    evidence_targets: tuple[str, ...]
    summary_points: tuple[str, ...]
    claim_safety_notes: tuple[str, ...]


def _readiness_progress_status(score: int) -> ProgressIndicatorStatus:
    if score < 50:
        return "Review"
    if score >= READINESS_TARGET_SCORE:
        return "Strong"
    return "Developing"


def _job_match_progress_status(score: int) -> ProgressIndicatorStatus:
    if score < JOB_MATCH_TARGET_SCORE:
        return "Review"
    return "Strong"


def _high_priority_progress_status(count: int) -> ProgressIndicatorStatus:
    if count > HIGH_PRIORITY_RECOMMENDATION_TARGET:
        return "Review"
    return "Strong"


def _assign_overall_status(dashboard: CareerReadinessDashboardResult) -> OverallStatus:
    if dashboard.readiness_score < 50 or dashboard.overall_priority == "High":
        return "Needs focused improvement"
    if (
        dashboard.readiness_score >= READINESS_TARGET_SCORE
        and dashboard.job_match_score >= JOB_MATCH_TARGET_SCORE
    ):
        return "Ready for targeted applications"
    if dashboard.high_priority_recommendation_count > 0:
        return "Manual review required"
    return "Developing readiness"


def _assign_strategy_label(dashboard: CareerReadinessDashboardResult) -> str:
    overall_status = _assign_overall_status(dashboard)
    if overall_status == "Needs focused improvement":
        return "Foundation-first career strategy"
    if overall_status == "Ready for targeted applications":
        return "Targeted application career strategy"
    if overall_status == "Manual review required":
        return "Evidence review career strategy"
    return "Developing readiness career strategy"


def _evidence_coverage_values(dashboard: CareerReadinessDashboardResult) -> tuple[str, str]:
    coverage_card = dashboard.kpi_cards[3]
    current_value = coverage_card.value
    if "/" in current_value:
        _, total = current_value.split("/", maxsplit=1)
        target_value = total
    else:
        target_value = str(dashboard.capability_count)
    return current_value, target_value


def _build_progress_indicators(
    dashboard: CareerReadinessDashboardResult,
) -> tuple[ProgressIndicator, ...]:
    evidence_current, evidence_target = _evidence_coverage_values(dashboard)
    return (
        ProgressIndicator(
            label="AI Readiness Score",
            current_value=str(dashboard.readiness_score),
            target_value=str(READINESS_TARGET_SCORE),
            status=_readiness_progress_status(dashboard.readiness_score),
            supporting_text=dashboard.readiness_label,
        ),
        ProgressIndicator(
            label="Job AI Match Score",
            current_value=str(dashboard.job_match_score),
            target_value=str(JOB_MATCH_TARGET_SCORE),
            status=_job_match_progress_status(dashboard.job_match_score),
            supporting_text=dashboard.job_match_label,
        ),
        ProgressIndicator(
            label="High-Priority Recommendations",
            current_value=str(dashboard.high_priority_recommendation_count),
            target_value=str(HIGH_PRIORITY_RECOMMENDATION_TARGET),
            status=_high_priority_progress_status(
                dashboard.high_priority_recommendation_count,
            ),
            supporting_text=(
                f"{dashboard.recommendation_count} total recommendation(s) from dashboard"
            ),
        ),
        ProgressIndicator(
            label="Capability Evidence Coverage",
            current_value=evidence_current,
            target_value=evidence_target,
            status="Manual check",
            supporting_text=(
                f"{dashboard.matched_capability_count} matched in sample job text; "
                f"{dashboard.missing_capability_count} missing or weak"
            ),
        ),
    )


def _build_action_items(
    dashboard: CareerReadinessDashboardResult,
) -> tuple[StrategyActionItem, ...]:
    items: list[StrategyActionItem] = []

    if dashboard.overall_priority == "High":
        items.append(
            StrategyActionItem(
                title="Execute dashboard next best action",
                category="Manual review",
                priority="High",
                status="Not started",
                reason=(
                    f"Dashboard overall priority is High with "
                    f"{dashboard.high_priority_recommendation_count} high-priority "
                    "recommendation(s)."
                ),
                suggested_next_step=dashboard.next_best_action,
                evidence_target="Manual review checklist",
                linked_dashboard_section="Learning Recommendations",
            )
        )

    if dashboard.high_priority_recommendation_count > 0:
        items.append(
            StrategyActionItem(
                title="Strengthen evidence for high-priority capability gaps",
                category="Evidence strengthening",
                priority="High",
                status="Not started",
                reason=(
                    f"{dashboard.high_priority_recommendation_count} high-priority "
                    "recommendation(s) require evidence review."
                ),
                suggested_next_step=(
                    "Review matched capabilities with weak evidence and add one verified "
                    "portfolio artifact before external claims."
                ),
                evidence_target="Portfolio or project artifact",
                linked_dashboard_section="Job AI Capability Match",
            )
        )
        items.append(
            StrategyActionItem(
                title="Close project improvement gaps from recommendations",
                category="Project improvement",
                priority="High",
                status="Not started",
                reason="High-priority recommendations include project or evidence gaps.",
                suggested_next_step=(
                    "Pick one job-matched capability and document a before-and-after "
                    "project note for manual review."
                ),
                evidence_target="Project improvement note",
                linked_dashboard_section="Learning Recommendations",
            )
        )

    if dashboard.readiness_score < 50:
        items.append(
            StrategyActionItem(
                title="Build foundation AI capability learning plan",
                category="Learning",
                priority="High",
                status="Not started",
                reason=(
                    f"AI readiness score is {dashboard.readiness_score}/100 "
                    f"({dashboard.readiness_label})."
                ),
                suggested_next_step=(
                    "Select one foundation capability from the Sprint 53 framework and "
                    "record a verified learning note before citing it externally."
                ),
                evidence_target="Foundation learning note",
                linked_dashboard_section="AI Readiness",
            )
        )

    if (
        dashboard.job_match_score >= JOB_MATCH_TARGET_SCORE
        and dashboard.missing_capability_count > 0
    ):
        items.append(
            StrategyActionItem(
                title="Review capability gaps against sample job signals",
                category="Learning",
                priority="Medium",
                status="Not started",
                reason=(
                    f"Job match score is {dashboard.job_match_score}/100 with "
                    f"{dashboard.missing_capability_count} missing or weak capability signal(s)."
                ),
                suggested_next_step=(
                    "Review each missing capability in the Sprint 53 framework and decide "
                    "whether to study, defer, or skip for the current role family."
                ),
                evidence_target="Capability awareness note",
                linked_dashboard_section="Job AI Capability Match",
            )
        )

    if (
        dashboard.readiness_score >= READINESS_TARGET_SCORE
        and dashboard.job_match_score >= JOB_MATCH_TARGET_SCORE
    ):
        items.append(
            StrategyActionItem(
                title="Prepare CV and interview evidence stories",
                category="CV / interview preparation",
                priority="Medium",
                status="Ready for review",
                reason=(
                    f"Readiness is {dashboard.readiness_label} and job match is "
                    f"{dashboard.job_match_label}."
                ),
                suggested_next_step=(
                    "Draft one STAR-style story per matched capability and source-check "
                    "every metric before practice."
                ),
                evidence_target="Interview story outline",
                linked_dashboard_section="AI Readiness",
            )
        )

    items.append(
        StrategyActionItem(
            title="Confirm action plan manually before acting",
            category="Manual review",
            priority="Low",
            status="Manual check",
            reason="All action plan outputs are advisory and require human verification.",
            suggested_next_step=(
                "Review each action item against portfolio evidence and reject any item "
                "you cannot support truthfully."
            ),
            evidence_target="Manual review checklist",
            linked_dashboard_section="Manual Review",
        )
    )

    return tuple(items)


def _collect_evidence_targets(
    action_items: tuple[StrategyActionItem, ...],
) -> tuple[str, ...]:
    seen: set[str] = set()
    targets: list[str] = []
    for item in action_items:
        if item.evidence_target in seen:
            continue
        seen.add(item.evidence_target)
        targets.append(item.evidence_target)
    return tuple(targets)


def _build_summary_points(
    dashboard: CareerReadinessDashboardResult,
    overall_status: OverallStatus,
    action_items: tuple[StrategyActionItem, ...],
) -> tuple[str, ...]:
    points = [
        (
            "Career strategy action plan derived from Sprint 57 career readiness dashboard "
            "signals for manual review."
        ),
        f"Overall status: {overall_status}.",
        (
            f"Dashboard readiness {dashboard.readiness_score}/100; "
            f"job match {dashboard.job_match_score}/100; "
            f"priority {dashboard.overall_priority}."
        ),
        f"Generated {len(action_items)} action item(s) with advisory progress indicators.",
        f"Next best action: {dashboard.next_best_action}",
    ]
    return tuple(points)


def build_career_strategy_action_plan(
    dashboard: CareerReadinessDashboardResult | None = None,
) -> CareerStrategyActionPlanResult:
    """Build a manual career strategy action plan from Sprint 57 dashboard output."""
    resolved_dashboard = dashboard or build_career_readiness_dashboard()
    overall_status = _assign_overall_status(resolved_dashboard)
    action_items = _build_action_items(resolved_dashboard)
    progress_indicators = _build_progress_indicators(resolved_dashboard)

    return CareerStrategyActionPlanResult(
        strategy_label=_assign_strategy_label(resolved_dashboard),
        overall_status=overall_status,
        next_best_action=resolved_dashboard.next_best_action,
        action_items=action_items,
        progress_indicators=progress_indicators,
        evidence_targets=_collect_evidence_targets(action_items),
        summary_points=_build_summary_points(
            resolved_dashboard,
            overall_status,
            action_items,
        ),
        claim_safety_notes=ACTION_PLAN_CLAIM_SAFETY_NOTES,
    )

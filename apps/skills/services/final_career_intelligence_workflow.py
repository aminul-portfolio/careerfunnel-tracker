"""Deterministic Final Career Intelligence Workflow aggregation (Sprint 59 Phase 1).

Integrates Sprint 53-58 service outputs into one end-to-end workflow summary. Advisory only -
no external AI calls.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .ai_capability_framework import get_ai_capability_framework
from .ai_readiness_scoring import (
    AIReadinessScoringResult,
    build_portfolio_baseline_ai_readiness_score,
)
from .career_readiness_dashboard import (
    CareerReadinessDashboardResult,
    build_career_readiness_dashboard,
)
from .career_strategy_action_plan import (
    CareerStrategyActionPlanResult,
    StrategyActionItem,
    build_career_strategy_action_plan,
)
from .job_ai_capability_matching import (
    JobAICapabilityMatchResult,
    match_job_description_to_ai_capabilities,
)
from .learning_recommendations import (
    DEFAULT_SAMPLE_JOB_DESCRIPTION,
    LearningRecommendationsResult,
    build_portfolio_baseline_learning_recommendations,
)

WorkflowStageStatus = Literal["Ready", "Review", "Manual check", "Developing"]

OverallWorkflowStatus = Literal[
    "Integrated workflow ready for manual use",
    "Needs evidence strengthening",
    "Manual review required",
    "Developing intelligence workflow",
]

ActionSequencePriority = Literal["High", "Medium", "Low"]

ActionSequenceStatus = Literal["Ready", "Review", "Manual check", "Developing"]

APPROVED_WORKFLOW_STAGE_STATUSES: frozenset[str] = frozenset({
    "Ready",
    "Review",
    "Manual check",
    "Developing",
})

APPROVED_OVERALL_WORKFLOW_STATUSES: frozenset[str] = frozenset({
    "Integrated workflow ready for manual use",
    "Needs evidence strengthening",
    "Manual review required",
    "Developing intelligence workflow",
})

APPROVED_ACTION_SEQUENCE_PRIORITIES: frozenset[str] = frozenset({
    "High",
    "Medium",
    "Low",
})

APPROVED_ACTION_SEQUENCE_STATUSES: frozenset[str] = frozenset({
    "Ready",
    "Review",
    "Manual check",
    "Developing",
})

WORKFLOW_CLAIM_SAFETY_NOTES: tuple[str, ...] = (
    "Rule-based end-to-end workflow summary for manual self-review only.",
    "Not predictive hiring AI, automated career advice, or external AI output.",
    "All stages derive from Sprint 53-58 local services; verify evidence manually.",
    "No external AI provider is called by this workflow aggregation service.",
    "Action sequence preserves manual-review boundaries from the Sprint 58 action plan.",
)

READINESS_TARGET_SCORE = 70
JOB_MATCH_TARGET_SCORE = 50

EXPECTED_WORKFLOW_STAGE_TITLES: tuple[str, ...] = (
    "Capability Framework",
    "AI Readiness Scoring",
    "Job-to-AI Capability Matching",
    "Learning Recommendations",
    "Career Readiness Dashboard",
    "Career Strategy Action Plan",
    "Manual Review Gate",
)


@dataclass(frozen=True)
class WorkflowStage:
    stage_number: int
    title: str
    source: str
    status: WorkflowStageStatus
    summary: str
    output_reference: str


@dataclass(frozen=True)
class ActionSequenceItem:
    step_number: int
    title: str
    priority: ActionSequencePriority
    status: ActionSequenceStatus
    reason: str
    manual_next_step: str
    source_stage: str
    evidence_target: str


@dataclass(frozen=True)
class FinalCareerIntelligenceWorkflowResult:
    workflow_label: str
    overall_status: OverallWorkflowStatus
    readiness_score: int
    job_match_score: int
    strategy_status: str
    next_best_action: str
    workflow_stages: tuple[WorkflowStage, ...]
    action_sequence: tuple[ActionSequenceItem, ...]
    integration_summary: tuple[str, ...]
    evidence_targets: tuple[str, ...]
    claim_safety_notes: tuple[str, ...]


def _readiness_stage_status(score: int) -> WorkflowStageStatus:
    if score < 50:
        return "Review"
    if score >= READINESS_TARGET_SCORE:
        return "Ready"
    return "Developing"


def _job_match_stage_status(score: int) -> WorkflowStageStatus:
    if score < 25:
        return "Review"
    if score >= JOB_MATCH_TARGET_SCORE:
        return "Ready"
    return "Developing"


def _recommendation_stage_status(priority: str) -> WorkflowStageStatus:
    if priority == "High":
        return "Review"
    if priority == "Low":
        return "Ready"
    return "Developing"


def _dashboard_stage_status(dashboard: CareerReadinessDashboardResult) -> WorkflowStageStatus:
    if dashboard.overall_priority == "High":
        return "Review"
    if (
        dashboard.readiness_score >= READINESS_TARGET_SCORE
        and dashboard.job_match_score >= JOB_MATCH_TARGET_SCORE
    ):
        return "Ready"
    return "Developing"


def _action_plan_stage_status(action_plan: CareerStrategyActionPlanResult) -> WorkflowStageStatus:
    if action_plan.overall_status == "Manual review required":
        return "Manual check"
    if action_plan.overall_status == "Needs focused improvement":
        return "Review"
    if action_plan.overall_status == "Ready for targeted applications":
        return "Ready"
    return "Developing"


def _map_action_item_status(item: StrategyActionItem) -> ActionSequenceStatus:
    if item.status == "Manual check":
        return "Manual check"
    if item.status == "Ready for review":
        return "Ready"
    if item.status == "In progress":
        return "Developing"
    if item.priority == "High":
        return "Review"
    return "Developing"


def _map_dashboard_section_to_stage(section: str) -> str:
    mapping = {
        "AI Readiness": "AI Readiness Scoring",
        "Job AI Capability Match": "Job-to-AI Capability Matching",
        "Learning Recommendations": "Learning Recommendations",
        "Manual Review": "Manual Review Gate",
    }
    return mapping.get(section, "Career Strategy Action Plan")


def _assign_overall_status(
    action_plan: CareerStrategyActionPlanResult,
    readiness_score: int,
    job_match_score: int,
) -> OverallWorkflowStatus:
    if action_plan.overall_status == "Needs focused improvement":
        return "Needs evidence strengthening"
    if action_plan.overall_status == "Manual review required":
        return "Manual review required"
    if (
        readiness_score >= READINESS_TARGET_SCORE
        and job_match_score >= JOB_MATCH_TARGET_SCORE
        and action_plan.overall_status == "Ready for targeted applications"
    ):
        return "Integrated workflow ready for manual use"
    if (
        readiness_score >= READINESS_TARGET_SCORE
        and job_match_score >= JOB_MATCH_TARGET_SCORE
    ):
        return "Manual review required"
    return "Developing intelligence workflow"


def _assign_workflow_label(overall_status: OverallWorkflowStatus) -> str:
    if overall_status == "Integrated workflow ready for manual use":
        return "Integrated career intelligence workflow"
    if overall_status == "Needs evidence strengthening":
        return "Evidence-strengthening career intelligence workflow"
    if overall_status == "Manual review required":
        return "Manual-review career intelligence workflow"
    return "Developing career intelligence workflow"


def _build_workflow_stages(
    framework_count: int,
    readiness: AIReadinessScoringResult,
    job_match: JobAICapabilityMatchResult,
    recommendations: LearningRecommendationsResult,
    dashboard: CareerReadinessDashboardResult,
    action_plan: CareerStrategyActionPlanResult,
) -> tuple[WorkflowStage, ...]:
    return (
        WorkflowStage(
            stage_number=1,
            title="Capability Framework",
            source="Sprint 53 - get_ai_capability_framework()",
            status="Ready",
            summary=(
                f"{framework_count} advisory AI capability categories available for "
                "manual employability mapping."
            ),
            output_reference="ai_capability_framework",
        ),
        WorkflowStage(
            stage_number=2,
            title="AI Readiness Scoring",
            source="Sprint 54 - build_portfolio_baseline_ai_readiness_score()",
            status=_readiness_stage_status(readiness.readiness_score),
            summary=(
                f"Readiness score {readiness.readiness_score}/100 "
                f"({readiness.readiness_label}); "
                f"{readiness.capabilities_with_evidence} of "
                f"{readiness.capabilities_total} capabilities have recorded evidence."
            ),
            output_reference="ai_readiness_scoring",
        ),
        WorkflowStage(
            stage_number=3,
            title="Job-to-AI Capability Matching",
            source="Sprint 55 - match_job_description_to_ai_capabilities()",
            status=_job_match_stage_status(job_match.match_score),
            summary=(
                f"Job match score {job_match.match_score}/100 ({job_match.match_label}); "
                f"{len(job_match.matched_capabilities)} matched and "
                f"{len(job_match.missing_capabilities)} missing or weak in sample job text."
            ),
            output_reference="job_ai_capability_matching",
        ),
        WorkflowStage(
            stage_number=4,
            title="Learning Recommendations",
            source="Sprint 56 - build_portfolio_baseline_learning_recommendations()",
            status=_recommendation_stage_status(recommendations.overall_priority),
            summary=(
                f"Overall priority {recommendations.overall_priority} with "
                f"{len(recommendations.recommendations)} advisory recommendation(s)."
            ),
            output_reference="learning_recommendations",
        ),
        WorkflowStage(
            stage_number=5,
            title="Career Readiness Dashboard",
            source="Sprint 57 - build_career_readiness_dashboard()",
            status=_dashboard_stage_status(dashboard),
            summary=(
                f"Dashboard combines readiness {dashboard.readiness_score}/100, "
                f"job match {dashboard.job_match_score}/100, and "
                f"{dashboard.recommendation_count} recommendation(s)."
            ),
            output_reference="career_readiness_dashboard",
        ),
        WorkflowStage(
            stage_number=6,
            title="Career Strategy Action Plan",
            source="Sprint 58 - build_career_strategy_action_plan()",
            status=_action_plan_stage_status(action_plan),
            summary=(
                f"Strategy status {action_plan.overall_status} with "
                f"{len(action_plan.action_items)} action item(s) and "
                f"{len(action_plan.progress_indicators)} progress indicator(s)."
            ),
            output_reference="career_strategy_action_plan",
        ),
        WorkflowStage(
            stage_number=7,
            title="Manual Review Gate",
            source="Sprint 59 - final workflow manual review boundary",
            status="Manual check",
            summary=(
                "All integrated workflow outputs require human verification before "
                "portfolio, application, or interview use."
            ),
            output_reference="manual_review_gate",
        ),
    )


def _build_action_sequence(
    action_plan: CareerStrategyActionPlanResult,
) -> tuple[ActionSequenceItem, ...]:
    sequence: list[ActionSequenceItem] = []
    for step_number, item in enumerate(action_plan.action_items, start=1):
        sequence.append(
            ActionSequenceItem(
                step_number=step_number,
                title=item.title,
                priority=item.priority,
                status=_map_action_item_status(item),
                reason=item.reason,
                manual_next_step=item.suggested_next_step,
                source_stage=_map_dashboard_section_to_stage(item.linked_dashboard_section),
                evidence_target=item.evidence_target,
            )
        )
    return tuple(sequence)


def _collect_evidence_targets(
    action_sequence: tuple[ActionSequenceItem, ...],
    action_plan: CareerStrategyActionPlanResult,
) -> tuple[str, ...]:
    seen: set[str] = set()
    targets: list[str] = []
    for target in action_plan.evidence_targets:
        if target in seen:
            continue
        seen.add(target)
        targets.append(target)
    for item in action_sequence:
        if item.evidence_target in seen:
            continue
        seen.add(item.evidence_target)
        targets.append(item.evidence_target)
    return tuple(targets)


def _build_integration_summary(
    overall_status: OverallWorkflowStatus,
    readiness: AIReadinessScoringResult,
    job_match: JobAICapabilityMatchResult,
    dashboard: CareerReadinessDashboardResult,
    action_plan: CareerStrategyActionPlanResult,
) -> tuple[str, ...]:
    high_priority_count = sum(
        1 for item in action_plan.action_items if item.priority == "High"
    )
    points = [
        (
            "Final career intelligence workflow integrates Sprint 53-58 service outputs "
            "into one deterministic, manual-review summary."
        ),
        f"Overall workflow status: {overall_status}.",
        (
            f"Readiness {readiness.readiness_score}/100 ({readiness.readiness_label}); "
            f"job match {job_match.match_score}/100 ({job_match.match_label})."
        ),
        (
            f"Strategy status {action_plan.overall_status}; "
            f"dashboard priority {dashboard.overall_priority}."
        ),
        (
            f"Action sequence contains {len(action_plan.action_items)} step(s), "
            f"including {high_priority_count} high-priority item(s)."
        ),
        f"Next best action: {action_plan.next_best_action}",
    ]
    return tuple(points)


def build_final_career_intelligence_workflow(
    readiness: AIReadinessScoringResult | None = None,
    job_match: JobAICapabilityMatchResult | None = None,
    recommendations: LearningRecommendationsResult | None = None,
    dashboard: CareerReadinessDashboardResult | None = None,
    action_plan: CareerStrategyActionPlanResult | None = None,
) -> FinalCareerIntelligenceWorkflowResult:
    """Build end-to-end career intelligence workflow from Sprint 53-58 service outputs."""
    resolved_readiness = readiness or build_portfolio_baseline_ai_readiness_score()
    resolved_job_match = job_match or match_job_description_to_ai_capabilities(
        DEFAULT_SAMPLE_JOB_DESCRIPTION,
    )
    resolved_recommendations = (
        recommendations or build_portfolio_baseline_learning_recommendations()
    )
    resolved_dashboard = dashboard or build_career_readiness_dashboard(
        resolved_readiness,
        resolved_job_match,
        resolved_recommendations,
    )
    resolved_action_plan = action_plan or build_career_strategy_action_plan(resolved_dashboard)

    overall_status = _assign_overall_status(
        resolved_action_plan,
        resolved_readiness.readiness_score,
        resolved_job_match.match_score,
    )
    workflow_stages = _build_workflow_stages(
        len(get_ai_capability_framework()),
        resolved_readiness,
        resolved_job_match,
        resolved_recommendations,
        resolved_dashboard,
        resolved_action_plan,
    )
    action_sequence = _build_action_sequence(resolved_action_plan)

    return FinalCareerIntelligenceWorkflowResult(
        workflow_label=_assign_workflow_label(overall_status),
        overall_status=overall_status,
        readiness_score=resolved_readiness.readiness_score,
        job_match_score=resolved_job_match.match_score,
        strategy_status=resolved_action_plan.overall_status,
        next_best_action=resolved_action_plan.next_best_action,
        workflow_stages=workflow_stages,
        action_sequence=action_sequence,
        integration_summary=_build_integration_summary(
            overall_status,
            resolved_readiness,
            resolved_job_match,
            resolved_dashboard,
            resolved_action_plan,
        ),
        evidence_targets=_collect_evidence_targets(action_sequence, resolved_action_plan),
        claim_safety_notes=WORKFLOW_CLAIM_SAFETY_NOTES,
    )

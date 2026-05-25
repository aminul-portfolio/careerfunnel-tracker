from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.utils import timezone

from apps.applications.choices import ApplicationStatus
from apps.applications.models import JobApplication

from .models import ApplicationSkillGap, SkillGapLongTermGoal, SkillGapPriority, SkillGapStage

FAILURE_STATUSES = (
    ApplicationStatus.REJECTED,
    ApplicationStatus.AUTO_REJECTED,
)

STAGE_WEIGHTS: dict[str, Decimal] = {
    SkillGapStage.APPLICATION: Decimal("1.00"),
    SkillGapStage.SCREENING: Decimal("1.25"),
    SkillGapStage.TECHNICAL: Decimal("1.50"),
    SkillGapStage.INTERVIEW: Decimal("1.75"),
}

GOAL_WEIGHTS: dict[str, Decimal] = {
    SkillGapLongTermGoal.DATA_ANALYST: Decimal("1.00"),
    SkillGapLongTermGoal.BI_ANALYST: Decimal("1.00"),
    SkillGapLongTermGoal.ANALYTICS_ENGINEER: Decimal("1.10"),
    SkillGapLongTermGoal.DATA_ENGINEER: Decimal("1.15"),
    SkillGapLongTermGoal.GENERAL: Decimal("0.90"),
}

PRIORITY_BANDS: tuple[tuple[Decimal, str], ...] = (
    (Decimal("10.00"), SkillGapPriority.CRITICAL),
    (Decimal("6.00"), SkillGapPriority.HIGH),
    (Decimal("3.00"), SkillGapPriority.MEDIUM),
)


@dataclass(frozen=True)
class SkillGapUpsertResult:
    gap: ApplicationSkillGap
    created: bool


@dataclass(frozen=True)
class SkillGapDashboardSummary:
    total: int
    unresolved: int
    resolved: int
    high_priority: int


@dataclass(frozen=True)
class ActionPlanGroup:
    key: str
    label: str
    items: tuple[ApplicationSkillGap, ...]


@dataclass(frozen=True)
class SkillGapActionPlanContext:
    high_priority_unresolved: ActionPlanGroup
    medium_priority_unresolved: ActionPlanGroup
    lower_priority_backlog: ActionPlanGroup
    resolved_context: ActionPlanGroup
    has_unresolved: bool


@dataclass(frozen=True)
class LearningPlanGroup:
    key: str
    label: str
    items: tuple[ApplicationSkillGap, ...]


@dataclass(frozen=True)
class SkillGapLearningPlanContext:
    immediate_learning_focus: LearningPlanGroup
    practice_next: LearningPlanGroup
    backlog_learning_items: LearningPlanGroup
    resolved_learning_context: LearningPlanGroup
    has_unresolved: bool


@dataclass(frozen=True)
class EvidenceReadinessGroup:
    key: str
    label: str
    items: tuple[ApplicationSkillGap, ...]


@dataclass(frozen=True)
class SkillGapEvidenceReadinessContext:
    evidence_needed_now: EvidenceReadinessGroup
    strengthen_next: EvidenceReadinessGroup
    evidence_backlog: EvidenceReadinessGroup
    resolved_evidence_context: EvidenceReadinessGroup
    has_unresolved: bool


@dataclass(frozen=True)
class SkillGapDashboardContext:
    summary: SkillGapDashboardSummary
    gaps: tuple[ApplicationSkillGap, ...]
    priority_filter: str
    stage_filter: str
    resolved_filter: str
    action_plan: SkillGapActionPlanContext
    learning_plan: SkillGapLearningPlanContext
    evidence_readiness: SkillGapEvidenceReadinessContext


HIGH_PRIORITY_VALUES = (
    SkillGapPriority.HIGH,
    SkillGapPriority.CRITICAL,
)

MEDIUM_PRIORITY_VALUES = (SkillGapPriority.MEDIUM,)


def get_stage_weight(stage: str) -> Decimal:
    return STAGE_WEIGHTS.get(stage, Decimal("1.00"))


def get_goal_weight(long_term_goal: str) -> Decimal:
    return GOAL_WEIGHTS.get(long_term_goal, Decimal("1.00"))


def compute_priority_score(
    *,
    failure_count: int,
    stage_weight: Decimal,
    goal_weight: Decimal,
) -> Decimal:
    score = Decimal(failure_count) * stage_weight * goal_weight
    return score.quantize(Decimal("0.01"))


def assign_priority(priority_score: Decimal) -> str:
    for threshold, priority in PRIORITY_BANDS:
        if priority_score >= threshold:
            return priority
    return SkillGapPriority.LOW


def _skill_name_matches_application_text(
    *,
    skill_name: str,
    required_skills: str,
    job_description: str,
) -> bool:
    normalized_skill = skill_name.strip().lower()
    if not normalized_skill:
        return False
    corpus = f"{required_skills or ''}\n{job_description or ''}".lower()
    return normalized_skill in corpus


def get_global_failure_count(*, user, skill_name: str) -> int:
    """Count rejected/auto-rejected applications for this user mentioning the skill."""
    queryset = JobApplication.objects.filter(
        user=user,
        status__in=FAILURE_STATUSES,
    ).only("required_skills", "job_description")

    count = 0
    for application in queryset:
        if _skill_name_matches_application_text(
            skill_name=skill_name,
            required_skills=application.required_skills,
            job_description=application.job_description,
        ):
            count += 1
    return count


def create_or_update_gap(
    *,
    application: JobApplication,
    skill_name: str,
    stage: str,
    current_tier: str,
    identified_by: str,
    long_term_goal: str = SkillGapLongTermGoal.GENERAL,
    jd_requirement: str = "",
    suggested_action: str = "",
) -> SkillGapUpsertResult:
    failure_count = get_global_failure_count(user=application.user, skill_name=skill_name)
    stage_weight = get_stage_weight(stage)
    goal_weight = get_goal_weight(long_term_goal)
    priority_score = compute_priority_score(
        failure_count=failure_count,
        stage_weight=stage_weight,
        goal_weight=goal_weight,
    )
    priority = assign_priority(priority_score)

    gap, created = ApplicationSkillGap.objects.update_or_create(
        application=application,
        skill_name=skill_name,
        stage=stage,
        defaults={
            "current_tier": current_tier,
            "priority": priority,
            "goal_weight": goal_weight,
            "failure_count": failure_count,
            "stage_weight": stage_weight,
            "priority_score": priority_score,
            "jd_requirement": jd_requirement,
            "identified_by": identified_by,
            "suggested_action": suggested_action,
            "long_term_goal": long_term_goal,
        },
    )
    return SkillGapUpsertResult(gap=gap, created=created)


def mark_gap_resolved(
    gap: ApplicationSkillGap,
    *,
    resolved_tier: str,
    resolved_date: date | None = None,
) -> ApplicationSkillGap:
    gap.resolved = True
    gap.resolved_tier = resolved_tier
    gap.resolved_date = resolved_date or timezone.localdate()
    gap.save(
        update_fields=["resolved", "resolved_tier", "resolved_date", "updated_at"],
    )
    return gap


def get_user_skill_gaps_queryset(*, user):
    """Read-only queryset scoped to the authenticated user."""
    return (
        ApplicationSkillGap.objects.filter(application__user=user)
        .select_related("application")
        .order_by("-priority_score", "-updated_at")
    )


def apply_skill_gap_dashboard_filters(
    queryset,
    *,
    priority: str,
    stage: str,
    resolved: str,
):
    """Read-only GET filters for the dashboard list."""
    if priority:
        queryset = queryset.filter(priority=priority)
    if stage:
        queryset = queryset.filter(stage=stage)
    if resolved == "yes":
        queryset = queryset.filter(resolved=True)
    elif resolved == "no":
        queryset = queryset.filter(resolved=False)
    return queryset


def build_skill_gap_dashboard_summary(*, user) -> SkillGapDashboardSummary:
    base_qs = get_user_skill_gaps_queryset(user=user)
    return SkillGapDashboardSummary(
        total=base_qs.count(),
        unresolved=base_qs.filter(resolved=False).count(),
        resolved=base_qs.filter(resolved=True).count(),
        high_priority=base_qs.filter(priority__in=HIGH_PRIORITY_VALUES).count(),
    )


def build_skill_gap_dashboard_context(*, user, query_params) -> SkillGapDashboardContext:
    priority_filter = (query_params.get("priority") or "").strip()
    stage_filter = (query_params.get("stage") or "").strip()
    resolved_filter = (query_params.get("resolved") or "").strip()

    base_qs = get_user_skill_gaps_queryset(user=user)
    filtered_qs = apply_skill_gap_dashboard_filters(
        base_qs,
        priority=priority_filter,
        stage=stage_filter,
        resolved=resolved_filter,
    )

    return SkillGapDashboardContext(
        summary=build_skill_gap_dashboard_summary(user=user),
        gaps=tuple(filtered_qs),
        priority_filter=priority_filter,
        stage_filter=stage_filter,
        resolved_filter=resolved_filter,
        action_plan=build_skill_gap_action_plan_context(user=user),
        learning_plan=build_skill_gap_learning_plan_context(user=user),
        evidence_readiness=build_skill_gap_evidence_readiness_context(user=user),
    )


def get_action_plan_items(*, user) -> tuple[ApplicationSkillGap, ...]:
    """Unresolved saved gaps for the user, highest priority score first."""
    return tuple(get_user_skill_gaps_queryset(user=user).filter(resolved=False))


def group_action_plan_items(
    unresolved_items: tuple[ApplicationSkillGap, ...],
    *,
    resolved_items: tuple[ApplicationSkillGap, ...],
) -> SkillGapActionPlanContext:
    high_priority: list[ApplicationSkillGap] = []
    medium_priority: list[ApplicationSkillGap] = []
    lower_backlog: list[ApplicationSkillGap] = []

    for gap in unresolved_items:
        if gap.priority in HIGH_PRIORITY_VALUES:
            high_priority.append(gap)
        elif gap.priority in MEDIUM_PRIORITY_VALUES:
            medium_priority.append(gap)
        else:
            lower_backlog.append(gap)

    return SkillGapActionPlanContext(
        high_priority_unresolved=ActionPlanGroup(
            key="high_priority",
            label="High-priority unresolved gaps",
            items=tuple(high_priority),
        ),
        medium_priority_unresolved=ActionPlanGroup(
            key="medium_priority",
            label="Medium-priority unresolved gaps",
            items=tuple(medium_priority),
        ),
        lower_priority_backlog=ActionPlanGroup(
            key="lower_backlog",
            label="Lower-priority backlog",
            items=tuple(lower_backlog),
        ),
        resolved_context=ActionPlanGroup(
            key="resolved_context",
            label="Resolved context",
            items=resolved_items,
        ),
        has_unresolved=bool(unresolved_items),
    )


def build_skill_gap_action_plan_context(*, user) -> SkillGapActionPlanContext:
    unresolved = get_action_plan_items(user=user)
    resolved = tuple(get_user_skill_gaps_queryset(user=user).filter(resolved=True))
    return group_action_plan_items(unresolved, resolved_items=resolved)


def get_learning_plan_items(*, user) -> tuple[ApplicationSkillGap, ...]:
    """Unresolved saved gaps for learning focus, highest priority score first."""
    return tuple(get_user_skill_gaps_queryset(user=user).filter(resolved=False))


def group_learning_plan_items(
    unresolved_items: tuple[ApplicationSkillGap, ...],
    *,
    resolved_items: tuple[ApplicationSkillGap, ...],
) -> SkillGapLearningPlanContext:
    immediate_focus: list[ApplicationSkillGap] = []
    practice_next: list[ApplicationSkillGap] = []
    backlog_items: list[ApplicationSkillGap] = []

    for gap in unresolved_items:
        if gap.priority in HIGH_PRIORITY_VALUES:
            immediate_focus.append(gap)
        elif gap.priority in MEDIUM_PRIORITY_VALUES:
            practice_next.append(gap)
        else:
            backlog_items.append(gap)

    return SkillGapLearningPlanContext(
        immediate_learning_focus=LearningPlanGroup(
            key="immediate_learning_focus",
            label="Immediate learning focus",
            items=tuple(immediate_focus),
        ),
        practice_next=LearningPlanGroup(
            key="practice_next",
            label="Practice next",
            items=tuple(practice_next),
        ),
        backlog_learning_items=LearningPlanGroup(
            key="backlog_learning_items",
            label="Backlog learning items",
            items=tuple(backlog_items),
        ),
        resolved_learning_context=LearningPlanGroup(
            key="resolved_learning_context",
            label="Resolved learning context",
            items=resolved_items,
        ),
        has_unresolved=bool(unresolved_items),
    )


def build_skill_gap_learning_plan_context(*, user) -> SkillGapLearningPlanContext:
    unresolved = get_learning_plan_items(user=user)
    resolved = tuple(get_user_skill_gaps_queryset(user=user).filter(resolved=True))
    return group_learning_plan_items(unresolved, resolved_items=resolved)


def get_evidence_readiness_items(*, user) -> tuple[ApplicationSkillGap, ...]:
    """Unresolved saved gaps for evidence focus, highest priority score first."""
    return tuple(get_user_skill_gaps_queryset(user=user).filter(resolved=False))


def group_evidence_readiness_items(
    unresolved_items: tuple[ApplicationSkillGap, ...],
    *,
    resolved_items: tuple[ApplicationSkillGap, ...],
) -> SkillGapEvidenceReadinessContext:
    evidence_now: list[ApplicationSkillGap] = []
    strengthen_next: list[ApplicationSkillGap] = []
    evidence_backlog: list[ApplicationSkillGap] = []

    for gap in unresolved_items:
        if gap.priority in HIGH_PRIORITY_VALUES:
            evidence_now.append(gap)
        elif gap.priority in MEDIUM_PRIORITY_VALUES:
            strengthen_next.append(gap)
        else:
            evidence_backlog.append(gap)

    return SkillGapEvidenceReadinessContext(
        evidence_needed_now=EvidenceReadinessGroup(
            key="evidence_needed_now",
            label="Evidence needed now",
            items=tuple(evidence_now),
        ),
        strengthen_next=EvidenceReadinessGroup(
            key="strengthen_next",
            label="Strengthen next",
            items=tuple(strengthen_next),
        ),
        evidence_backlog=EvidenceReadinessGroup(
            key="evidence_backlog",
            label="Evidence backlog",
            items=tuple(evidence_backlog),
        ),
        resolved_evidence_context=EvidenceReadinessGroup(
            key="resolved_evidence_context",
            label="Resolved evidence context",
            items=resolved_items,
        ),
        has_unresolved=bool(unresolved_items),
    )


def build_skill_gap_evidence_readiness_context(
    *,
    user,
) -> SkillGapEvidenceReadinessContext:
    unresolved = get_evidence_readiness_items(user=user)
    resolved = tuple(get_user_skill_gaps_queryset(user=user).filter(resolved=True))
    return group_evidence_readiness_items(unresolved, resolved_items=resolved)

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
class SkillGapDashboardContext:
    summary: SkillGapDashboardSummary
    gaps: tuple[ApplicationSkillGap, ...]
    priority_filter: str
    stage_filter: str
    resolved_filter: str


HIGH_PRIORITY_VALUES = (
    SkillGapPriority.HIGH,
    SkillGapPriority.CRITICAL,
)


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
    )

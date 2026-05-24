from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from django.db.models import Q, Sum
from django.urls import reverse
from django.utils import timezone

from apps.applications.choices import ApplicationStatus, FollowUpStatus
from apps.applications.models import JobApplication
from apps.daily_log.models import DailyLog
from apps.interviews.choices import InterviewOutcome
from apps.interviews.models import InterviewPrep
from apps.metrics.services import build_data_quality_report, build_funnel_metrics, diagnose_funnel
from apps.recruiter_emails.models import RecruiterEmail
from apps.weekly_review.models import WeeklyReview

PRIORITY_SORT_ORDER = {
    "High": 0,
    "Medium": 1,
    "Low": 2,
}

OPEN_FOLLOW_UP_STATUSES = [
    FollowUpStatus.NOT_SET,
    FollowUpStatus.NOT_DUE,
    FollowUpStatus.DUE,
]

ACTIVE_APPLICATION_STATUSES = [
    ApplicationStatus.SUBMITTED,
    ApplicationStatus.NO_RESPONSE,
    ApplicationStatus.ACKNOWLEDGED,
    ApplicationStatus.SCREENING_CALL,
    ApplicationStatus.TECHNICAL_SCREEN,
    ApplicationStatus.INTERVIEW,
]


@dataclass(frozen=True)
class DashboardSummary:
    total_applications: int
    applications_this_week: int
    responses_this_week: int
    calls_this_week: int
    interviews_this_week: int
    response_rate: float
    interview_rate: float
    offer_rate: float
    daily_target_total: int
    daily_actual_total: int
    daily_variance_total: int
    daily_target_hit_rate: float
    diagnosis_title: str
    diagnosis_label: str
    diagnosis_explanation: str
    recommended_action: str
    diagnosis_severity: str


@dataclass(frozen=True)
class TodayActionItem:
    priority: str
    title: str
    reason: str
    recommended_action: str
    related_url: str | None = None


@dataclass(frozen=True)
class TodaySignal:
    priority: str
    title: str
    reason: str
    recommended_action: str
    related_url: str | None = None


@dataclass(frozen=True)
class SignatureCareerInsight:
    diagnosis: str
    best_manual_action: str
    why_it_matters: str
    manual_url: str | None


@dataclass(frozen=True)
class WeekPulse:
    week_start: date
    week_end: date
    week_range_label: str
    target_applications: int
    actual_applications: int
    variance: int
    weekly_review_status: str
    weekly_review_url: str | None
    follow_ups_due: int
    follow_ups_url: str
    interview_prep_status: str
    interview_prep_count: int
    interview_prep_url: str


@dataclass(frozen=True)
class PipelineHealthMetric:
    label: str
    score: int
    status_label: str
    detail: str
    manual_url: str


@dataclass(frozen=True)
class PipelineHealthMatrix:
    metrics: tuple[PipelineHealthMetric, ...]


@dataclass(frozen=True)
class EvidenceReadinessSummary:
    missing_cv_versions: int
    missing_job_descriptions: int
    missing_required_skills: int
    missing_follow_up_data: int
    analytics_ready_rate: float
    manual_url: str


@dataclass(frozen=True)
class FunnelSnapshot:
    applications: int
    responses: int
    interviews: int
    offers: int


@dataclass(frozen=True)
class WeeklyOperatingStep:
    step: str
    label: str
    description: str
    manual_url: str


@dataclass(frozen=True)
class RecentActivityItem:
    activity_type: str
    title: str
    detail: str
    occurred_at_label: str
    related_url: str | None


def get_current_week_range():
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def build_dashboard_summary(user) -> DashboardSummary:
    week_start, week_end = get_current_week_range()
    applications = JobApplication.objects.filter(user=user)
    applications_this_week = applications.filter(
        date_applied__gte=week_start,
        date_applied__lte=week_end,
    ).count()
    response_statuses = [
        ApplicationStatus.ACKNOWLEDGED,
        ApplicationStatus.SCREENING_CALL,
        ApplicationStatus.TECHNICAL_SCREEN,
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.OFFER,
        ApplicationStatus.REJECTED,
        ApplicationStatus.AUTO_REJECTED,
    ]
    responses_this_week = applications.filter(
        date_applied__gte=week_start,
        date_applied__lte=week_end,
        status__in=response_statuses,
    ).count()
    calls_this_week = applications.filter(
        date_applied__gte=week_start,
        date_applied__lte=week_end,
        status__in=[
            ApplicationStatus.SCREENING_CALL,
            ApplicationStatus.TECHNICAL_SCREEN,
        ],
    ).count()
    interviews_this_week = applications.filter(
        date_applied__gte=week_start,
        date_applied__lte=week_end,
        status__in=[ApplicationStatus.INTERVIEW, ApplicationStatus.OFFER],
    ).count()
    metrics = build_funnel_metrics(user)
    diagnosis = diagnose_funnel(metrics)
    return DashboardSummary(
        metrics.total_applications,
        applications_this_week,
        responses_this_week,
        calls_this_week,
        interviews_this_week,
        metrics.response_rate,
        metrics.interview_rate,
        metrics.offer_rate,
        metrics.daily_target_total,
        metrics.daily_actual_total,
        metrics.daily_variance_total,
        metrics.daily_target_hit_rate,
        diagnosis.diagnosis_title,
        diagnosis.diagnosis_label,
        diagnosis.explanation,
        diagnosis.recommended_action,
        diagnosis.severity,
    )


def get_recent_applications(user, limit: int = 5):
    return JobApplication.objects.filter(user=user).order_by("-date_applied", "-created_at")[:limit]


def get_recent_daily_logs(user, limit: int = 5):
    return DailyLog.objects.filter(user=user).order_by("-log_date")[:limit]


def get_recent_weekly_reviews(user, limit: int = 3):
    return WeeklyReview.objects.filter(user=user).order_by("-week_ending")[:limit]


def _application_label(application: JobApplication) -> str:
    return f"{application.company_name} - {application.job_title}"


def should_prompt_weekly_review(user, today=None) -> bool:
    """Return True when the user should be reminded to add a manual weekly review."""
    if today is None:
        today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    if today != week_end:
        return False
    return not WeeklyReview.objects.filter(user=user, week_ending=today).exists()


def _missing_evidence_reason(application: JobApplication) -> str:
    missing_fields = []
    if not application.required_skills:
        missing_fields.append("required skills")
    if not application.job_description:
        missing_fields.append("job description evidence")

    if len(missing_fields) == 1:
        return f"{missing_fields[0].capitalize()} is missing for {_application_label(application)}."
    return (
        "Required skills and job description evidence are missing for "
        f"{_application_label(application)}."
    )


def build_today_action_panel(user, limit: int = 8) -> list[TodayActionItem]:
    if limit <= 0:
        return []

    today = timezone.localdate()
    actions: list[TodayActionItem] = []

    overdue_followups = (
        JobApplication.objects.filter(
            user=user,
            follow_up_date__lt=today,
            follow_up_status__in=OPEN_FOLLOW_UP_STATUSES,
        )
        .order_by("follow_up_date", "company_name", "job_title", "pk")[:limit]
    )
    for application in overdue_followups:
        actions.append(
            TodayActionItem(
                priority="High",
                title=f"Overdue follow-up: {application.company_name}",
                reason=(
                    f"Follow-up was due on {application.follow_up_date} for "
                    f"{_application_label(application)}."
                ),
                recommended_action="Send a short follow-up and update the follow-up status.",
                related_url=application.get_absolute_url(),
            )
        )

    due_today_followups = (
        JobApplication.objects.filter(
            user=user,
            follow_up_date=today,
            follow_up_status__in=OPEN_FOLLOW_UP_STATUSES,
        )
        .order_by("company_name", "job_title", "pk")[:limit]
    )
    for application in due_today_followups:
        actions.append(
            TodayActionItem(
                priority="High",
                title=f"Follow up today: {application.company_name}",
                reason=f"Follow-up is due today for {_application_label(application)}.",
                recommended_action="Send the planned follow-up or mark it as not needed.",
                related_url=application.get_absolute_url(),
            )
        )

    upcoming_interviews = (
        InterviewPrep.objects.select_related("application")
        .filter(
            user=user,
            interview_date__gte=today,
            interview_date__lte=today + timedelta(days=7),
            outcome=InterviewOutcome.SCHEDULED,
        )
        .order_by("interview_date", "application__company_name", "pk")[:limit]
    )
    for interview in upcoming_interviews:
        if interview.readiness_score >= 80:
            continue
        actions.append(
            TodayActionItem(
                priority="High",
                title=f"Prepare for interview: {interview.application.company_name}",
                reason=(
                    f"Interview is on {interview.interview_date} and readiness is "
                    f"{interview.readiness_score}%."
                ),
                recommended_action=(
                    "Complete the interview checklist and prepare one project walkthrough."
                ),
                related_url=interview.get_absolute_url(),
            )
        )

    active_applications = JobApplication.objects.filter(
        user=user,
        status__in=ACTIVE_APPLICATION_STATUSES,
    )

    missing_cv_versions = active_applications.filter(cv_version="").order_by(
        "-date_applied", "company_name", "job_title", "pk"
    )[:limit]
    for application in missing_cv_versions:
        actions.append(
            TodayActionItem(
                priority="Medium",
                title=f"Add CV version: {application.company_name}",
                reason=f"No CV version is recorded for {_application_label(application)}.",
                recommended_action="Record the CV version used so later results can be compared.",
                related_url=application.get_absolute_url(),
            )
        )

    missing_evidence = active_applications.filter(
        Q(required_skills="") | Q(job_description="")
    ).order_by("-date_applied", "company_name", "job_title", "pk")[:limit]
    for application in missing_evidence:
        actions.append(
            TodayActionItem(
                priority="Medium",
                title=f"Add job evidence: {application.company_name}",
                reason=_missing_evidence_reason(application),
                recommended_action=(
                    "Capture the required skills or job description notes before the "
                    "advert changes."
                ),
                related_url=application.get_absolute_url(),
            )
        )

    if not DailyLog.objects.filter(user=user, log_date=today).exists():
        actions.append(
            TodayActionItem(
                priority="Medium",
                title="Add today's daily log",
                reason="No daily activity log exists for today.",
                recommended_action=(
                    "Record today's target, actual applications, responses, and useful notes."
                ),
                related_url=reverse("daily_log:daily_log_create"),
            )
        )

    if should_prompt_weekly_review(user, today):
        actions.append(
            TodayActionItem(
                priority="Medium",
                title="Weekly review due",
                reason="Today is the end of the current week and no weekly review exists yet.",
                recommended_action=(
                    "Complete the manual weekly review and compare it with the AI Weekly Coach."
                ),
                related_url=reverse("weekly_review:weekly_review_create"),
            )
        )

    missing_job_urls = active_applications.filter(job_url="").order_by(
        "-date_applied", "company_name", "job_title", "pk"
    )[:limit]
    for application in missing_job_urls:
        actions.append(
            TodayActionItem(
                priority="Low",
                title=f"Add job URL: {application.company_name}",
                reason=f"No job URL is saved for {_application_label(application)}.",
                recommended_action="Add the source URL if it is still available.",
                related_url=application.get_absolute_url(),
            )
        )

    actions.sort(key=lambda action: PRIORITY_SORT_ORDER[action.priority])
    return actions[:limit]


def _health_status_label(score: int) -> str:
    if score >= 80:
        return "Strong"
    if score >= 50:
        return "Needs attention"
    return "Missing"


def _format_week_range_label(week_start: date, week_end: date) -> str:
    return f"{week_start.strftime('%d %b')} - {week_end.strftime('%d %b %Y')}"


def build_week_pulse(user) -> WeekPulse:
    today = timezone.localdate()
    week_start, week_end = get_current_week_range()
    week_logs = DailyLog.objects.filter(
        user=user,
        log_date__gte=week_start,
        log_date__lte=week_end,
    )
    log_stats = week_logs.aggregate(
        target_total=Sum("target_applications"),
        actual_total=Sum("actual_applications"),
    )
    target_applications = log_stats["target_total"] or 0
    actual_applications = log_stats["actual_total"] or 0
    variance = actual_applications - target_applications

    current_review = WeeklyReview.objects.filter(
        user=user,
        week_starting=week_start,
        week_ending=week_end,
    ).first()
    if current_review:
        weekly_review_status = "Complete for this week"
        weekly_review_url = current_review.get_absolute_url()
    elif should_prompt_weekly_review(user, today):
        weekly_review_status = "Due today - manual review not logged"
        weekly_review_url = reverse("weekly_review:weekly_review_create")
    elif today <= week_end:
        weekly_review_status = "In progress - complete before week end"
        weekly_review_url = reverse("weekly_review:weekly_review_list")
    else:
        weekly_review_status = "Not logged for this week"
        weekly_review_url = reverse("weekly_review:weekly_review_create")

    follow_ups_due = JobApplication.objects.filter(
        user=user,
        follow_up_date__lte=today,
        follow_up_status__in=OPEN_FOLLOW_UP_STATUSES,
    ).count()

    upcoming_interviews = list(
        InterviewPrep.objects.filter(
            user=user,
            interview_date__gte=today,
            outcome=InterviewOutcome.SCHEDULED,
        )
    )
    interview_prep_count = len(upcoming_interviews)
    low_readiness_count = sum(
        1 for prep in upcoming_interviews if prep.readiness_score < 80
    )
    if interview_prep_count == 0:
        interview_prep_status = "No upcoming interview prep logged"
    elif low_readiness_count:
        interview_prep_status = (
            f"{low_readiness_count} of {interview_prep_count} prep record(s) below 80% readiness"
        )
    else:
        interview_prep_status = f"{interview_prep_count} prep record(s) scheduled"

    return WeekPulse(
        week_start=week_start,
        week_end=week_end,
        week_range_label=_format_week_range_label(week_start, week_end),
        target_applications=target_applications,
        actual_applications=actual_applications,
        variance=variance,
        weekly_review_status=weekly_review_status,
        weekly_review_url=weekly_review_url,
        follow_ups_due=follow_ups_due,
        follow_ups_url=reverse("followups:followup_list"),
        interview_prep_status=interview_prep_status,
        interview_prep_count=interview_prep_count,
        interview_prep_url=reverse("interviews:interview_list"),
    )


def build_pipeline_health_matrix(user) -> PipelineHealthMatrix:
    summary = build_dashboard_summary(user)
    data_quality = build_data_quality_report(user)
    week_pulse = build_week_pulse(user)

    if week_pulse.target_applications > 0:
        activity_score = min(
            100,
            int(round((week_pulse.actual_applications / week_pulse.target_applications) * 100)),
        )
        activity_detail = (
            f"{week_pulse.actual_applications} actual vs {week_pulse.target_applications} "
            "target applications logged this week."
        )
    elif summary.applications_this_week > 0:
        activity_score = min(100, summary.applications_this_week * 20)
        activity_detail = f"{summary.applications_this_week} application(s) logged this week."
    else:
        activity_score = 0
        activity_detail = "No weekly activity logged yet."

    evidence_score = int(round(data_quality.analytics_ready_rate))
    evidence_detail = (
        f"{data_quality.analytics_ready_rate}% of applications are analytics-ready."
    )

    if data_quality.total_applications == 0:
        follow_up_score = 0
        follow_up_detail = "No applications to assess follow-up discipline."
    else:
        complete = data_quality.total_applications - data_quality.missing_follow_up_count
        follow_up_score = int(round((complete / data_quality.total_applications) * 100))
        follow_up_detail = (
            f"{data_quality.missing_follow_up_count} application(s) still missing follow-up dates."
        )

    upcoming = list(
        InterviewPrep.objects.filter(
            user=user,
            interview_date__gte=timezone.localdate(),
            outcome=InterviewOutcome.SCHEDULED,
        )
    )
    if upcoming:
        avg_readiness = int(
            round(sum(prep.readiness_score for prep in upcoming) / len(upcoming))
        )
        interview_score = avg_readiness
        interview_detail = f"Average readiness across {len(upcoming)} upcoming prep record(s)."
    else:
        interview_score = 100 if summary.total_applications == 0 else 70
        interview_detail = "No upcoming interview prep requires immediate attention."

    if week_pulse.weekly_review_status.startswith("Complete"):
        review_score = 100
    elif "Due today" in week_pulse.weekly_review_status:
        review_score = 40
    elif "In progress" in week_pulse.weekly_review_status:
        review_score = 60
    else:
        review_score = 20
    review_detail = week_pulse.weekly_review_status

    response_score = min(100, int(round(summary.response_rate)))
    response_detail = f"{summary.response_rate}% response conversion across logged applications."

    metrics = (
        PipelineHealthMetric(
            label="Activity volume",
            score=activity_score,
            status_label=_health_status_label(activity_score),
            detail=activity_detail,
            manual_url=reverse("daily_log:daily_log_list"),
        ),
        PipelineHealthMetric(
            label="Evidence quality",
            score=evidence_score,
            status_label=_health_status_label(evidence_score),
            detail=evidence_detail,
            manual_url=reverse("applications:application_list"),
        ),
        PipelineHealthMetric(
            label="Follow-up discipline",
            score=follow_up_score,
            status_label=_health_status_label(follow_up_score),
            detail=follow_up_detail,
            manual_url=reverse("followups:followup_list"),
        ),
        PipelineHealthMetric(
            label="Interview readiness",
            score=interview_score,
            status_label=_health_status_label(interview_score),
            detail=interview_detail,
            manual_url=reverse("interviews:interview_list"),
        ),
        PipelineHealthMetric(
            label="Weekly review discipline",
            score=review_score,
            status_label=_health_status_label(review_score),
            detail=review_detail,
            manual_url=week_pulse.weekly_review_url or reverse("weekly_review:weekly_review_list"),
        ),
        PipelineHealthMetric(
            label="Response conversion",
            score=response_score,
            status_label=_health_status_label(response_score),
            detail=response_detail,
            manual_url=reverse("metrics:funnel_metrics"),
        ),
    )
    return PipelineHealthMatrix(metrics=metrics)


def build_evidence_readiness_summary(user) -> EvidenceReadinessSummary:
    report = build_data_quality_report(user)
    return EvidenceReadinessSummary(
        missing_cv_versions=report.missing_cv_version_count,
        missing_job_descriptions=report.missing_job_description_count,
        missing_required_skills=report.missing_required_skills_count,
        missing_follow_up_data=report.missing_follow_up_count,
        analytics_ready_rate=report.analytics_ready_rate,
        manual_url=reverse("metrics:funnel_metrics"),
    )


def build_today_signals(user, limit: int = 8) -> list[TodaySignal]:
    actions = build_today_action_panel(user, limit=limit)
    signals = [
        TodaySignal(
            priority=action.priority,
            title=action.title,
            reason=action.reason,
            recommended_action=action.recommended_action,
            related_url=action.related_url,
        )
        for action in actions
    ]
    if not signals:
        signals.append(
            TodaySignal(
                priority="Info",
                title="Command centre clear",
                reason="No urgent manual actions detected from saved tracker records.",
                recommended_action=(
                    "Continue logging applications, daily activity, and weekly reviews manually."
                ),
                related_url=reverse("applications:application_create"),
            )
        )
    return signals


def build_signature_career_insight(user) -> SignatureCareerInsight:
    signals = build_today_signals(user, limit=8)
    summary = build_dashboard_summary(user)
    urgent = next((signal for signal in signals if signal.priority in {"High", "Medium"}), None)
    if urgent:
        return SignatureCareerInsight(
            diagnosis=urgent.title,
            best_manual_action=urgent.recommended_action,
            why_it_matters=urgent.reason,
            manual_url=urgent.related_url,
        )
    return SignatureCareerInsight(
        diagnosis=summary.diagnosis_title,
        best_manual_action=summary.recommended_action,
        why_it_matters=summary.diagnosis_explanation,
        manual_url=reverse("metrics:funnel_metrics"),
    )


def build_funnel_snapshot(user) -> FunnelSnapshot:
    metrics = build_funnel_metrics(user)
    return FunnelSnapshot(
        applications=metrics.total_applications,
        responses=metrics.response_count,
        interviews=metrics.interview_count,
        offers=metrics.offer_count,
    )


def build_weekly_operating_pipeline() -> tuple[WeeklyOperatingStep, ...]:
    return (
        WeeklyOperatingStep(
            step="Capture",
            label="Capture activity",
            description="Record applications, daily logs, and recruiter evidence manually.",
            manual_url=reverse("daily_log:daily_log_create"),
        ),
        WeeklyOperatingStep(
            step="Analyze",
            label="Analyze funnel",
            description="Review funnel metrics and rule-based diagnosis from saved records.",
            manual_url=reverse("metrics:funnel_metrics"),
        ),
        WeeklyOperatingStep(
            step="Decide",
            label="Decide next moves",
            description="Use Smart Review to compare fit and readiness before applying.",
            manual_url=reverse("job_intelligence:smart_review"),
        ),
        WeeklyOperatingStep(
            step="Track",
            label="Track pipeline",
            description="Maintain application records, follow-ups, and interview prep manually.",
            manual_url=reverse("applications:application_list"),
        ),
        WeeklyOperatingStep(
            step="Review",
            label="Review the week",
            description="Complete a manual weekly review and compare with advisory coach output.",
            manual_url=reverse("weekly_review:weekly_review_create"),
        ),
        WeeklyOperatingStep(
            step="Improve",
            label="Improve next week",
            description="Read advisory weekly coach guidance and choose one manual improvement.",
            manual_url=reverse("ai_agents:weekly_coach"),
        ),
    )


def build_recent_activity_timeline(user, limit: int = 5) -> list[RecentActivityItem]:
    items: list[RecentActivityItem] = []

    latest_application = (
        JobApplication.objects.filter(user=user).order_by("-date_applied", "-created_at").first()
    )
    if latest_application:
        items.append(
            RecentActivityItem(
                activity_type="Application",
                title=latest_application.company_name,
                detail=latest_application.job_title,
                occurred_at_label=str(latest_application.date_applied),
                related_url=latest_application.get_absolute_url(),
            )
        )

    latest_log = DailyLog.objects.filter(user=user).order_by("-log_date").first()
    if latest_log:
        items.append(
            RecentActivityItem(
                activity_type="Daily Log",
                title=str(latest_log.log_date),
                detail=(
                    f"Target {latest_log.target_applications} / "
                    f"Actual {latest_log.actual_applications}"
                ),
                occurred_at_label=str(latest_log.log_date),
                related_url=latest_log.get_absolute_url(),
            )
        )

    latest_review = WeeklyReview.objects.filter(user=user).order_by("-week_ending").first()
    if latest_review:
        items.append(
            RecentActivityItem(
                activity_type="Weekly Review",
                title=f"Week ending {latest_review.week_ending}",
                detail=latest_review.get_diagnosis_display(),
                occurred_at_label=str(latest_review.week_ending),
                related_url=latest_review.get_absolute_url(),
            )
        )

    latest_email = (
        RecruiterEmail.objects.filter(application__user=user)
        .select_related("application")
        .order_by("-date_received", "-created_at")
        .first()
    )
    if latest_email:
        subject = latest_email.subject or "Recruiter email"
        items.append(
            RecentActivityItem(
                activity_type="Recruiter Email",
                title=subject,
                detail=latest_email.application.company_name if latest_email.application else "",
                occurred_at_label=timezone.localtime(latest_email.date_received).strftime(
                    "%d %b %Y"
                ),
                related_url=reverse("recruiter_emails:detail", kwargs={"pk": latest_email.pk}),
            )
        )

    latest_interview = (
        InterviewPrep.objects.filter(user=user)
        .select_related("application")
        .order_by("-interview_date", "-created_at")
        .first()
    )
    if latest_interview:
        items.append(
            RecentActivityItem(
                activity_type="Interview Prep",
                title=latest_interview.application.company_name,
                detail=(
                    f"{latest_interview.get_stage_display()} on "
                    f"{latest_interview.interview_date}"
                ),
                occurred_at_label=str(latest_interview.interview_date),
                related_url=latest_interview.get_absolute_url(),
            )
        )

    return items[:limit]


def build_dashboard_context(user) -> dict:
    summary = build_dashboard_summary(user)
    return {
        "summary": summary,
        "signature_insight": build_signature_career_insight(user),
        "week_pulse": build_week_pulse(user),
        "pipeline_health": build_pipeline_health_matrix(user),
        "evidence_readiness": build_evidence_readiness_summary(user),
        "today_signals": build_today_signals(user),
        "today_action_panel": build_today_action_panel(user),
        "funnel_snapshot": build_funnel_snapshot(user),
        "weekly_operating_pipeline": build_weekly_operating_pipeline(),
        "recent_activity_timeline": build_recent_activity_timeline(user),
        "recent_applications": get_recent_applications(user),
        "recent_daily_logs": get_recent_daily_logs(user),
        "recent_weekly_reviews": get_recent_weekly_reviews(user),
    }

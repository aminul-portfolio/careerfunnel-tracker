from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from apps.applications.choices import ApplicationStatus, FollowUpStatus
from apps.applications.models import JobApplication
from apps.daily_log.models import DailyLog
from apps.interviews.choices import InterviewOutcome
from apps.interviews.models import InterviewPrep
from apps.metrics.services import build_funnel_metrics, diagnose_funnel
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


def build_dashboard_context(user) -> dict:
    return {
        "summary": build_dashboard_summary(user),
        "recent_applications": get_recent_applications(user),
        "recent_daily_logs": get_recent_daily_logs(user),
        "recent_weekly_reviews": get_recent_weekly_reviews(user),
    }

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from apps.applications.choices import ApplicationStatus
from apps.applications.models import JobApplication
from apps.daily_log.models import DailyLog
from apps.metrics.services import build_funnel_metrics, diagnose_funnel
from apps.weekly_review.models import WeeklyReview


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


def build_dashboard_context(user) -> dict:
    return {
        "summary": build_dashboard_summary(user),
        "recent_applications": get_recent_applications(user),
        "recent_daily_logs": get_recent_daily_logs(user),
        "recent_weekly_reviews": get_recent_weekly_reviews(user),
    }

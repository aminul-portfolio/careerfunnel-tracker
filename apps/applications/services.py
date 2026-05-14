from __future__ import annotations

from dataclasses import dataclass

from django.db.models import Count

from .choices import ApplicationStatus
from .selectors import get_user_applications


@dataclass(frozen=True)
class ApplicationSummary:
    total_applications: int
    submitted_count: int
    acknowledged_count: int
    screening_call_count: int
    technical_screen_count: int
    interview_count: int
    offer_count: int
    rejected_count: int
    auto_rejected_count: int
    no_response_count: int


def build_application_summary(user) -> ApplicationSummary:
    applications = get_user_applications(user)
    status_counts = applications.values("status").annotate(total=Count("id"))
    count_map = {row["status"]: row["total"] for row in status_counts}
    return ApplicationSummary(
        total_applications=applications.count(),
        submitted_count=count_map.get(ApplicationStatus.SUBMITTED, 0),
        acknowledged_count=count_map.get(ApplicationStatus.ACKNOWLEDGED, 0),
        screening_call_count=count_map.get(ApplicationStatus.SCREENING_CALL, 0),
        technical_screen_count=count_map.get(ApplicationStatus.TECHNICAL_SCREEN, 0),
        interview_count=count_map.get(ApplicationStatus.INTERVIEW, 0),
        offer_count=count_map.get(ApplicationStatus.OFFER, 0),
        rejected_count=count_map.get(ApplicationStatus.REJECTED, 0),
        auto_rejected_count=count_map.get(ApplicationStatus.AUTO_REJECTED, 0),
        no_response_count=count_map.get(ApplicationStatus.NO_RESPONSE, 0),
    )


def calculate_response_rate(user) -> float:
    applications = get_user_applications(user)
    total = applications.count()
    if total == 0:
        return 0.0
    response_statuses = [
        ApplicationStatus.ACKNOWLEDGED,
        ApplicationStatus.SCREENING_CALL,
        ApplicationStatus.TECHNICAL_SCREEN,
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.OFFER,
        ApplicationStatus.REJECTED,
        ApplicationStatus.AUTO_REJECTED,
    ]
    response_count = applications.filter(status__in=response_statuses).count()
    return round((response_count / total) * 100, 2)


def calculate_interview_rate(user) -> float:
    applications = get_user_applications(user)
    total = applications.count()
    if total == 0:
        return 0.0
    interview_count = applications.filter(
        status__in=[ApplicationStatus.INTERVIEW, ApplicationStatus.OFFER],
    ).count()
    return round((interview_count / total) * 100, 2)


def calculate_offer_rate(user) -> float:
    applications = get_user_applications(user)
    total = applications.count()
    if total == 0:
        return 0.0
    offer_count = applications.filter(status=ApplicationStatus.OFFER).count()
    return round((offer_count / total) * 100, 2)


def get_status_badge_class(status: str) -> str:
    status_map = {
        ApplicationStatus.SUBMITTED: "badge-neutral",
        ApplicationStatus.NO_RESPONSE: "badge-muted",
        ApplicationStatus.ACKNOWLEDGED: "badge-info",
        ApplicationStatus.SCREENING_CALL: "badge-primary",
        ApplicationStatus.TECHNICAL_SCREEN: "badge-warning",
        ApplicationStatus.INTERVIEW: "badge-warning",
        ApplicationStatus.OFFER: "badge-success",
        ApplicationStatus.REJECTED: "badge-danger",
        ApplicationStatus.AUTO_REJECTED: "badge-danger",
        ApplicationStatus.WITHDREW: "badge-muted",
    }
    return status_map.get(status, "badge-neutral")


def build_application_table_rows(applications):
    return [
        {
            "application": application,
            "badge_class": get_status_badge_class(application.status),
            "days_to_response": application.days_to_response,
        }
        for application in applications
    ]

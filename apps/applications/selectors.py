from django.db.models import QuerySet

from .choices import ApplicationStatus
from .models import JobApplication


def get_user_applications(user) -> QuerySet[JobApplication]:
    return JobApplication.objects.filter(user=user)


def get_recent_applications(user, limit: int = 10) -> QuerySet[JobApplication]:
    return get_user_applications(user)[:limit]


def get_applications_by_status(user, status: str) -> QuerySet[JobApplication]:
    return get_user_applications(user).filter(status=status)


def get_active_applications(user) -> QuerySet[JobApplication]:
    closed_statuses = [ApplicationStatus.REJECTED, ApplicationStatus.AUTO_REJECTED, ApplicationStatus.WITHDREW]
    return get_user_applications(user).exclude(status__in=closed_statuses)


def get_responded_applications(user) -> QuerySet[JobApplication]:
    response_statuses = [
        ApplicationStatus.ACKNOWLEDGED,
        ApplicationStatus.SCREENING_CALL,
        ApplicationStatus.TECHNICAL_SCREEN,
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.OFFER,
        ApplicationStatus.REJECTED,
        ApplicationStatus.AUTO_REJECTED,
    ]
    return get_user_applications(user).filter(status__in=response_statuses)

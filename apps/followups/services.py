from django.utils import timezone

from apps.applications.choices import FollowUpStatus
from apps.applications.models import JobApplication


def get_followup_applications(user):
    return JobApplication.objects.filter(user=user).exclude(follow_up_date__isnull=True).order_by("follow_up_date")


def get_due_followups(user):
    return get_followup_applications(user).filter(
        follow_up_date__lte=timezone.localdate(),
    ).exclude(
        follow_up_status__in=[FollowUpStatus.SENT, FollowUpStatus.RESPONDED, FollowUpStatus.NOT_NEEDED]
    )


def mark_followup_sent(application):
    application.follow_up_status = FollowUpStatus.SENT
    application.last_contacted_date = timezone.localdate()
    application.save(update_fields=["follow_up_status", "last_contacted_date", "updated_at"])
    return application

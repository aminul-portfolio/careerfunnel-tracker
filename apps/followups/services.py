from dataclasses import dataclass

from django.utils import timezone
from django.utils.formats import date_format

from apps.applications.choices import FollowUpStatus
from apps.applications.models import JobApplication


@dataclass(frozen=True)
class FollowupEmailDraft:
    subject: str
    body: str
    guidance: str
    recipient_email: str | None
    copy_ready: bool


def get_followup_applications(user):
    return (
        JobApplication.objects.filter(user=user)
        .exclude(follow_up_date__isnull=True)
        .order_by("follow_up_date")
    )


def get_due_followups(user):
    return get_followup_applications(user).filter(
        follow_up_date__lte=timezone.localdate(),
    ).exclude(
        follow_up_status__in=[
            FollowUpStatus.SENT,
            FollowUpStatus.RESPONDED,
            FollowUpStatus.NOT_NEEDED,
        ]
    )


def mark_followup_sent(application):
    application.follow_up_status = FollowUpStatus.SENT
    application.last_contacted_date = timezone.localdate()
    application.save(update_fields=["follow_up_status", "last_contacted_date", "updated_at"])
    return application


def build_followup_email_draft(application):
    applied_date = date_format(application.date_applied, "F j, Y")
    greeting = f"Dear {application.contact_name}," if application.contact_name else "Hello,"

    subject = f"Follow-up on {application.job_title} application at {application.company_name}"
    body = "\n\n".join(
        [
            greeting,
            (
                f"I hope you are well. I applied for the {application.job_title} "
                f"position at {application.company_name} on {applied_date} and "
                "wanted to follow up on my application."
            ),
            (
                "I remain interested in the role and would welcome any update you "
                "are able to share about the hiring process."
            ),
            "Thank you for your time and consideration.",
            "Kind regards,",
        ]
    )
    guidance = (
        "Manual draft only. Review the message, confirm the recipient, and copy it "
        "into your email client if you decide to send it."
    )

    return FollowupEmailDraft(
        subject=subject,
        body=body,
        guidance=guidance,
        recipient_email=application.contact_email or None,
        copy_ready=True,
    )

from django.db import models


class EmailType(models.TextChoices):
    UNKNOWN = "unknown", "Unknown"
    ACKNOWLEDGEMENT = "acknowledgement", "Application Acknowledgement"
    INTEREST = "interest", "Recruiter Interest"
    NEW_OPPORTUNITY = "new_opportunity", "New Opportunity"
    AVAILABILITY_REQUEST = "availability_request", "Availability Request"
    SCREENING_INVITE = "screening_invite", "Screening Call Invite"
    INTERVIEW_INVITE = "interview_invite", "Interview Invite"
    RESCHEDULE_OR_CANCELLATION = "reschedule_or_cancellation", "Reschedule or Cancellation"
    TASK_OR_TEST = "task_or_test", "Task or Test Request"
    CV_REQUEST = "cv_request", "CV or Portfolio Request"
    DOCUMENT_REQUEST = "document_request", "Document Request"
    SALARY_QUESTION = "salary_question", "Salary Question"
    RIGHT_TO_WORK_QUESTION = "right_to_work_question", "Right-to-Work Question"
    LOCATION_WORK_MODE_QUESTION = (
        "location_work_mode_question",
        "Location or Work Mode Question",
    )
    REJECTION = "rejection", "Rejection"
    ROLE_CLOSED_OR_ON_HOLD = "role_closed_or_on_hold", "Role Closed or On Hold"
    OFFER_OR_NEXT_STEPS = "offer_or_next_steps", "Offer or Next Steps"
    OTHER = "other", "Other"


class ReplyStatus(models.TextChoices):
    DRAFTED = "drafted", "Draft ready"
    NEEDS_REVIEW = "needs_review", "Needs review"
    NOT_REQUIRED = "not_required", "No reply required"
    SENT_MANUALLY = "sent_manually", "Sent manually"
    ARCHIVED = "archived", "Archived"


class ImportSource(models.TextChoices):
    MANUAL = "manual", "Manual paste"
    # Reserved for future Sprint 32+ read-only user-triggered import.
    # Sprint 28A is manual paste only.
    GMAIL = "gmail", "Gmail API import"

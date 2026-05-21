from django.db import models

from .choices import EmailType, ImportSource, ReplyStatus


class RecruiterEmail(models.Model):
    # Model allows null for future unlinked Gmail imports, but Sprint 28A forms
    # will require an application.
    application = models.ForeignKey(
        "applications.JobApplication",
        on_delete=models.CASCADE,
        related_name="recruiter_emails",
        null=True,
        blank=True,
    )
    subject = models.CharField(max_length=300, blank=True)
    sender_name = models.CharField(max_length=160, blank=True)
    sender_email = models.EmailField(blank=True)
    body = models.TextField()
    date_received = models.DateTimeField()
    email_type = models.CharField(
        max_length=40,
        choices=EmailType.choices,
        default=EmailType.UNKNOWN,
    )
    matched_signals = models.TextField(blank=True)
    classification_rationale = models.CharField(max_length=300, blank=True)
    reply_draft = models.TextField(blank=True)
    reply_status = models.CharField(
        max_length=20,
        choices=ReplyStatus.choices,
        default=ReplyStatus.NEEDS_REVIEW,
    )
    requires_reply = models.BooleanField(default=True)
    action_due_at = models.DateTimeField(null=True, blank=True)
    suggested_application_status = models.CharField(max_length=40, blank=True)
    import_source = models.CharField(
        max_length=20,
        choices=ImportSource.choices,
        default=ImportSource.MANUAL,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date_received", "-created_at"]
        verbose_name = "Recruiter email"
        verbose_name_plural = "Recruiter emails"

    def __str__(self):
        if self.subject:
            return self.subject
        if self.sender_email:
            return self.sender_email
        return self.get_email_type_display()

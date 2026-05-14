from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from .choices import (
    ApplicationSource,
    ApplicationStatus,
    FollowUpStatus,
    PipelineStage,
    RoleFit,
    WorkType,
)


class JobApplication(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="job_applications",
    )
    company_name = models.CharField(max_length=160)
    job_title = models.CharField(max_length=180)
    job_url = models.URLField(blank=True)
    location = models.CharField(max_length=160, blank=True)
    work_type = models.CharField(
        max_length=20,
        choices=WorkType.choices,
        default=WorkType.UNKNOWN,
    )
    salary_range = models.CharField(max_length=120, blank=True)
    source = models.CharField(
        max_length=40,
        choices=ApplicationSource.choices,
        default=ApplicationSource.OTHER,
    )
    role_fit = models.CharField(
        max_length=20,
        choices=RoleFit.choices,
        default=RoleFit.UNKNOWN,
    )
    experience_level = models.CharField(
        max_length=120,
        blank=True,
        help_text="Example: graduate, junior, 0-2 years, 3+ years",
    )
    required_skills = models.TextField(
        blank=True,
        help_text="Paste key skills from the job description.",
    )
    job_description = models.TextField(
        blank=True,
        help_text="Optional short job description or copied requirements.",
    )

    date_applied = models.DateField()
    status = models.CharField(
        max_length=40,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.SUBMITTED,
    )
    pipeline_stage = models.CharField(
        max_length=40,
        choices=PipelineStage.choices,
        default=PipelineStage.JOB_FOUND,
    )
    response_date = models.DateField(blank=True, null=True)

    cv_version = models.CharField(max_length=120, blank=True)
    cover_letter_version = models.CharField(max_length=120, blank=True)
    is_cv_tailored = models.BooleanField(default=False)
    is_cover_letter_tailored = models.BooleanField(default=False)
    portfolio_project_included = models.BooleanField(default=False)
    company_researched = models.BooleanField(default=False)

    follow_up_date = models.DateField(blank=True, null=True)
    follow_up_status = models.CharField(
        max_length=30,
        choices=FollowUpStatus.choices,
        default=FollowUpStatus.NOT_SET,
    )
    last_contacted_date = models.DateField(blank=True, null=True)
    next_action = models.CharField(max_length=240, blank=True)

    contact_name = models.CharField(max_length=160, blank=True)
    contact_email = models.EmailField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date_applied", "-created_at"]
        verbose_name = "Job application"
        verbose_name_plural = "Job applications"

    def __str__(self):
        return f"{self.company_name} — {self.job_title}"

    def get_absolute_url(self):
        return reverse("applications:application_detail", kwargs={"pk": self.pk})

    @property
    def days_to_response(self):
        if not self.response_date:
            return None
        return (self.response_date - self.date_applied).days

    @property
    def has_response(self):
        response_statuses = {
            ApplicationStatus.ACKNOWLEDGED,
            ApplicationStatus.SCREENING_CALL,
            ApplicationStatus.TECHNICAL_SCREEN,
            ApplicationStatus.INTERVIEW,
            ApplicationStatus.OFFER,
            ApplicationStatus.REJECTED,
            ApplicationStatus.AUTO_REJECTED,
        }
        return self.status in response_statuses or self.response_date is not None

    @property
    def is_follow_up_due(self):
        if not self.follow_up_date:
            return False
        if self.follow_up_status in {
            FollowUpStatus.SENT,
            FollowUpStatus.RESPONDED,
            FollowUpStatus.NOT_NEEDED,
        }:
            return False
        return self.follow_up_date <= timezone.localdate()

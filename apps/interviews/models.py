from django.conf import settings
from django.db import models
from django.urls import reverse

from apps.applications.models import JobApplication

from .choices import InterviewOutcome, InterviewStage


class InterviewPrep(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="interview_preps",
    )
    application = models.ForeignKey(
        JobApplication,
        on_delete=models.CASCADE,
        related_name="interview_preps",
    )
    interview_date = models.DateField()
    stage = models.CharField(
        max_length=30,
        choices=InterviewStage.choices,
        default=InterviewStage.SCREENING,
    )
    outcome = models.CharField(
        max_length=30,
        choices=InterviewOutcome.choices,
        default=InterviewOutcome.SCHEDULED,
    )
    interviewer_names = models.CharField(max_length=240, blank=True)
    expected_topics = models.TextField(blank=True)
    projects_to_mention = models.TextField(blank=True)
    questions_to_prepare = models.TextField(blank=True)
    profile_answer_prepared = models.BooleanField(default=False)
    company_answer_prepared = models.BooleanField(default=False)
    project_walkthrough_prepared = models.BooleanField(default=False)
    sql_practice_done = models.BooleanField(default=False)
    python_practice_done = models.BooleanField(default=False)
    star_examples_prepared = models.BooleanField(default=False)
    questions_for_employer_prepared = models.BooleanField(default=False)
    reflection = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["interview_date", "created_at"]

    def __str__(self):
        return f"{self.application.company_name} — {self.get_stage_display()}"

    def get_absolute_url(self):
        return reverse("interviews:interview_detail", kwargs={"pk": self.pk})

    @property
    def readiness_score(self):
        checks = [
            self.profile_answer_prepared,
            self.company_answer_prepared,
            self.project_walkthrough_prepared,
            self.sql_practice_done,
            self.python_practice_done,
            self.star_examples_prepared,
            self.questions_for_employer_prepared,
        ]
        return int((sum(1 for item in checks if item) / len(checks)) * 100)

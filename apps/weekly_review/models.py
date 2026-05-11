from django.conf import settings
from django.db import models
from django.urls import reverse

from .choices import FunnelDiagnosis, WeeklyMood


class WeeklyReview(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="weekly_reviews")
    week_starting = models.DateField()
    week_ending = models.DateField()
    target_applications = models.PositiveIntegerField(default=0)
    actual_applications = models.PositiveIntegerField(default=0)
    responses_received = models.PositiveIntegerField(default=0)
    screening_calls = models.PositiveIntegerField(default=0)
    technical_screens = models.PositiveIntegerField(default=0)
    interviews = models.PositiveIntegerField(default=0)
    offers = models.PositiveIntegerField(default=0)
    rejections = models.PositiveIntegerField(default=0)
    diagnosis = models.CharField(max_length=40, choices=FunnelDiagnosis.choices, default=FunnelDiagnosis.UNKNOWN)
    mood = models.CharField(max_length=20, choices=WeeklyMood.choices, default=WeeklyMood.MIXED)
    what_worked = models.TextField(blank=True)
    what_blocked = models.TextField(blank=True)
    lessons_learned = models.TextField(blank=True)
    change_next_week = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-week_ending"]
        unique_together = ["user", "week_ending"]
        verbose_name = "Weekly review"
        verbose_name_plural = "Weekly reviews"

    def __str__(self):
        return f"{self.user} — week ending {self.week_ending}"

    def get_absolute_url(self):
        return reverse("weekly_review:weekly_review_detail", kwargs={"pk": self.pk})

    @property
    def application_variance(self):
        return self.actual_applications - self.target_applications

    @property
    def target_met(self):
        return self.actual_applications >= self.target_applications

    @property
    def response_rate(self):
        if self.actual_applications == 0:
            return 0.0
        return round((self.responses_received / self.actual_applications) * 100, 2)

    @property
    def screening_rate(self):
        if self.actual_applications == 0:
            return 0.0
        return round((self.screening_calls / self.actual_applications) * 100, 2)

    @property
    def interview_rate(self):
        if self.actual_applications == 0:
            return 0.0
        return round((self.interviews / self.actual_applications) * 100, 2)

    @property
    def offer_rate(self):
        if self.actual_applications == 0:
            return 0.0
        return round((self.offers / self.actual_applications) * 100, 2)

from django.conf import settings
from django.db import models
from django.urls import reverse


class DailyLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="daily_logs",
    )
    log_date = models.DateField()
    target_applications = models.PositiveIntegerField(default=0)
    actual_applications = models.PositiveIntegerField(default=0)
    cover_letters_drafted = models.PositiveIntegerField(default=0)
    responses_received = models.PositiveIntegerField(default=0)
    calls_received = models.PositiveIntegerField(default=0)
    hours_spent = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    energy_level = models.PositiveSmallIntegerField(default=3)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-log_date"]
        unique_together = ["user", "log_date"]
        verbose_name = "Daily log"
        verbose_name_plural = "Daily logs"

    def __str__(self):
        return f"{self.user} — {self.log_date}"

    def get_absolute_url(self):
        return reverse("daily_log:daily_log_detail", kwargs={"pk": self.pk})

    @property
    def variance(self):
        return self.actual_applications - self.target_applications

    @property
    def target_met(self):
        return self.actual_applications >= self.target_applications

    @property
    def activity_signal(self):
        if self.target_applications == 0 and self.actual_applications == 0:
            return "No target set"
        if self.actual_applications == 0 and self.target_applications > 0:
            return "No action taken"
        if self.actual_applications < self.target_applications:
            return "Below target"
        if self.actual_applications == self.target_applications:
            return "Target met"
        return "Above target"

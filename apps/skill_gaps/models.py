from django.conf import settings
from django.db import models

from apps.applications.models import JobApplication


class SkillGapStage(models.TextChoices):
    APPLICATION = "application", "Application"
    SCREENING = "screening", "Screening"
    TECHNICAL = "technical", "Technical"
    INTERVIEW = "interview", "Interview"


class SkillTier(models.TextChoices):
    MISSING = "missing", "Missing"
    EMERGING = "emerging", "Emerging"
    PRACTICING = "practicing", "Practicing"
    DEMONSTRATED = "demonstrated", "Demonstrated"


class SkillGapPriority(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


class SkillGapIdentifiedBy(models.TextChoices):
    MANUAL = "manual", "Manual review"
    RULE_BASED = "rule_based", "Rule-based review"
    SELF_REVIEW = "self_review", "Self review"


class SkillGapLongTermGoal(models.TextChoices):
    DATA_ANALYST = "data_analyst", "Data Analyst"
    BI_ANALYST = "bi_analyst", "BI Analyst"
    ANALYTICS_ENGINEER = "analytics_engineer", "Analytics Engineer"
    DATA_ENGINEER = "data_engineer", "Data Engineer"
    GENERAL = "general", "General"


class ApplicationSkillGap(models.Model):
    application = models.ForeignKey(
        JobApplication,
        on_delete=models.CASCADE,
        related_name="skill_gaps",
    )
    stage = models.CharField(max_length=40, choices=SkillGapStage.choices)
    skill_name = models.CharField(max_length=120)
    current_tier = models.CharField(max_length=40, choices=SkillTier.choices)
    priority = models.CharField(max_length=20, choices=SkillGapPriority.choices)
    goal_weight = models.DecimalField(max_digits=6, decimal_places=2, default=1.0)
    failure_count = models.PositiveIntegerField(default=0)
    stage_weight = models.DecimalField(max_digits=6, decimal_places=2, default=1.0)
    priority_score = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    jd_requirement = models.TextField(blank=True)
    identified_by = models.CharField(
        max_length=40,
        choices=SkillGapIdentifiedBy.choices,
        default=SkillGapIdentifiedBy.MANUAL,
    )
    suggested_action = models.TextField(blank=True)
    long_term_goal = models.CharField(
        max_length=40,
        choices=SkillGapLongTermGoal.choices,
        default=SkillGapLongTermGoal.GENERAL,
    )
    resolved = models.BooleanField(default=False)
    resolved_date = models.DateField(blank=True, null=True)
    resolved_tier = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-priority_score", "-updated_at"]
        verbose_name = "Application skill gap"
        verbose_name_plural = "Application skill gaps"
        constraints = [
            models.UniqueConstraint(
                fields=["application", "skill_name", "stage"],
                name="uniq_application_skill_gap_stage",
            ),
        ]
        indexes = [
            models.Index(fields=["application"], name="skill_gap_application_idx"),
            models.Index(fields=["stage"], name="skill_gap_stage_idx"),
            models.Index(fields=["priority"], name="skill_gap_priority_idx"),
            models.Index(fields=["skill_name"], name="skill_gap_skill_name_idx"),
            models.Index(fields=["resolved"], name="skill_gap_resolved_idx"),
        ]

    def __str__(self):
        return f"{self.skill_name} ({self.get_stage_display()}) — {self.application}"


class ExplanationRequestCounter(models.Model):
    """Per-user daily request-count governance for advisory explanations."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="explanation_request_counters",
    )
    window_date = models.DateField()
    request_count = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Explanation request counter"
        verbose_name_plural = "Explanation request counters"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "window_date"],
                name="uniq_explanation_request_counter_user_date",
            ),
            models.CheckConstraint(
                condition=models.Q(request_count__gte=1),
                name="chk_explanation_request_counter_count_gte_1",
            ),
        ]

    def __str__(self):
        return (
            f"ExplanationRequestCounter(user={self.user_id}, "
            f"window_date={self.window_date}, request_count={self.request_count})"
        )

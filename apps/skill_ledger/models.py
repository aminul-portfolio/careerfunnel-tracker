from django.db import models


class SkillEntry(models.Model):
    class EvidenceLevel(models.TextChoices):
        VERIFIED = "VERIFIED", "Verified - portfolio evidence confirmed"
        LEARNING_TARGET = "LEARNING_TARGET", "Learning Target - developing, not yet evidenced"
        STUDYING = "STUDYING", "Studying - personal study only"
        NO_EVIDENCE = "NO_EVIDENCE", "No Evidence - gap identified, not yet started"

    class Category(models.TextChoices):
        DATA_ENGINEERING = "data_engineering", "Data Engineering"
        ANALYTICS_ENGINEERING = "analytics_engineering", "Analytics Engineering"
        BUSINESS_INTELLIGENCE = "business_intelligence", "Business Intelligence"
        PROGRAMMING = "programming", "Programming"
        CLOUD = "cloud", "Cloud Platform"
        GOVERNANCE = "governance", "Data Governance / AI Governance"
        DOMAIN = "domain", "Domain Knowledge"
        OTHER = "other", "Other"

    class Visibility(models.TextChoices):
        PRIVATE = "private", "Private"
        PUBLIC = "public", "Public"

    skill_name = models.CharField(max_length=255)
    category = models.CharField(
        max_length=100,
        choices=Category.choices,
        default=Category.OTHER,
    )
    evidence_level = models.CharField(
        max_length=30,
        choices=EvidenceLevel.choices,
        default=EvidenceLevel.NO_EVIDENCE,
    )
    sprint_reference = models.CharField(max_length=100, blank=True)
    project_link = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
    )
    date_added = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Skill Entry"
        verbose_name_plural = "Skill Entries"

    def __str__(self):
        return f"{self.skill_name} ({self.get_evidence_level_display()})"

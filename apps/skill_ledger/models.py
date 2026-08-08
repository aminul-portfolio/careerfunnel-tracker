from django.conf import settings
from django.db import models


class SkillEntryQuerySet(models.QuerySet):
    def for_user(self, user):
        """Return only SkillEntry rows owned by a persisted authenticated user."""
        if user is None:
            return self.none()
        if not getattr(user, "is_authenticated", False):
            return self.none()
        user_pk = getattr(user, "pk", None)
        if user_pk is None:
            return self.none()
        return self.filter(user_id=user_pk)


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

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="skill_entries",
    )
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

    objects = SkillEntryQuerySet.as_manager()

    class Meta:
        verbose_name = "Skill Entry"
        verbose_name_plural = "Skill Entries"

    def __str__(self):
        return f"{self.skill_name} ({self.get_evidence_level_display()})"


class EvidenceEmbedding(models.Model):
    """Offline embedding cache row for one SkillEntry + provider + model."""

    skill_entry = models.ForeignKey(
        SkillEntry,
        on_delete=models.CASCADE,
        related_name="evidence_embeddings",
    )
    embedding_provider = models.CharField(max_length=100)
    embedding_model = models.CharField(max_length=100)
    content_sha256 = models.CharField(max_length=64)
    embedding_dimensions = models.PositiveIntegerField()
    embedding_vector = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Evidence Embedding"
        verbose_name_plural = "Evidence Embeddings"
        constraints = [
            models.UniqueConstraint(
                fields=["skill_entry", "embedding_provider", "embedding_model"],
                name="uniq_evidence_embedding_entry_provider_model",
            ),
        ]

    def __str__(self):
        return (
            f"EvidenceEmbedding(skill_entry={self.skill_entry_id}, "
            f"provider={self.embedding_provider}, model={self.embedding_model})"
        )

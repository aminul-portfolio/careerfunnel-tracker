# Generated manually for Sprint 119 Phase 1 EvidenceEmbedding cache.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("skill_ledger", "0003_require_skillentry_user"),
    ]

    operations = [
        migrations.CreateModel(
            name="EvidenceEmbedding",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("embedding_provider", models.CharField(max_length=100)),
                ("embedding_model", models.CharField(max_length=100)),
                ("content_sha256", models.CharField(max_length=64)),
                ("embedding_dimensions", models.PositiveIntegerField()),
                ("embedding_vector", models.JSONField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "skill_entry",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="evidence_embeddings",
                        to="skill_ledger.skillentry",
                    ),
                ),
            ],
            options={
                "verbose_name": "Evidence Embedding",
                "verbose_name_plural": "Evidence Embeddings",
                "constraints": [
                    models.UniqueConstraint(
                        fields=(
                            "skill_entry",
                            "embedding_provider",
                            "embedding_model",
                        ),
                        name="uniq_evidence_embedding_entry_provider_model",
                    ),
                ],
            },
        ),
    ]

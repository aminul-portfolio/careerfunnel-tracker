"""EvidenceEmbedding cache currency and explicit synchronous regeneration.

A row is CURRENT only when stored content_sha256 matches the fresh
canonical source SHA-256. Stale rows are never auto-deleted or refreshed
in the background.
"""

from __future__ import annotations

import json
from typing import Literal

from .embedding_provider import (
    DeterministicOfflineEmbeddingProvider,
    EmbeddingProvider,
    EmbeddingProviderError,
    validate_embedding_vector,
)
from .models import EvidenceEmbedding, SkillEntry
from .rag_corpus import (
    build_canonical_source_representation,
    canonical_json_bytes,
    content_sha256_for_entry,
)

CacheCurrency = Literal["CURRENT", "STALE"]

CACHE_STATUS_CURRENT: CacheCurrency = "CURRENT"
CACHE_STATUS_STALE: CacheCurrency = "STALE"


def evaluate_cache_currency(
    embedding: EvidenceEmbedding,
    skill_entry: SkillEntry,
) -> CacheCurrency:
    """Return CURRENT when hashes match; otherwise STALE."""
    fresh_hash = content_sha256_for_entry(skill_entry)
    if embedding.content_sha256 == fresh_hash:
        return CACHE_STATUS_CURRENT
    return CACHE_STATUS_STALE


def is_cache_current(
    embedding: EvidenceEmbedding,
    skill_entry: SkillEntry,
) -> bool:
    """True only when the cache row is CURRENT for the skill entry."""
    return evaluate_cache_currency(embedding, skill_entry) == CACHE_STATUS_CURRENT


def _canonical_text_for_embedding(skill_entry: SkillEntry) -> str:
    """UTF-8 canonical JSON text used as the offline embedding input."""
    return canonical_json_bytes(
        build_canonical_source_representation(skill_entry)
    ).decode("utf-8")


def regenerate_evidence_embedding(
    skill_entry: SkillEntry,
    *,
    provider: EmbeddingProvider | None = None,
) -> EvidenceEmbedding:
    """Explicitly and synchronously upsert the cache row for one SkillEntry.

    Does not perform background refresh. Updates the single unique row for
    (skill_entry, embedding_provider, embedding_model).
    """
    active_provider: EmbeddingProvider = (
        provider or DeterministicOfflineEmbeddingProvider()
    )
    provider_name = active_provider.provider_name
    model_name = active_provider.model_name
    dimensions = active_provider.dimensions
    if not isinstance(provider_name, str) or not provider_name.strip():
        raise EmbeddingProviderError("embedding_provider name is required.")
    if not isinstance(model_name, str) or not model_name.strip():
        raise EmbeddingProviderError("embedding_model name is required.")
    if (
        isinstance(dimensions, bool)
        or not isinstance(dimensions, int)
        or dimensions < 1
    ):
        raise EmbeddingProviderError("embedding dimensions must be a positive int.")

    content_hash = content_sha256_for_entry(skill_entry)
    vector = validate_embedding_vector(
        active_provider.embed_query(_canonical_text_for_embedding(skill_entry)),
        expected_dimensions=dimensions,
    )
    # Prove JSON serialisability before persistence.
    json.dumps(vector)

    embedding, _created = EvidenceEmbedding.objects.update_or_create(
        skill_entry=skill_entry,
        embedding_provider=provider_name.strip(),
        embedding_model=model_name.strip(),
        defaults={
            "content_sha256": content_hash,
            "embedding_dimensions": dimensions,
            "embedding_vector": vector,
        },
    )
    return embedding

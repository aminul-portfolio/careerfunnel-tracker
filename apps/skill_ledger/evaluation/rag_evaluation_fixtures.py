"""Sprint 120 Phase 1: fixed-vector fixtures and CURRENT cache helpers.

Evaluation-local EmbeddingProvider only. No network, SDK, or API keys.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Sequence as TypingSequence

from apps.skill_ledger.embedding_cache import is_cache_current
from apps.skill_ledger.embedding_provider import (
    EmbeddingProviderError,
    validate_embedding_vector,
)
from apps.skill_ledger.models import EvidenceEmbedding, SkillEntry
from apps.skill_ledger.rag_corpus import content_sha256_for_entry
from apps.skill_ledger.rag_retrieval import vector_l2_norm

from .rag_evaluation_cases import EVAL_EMBEDDING_DIMENSIONS


class RagEvaluationFixtureError(ValueError):
    """Fail-closed fixture / cache helper failure."""


class FixedVectorEmbeddingProvider:
    """Evaluation-local EmbeddingProvider returning a predetermined query vector."""

    PROVIDER_NAME = "rag_eval_fixed"
    MODEL_NAME = "rag_eval_fixed_v1"
    DIMENSIONS = EVAL_EMBEDDING_DIMENSIONS

    def __init__(self, query_vector: Sequence[float]):
        validated = validate_embedding_vector(
            list(query_vector),
            expected_dimensions=self.DIMENSIONS,
        )
        if vector_l2_norm(validated) == 0.0:
            raise RagEvaluationFixtureError("query_vector must be non-zero.")
        self._query_vector = validated

    @property
    def provider_name(self) -> str:
        return self.PROVIDER_NAME

    @property
    def model_name(self) -> str:
        return self.MODEL_NAME

    @property
    def dimensions(self) -> int:
        return self.DIMENSIONS

    def embed_documents(self, texts: TypingSequence[str]) -> list[list[float]]:
        if not isinstance(texts, (list, tuple)):
            raise EmbeddingProviderError("texts must be a list or tuple of strings.")
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        if not isinstance(text, str):
            raise EmbeddingProviderError("text must be a string.")
        # Deterministic offline fixture: ignore text content; return fixed vector.
        return list(self._query_vector)


MISMATCH_PROVIDER_NAME = "rag_eval_mismatch_provider"
MISMATCH_MODEL_NAME = "rag_eval_mismatch_model"


def ensure_current_fixed_embedding_cache(
    skill_entry: SkillEntry,
    *,
    provider: FixedVectorEmbeddingProvider,
    vector: Sequence[float],
) -> EvidenceEmbedding:
    """Upsert a CURRENT EvidenceEmbedding row for a synthetic evaluation entry.

    Validates the vector, writes content_sha256_for_entry(skill_entry), and
    proves the row is CURRENT before returning.
    """
    if not isinstance(skill_entry, SkillEntry):
        raise RagEvaluationFixtureError("skill_entry must be a SkillEntry instance.")
    if not isinstance(provider, FixedVectorEmbeddingProvider):
        raise RagEvaluationFixtureError(
            "provider must be a FixedVectorEmbeddingProvider."
        )
    try:
        validated = validate_embedding_vector(
            list(vector),
            expected_dimensions=provider.dimensions,
        )
    except EmbeddingProviderError as exc:
        raise RagEvaluationFixtureError(
            "document vector failed embedding validation."
        ) from exc
    if vector_l2_norm(validated) == 0.0:
        raise RagEvaluationFixtureError("document vector must be non-zero.")

    content_hash = content_sha256_for_entry(skill_entry)
    embedding, _created = EvidenceEmbedding.objects.update_or_create(
        skill_entry=skill_entry,
        embedding_provider=provider.provider_name.strip(),
        embedding_model=provider.model_name.strip(),
        defaults={
            "content_sha256": content_hash,
            "embedding_dimensions": provider.dimensions,
            "embedding_vector": validated,
        },
    )
    if not is_cache_current(embedding, skill_entry):
        raise RagEvaluationFixtureError(
            "cache row is not CURRENT after ensure_current_fixed_embedding_cache."
        )
    return embedding


def write_stale_fixed_embedding_cache(
    skill_entry: SkillEntry,
    *,
    provider: FixedVectorEmbeddingProvider,
    vector: Sequence[float],
) -> EvidenceEmbedding:
    """Deliberately write a STALE cache row (content_sha256 mismatch)."""
    if not isinstance(provider, FixedVectorEmbeddingProvider):
        raise RagEvaluationFixtureError(
            "provider must be a FixedVectorEmbeddingProvider."
        )
    validated = validate_embedding_vector(
        list(vector),
        expected_dimensions=provider.dimensions,
    )
    if vector_l2_norm(validated) == 0.0:
        raise RagEvaluationFixtureError("document vector must be non-zero.")
    fresh = content_sha256_for_entry(skill_entry)
    stale_hash = "0" * 64
    if stale_hash == fresh:
        stale_hash = "f" * 64
    embedding, _created = EvidenceEmbedding.objects.update_or_create(
        skill_entry=skill_entry,
        embedding_provider=provider.provider_name.strip(),
        embedding_model=provider.model_name.strip(),
        defaults={
            "content_sha256": stale_hash,
            "embedding_dimensions": provider.dimensions,
            "embedding_vector": validated,
        },
    )
    if is_cache_current(embedding, skill_entry):
        raise RagEvaluationFixtureError(
            "stale fixture unexpectedly evaluated as CURRENT."
        )
    return embedding


def write_mismatched_provider_embedding_cache(
    skill_entry: SkillEntry,
    *,
    provider: FixedVectorEmbeddingProvider,
    vector: Sequence[float],
) -> EvidenceEmbedding:
    """Write a cache row under a different provider/model pair."""
    if not isinstance(provider, FixedVectorEmbeddingProvider):
        raise RagEvaluationFixtureError(
            "provider must be a FixedVectorEmbeddingProvider."
        )
    validated = validate_embedding_vector(
        list(vector),
        expected_dimensions=provider.dimensions,
    )
    if vector_l2_norm(validated) == 0.0:
        raise RagEvaluationFixtureError("document vector must be non-zero.")
    embedding, _created = EvidenceEmbedding.objects.update_or_create(
        skill_entry=skill_entry,
        embedding_provider=MISMATCH_PROVIDER_NAME,
        embedding_model=MISMATCH_MODEL_NAME,
        defaults={
            "content_sha256": content_sha256_for_entry(skill_entry),
            "embedding_dimensions": provider.dimensions,
            "embedding_vector": validated,
        },
    )
    return embedding

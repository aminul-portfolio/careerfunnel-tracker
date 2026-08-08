"""Exact cosine retrieval over ownership-scoped EvidenceEmbedding cache.

Sprint 119 Phase 2: read-only retrieval. Does not regenerate cache rows,
call live providers, or perform grounded generation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from django.db.models import Prefetch

from .embedding_provider import (
    EmbeddingProvider,
    EmbeddingProviderError,
    validate_embedding_vector,
)
from .models import EvidenceEmbedding, SkillEntry
from .rag_corpus import content_sha256_for_entry

TOP_K = 5


class EvidenceRetrievalError(ValueError):
    """Raised when retrieval inputs fail closed before ranking."""


@dataclass(frozen=True)
class RetrievedSkillEvidence:
    skill_entry_id: int
    skill_name: str
    category: str
    evidence_level: str
    sprint_reference: str
    content_sha256: str
    similarity_score: float


def vector_l2_norm(vector: Sequence[float]) -> float:
    """Exact Euclidean L2 norm using math.fsum and math.sqrt."""
    return math.sqrt(math.fsum(float(value) * float(value) for value in vector))


def exact_cosine_similarity(
    left: Sequence[float],
    right: Sequence[float],
) -> float:
    """Exact cosine similarity for equal-length finite non-zero vectors."""
    if len(left) != len(right):
        raise EvidenceRetrievalError(
            "cosine similarity requires equal-length vectors."
        )
    if len(left) < 1:
        raise EvidenceRetrievalError(
            "cosine similarity requires a non-empty vector."
        )
    left_norm = vector_l2_norm(left)
    right_norm = vector_l2_norm(right)
    if left_norm == 0.0 or right_norm == 0.0:
        raise EvidenceRetrievalError(
            "cosine similarity requires non-zero vector norms."
        )
    dot = math.fsum(float(a) * float(b) for a, b in zip(left, right, strict=True))
    return dot / (left_norm * right_norm)


def _validated_non_zero_vector(
    raw: object,
    *,
    expected_dimensions: int,
) -> list[float] | None:
    """Return a valid non-zero vector, or None when the stored row is ineligible."""
    try:
        validated = validate_embedding_vector(
            raw,
            expected_dimensions=expected_dimensions,
        )
    except EmbeddingProviderError:
        return None
    if vector_l2_norm(validated) == 0.0:
        return None
    return validated


def _validate_query_vector(
    raw: object,
    *,
    expected_dimensions: int,
) -> list[float]:
    """Validate the query embedding; fail closed on invalid or zero vectors."""
    try:
        validated = validate_embedding_vector(
            raw,
            expected_dimensions=expected_dimensions,
        )
    except EmbeddingProviderError as exc:
        raise EvidenceRetrievalError(
            "query embedding is invalid for retrieval."
        ) from exc
    if vector_l2_norm(validated) == 0.0:
        raise EvidenceRetrievalError(
            "query embedding must have a non-zero norm."
        )
    return validated


def retrieve_owned_skill_evidence(
    user,
    query: str,
    *,
    provider: EmbeddingProvider,
) -> tuple[RetrievedSkillEvidence, ...]:
    """Rank CURRENT owned EvidenceEmbedding rows by exact cosine similarity.

    Ownership originates from SkillEntry.objects.for_user(user). Missing or
    stale cache rows are skipped; they are never regenerated here.
    """
    if not isinstance(query, str) or not query.strip():
        raise EvidenceRetrievalError("query must be a non-empty string.")

    provider_name = provider.provider_name
    model_name = provider.model_name
    dimensions = provider.dimensions
    if not isinstance(provider_name, str) or not provider_name.strip():
        raise EvidenceRetrievalError("embedding provider_name is required.")
    if not isinstance(model_name, str) or not model_name.strip():
        raise EvidenceRetrievalError("embedding model_name is required.")
    if (
        isinstance(dimensions, bool)
        or not isinstance(dimensions, int)
        or dimensions < 1
    ):
        raise EvidenceRetrievalError(
            "embedding dimensions must be a positive integer."
        )

    try:
        raw_query_vector = provider.embed_query(query.strip())
    except EmbeddingProviderError as exc:
        raise EvidenceRetrievalError(
            "query embedding provider rejected the retrieval query."
        ) from exc
    query_vector = _validate_query_vector(
        raw_query_vector,
        expected_dimensions=dimensions,
    )

    owned_entries = SkillEntry.objects.for_user(user).prefetch_related(
        Prefetch(
            "evidence_embeddings",
            queryset=EvidenceEmbedding.objects.filter(
                embedding_provider=provider_name.strip(),
                embedding_model=model_name.strip(),
            ),
        )
    )

    ranked: list[tuple[float, int, RetrievedSkillEvidence]] = []
    for entry in owned_entries:
        embeddings = list(entry.evidence_embeddings.all())
        if len(embeddings) != 1:
            # UniqueConstraint guarantees at most one; zero means no match.
            continue
        embedding = embeddings[0]
        if embedding.embedding_dimensions != dimensions:
            continue
        if embedding.content_sha256 != content_sha256_for_entry(entry):
            continue
        stored_vector = _validated_non_zero_vector(
            embedding.embedding_vector,
            expected_dimensions=dimensions,
        )
        if stored_vector is None:
            continue
        score = exact_cosine_similarity(query_vector, stored_vector)
        ranked.append(
            (
                score,
                entry.pk,
                RetrievedSkillEvidence(
                    skill_entry_id=entry.pk,
                    skill_name=entry.skill_name,
                    category=entry.category,
                    evidence_level=entry.evidence_level,
                    sprint_reference=entry.sprint_reference,
                    content_sha256=embedding.content_sha256,
                    similarity_score=score,
                ),
            )
        )

    ranked.sort(key=lambda item: (-item[0], item[1]))
    return tuple(item[2] for item in ranked[:TOP_K])

"""Offline embedding provider abstraction (Sprint 119 Phase 1).

Separate from ExplanationProvider. Phase 1 ships only a deterministic
local implementation with no network, SDK, or API-key dependency.
"""

from __future__ import annotations

import hashlib
import math
from typing import Protocol, Sequence


class EmbeddingProviderError(ValueError):
    """Raised when embedding input or output fails Phase 1 validity rules."""


class EmbeddingProvider(Protocol):
    """Callable contract for document and query embeddings."""

    @property
    def provider_name(self) -> str: ...

    @property
    def model_name(self) -> str: ...

    @property
    def dimensions(self) -> int: ...

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


def validate_embedding_vector(
    vector: object,
    *,
    expected_dimensions: int,
) -> list[float]:
    """Validate a flat finite numeric vector; reject bool/NaN/Inf/bad shape."""
    if not isinstance(vector, list):
        raise EmbeddingProviderError("embedding vector must be a list.")
    if len(vector) != expected_dimensions:
        raise EmbeddingProviderError(
            "embedding vector dimensions do not match expected_dimensions."
        )
    if expected_dimensions < 1:
        raise EmbeddingProviderError("embedding dimensions must be positive.")
    validated: list[float] = []
    for index, value in enumerate(vector):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise EmbeddingProviderError(
                f"embedding vector index {index} is not a finite number."
            )
        number = float(value)
        if not math.isfinite(number):
            raise EmbeddingProviderError(
                f"embedding vector index {index} is not a finite number."
            )
        validated.append(number)
    return validated


class DeterministicOfflineEmbeddingProvider:
    """Stable hash-derived local embeddings for identical text."""

    PROVIDER_NAME = "deterministic_offline"
    MODEL_NAME = "local_hash_v1"
    DIMENSIONS = 32

    @property
    def provider_name(self) -> str:
        return self.PROVIDER_NAME

    @property
    def model_name(self) -> str:
        return self.MODEL_NAME

    @property
    def dimensions(self) -> int:
        return self.DIMENSIONS

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not isinstance(texts, (list, tuple)):
            raise EmbeddingProviderError("texts must be a list or tuple of strings.")
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        if not isinstance(text, str):
            raise EmbeddingProviderError("text must be a string.")
        vector = self._vector_from_text(text)
        return validate_embedding_vector(
            vector,
            expected_dimensions=self.DIMENSIONS,
        )

    def _vector_from_text(self, text: str) -> list[float]:
        seed = hashlib.sha256(text.encode("utf-8")).digest()
        values: list[float] = []
        counter = 0
        while len(values) < self.DIMENSIONS:
            block = hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
            for offset in range(0, len(block), 4):
                if len(values) >= self.DIMENSIONS:
                    break
                raw = int.from_bytes(block[offset : offset + 4], "big")
                # Map uint32 into (-1, 1] as a plain float (never bool).
                values.append(float((raw / 0xFFFFFFFF) * 2.0 - 1.0))
            counter += 1
        return values

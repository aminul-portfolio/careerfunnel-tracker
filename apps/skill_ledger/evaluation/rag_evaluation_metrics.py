"""Sprint 120 Phase 1: retrieval evaluation metrics (offline, pure Python).

Recall@5 is the hard gate for RETRIEVAL_QUALITY cases.
Recall@1 and MRR are advisory diagnostics only.
Recall@3 is intentionally not implemented.
"""

from __future__ import annotations

from collections.abc import Sequence


class RagEvaluationMetricError(ValueError):
    """Fail-closed metric input contract failure."""


def _normalise_id_sequence(values: Sequence[str], *, field_name: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, bytearray)):
        raise RagEvaluationMetricError(
            f"{field_name} must be a non-string sequence of strings."
        )
    if not isinstance(values, Sequence):
        raise RagEvaluationMetricError(
            f"{field_name} must be a non-string sequence of strings."
        )
    normalised: list[str] = []
    for item in values:
        if not isinstance(item, str):
            raise RagEvaluationMetricError(
                f"{field_name} must contain only strings."
            )
        if not item.strip():
            raise RagEvaluationMetricError(
                f"{field_name} items must be non-empty strings."
            )
        normalised.append(item)
    return tuple(normalised)


def recall_at_5(
    expected_relevant: Sequence[str],
    ranked_local_ids: Sequence[str],
) -> float:
    """Recall@5 = |R intersect T5| / |R| with non-empty R."""
    relevant = set(_normalise_id_sequence(expected_relevant, field_name="expected_relevant"))
    if not relevant:
        raise RagEvaluationMetricError(
            "expected_relevant must be non-empty for Recall@5."
        )
    ranked = _normalise_id_sequence(ranked_local_ids, field_name="ranked_local_ids")
    top5 = set(ranked[:5])
    hits = len(relevant.intersection(top5))
    return hits / len(relevant)


def recall_at_1(
    expected_relevant: Sequence[str],
    ranked_local_ids: Sequence[str],
) -> float:
    """Advisory Recall@1: 1.0 when the first ranked id is relevant, else 0.0."""
    relevant = set(_normalise_id_sequence(expected_relevant, field_name="expected_relevant"))
    if not relevant:
        raise RagEvaluationMetricError(
            "expected_relevant must be non-empty for Recall@1."
        )
    ranked = _normalise_id_sequence(ranked_local_ids, field_name="ranked_local_ids")
    if not ranked:
        return 0.0
    return 1.0 if ranked[0] in relevant else 0.0


def mean_reciprocal_rank(
    expected_relevant: Sequence[str],
    ranked_local_ids: Sequence[str],
) -> float:
    """Advisory MRR: 1/rank of first relevant hit, or 0.0 when absent."""
    relevant = set(_normalise_id_sequence(expected_relevant, field_name="expected_relevant"))
    if not relevant:
        raise RagEvaluationMetricError(
            "expected_relevant must be non-empty for MRR."
        )
    ranked = _normalise_id_sequence(ranked_local_ids, field_name="ranked_local_ids")
    for index, local_id in enumerate(ranked, start=1):
        if local_id in relevant:
            return 1.0 / float(index)
    return 0.0

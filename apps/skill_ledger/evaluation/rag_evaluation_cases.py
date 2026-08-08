"""Sprint 120 Phase 1: immutable Skill Ledger RAG evaluation case contracts.

Retrieval-quality and adversarial-retrieval cases only in Phase 1.
No provider, network, ORM, or filesystem access in this module.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any

from apps.skill_ledger.rag_retrieval import TOP_K

EVALUATION_VERSION = "skill_ledger_rag_eval_v1"
CASE_SCHEMA_VERSION = "skill_ledger_rag_eval_case_v1"
EVAL_EMBEDDING_DIMENSIONS = 2

_RESERVED_METADATA_KEYS = frozenset(
    {
        "timestamp",
        "created_at",
        "updated_at",
        "duration",
        "duration_seconds",
        "machine_name",
        "hostname",
        "repository_path",
        "report_path",
        "output_path",
        "proof_path",
    }
)

_WINDOWS_ABSOLUTE_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")


class RagEvalCategory(str, Enum):
    RETRIEVAL_QUALITY = "RETRIEVAL_QUALITY"
    ATTRIBUTION_SAFETY = "ATTRIBUTION_SAFETY"
    UNSUPPORTED_OUTPUT = "UNSUPPORTED_OUTPUT"
    ZERO_EVIDENCE = "ZERO_EVIDENCE"
    PROMPT_INJECTION = "PROMPT_INJECTION"
    ADVERSARIAL_RETRIEVAL = "ADVERSARIAL_RETRIEVAL"


class AdversarialRetrievalMode(str, Enum):
    CROSS_USER = "CROSS_USER"
    STALE_CACHE = "STALE_CACHE"
    MISSING_CACHE = "MISSING_CACHE"
    PROVIDER_MODEL_MISMATCH = "PROVIDER_MODEL_MISMATCH"


class RagEvaluationCaseContractError(ValueError):
    """Fail-closed validation failure for RAG evaluation case contracts."""


def _assert_absolute_path_rejected(value: str) -> None:
    if _WINDOWS_ABSOLUTE_PATH_RE.match(value):
        raise RagEvaluationCaseContractError(
            "absolute Windows path values are not permitted in evaluation case content."
        )
    if value.startswith("\\\\"):
        raise RagEvaluationCaseContractError(
            "UNC path values are not permitted in evaluation case content."
        )
    if value.startswith("//"):
        raise RagEvaluationCaseContractError(
            "network path values are not permitted in evaluation case content."
        )
    if value.startswith("/"):
        raise RagEvaluationCaseContractError(
            "absolute POSIX path values are not permitted in evaluation case content."
        )


def _canonical_string(value: object, *, field_name: str = "value") -> str:
    if not isinstance(value, str):
        raise RagEvaluationCaseContractError(f"{field_name} must be a string.")
    normalised = unicodedata.normalize("NFC", value)
    normalised = normalised.replace("\r\n", "\n").replace("\r", "\n")
    _assert_absolute_path_rejected(normalised)
    return normalised


def _is_reserved_metadata_key(normalised_key: str) -> bool:
    return normalised_key.strip().casefold() in _RESERVED_METADATA_KEYS


def _normalise_safety_assertions(value: object) -> tuple[str, ...]:
    if isinstance(value, (str, bytes, bytearray)):
        raise RagEvaluationCaseContractError(
            "safety_assertions must be a non-string sequence of strings."
        )
    if not isinstance(value, Sequence):
        raise RagEvaluationCaseContractError(
            "safety_assertions must be a non-string sequence of strings."
        )
    if not all(isinstance(item, str) for item in value):
        raise RagEvaluationCaseContractError(
            "safety_assertions must contain only strings."
        )
    return tuple(
        _canonical_string(item, field_name="safety_assertions item") for item in value
    )


def _validate_vector(
    value: object,
    *,
    field_name: str,
    expected_dimensions: int = EVAL_EMBEDDING_DIMENSIONS,
) -> tuple[float, ...]:
    if isinstance(value, (str, bytes, bytearray, Mapping)):
        raise RagEvaluationCaseContractError(
            f"{field_name} must be a non-string sequence of numbers."
        )
    if not isinstance(value, Sequence):
        raise RagEvaluationCaseContractError(
            f"{field_name} must be a non-string sequence of numbers."
        )
    if len(value) != expected_dimensions:
        raise RagEvaluationCaseContractError(
            f"{field_name} must have exactly {expected_dimensions} dimensions."
        )
    validated: list[float] = []
    for index, item in enumerate(value):
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise RagEvaluationCaseContractError(
                f"{field_name}[{index}] must be a finite number (bool rejected)."
            )
        number = float(item)
        if not math.isfinite(number):
            raise RagEvaluationCaseContractError(
                f"{field_name}[{index}] must be a finite number."
            )
        validated.append(number)
    norm_sq = math.fsum(component * component for component in validated)
    if norm_sq == 0.0:
        raise RagEvaluationCaseContractError(
            f"{field_name} must be a non-zero vector."
        )
    return tuple(validated)


def _validate_corpus(corpus: object, *, field_name: str) -> tuple["RagCorpusMember", ...]:
    if isinstance(corpus, (str, bytes, bytearray, Mapping)):
        raise RagEvaluationCaseContractError(
            f"{field_name} must be a non-string sequence of RagCorpusMember."
        )
    if not isinstance(corpus, Sequence):
        raise RagEvaluationCaseContractError(
            f"{field_name} must be a non-string sequence of RagCorpusMember."
        )
    if not corpus:
        raise RagEvaluationCaseContractError(f"{field_name} must be non-empty.")
    members: list[RagCorpusMember] = []
    seen_local_ids: set[str] = set()
    for item in corpus:
        if not isinstance(item, RagCorpusMember):
            raise RagEvaluationCaseContractError(
                f"{field_name} items must be RagCorpusMember instances."
            )
        if item.local_id in seen_local_ids:
            raise RagEvaluationCaseContractError(
                f"duplicate local_id in {field_name}: {item.local_id}."
            )
        seen_local_ids.add(item.local_id)
        members.append(item)
    return tuple(members)


def _validate_local_id_refs(
    values: object,
    *,
    field_name: str,
    corpus_ids: set[str],
    allow_empty: bool,
) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, bytearray)):
        raise RagEvaluationCaseContractError(
            f"{field_name} must be a non-string sequence of strings."
        )
    if not isinstance(values, Sequence):
        raise RagEvaluationCaseContractError(
            f"{field_name} must be a non-string sequence of strings."
        )
    normalised: list[str] = []
    seen: set[str] = set()
    for item in values:
        local_id = _canonical_string(item, field_name=f"{field_name} item")
        if not local_id.strip():
            raise RagEvaluationCaseContractError(
                f"{field_name} items must be non-empty."
            )
        if local_id in seen:
            raise RagEvaluationCaseContractError(
                f"duplicate local_id in {field_name}: {local_id}."
            )
        if local_id not in corpus_ids:
            raise RagEvaluationCaseContractError(
                f"{field_name} local_id is absent from corpus: {local_id}."
            )
        seen.add(local_id)
        normalised.append(local_id)
    if not allow_empty and not normalised:
        raise RagEvaluationCaseContractError(f"{field_name} must be non-empty.")
    return tuple(normalised)


@dataclass(frozen=True)
class RagCorpusMember:
    """One synthetic corpus candidate with a fixed document vector."""

    local_id: str
    skill_name: str
    category: str
    evidence_level: str
    sprint_reference: str
    document_vector: tuple[float, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "local_id",
            _canonical_string(self.local_id, field_name="local_id"),
        )
        if not self.local_id.strip():
            raise RagEvaluationCaseContractError("local_id must be non-empty.")
        object.__setattr__(
            self,
            "skill_name",
            _canonical_string(self.skill_name, field_name="skill_name"),
        )
        if not self.skill_name.strip():
            raise RagEvaluationCaseContractError("skill_name must be non-empty.")
        object.__setattr__(
            self,
            "category",
            _canonical_string(self.category, field_name="category"),
        )
        object.__setattr__(
            self,
            "evidence_level",
            _canonical_string(self.evidence_level, field_name="evidence_level"),
        )
        object.__setattr__(
            self,
            "sprint_reference",
            _canonical_string(self.sprint_reference, field_name="sprint_reference"),
        )
        object.__setattr__(
            self,
            "document_vector",
            _validate_vector(self.document_vector, field_name="document_vector"),
        )


@dataclass(frozen=True)
class RagRetrievalQualityCase:
    """Immutable retrieval-quality evaluation case."""

    case_id: str
    schema_version: str
    category: RagEvalCategory
    description: str
    is_synthetic: bool
    corpus: tuple[RagCorpusMember, ...]
    query_text: str
    query_vector: tuple[float, ...]
    expected_relevant_local_ids: tuple[str, ...]
    expected_recall_at_5: float
    safety_assertions: tuple[str, ...]

    def __post_init__(self) -> None:
        case_id = _canonical_string(self.case_id, field_name="case_id")
        if not case_id.strip():
            raise RagEvaluationCaseContractError("case_id must be a non-empty string.")
        object.__setattr__(self, "case_id", case_id)

        schema_version = _canonical_string(
            self.schema_version,
            field_name="schema_version",
        )
        if schema_version != CASE_SCHEMA_VERSION:
            raise RagEvaluationCaseContractError(
                "schema_version must equal CASE_SCHEMA_VERSION."
            )
        object.__setattr__(self, "schema_version", schema_version)

        if self.category is not RagEvalCategory.RETRIEVAL_QUALITY:
            raise RagEvaluationCaseContractError(
                "RagRetrievalQualityCase.category must be RETRIEVAL_QUALITY."
            )

        if self.is_synthetic is not True:
            raise RagEvaluationCaseContractError(
                "is_synthetic must be exactly True."
            )

        object.__setattr__(
            self,
            "description",
            _canonical_string(self.description, field_name="description"),
        )
        object.__setattr__(
            self,
            "query_text",
            _canonical_string(self.query_text, field_name="query_text"),
        )
        if not self.query_text.strip():
            raise RagEvaluationCaseContractError("query_text must be non-empty.")

        corpus = _validate_corpus(self.corpus, field_name="corpus")
        if len(corpus) <= TOP_K:
            raise RagEvaluationCaseContractError(
                f"retrieval-quality corpus must contain more than TOP_K={TOP_K} candidates."
            )
        object.__setattr__(self, "corpus", corpus)

        object.__setattr__(
            self,
            "query_vector",
            _validate_vector(self.query_vector, field_name="query_vector"),
        )

        corpus_ids = {member.local_id for member in corpus}
        relevant = _validate_local_id_refs(
            self.expected_relevant_local_ids,
            field_name="expected_relevant_local_ids",
            corpus_ids=corpus_ids,
            allow_empty=False,
        )
        object.__setattr__(self, "expected_relevant_local_ids", relevant)

        if (
            isinstance(self.expected_recall_at_5, bool)
            or not isinstance(self.expected_recall_at_5, (int, float))
        ):
            raise RagEvaluationCaseContractError(
                "expected_recall_at_5 must be a finite number."
            )
        expected = float(self.expected_recall_at_5)
        if not math.isfinite(expected) or expected != 1.0:
            raise RagEvaluationCaseContractError(
                "expected_recall_at_5 must equal exactly 1.0."
            )
        object.__setattr__(self, "expected_recall_at_5", 1.0)

        object.__setattr__(
            self,
            "safety_assertions",
            _normalise_safety_assertions(self.safety_assertions),
        )


@dataclass(frozen=True)
class RagAdversarialRetrievalCase:
    """Immutable adversarial retrieval evaluation case."""

    case_id: str
    schema_version: str
    category: RagEvalCategory
    description: str
    is_synthetic: bool
    adversarial_mode: AdversarialRetrievalMode
    corpus: tuple[RagCorpusMember, ...]
    other_user_corpus: tuple[RagCorpusMember, ...]
    query_text: str
    query_vector: tuple[float, ...]
    expected_retrieved_local_ids: tuple[str, ...]
    forbidden_local_ids: tuple[str, ...]
    cache_exception_local_ids: tuple[str, ...]
    safety_assertions: tuple[str, ...]

    def __post_init__(self) -> None:
        case_id = _canonical_string(self.case_id, field_name="case_id")
        if not case_id.strip():
            raise RagEvaluationCaseContractError("case_id must be a non-empty string.")
        object.__setattr__(self, "case_id", case_id)

        schema_version = _canonical_string(
            self.schema_version,
            field_name="schema_version",
        )
        if schema_version != CASE_SCHEMA_VERSION:
            raise RagEvaluationCaseContractError(
                "schema_version must equal CASE_SCHEMA_VERSION."
            )
        object.__setattr__(self, "schema_version", schema_version)

        if self.category is not RagEvalCategory.ADVERSARIAL_RETRIEVAL:
            raise RagEvaluationCaseContractError(
                "RagAdversarialRetrievalCase.category must be ADVERSARIAL_RETRIEVAL."
            )
        if not isinstance(self.adversarial_mode, AdversarialRetrievalMode):
            raise RagEvaluationCaseContractError(
                "adversarial_mode must be an AdversarialRetrievalMode member."
            )
        if self.is_synthetic is not True:
            raise RagEvaluationCaseContractError(
                "is_synthetic must be exactly True."
            )

        object.__setattr__(
            self,
            "description",
            _canonical_string(self.description, field_name="description"),
        )
        object.__setattr__(
            self,
            "query_text",
            _canonical_string(self.query_text, field_name="query_text"),
        )
        if not self.query_text.strip():
            raise RagEvaluationCaseContractError("query_text must be non-empty.")

        corpus = _validate_corpus(self.corpus, field_name="corpus")
        object.__setattr__(self, "corpus", corpus)
        other = _validate_corpus(
            self.other_user_corpus,
            field_name="other_user_corpus",
        ) if self.other_user_corpus else tuple()
        if self.adversarial_mode is AdversarialRetrievalMode.CROSS_USER:
            if not other:
                raise RagEvaluationCaseContractError(
                    "CROSS_USER cases require a non-empty other_user_corpus."
                )
        elif other:
            raise RagEvaluationCaseContractError(
                "other_user_corpus is only permitted for CROSS_USER cases."
            )
        object.__setattr__(self, "other_user_corpus", other)

        owner_ids = {member.local_id for member in corpus}
        other_ids = {member.local_id for member in other}
        if owner_ids.intersection(other_ids):
            raise RagEvaluationCaseContractError(
                "owner and other_user local_id namespaces must be disjoint."
            )

        object.__setattr__(
            self,
            "query_vector",
            _validate_vector(self.query_vector, field_name="query_vector"),
        )

        expected = _validate_local_id_refs(
            self.expected_retrieved_local_ids,
            field_name="expected_retrieved_local_ids",
            corpus_ids=owner_ids,
            allow_empty=True,
        )
        object.__setattr__(self, "expected_retrieved_local_ids", expected)

        forbidden_raw = self.forbidden_local_ids
        if isinstance(forbidden_raw, (str, bytes, bytearray)):
            raise RagEvaluationCaseContractError(
                "forbidden_local_ids must be a non-string sequence of strings."
            )
        if not isinstance(forbidden_raw, Sequence):
            raise RagEvaluationCaseContractError(
                "forbidden_local_ids must be a non-string sequence of strings."
            )
        forbidden: list[str] = []
        seen_forbidden: set[str] = set()
        allowed_forbidden = owner_ids.union(other_ids)
        for item in forbidden_raw:
            local_id = _canonical_string(item, field_name="forbidden_local_ids item")
            if local_id in seen_forbidden:
                raise RagEvaluationCaseContractError(
                    f"duplicate forbidden_local_ids item: {local_id}."
                )
            if local_id not in allowed_forbidden:
                raise RagEvaluationCaseContractError(
                    f"forbidden_local_ids local_id is absent from corpora: {local_id}."
                )
            seen_forbidden.add(local_id)
            forbidden.append(local_id)
        object.__setattr__(self, "forbidden_local_ids", tuple(forbidden))

        exceptions = _validate_local_id_refs(
            self.cache_exception_local_ids,
            field_name="cache_exception_local_ids",
            corpus_ids=owner_ids,
            allow_empty=True,
        )
        if self.adversarial_mode is AdversarialRetrievalMode.CROSS_USER:
            if exceptions:
                raise RagEvaluationCaseContractError(
                    "CROSS_USER cases must not set cache_exception_local_ids."
                )
        elif not exceptions:
            raise RagEvaluationCaseContractError(
                "cache_exception_local_ids must be non-empty for this adversarial mode."
            )
        object.__setattr__(self, "cache_exception_local_ids", exceptions)

        object.__setattr__(
            self,
            "safety_assertions",
            _normalise_safety_assertions(self.safety_assertions),
        )


RagEvalCase = RagRetrievalQualityCase | RagAdversarialRetrievalCase


def validate_and_sort_rag_evaluation_cases(
    cases: Iterable[RagEvalCase],
) -> tuple[RagEvalCase, ...]:
    """Validate uniqueness and return cases sorted by canonical case_id."""
    materialised = list(cases)
    seen_ids: set[str] = set()
    for case in materialised:
        if not isinstance(case, (RagRetrievalQualityCase, RagAdversarialRetrievalCase)):
            raise RagEvaluationCaseContractError(
                "cases must be RagRetrievalQualityCase or RagAdversarialRetrievalCase."
            )
        if case.is_synthetic is not True:
            raise RagEvaluationCaseContractError(
                "is_synthetic must be exactly True."
            )
        canonical_id = _canonical_string(case.case_id, field_name="case_id")
        if canonical_id in seen_ids:
            raise RagEvaluationCaseContractError(
                f"duplicate case_id: {canonical_id}."
            )
        seen_ids.add(canonical_id)
    return tuple(
        sorted(
            materialised,
            key=lambda item: _canonical_string(item.case_id, field_name="case_id"),
        )
    )


def _corpus_member_to_canonical_dict(member: RagCorpusMember) -> dict[str, Any]:
    return {
        "category": member.category,
        "document_vector": list(member.document_vector),
        "evidence_level": member.evidence_level,
        "local_id": member.local_id,
        "skill_name": member.skill_name,
        "sprint_reference": member.sprint_reference,
    }


def retrieval_quality_case_to_canonical_dict(
    case: RagRetrievalQualityCase,
) -> dict[str, Any]:
    return {
        "case_id": case.case_id,
        "category": case.category.value,
        "corpus": [_corpus_member_to_canonical_dict(item) for item in case.corpus],
        "description": case.description,
        "expected_recall_at_5": case.expected_recall_at_5,
        "expected_relevant_local_ids": list(case.expected_relevant_local_ids),
        "is_synthetic": case.is_synthetic,
        "query_text": case.query_text,
        "query_vector": list(case.query_vector),
        "safety_assertions": list(case.safety_assertions),
        "schema_version": case.schema_version,
    }


def adversarial_retrieval_case_to_canonical_dict(
    case: RagAdversarialRetrievalCase,
) -> dict[str, Any]:
    return {
        "adversarial_mode": case.adversarial_mode.value,
        "cache_exception_local_ids": list(case.cache_exception_local_ids),
        "case_id": case.case_id,
        "category": case.category.value,
        "corpus": [_corpus_member_to_canonical_dict(item) for item in case.corpus],
        "description": case.description,
        "expected_retrieved_local_ids": list(case.expected_retrieved_local_ids),
        "forbidden_local_ids": list(case.forbidden_local_ids),
        "is_synthetic": case.is_synthetic,
        "other_user_corpus": [
            _corpus_member_to_canonical_dict(item) for item in case.other_user_corpus
        ],
        "query_text": case.query_text,
        "query_vector": list(case.query_vector),
        "safety_assertions": list(case.safety_assertions),
        "schema_version": case.schema_version,
    }


def rag_evaluation_case_to_canonical_dict(case: RagEvalCase) -> dict[str, Any]:
    if isinstance(case, RagRetrievalQualityCase):
        return retrieval_quality_case_to_canonical_dict(case)
    if isinstance(case, RagAdversarialRetrievalCase):
        return adversarial_retrieval_case_to_canonical_dict(case)
    raise RagEvaluationCaseContractError("unsupported evaluation case type.")


def case_set_to_canonical_dict(cases: Iterable[RagEvalCase]) -> dict[str, Any]:
    sorted_cases = validate_and_sort_rag_evaluation_cases(cases)
    return {
        "case_schema_version": CASE_SCHEMA_VERSION,
        "cases": [rag_evaluation_case_to_canonical_dict(case) for case in sorted_cases],
        "evaluation_version": EVALUATION_VERSION,
    }


def canonical_case_set_bytes(cases: Iterable[RagEvalCase]) -> bytes:
    text = json.dumps(
        case_set_to_canonical_dict(cases),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return text.encode("utf-8")


def compute_case_set_hash(cases: Iterable[RagEvalCase]) -> str:
    return hashlib.sha256(canonical_case_set_bytes(cases)).hexdigest()


def _member(
    local_id: str,
    skill_name: str,
    vector: Sequence[float],
    *,
    evidence_level: str = "VERIFIED",
    category: str = "programming",
    sprint_reference: str = "Sprint 120",
) -> RagCorpusMember:
    return RagCorpusMember(
        local_id=local_id,
        skill_name=skill_name,
        category=category,
        evidence_level=evidence_level,
        sprint_reference=sprint_reference,
        document_vector=tuple(float(value) for value in vector),
    )


def _rq_case(
    *,
    case_id: str,
    description: str,
    corpus: Sequence[RagCorpusMember],
    query_text: str,
    query_vector: Sequence[float],
    expected_relevant_local_ids: Sequence[str],
    safety_assertions: Sequence[str],
) -> RagRetrievalQualityCase:
    return RagRetrievalQualityCase(
        case_id=case_id,
        schema_version=CASE_SCHEMA_VERSION,
        category=RagEvalCategory.RETRIEVAL_QUALITY,
        description=description,
        is_synthetic=True,
        corpus=tuple(corpus),
        query_text=query_text,
        query_vector=tuple(float(value) for value in query_vector),
        expected_relevant_local_ids=tuple(expected_relevant_local_ids),
        expected_recall_at_5=1.0,
        safety_assertions=tuple(safety_assertions),
    )


def _ar_case(
    *,
    case_id: str,
    description: str,
    adversarial_mode: AdversarialRetrievalMode,
    corpus: Sequence[RagCorpusMember],
    other_user_corpus: Sequence[RagCorpusMember] = (),
    query_text: str,
    query_vector: Sequence[float],
    expected_retrieved_local_ids: Sequence[str],
    forbidden_local_ids: Sequence[str],
    cache_exception_local_ids: Sequence[str] = (),
    safety_assertions: Sequence[str],
) -> RagAdversarialRetrievalCase:
    return RagAdversarialRetrievalCase(
        case_id=case_id,
        schema_version=CASE_SCHEMA_VERSION,
        category=RagEvalCategory.ADVERSARIAL_RETRIEVAL,
        description=description,
        is_synthetic=True,
        adversarial_mode=adversarial_mode,
        corpus=tuple(corpus),
        other_user_corpus=tuple(other_user_corpus),
        query_text=query_text,
        query_vector=tuple(float(value) for value in query_vector),
        expected_retrieved_local_ids=tuple(expected_retrieved_local_ids),
        forbidden_local_ids=tuple(forbidden_local_ids),
        cache_exception_local_ids=tuple(cache_exception_local_ids),
        safety_assertions=tuple(safety_assertions),
    )


# --- Retrieval quality cases (corpus always > TOP_K=5) ---

RETRIEVAL_QUALITY_CASES: tuple[RagRetrievalQualityCase, ...] = (
    _rq_case(
        case_id="RQ-01",
        description="Single relevant source among six candidates recovers at Recall@5=1.0.",
        corpus=(
            _member("rq01_relevant", "PythonPandas", (1.0, 0.0)),
            _member("rq01_d1", "DistractorOne", (0.0, 1.0)),
            _member("rq01_d2", "DistractorTwo", (0.1, 0.9)),
            _member("rq01_d3", "DistractorThree", (0.2, 0.8)),
            _member("rq01_d4", "DistractorFour", (0.3, 0.7)),
            _member("rq01_d5", "DistractorFive", (0.4, 0.6)),
        ),
        query_text="rq01-single-relevant-query",
        query_vector=(1.0, 0.0),
        expected_relevant_local_ids=("rq01_relevant",),
        safety_assertions=("single relevant source must appear in top-5",),
    ),
    _rq_case(
        case_id="RQ-02",
        description="Multiple relevant sources among seven candidates all appear in top-5.",
        corpus=(
            _member("rq02_rel_a", "SQLCore", (1.0, 0.0)),
            _member("rq02_rel_b", "SQLWindow", (0.95, 0.05)),
            _member("rq02_rel_c", "SQLJoin", (0.9, 0.1)),
            _member("rq02_d1", "NoiseAlpha", (0.0, 1.0)),
            _member("rq02_d2", "NoiseBeta", (0.05, 0.95)),
            _member("rq02_d3", "NoiseGamma", (0.1, 0.9)),
            _member("rq02_d4", "NoiseDelta", (0.15, 0.85)),
        ),
        query_text="rq02-multi-relevant-query",
        query_vector=(1.0, 0.0),
        expected_relevant_local_ids=("rq02_rel_a", "rq02_rel_b", "rq02_rel_c"),
        safety_assertions=("all expected relevant sources must appear in top-5",),
    ),
    _rq_case(
        case_id="RQ-03",
        description=(
            "Exact cosine ties break by SkillEntry PK ascending "
            "(creation order of corpus members)."
        ),
        corpus=(
            _member("rq03_tie_low", "TieLowPk", (1.0, 0.0)),
            _member("rq03_tie_high", "TieHighPk", (1.0, 0.0)),
            _member("rq03_d1", "TieDistractor1", (0.0, 1.0)),
            _member("rq03_d2", "TieDistractor2", (0.1, 0.9)),
            _member("rq03_d3", "TieDistractor3", (0.2, 0.8)),
            _member("rq03_d4", "TieDistractor4", (0.3, 0.7)),
        ),
        query_text="rq03-tie-break-query",
        query_vector=(1.0, 0.0),
        expected_relevant_local_ids=("rq03_tie_low", "rq03_tie_high"),
        safety_assertions=(
            "identical cosine scores must order by SkillEntry PK ascending",
        ),
    ),
    _rq_case(
        case_id="RQ-04",
        description="Known cosine ranked separation with deterministic descending order.",
        corpus=(
            _member("rq04_near", "NearMatch", (1.0, 0.0)),
            _member("rq04_mid", "MidMatch", (0.7, 0.3)),
            _member("rq04_far", "FarMatch", (0.2, 0.8)),
            _member("rq04_d1", "SepDistractor1", (0.0, 1.0)),
            _member("rq04_d2", "SepDistractor2", (0.05, 0.95)),
            _member("rq04_d3", "SepDistractor3", (0.1, 0.9)),
        ),
        query_text="rq04-ranked-separation-query",
        query_vector=(1.0, 0.0),
        expected_relevant_local_ids=("rq04_near", "rq04_mid", "rq04_far"),
        safety_assertions=("ranked order must follow exact cosine descending",),
    ),
    _rq_case(
        case_id="RQ-05",
        description="Heavy distractor corpus still recovers the single relevant source in top-5.",
        corpus=(
            _member("rq05_relevant", "PowerBICore", (1.0, 0.0)),
            _member("rq05_d1", "HeavyD1", (0.0, 1.0)),
            _member("rq05_d2", "HeavyD2", (0.05, 0.95)),
            _member("rq05_d3", "HeavyD3", (0.1, 0.9)),
            _member("rq05_d4", "HeavyD4", (0.15, 0.85)),
            _member("rq05_d5", "HeavyD5", (0.2, 0.8)),
            _member("rq05_d6", "HeavyD6", (0.25, 0.75)),
            _member("rq05_d7", "HeavyD7", (0.3, 0.7)),
        ),
        query_text="rq05-heavy-distractor-query",
        query_vector=(1.0, 0.0),
        expected_relevant_local_ids=("rq05_relevant",),
        safety_assertions=("relevant source recovered despite heavy distractors",),
    ),
)


ADVERSARIAL_RETRIEVAL_CASES: tuple[RagAdversarialRetrievalCase, ...] = (
    _ar_case(
        case_id="AR-01",
        description="Cross-user evidence is excluded from ownership-scoped retrieval.",
        adversarial_mode=AdversarialRetrievalMode.CROSS_USER,
        corpus=(
            _member("ar01_owner", "OwnerPython", (1.0, 0.0)),
            _member("ar01_owner_d1", "OwnerNoise1", (0.0, 1.0)),
            _member("ar01_owner_d2", "OwnerNoise2", (0.1, 0.9)),
        ),
        other_user_corpus=(
            _member("ar01_other", "OtherSQL", (1.0, 0.0)),
            _member("ar01_other_d1", "OtherNoise1", (0.95, 0.05)),
        ),
        query_text="ar01-cross-user-query",
        query_vector=(1.0, 0.0),
        expected_retrieved_local_ids=("ar01_owner",),
        forbidden_local_ids=("ar01_other", "ar01_other_d1"),
        safety_assertions=("other-user evidence must never enter ranked results",),
    ),
    _ar_case(
        case_id="AR-02",
        description="Stale cache rows with mismatched content_sha256 are excluded.",
        adversarial_mode=AdversarialRetrievalMode.STALE_CACHE,
        corpus=(
            _member("ar02_fresh", "FreshPython", (1.0, 0.0)),
            _member("ar02_stale", "StalePython", (0.99, 0.01)),
            _member("ar02_d1", "StaleNoise1", (0.0, 1.0)),
            _member("ar02_d2", "StaleNoise2", (0.1, 0.9)),
        ),
        query_text="ar02-stale-cache-query",
        query_vector=(1.0, 0.0),
        expected_retrieved_local_ids=("ar02_fresh",),
        forbidden_local_ids=("ar02_stale",),
        cache_exception_local_ids=("ar02_stale",),
        safety_assertions=("stale content_sha256 rows must be excluded",),
    ),
    _ar_case(
        case_id="AR-03",
        description="Isolated missing-cache row is excluded; other CURRENT rows remain eligible.",
        adversarial_mode=AdversarialRetrievalMode.MISSING_CACHE,
        corpus=(
            _member("ar03_cached", "CachedPython", (1.0, 0.0)),
            _member("ar03_missing", "MissingPython", (0.99, 0.01)),
            _member("ar03_d1", "MissingNoise1", (0.0, 1.0)),
            _member("ar03_d2", "MissingNoise2", (0.1, 0.9)),
        ),
        query_text="ar03-missing-cache-query",
        query_vector=(1.0, 0.0),
        expected_retrieved_local_ids=("ar03_cached",),
        forbidden_local_ids=("ar03_missing",),
        cache_exception_local_ids=("ar03_missing",),
        safety_assertions=("missing-cache behaviour is isolated to dedicated case",),
    ),
    _ar_case(
        case_id="AR-04",
        description="Provider/model mismatch cache rows are excluded from retrieval.",
        adversarial_mode=AdversarialRetrievalMode.PROVIDER_MODEL_MISMATCH,
        corpus=(
            _member("ar04_match", "MatchedPython", (1.0, 0.0)),
            _member("ar04_mismatch", "MismatchPython", (0.99, 0.01)),
            _member("ar04_d1", "MismatchNoise1", (0.0, 1.0)),
            _member("ar04_d2", "MismatchNoise2", (0.1, 0.9)),
        ),
        query_text="ar04-provider-model-mismatch-query",
        query_vector=(1.0, 0.0),
        expected_retrieved_local_ids=("ar04_match",),
        forbidden_local_ids=("ar04_mismatch",),
        cache_exception_local_ids=("ar04_mismatch",),
        safety_assertions=("provider/model mismatched rows must be excluded",),
    ),
)


PHASE1_EVALUATION_CASES: tuple[RagEvalCase, ...] = (
    validate_and_sort_rag_evaluation_cases(
        tuple(RETRIEVAL_QUALITY_CASES) + tuple(ADVERSARIAL_RETRIEVAL_CASES)
    )
)

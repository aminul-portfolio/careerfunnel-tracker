"""Evidence-alignment explanation offline evaluation contract (Sprint 115 Phase 1).

Immutable case schema, canonical serialisation and case-set hashing only.
No replay runner, management command, provider, ORM, network or filesystem access.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any

from apps.skill_gaps.deterministic_evidence_alignment import RULE_VERSION
from apps.skill_gaps.explanation_output_validator import ExplanationRejectionCode

EVALUATION_VERSION = "evidence_alignment_explanation_eval_v1"
CASE_SCHEMA_VERSION = "evidence_alignment_explanation_case_v1"

# Authoritative evidence-alignment rule version (imported, not redeclared).
EVIDENCE_ALIGNMENT_RULE_VERSION = RULE_VERSION

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


class EvaluationCategory(str, Enum):
    GOLDEN_VALID_OUTPUT = "GOLDEN_VALID_OUTPUT"
    EVIDENCE_GROUNDING_AND_INJECTION = "EVIDENCE_GROUNDING_AND_INJECTION"
    STRUCTURAL_SCHEMA_FAILURE = "STRUCTURAL_SCHEMA_FAILURE"
    PROHIBITED_CLAIM_LANGUAGE = "PROHIBITED_CLAIM_LANGUAGE"
    CONTENT_FORMAT_FAILURE = "CONTENT_FORMAT_FAILURE"
    ROUTE_PROVIDER_BOUNDARY = "ROUTE_PROVIDER_BOUNDARY"
    RENDERING_AND_FALLBACK = "RENDERING_AND_FALLBACK"
    REJECTION_CODE_STABILITY = "REJECTION_CODE_STABILITY"


class EvaluationCaseContractError(ValueError):
    """Fail-closed validation failure for evaluation case contract data."""


def _assert_absolute_path_rejected(value: str) -> None:
    """Reject absolute local and network path values. Fail closed."""
    if _WINDOWS_ABSOLUTE_PATH_RE.match(value):
        raise EvaluationCaseContractError(
            "absolute Windows path values are not permitted in evaluation case content."
        )
    if value.startswith("\\\\"):
        raise EvaluationCaseContractError(
            "UNC path values are not permitted in evaluation case content."
        )
    if value.startswith("//"):
        raise EvaluationCaseContractError(
            "network path values are not permitted in evaluation case content."
        )
    if value.startswith("/"):
        raise EvaluationCaseContractError(
            "absolute POSIX path values are not permitted in evaluation case content."
        )


def _canonical_string(value: object, *, field_name: str = "value") -> str:
    """Require a string, normalise NFC/newlines, reject absolute paths, return text."""
    if not isinstance(value, str):
        raise EvaluationCaseContractError(f"{field_name} must be a string.")
    normalised = unicodedata.normalize("NFC", value)
    normalised = normalised.replace("\r\n", "\n").replace("\r", "\n")
    _assert_absolute_path_rejected(normalised)
    return normalised


def _is_reserved_metadata_key(normalised_key: str) -> bool:
    return normalised_key.strip().casefold() in _RESERVED_METADATA_KEYS


def _freeze_mapping(mapping: Mapping[Any, Any]) -> MappingProxyType:
    """Freeze a mapping with string-key normalisation and fail-closed checks."""
    frozen: dict[str, Any] = {}
    for key, item in mapping.items():
        if not isinstance(key, str):
            raise EvaluationCaseContractError("mapping keys must be strings.")
        normalised_key = _canonical_string(key, field_name="mapping key")
        if _is_reserved_metadata_key(normalised_key):
            raise EvaluationCaseContractError(
                "reserved execution metadata key is not permitted: "
                f"{normalised_key.strip().casefold()}."
            )
        if normalised_key in frozen:
            raise EvaluationCaseContractError(
                "mapping keys collide after Unicode and newline normalisation."
            )
        frozen[normalised_key] = _freeze_value(item)
    return MappingProxyType(frozen)


def _freeze_value(value: Any) -> Any:
    """Return a deeply immutable Python-native structure."""
    if isinstance(value, Mapping):
        return _freeze_mapping(value)
    if isinstance(value, (set, frozenset)):
        raise EvaluationCaseContractError(
            "set and frozenset values are not permitted in evaluation case content."
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, str):
        return _canonical_string(value)
    if isinstance(value, (int, bool, type(None))):
        return value
    if isinstance(value, float):
        raise EvaluationCaseContractError(
            "floating-point values are not permitted in evaluation case content."
        )
    raise EvaluationCaseContractError(
        f"unsupported evaluation case value type: {type(value).__name__}."
    )


def _require_immutable_mapping_or_none(
    value: object,
    *,
    field_name: str,
) -> Mapping[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise EvaluationCaseContractError(
            f"{field_name} must be an immutable mapping or None."
        )
    frozen = _freeze_value(value)
    if not isinstance(frozen, Mapping):
        raise EvaluationCaseContractError(
            f"{field_name} must be an immutable mapping or None."
        )
    return frozen


def _require_immutable_mapping(
    value: object,
    *,
    field_name: str,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise EvaluationCaseContractError(f"{field_name} must be an immutable mapping.")
    frozen = _freeze_value(value)
    if not isinstance(frozen, Mapping):
        raise EvaluationCaseContractError(f"{field_name} must be an immutable mapping.")
    return frozen


def _normalise_safety_assertions(value: object) -> tuple[str, ...]:
    if isinstance(value, (str, bytes, bytearray)):
        raise EvaluationCaseContractError(
            "safety_assertions must be a non-string sequence of strings."
        )
    if not isinstance(value, Sequence):
        raise EvaluationCaseContractError(
            "safety_assertions must be a non-string sequence of strings."
        )
    if not all(isinstance(item, str) for item in value):
        raise EvaluationCaseContractError(
            "safety_assertions must contain only strings."
        )
    return tuple(
        _canonical_string(item, field_name="safety_assertions item") for item in value
    )


@dataclass(frozen=True)
class EvaluationCase:
    """Immutable synthetic evaluation case contract."""

    case_id: str
    schema_version: str
    category: EvaluationCategory
    description: str
    deterministic_outcome: str
    builder_input: Mapping[str, Any] | None
    expected_provider_payload: Mapping[str, Any]
    simulated_provider_output: str
    expected_acceptance: bool
    expected_rejection_code: ExplanationRejectionCode | None
    safety_assertions: tuple[str, ...]
    is_synthetic: bool

    def __post_init__(self) -> None:
        case_id = _canonical_string(self.case_id, field_name="case_id")
        if not case_id.strip():
            raise EvaluationCaseContractError("case_id must be a non-empty string.")
        object.__setattr__(self, "case_id", case_id)

        schema_version = _canonical_string(
            self.schema_version,
            field_name="schema_version",
        )
        if schema_version != CASE_SCHEMA_VERSION:
            raise EvaluationCaseContractError(
                "schema_version must equal CASE_SCHEMA_VERSION."
            )
        object.__setattr__(self, "schema_version", schema_version)

        if not isinstance(self.category, EvaluationCategory):
            raise EvaluationCaseContractError(
                "category must be an EvaluationCategory member."
            )
        # Validate category value through the shared string safety helper.
        _canonical_string(self.category.value, field_name="category")

        object.__setattr__(
            self,
            "description",
            _canonical_string(self.description, field_name="description"),
        )
        object.__setattr__(
            self,
            "deterministic_outcome",
            _canonical_string(
                self.deterministic_outcome,
                field_name="deterministic_outcome",
            ),
        )
        object.__setattr__(
            self,
            "simulated_provider_output",
            _canonical_string(
                self.simulated_provider_output,
                field_name="simulated_provider_output",
            ),
        )

        if self.is_synthetic is not True:
            raise EvaluationCaseContractError(
                "is_synthetic must be exactly True in Phase 1."
            )
        if type(self.expected_acceptance) is not bool:
            raise EvaluationCaseContractError(
                "expected_acceptance must be exactly bool."
            )
        if self.expected_acceptance is True:
            if self.expected_rejection_code is not None:
                raise EvaluationCaseContractError(
                    "accepted cases must have expected_rejection_code=None."
                )
        else:
            if not isinstance(
                self.expected_rejection_code,
                ExplanationRejectionCode,
            ):
                raise EvaluationCaseContractError(
                    "rejected cases must have an ExplanationRejectionCode."
                )
            _canonical_string(
                self.expected_rejection_code.value,
                field_name="expected_rejection_code",
            )

        object.__setattr__(
            self,
            "safety_assertions",
            _normalise_safety_assertions(self.safety_assertions),
        )
        object.__setattr__(
            self,
            "builder_input",
            _require_immutable_mapping_or_none(
                self.builder_input,
                field_name="builder_input",
            ),
        )
        object.__setattr__(
            self,
            "expected_provider_payload",
            _require_immutable_mapping(
                self.expected_provider_payload,
                field_name="expected_provider_payload",
            ),
        )


def validate_and_sort_evaluation_cases(
    cases: Iterable[EvaluationCase],
) -> tuple[EvaluationCase, ...]:
    """Validate and return cases sorted by canonical case_id.

    Duplicate IDs fail closed after Unicode NFC and newline normalisation.
    """
    materialised: list[EvaluationCase] = []
    seen_ids: set[str] = set()
    for case in cases:
        if not isinstance(case, EvaluationCase):
            raise EvaluationCaseContractError(
                "every case must be an EvaluationCase instance."
            )
        canonical_id = _canonical_string(case.case_id, field_name="case_id")
        if canonical_id in seen_ids:
            raise EvaluationCaseContractError(
                "duplicate case_id is not permitted after normalisation."
            )
        seen_ids.add(canonical_id)
        materialised.append(case)
    return tuple(
        sorted(
            materialised,
            key=lambda item: _canonical_string(item.case_id, field_name="case_id"),
        )
    )


def _canonicalise_mapping(mapping: Mapping[Any, Any]) -> dict[str, Any]:
    """Canonicalise a mapping with string-key normalisation and fail-closed checks."""
    canonical: dict[str, Any] = {}
    for key, item in mapping.items():
        if not isinstance(key, str):
            raise EvaluationCaseContractError("mapping keys must be strings.")
        normalised_key = _canonical_string(key, field_name="mapping key")
        if _is_reserved_metadata_key(normalised_key):
            raise EvaluationCaseContractError(
                "reserved execution metadata key is not permitted: "
                f"{normalised_key.strip().casefold()}."
            )
        if normalised_key in canonical:
            raise EvaluationCaseContractError(
                "mapping keys collide after Unicode and newline normalisation."
            )
        canonical[normalised_key] = _canonicalise_value(item)
    return canonical


def _canonicalise_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _canonicalise_mapping(value)
    if isinstance(value, (list, tuple)):
        return [_canonicalise_value(item) for item in value]
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        raise EvaluationCaseContractError(
            "floating-point values are not permitted in canonical case content."
        )
    if isinstance(value, Enum):
        return _canonical_string(value.value, field_name="enum value")
    if isinstance(value, str):
        return _canonical_string(value)
    raise EvaluationCaseContractError(
        f"unsupported canonical value type: {type(value).__name__}."
    )


def evaluation_case_to_canonical_dict(case: EvaluationCase) -> dict[str, Any]:
    """Produce canonical serialisable data for one evaluation case."""
    return {
        "builder_input": _canonicalise_value(case.builder_input),
        "case_id": _canonical_string(case.case_id, field_name="case_id"),
        "category": _canonical_string(case.category.value, field_name="category"),
        "description": _canonical_string(case.description, field_name="description"),
        "deterministic_outcome": _canonical_string(
            case.deterministic_outcome,
            field_name="deterministic_outcome",
        ),
        "expected_acceptance": case.expected_acceptance,
        "expected_provider_payload": _canonicalise_value(
            case.expected_provider_payload
        ),
        "expected_rejection_code": (
            None
            if case.expected_rejection_code is None
            else _canonical_string(
                case.expected_rejection_code.value,
                field_name="expected_rejection_code",
            )
        ),
        "is_synthetic": case.is_synthetic,
        "safety_assertions": [
            _canonical_string(item, field_name="safety_assertions item")
            for item in case.safety_assertions
        ],
        "schema_version": _canonical_string(
            case.schema_version,
            field_name="schema_version",
        ),
        "simulated_provider_output": _canonical_string(
            case.simulated_provider_output,
            field_name="simulated_provider_output",
        ),
    }


def case_set_to_canonical_dict(
    cases: Iterable[EvaluationCase],
) -> dict[str, Any]:
    """Produce canonical serialisable data for a validated sorted case set."""
    sorted_cases = validate_and_sort_evaluation_cases(cases)
    return {
        "case_schema_version": CASE_SCHEMA_VERSION,
        "cases": [evaluation_case_to_canonical_dict(case) for case in sorted_cases],
        "evaluation_version": EVALUATION_VERSION,
        "rule_version": EVIDENCE_ALIGNMENT_RULE_VERSION,
    }


def canonical_case_set_bytes(cases: Iterable[EvaluationCase]) -> bytes:
    """Produce canonical UTF-8 bytes for a case set."""
    data = case_set_to_canonical_dict(cases)
    text = json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return text.encode("utf-8")


def compute_case_set_hash(cases: Iterable[EvaluationCase]) -> str:
    """Produce the SHA-256 hex digest of the canonical case-set bytes."""
    return hashlib.sha256(canonical_case_set_bytes(cases)).hexdigest()


def make_evaluation_case(
    *,
    case_id: str,
    category: EvaluationCategory,
    description: str,
    deterministic_outcome: str,
    builder_input: Mapping[str, Any] | None,
    expected_provider_payload: Mapping[str, Any],
    simulated_provider_output: str,
    expected_acceptance: bool,
    expected_rejection_code: ExplanationRejectionCode | None,
    safety_assertions: Sequence[str],
    is_synthetic: bool = True,
    schema_version: str = CASE_SCHEMA_VERSION,
) -> EvaluationCase:
    """Construct a validated EvaluationCase (synthetic contract fixtures only)."""
    return EvaluationCase(
        case_id=case_id,
        schema_version=schema_version,
        category=category,
        description=description,
        deterministic_outcome=deterministic_outcome,
        builder_input=builder_input,
        expected_provider_payload=expected_provider_payload,
        simulated_provider_output=simulated_provider_output,
        expected_acceptance=expected_acceptance,
        expected_rejection_code=expected_rejection_code,
        safety_assertions=_normalise_safety_assertions(safety_assertions),
        is_synthetic=is_synthetic,
    )

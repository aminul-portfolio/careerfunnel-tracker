"""Deterministic contract for one synthetic evidence-alignment canary case."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass

CANARY_CONTRACT_SCHEMA_VERSION = (
    "evidence_alignment_explanation_canary_contract_v1"
)
_LOCKED_CASE_ID = "sprint-116-evidence-alignment-explanation-canary-001"
_LOCKED_SURFACE = "evidence_alignment_advisory_explanation"
_LOCKED_VERIFIED_SKILLS = ("Python", "Django", "SQL")
_LOCKED_LEARNING_TARGET_SKILLS = ("Snowflake",)
_LOCKED_UNMATCHED_REQUIREMENTS = ("GraphQL",)
_LOCKED_OUTCOME = "SOME_REQUIREMENTS_VERIFIED"


@dataclass(frozen=True, slots=True)
class EvidenceAlignmentExplanationCanaryCase:
    """Immutable synthetic input and expected deterministic outcome."""

    schema_version: str
    case_id: str
    surface: str
    verified_skills: tuple[str, ...]
    learning_target_skills: tuple[str, ...]
    unmatched_requirements: tuple[str, ...]
    expected_deterministic_outcome: str


_AUTHORITATIVE_CANARY_CASE = EvidenceAlignmentExplanationCanaryCase(
    schema_version=CANARY_CONTRACT_SCHEMA_VERSION,
    case_id=_LOCKED_CASE_ID,
    surface=_LOCKED_SURFACE,
    verified_skills=_LOCKED_VERIFIED_SKILLS,
    learning_target_skills=_LOCKED_LEARNING_TARGET_SKILLS,
    unmatched_requirements=_LOCKED_UNMATCHED_REQUIREMENTS,
    expected_deterministic_outcome=_LOCKED_OUTCOME,
)


def _validate_string_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise ValueError(f"{field_name} must be an immutable tuple.")
    if not values or any(not isinstance(value, str) or not value for value in values):
        raise ValueError(f"{field_name} must contain non-empty strings.")
    if len(values) != len(set(values)):
        raise ValueError(f"{field_name} must not contain duplicates.")
    return values


def validate_canary_contract(
    case: EvidenceAlignmentExplanationCanaryCase,
) -> None:
    """Fail closed unless the case matches the locked synthetic contract."""

    if not isinstance(case, EvidenceAlignmentExplanationCanaryCase):
        raise ValueError("canary contract must use the immutable case type.")
    if case.schema_version != CANARY_CONTRACT_SCHEMA_VERSION:
        raise ValueError("unsupported canary contract schema version.")
    if case.case_id != _LOCKED_CASE_ID:
        raise ValueError("unexpected canary case ID.")
    if case.surface != _LOCKED_SURFACE:
        raise ValueError("unexpected canary surface.")

    verified = _validate_string_tuple(case.verified_skills, "verified_skills")
    learning = _validate_string_tuple(
        case.learning_target_skills,
        "learning_target_skills",
    )
    unmatched = _validate_string_tuple(
        case.unmatched_requirements,
        "unmatched_requirements",
    )
    verified_set = set(verified)
    learning_set = set(learning)
    unmatched_set = set(unmatched)
    if (
        verified_set & learning_set
        or verified_set & unmatched_set
        or learning_set & unmatched_set
    ):
        raise ValueError("evidence categories must not overlap.")
    if verified != _LOCKED_VERIFIED_SKILLS:
        raise ValueError("unexpected verified skills.")
    if learning != _LOCKED_LEARNING_TARGET_SKILLS:
        raise ValueError("unexpected learning-target skills.")
    if unmatched != _LOCKED_UNMATCHED_REQUIREMENTS:
        raise ValueError("unexpected unmatched requirements.")
    if case.expected_deterministic_outcome != _LOCKED_OUTCOME:
        raise ValueError("unexpected deterministic outcome.")


def get_authoritative_canary_case() -> EvidenceAlignmentExplanationCanaryCase:
    """Return the single validated synthetic canary case."""

    validate_canary_contract(_AUTHORITATIVE_CANARY_CASE)
    return _AUTHORITATIVE_CANARY_CASE


def get_canary_manifest(
    case: EvidenceAlignmentExplanationCanaryCase | None = None,
) -> dict[str, object]:
    """Return deterministic JSON-compatible values for the contract manifest."""

    selected_case = case or get_authoritative_canary_case()
    validate_canary_contract(selected_case)
    return {
        "schema_version": selected_case.schema_version,
        "case_id": selected_case.case_id,
        "surface": selected_case.surface,
        "verified_skills": list(selected_case.verified_skills),
        "learning_target_skills": list(selected_case.learning_target_skills),
        "unmatched_requirements": list(selected_case.unmatched_requirements),
        "expected_deterministic_outcome": selected_case.expected_deterministic_outcome,
    }


def canonical_manifest_bytes(
    manifest: Mapping[str, object] | None = None,
) -> bytes:
    """Serialise a manifest with the explicit canonical JSON policy."""

    selected_manifest = get_canary_manifest() if manifest is None else manifest
    try:
        canonical_json = json.dumps(
            selected_manifest,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("manifest must contain deterministic JSON values.") from exc
    return canonical_json.encode("utf-8")


def contract_manifest_sha256(
    manifest: Mapping[str, object] | None = None,
) -> str:
    """Calculate the lowercase SHA-256 of canonical contract manifest bytes."""

    return hashlib.sha256(canonical_manifest_bytes(manifest)).hexdigest()


CONTRACT_MANIFEST_SHA256 = (
    "0f062ecb32fba77875b70fe8ee9616c78fc9657ac6a5aa83946ca0bfc68ca6e9"
)

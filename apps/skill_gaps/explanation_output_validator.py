"""Evidence-alignment explanation output validator (Sprint 114 Phase 2).

Pure schema, traceability and claim-safety validation for untrusted provider
output against the Phase 1 allowlisted explanation payload. No ORM, settings,
provider, network or persistence access.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

from apps.skill_gaps.deterministic_evidence_alignment import (
    RULE_VERSION,
    EvidenceAlignmentOutcome,
)
from apps.skill_gaps.deterministic_gap_classifier import (
    MatchBasis,
    RequirementClassification,
)

_TOP_LEVEL_KEYS = frozenset(
    {"summary", "verified_evidence", "development_evidence", "missing_evidence"}
)
_VERIFIED_ITEM_KEYS = frozenset(
    {"requirement_index", "skill_names", "explanation"}
)
_DEVELOPMENT_ITEM_KEYS = frozenset(
    {"requirement_index", "skill_names", "evidence_level", "explanation"}
)
_MISSING_ITEM_KEYS = frozenset({"requirement_index", "explanation"})

_PAYLOAD_TOP_LEVEL_KEYS = frozenset(
    {"rule_version", "overall_outcome", "requirements"}
)
_PAYLOAD_REQUIREMENT_KEYS = frozenset(
    {
        "requirement_index",
        "requirement_text",
        "classification",
        "match_basis",
        "matched_evidence_level",
        "matched_skill_name",
        "unresolved",
    }
)

_SUMMARY_MAX_LEN = 500
_EXPLANATION_MAX_LEN = 200
_ARRAY_MAX_ITEMS = 10

_OUTCOME_VALUES = frozenset(member.value for member in EvidenceAlignmentOutcome)
_CLASSIFICATION_VALUES = frozenset(
    member.value for member in RequirementClassification
)
_MATCH_BASIS_VALUES = frozenset(member.value for member in MatchBasis)
_EVIDENCE_LEVEL_VALUES = frozenset(
    {"VERIFIED", "LEARNING_TARGET", "STUDYING", "NO_EVIDENCE"}
)

_DEVELOPMENT_LEVELS = frozenset({"LEARNING_TARGET", "STUDYING"})
_CLASSIFICATION_TO_DEVELOPMENT_LEVEL = {
    "LEARNING_TARGET_MATCH": "LEARNING_TARGET",
    "STUDYING_MATCH": "STUDYING",
}

_MARKDOWN_OR_HTML_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?m)^\s{0,3}#{1,6}\s"),  # Markdown headings
    re.compile(r"(?m)^\s{0,3}([-*+]|\d+[.)])\s"),  # Markdown list markers
    re.compile(r"(?m)^\s{0,3}>"),  # block quotes
    re.compile(r"```"),  # fenced code
    re.compile(r"\[[^\]]+\]\([^)]+\)"),  # inline Markdown links
    re.compile(r"\*\*[^*\n]+?\*\*"),  # **bold**
    re.compile(r"__[^_\n]+?__"),  # __bold__
    re.compile(r"(?<!\*)\*[^*\n]+?\*(?!\*)"),  # *italic*
    re.compile(r"(?<!_)_[^_\n]+?_(?!_)"),  # _italic_
    re.compile(r"<[^>]+>"),  # HTML tags
)

_URL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"https?://", re.IGNORECASE),
    re.compile(r"\bwww\.", re.IGNORECASE),
)

_CLAIM_SAFETY_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\d+\s*%"), "percentage"),
    (re.compile(r"\bpercent(?:age)?\b", re.IGNORECASE), "percentage"),
    (re.compile(r"\b\d+\s*/\s*\d+\b"), "numeric_score"),
    (re.compile(r"\bscore\b", re.IGNORECASE), "score_labelled"),
    (re.compile(r"\bconfidence\b", re.IGNORECASE), "confidence"),
    (re.compile(r"\bprobability\b", re.IGNORECASE), "probability"),
    (re.compile(r"\blikelihood\b", re.IGNORECASE), "likelihood"),
    (re.compile(r"\bhiring\b", re.IGNORECASE), "hiring"),
    (re.compile(r"\breadiness\b", re.IGNORECASE), "readiness"),
    (re.compile(r"\bcandidate\s+strength\b", re.IGNORECASE), "candidate_strength"),
    (re.compile(r"\bsuitability\b", re.IGNORECASE), "suitability"),
    (re.compile(r"\bemployer\s+fit\b", re.IGNORECASE), "employer_fit"),
    (re.compile(r"\bproficiency\b", re.IGNORECASE), "proficiency"),
    (re.compile(r"\bqualified\b", re.IGNORECASE), "qualification"),
    (re.compile(r"\bqualification\b", re.IGNORECASE), "qualification"),
    (
        re.compile(r"\bguaranteed\s+employability\b", re.IGNORECASE),
        "guaranteed_employability",
    ),
    (re.compile(r"\bauto(?:matic)?[-\s]?apply\b", re.IGNORECASE), "auto_apply"),
    (
        re.compile(r"\bautomatic(?:ally)?\s+appl(?:y|ication)\b", re.IGNORECASE),
        "auto_apply",
    ),
    (re.compile(r"\byou\s+should\s+apply\b", re.IGNORECASE), "should_apply"),
)


class ExplanationRejectionCode(str, Enum):
    """Stable rejection categories produced by this validator."""

    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    INVALID_FIELD_TYPE = "INVALID_FIELD_TYPE"
    NULL_BYTE_DETECTED = "NULL_BYTE_DETECTED"
    EMPTY_OUTPUT = "EMPTY_OUTPUT"
    OVERSIZED_FIELD = "OVERSIZED_FIELD"
    MARKUP_DETECTED = "MARKUP_DETECTED"
    URL_DETECTED = "URL_DETECTED"
    PROHIBITED_CLAIM = "PROHIBITED_CLAIM"
    INVALID_INDEX = "INVALID_INDEX"
    DUPLICATE_INDEX = "DUPLICATE_INDEX"
    EVIDENCE_LEVEL_MISMATCH = "EVIDENCE_LEVEL_MISMATCH"
    SKILL_NAME_MISMATCH = "SKILL_NAME_MISMATCH"
    UNSUPPORTED_EVIDENCE = "UNSUPPORTED_EVIDENCE"
    SEMANTIC_CONTRADICTION = "SEMANTIC_CONTRADICTION"
    CATEGORY_MISMATCH = "CATEGORY_MISMATCH"


class EvidenceAlignmentExplanationValidationError(ValueError):
    """Raised when explanation output fails schema, traceability or claim-safety."""

    def __init__(
        self,
        message: str,
        code: ExplanationRejectionCode | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code


def _fail(message: str, code: ExplanationRejectionCode) -> None:
    raise EvidenceAlignmentExplanationValidationError(message, code=code)


def _require_dict(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(
            f"{label} must be a dictionary.",
            ExplanationRejectionCode.INVALID_FIELD_TYPE,
        )
    return value


def _require_exact_keys(
    mapping: dict[str, Any],
    allowed: frozenset[str],
    label: str,
) -> None:
    keys = frozenset(mapping.keys())
    if keys != allowed:
        _fail(
            f"{label} has invalid fields.",
            ExplanationRejectionCode.SCHEMA_MISMATCH,
        )


def _require_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _fail(
            f"{label} must be an integer.",
            ExplanationRejectionCode.INVALID_FIELD_TYPE,
        )
    return value


def _require_bool(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        _fail(
            f"{label} must be a boolean.",
            ExplanationRejectionCode.INVALID_FIELD_TYPE,
        )
    return value


def _require_plain_string(
    value: object,
    *,
    label: str,
    max_length: int,
) -> str:
    if not isinstance(value, str):
        _fail(
            f"{label} must be a string.",
            ExplanationRejectionCode.INVALID_FIELD_TYPE,
        )
    if "\x00" in value:
        _fail(
            f"{label} contains a null byte.",
            ExplanationRejectionCode.NULL_BYTE_DETECTED,
        )
    stripped = value.strip()
    if not stripped:
        _fail(
            f"{label} must be a non-empty string.",
            ExplanationRejectionCode.EMPTY_OUTPUT,
        )
    if len(stripped) > max_length:
        _fail(
            f"{label} exceeds maximum length.",
            ExplanationRejectionCode.OVERSIZED_FIELD,
        )
    _assert_plain_text_and_claim_safe(stripped, label=label)
    return stripped


def _assert_plain_text_and_claim_safe(text: str, *, label: str) -> None:
    for pattern in _MARKDOWN_OR_HTML_PATTERNS:
        if pattern.search(text):
            _fail(
                f"{label} contains Markdown or HTML content.",
                ExplanationRejectionCode.MARKUP_DETECTED,
            )
    for pattern in _URL_PATTERNS:
        if pattern.search(text):
            _fail(
                f"{label} contains a URL.",
                ExplanationRejectionCode.URL_DETECTED,
            )
    for pattern, code in _CLAIM_SAFETY_PATTERNS:
        if pattern.search(text):
            _fail(
                f"{label} contains prohibited claim-safety content ({code}).",
                ExplanationRejectionCode.PROHIBITED_CLAIM,
            )


def _require_requirement_text(value: object) -> str:
    if not isinstance(value, str):
        _fail(
            "requirement_text must be a string.",
            ExplanationRejectionCode.INVALID_FIELD_TYPE,
        )
    if "\x00" in value:
        _fail(
            "requirement_text contains a null byte.",
            ExplanationRejectionCode.NULL_BYTE_DETECTED,
        )
    if not value.strip():
        _fail(
            "requirement_text must be a non-empty string.",
            ExplanationRejectionCode.EMPTY_OUTPUT,
        )
    return value


def _index_provider_payload(
    provider_payload: object,
) -> dict[int, dict[str, Any]]:
    payload = _require_dict(provider_payload, "provider_payload")
    _require_exact_keys(payload, _PAYLOAD_TOP_LEVEL_KEYS, "provider_payload")

    rule_version = payload.get("rule_version")
    if rule_version != RULE_VERSION:
        _fail(
            "provider_payload.rule_version is invalid.",
            ExplanationRejectionCode.SCHEMA_MISMATCH,
        )

    overall_outcome = payload.get("overall_outcome")
    if not isinstance(overall_outcome, str) or overall_outcome not in _OUTCOME_VALUES:
        _fail(
            "provider_payload.overall_outcome is invalid.",
            ExplanationRejectionCode.SCHEMA_MISMATCH,
        )

    requirements = payload.get("requirements")
    if not isinstance(requirements, list):
        _fail(
            "provider_payload.requirements must be a list.",
            ExplanationRejectionCode.INVALID_FIELD_TYPE,
        )

    indexed: dict[int, dict[str, Any]] = {}
    for item in requirements:
        row = _require_dict(item, "provider_payload requirement")
        _require_exact_keys(
            row,
            _PAYLOAD_REQUIREMENT_KEYS,
            "provider_payload requirement",
        )
        index = _require_int(row.get("requirement_index"), "requirement_index")
        if index < 0:
            _fail(
                "requirement_index must be zero or greater.",
                ExplanationRejectionCode.INVALID_INDEX,
            )
        if index in indexed:
            _fail(
                "provider_payload requirement indexes must be unique.",
                ExplanationRejectionCode.DUPLICATE_INDEX,
            )

        _require_requirement_text(row.get("requirement_text"))

        classification = row.get("classification")
        if (
            not isinstance(classification, str)
            or classification not in _CLASSIFICATION_VALUES
        ):
            _fail(
                "provider_payload classification is invalid.",
                ExplanationRejectionCode.SCHEMA_MISMATCH,
            )

        match_basis = row.get("match_basis")
        if not isinstance(match_basis, str) or match_basis not in _MATCH_BASIS_VALUES:
            _fail(
                "provider_payload match_basis is invalid.",
                ExplanationRejectionCode.SCHEMA_MISMATCH,
            )

        matched_evidence_level = row.get("matched_evidence_level")
        if matched_evidence_level is not None:
            if (
                not isinstance(matched_evidence_level, str)
                or matched_evidence_level not in _EVIDENCE_LEVEL_VALUES
            ):
                _fail(
                    "matched_evidence_level is invalid.",
                    ExplanationRejectionCode.EVIDENCE_LEVEL_MISMATCH,
                )

        matched_skill_name = row.get("matched_skill_name")
        if matched_skill_name is not None:
            if not isinstance(matched_skill_name, str) or not matched_skill_name.strip():
                _fail(
                    "matched_skill_name must be a non-empty string or None.",
                    ExplanationRejectionCode.INVALID_FIELD_TYPE,
                )
            matched_skill_name = matched_skill_name.strip()

        unresolved = _require_bool(row.get("unresolved"), "unresolved")
        indexed[index] = {
            "classification": classification,
            "match_basis": match_basis,
            "matched_skill_name": matched_skill_name,
            "matched_evidence_level": matched_evidence_level,
            "unresolved": unresolved,
        }
    return indexed


def _require_list(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        _fail(
            f"{label} must be a list.",
            ExplanationRejectionCode.INVALID_FIELD_TYPE,
        )
    if len(value) > _ARRAY_MAX_ITEMS:
        _fail(
            f"{label} exceeds maximum item count.",
            ExplanationRejectionCode.OVERSIZED_FIELD,
        )
    return value


def _validate_skill_names(
    value: object,
    *,
    expected_skill_name: str | None,
    label: str,
) -> list[str]:
    if not isinstance(value, list):
        _fail(
            f"{label} must be a list.",
            ExplanationRejectionCode.INVALID_FIELD_TYPE,
        )
    if len(value) != 1:
        _fail(
            f"{label} must contain exactly one skill name.",
            ExplanationRejectionCode.SKILL_NAME_MISMATCH,
        )
    skill = value[0]
    if not isinstance(skill, str) or not skill.strip():
        _fail(
            f"{label} must contain exactly one non-empty string.",
            ExplanationRejectionCode.SKILL_NAME_MISMATCH,
        )
    cleaned = skill.strip()
    _assert_plain_text_and_claim_safe(cleaned, label=label)
    if expected_skill_name is None or cleaned != expected_skill_name:
        _fail(
            f"{label} does not match the deterministic matched_skill_name.",
            ExplanationRejectionCode.SKILL_NAME_MISMATCH,
        )
    return [cleaned]


def _validate_requirement_index(
    value: object,
    *,
    payload_index: dict[int, dict[str, Any]],
    seen_indexes: set[int],
    label: str,
) -> tuple[int, dict[str, Any]]:
    index = _require_int(value, label)
    if index not in payload_index:
        _fail(
            f"{label} is not present in provider_payload requirements.",
            ExplanationRejectionCode.INVALID_INDEX,
        )
    if index in seen_indexes:
        _fail(
            f"{label} appears more than once across output categories.",
            ExplanationRejectionCode.DUPLICATE_INDEX,
        )
    row = payload_index[index]
    if row["unresolved"]:
        _fail(
            f"{label} refers to an unresolved requirement.",
            ExplanationRejectionCode.UNSUPPORTED_EVIDENCE,
        )
    if row["classification"] == "REVIEW_REQUIRED":
        _fail(
            f"{label} refers to a REVIEW_REQUIRED requirement.",
            ExplanationRejectionCode.UNSUPPORTED_EVIDENCE,
        )
    seen_indexes.add(index)
    return index, row


def _assert_missing_source_consistent(source: dict[str, Any]) -> None:
    basis = source["match_basis"]
    skill = source["matched_skill_name"]
    level = source["matched_evidence_level"]
    if basis == "no_match":
        if skill is not None or level is not None:
            _fail(
                "NO_EVIDENCE_GAP no_match row fields are inconsistent.",
                ExplanationRejectionCode.SEMANTIC_CONTRADICTION,
            )
        return
    if basis == "no_evidence":
        if not isinstance(skill, str) or not skill:
            _fail(
                "NO_EVIDENCE_GAP no_evidence row requires matched_skill_name.",
                ExplanationRejectionCode.SEMANTIC_CONTRADICTION,
            )
        if level != "NO_EVIDENCE":
            _fail(
                "NO_EVIDENCE_GAP no_evidence row requires NO_EVIDENCE level.",
                ExplanationRejectionCode.EVIDENCE_LEVEL_MISMATCH,
            )
        return
    _fail(
        "NO_EVIDENCE_GAP match_basis is invalid for missing_evidence.",
        ExplanationRejectionCode.CATEGORY_MISMATCH,
    )


def _validate_verified_item(
    item: object,
    *,
    payload_index: dict[int, dict[str, Any]],
    seen_indexes: set[int],
) -> dict[str, Any]:
    row = _require_dict(item, "verified_evidence item")
    _require_exact_keys(row, _VERIFIED_ITEM_KEYS, "verified_evidence item")
    index, source = _validate_requirement_index(
        row.get("requirement_index"),
        payload_index=payload_index,
        seen_indexes=seen_indexes,
        label="verified_evidence.requirement_index",
    )
    if source["classification"] != "VERIFIED_MATCH":
        _fail(
            "verified_evidence item classification mismatch.",
            ExplanationRejectionCode.CATEGORY_MISMATCH,
        )
    skill_names = _validate_skill_names(
        row.get("skill_names"),
        expected_skill_name=source["matched_skill_name"],
        label="verified_evidence.skill_names",
    )
    explanation = _require_plain_string(
        row.get("explanation"),
        label="verified_evidence.explanation",
        max_length=_EXPLANATION_MAX_LEN,
    )
    return {
        "requirement_index": index,
        "skill_names": skill_names,
        "explanation": explanation,
    }


def _validate_development_item(
    item: object,
    *,
    payload_index: dict[int, dict[str, Any]],
    seen_indexes: set[int],
) -> dict[str, Any]:
    row = _require_dict(item, "development_evidence item")
    _require_exact_keys(row, _DEVELOPMENT_ITEM_KEYS, "development_evidence item")
    index, source = _validate_requirement_index(
        row.get("requirement_index"),
        payload_index=payload_index,
        seen_indexes=seen_indexes,
        label="development_evidence.requirement_index",
    )
    classification = source["classification"]
    if classification not in _CLASSIFICATION_TO_DEVELOPMENT_LEVEL:
        _fail(
            "development_evidence item classification mismatch.",
            ExplanationRejectionCode.CATEGORY_MISMATCH,
        )
    expected_level = _CLASSIFICATION_TO_DEVELOPMENT_LEVEL[classification]
    evidence_level = row.get("evidence_level")
    if not isinstance(evidence_level, str):
        _fail(
            "development_evidence.evidence_level must be a string.",
            ExplanationRejectionCode.INVALID_FIELD_TYPE,
        )
    if evidence_level not in _DEVELOPMENT_LEVELS:
        _fail(
            "development_evidence.evidence_level has an invalid value.",
            ExplanationRejectionCode.EVIDENCE_LEVEL_MISMATCH,
        )
    if evidence_level != expected_level:
        _fail(
            "development_evidence.evidence_level classification mismatch.",
            ExplanationRejectionCode.EVIDENCE_LEVEL_MISMATCH,
        )
    if evidence_level != source["matched_evidence_level"]:
        _fail(
            "development_evidence.evidence_level does not match payload.",
            ExplanationRejectionCode.EVIDENCE_LEVEL_MISMATCH,
        )
    skill_names = _validate_skill_names(
        row.get("skill_names"),
        expected_skill_name=source["matched_skill_name"],
        label="development_evidence.skill_names",
    )
    explanation = _require_plain_string(
        row.get("explanation"),
        label="development_evidence.explanation",
        max_length=_EXPLANATION_MAX_LEN,
    )
    return {
        "requirement_index": index,
        "skill_names": skill_names,
        "evidence_level": evidence_level,
        "explanation": explanation,
    }


def _validate_missing_item(
    item: object,
    *,
    payload_index: dict[int, dict[str, Any]],
    seen_indexes: set[int],
) -> dict[str, Any]:
    row = _require_dict(item, "missing_evidence item")
    _require_exact_keys(row, _MISSING_ITEM_KEYS, "missing_evidence item")
    index, source = _validate_requirement_index(
        row.get("requirement_index"),
        payload_index=payload_index,
        seen_indexes=seen_indexes,
        label="missing_evidence.requirement_index",
    )
    if source["classification"] != "NO_EVIDENCE_GAP":
        _fail(
            "missing_evidence item classification mismatch.",
            ExplanationRejectionCode.CATEGORY_MISMATCH,
        )
    _assert_missing_source_consistent(source)
    explanation = _require_plain_string(
        row.get("explanation"),
        label="missing_evidence.explanation",
        max_length=_EXPLANATION_MAX_LEN,
    )
    return {
        "requirement_index": index,
        "explanation": explanation,
    }


def validate_evidence_alignment_explanation_output(
    raw_output: object,
    provider_payload: dict[str, object],
) -> dict[str, object]:
    """Validate untrusted explanation output against the allowlisted payload.

    Returns a newly constructed validated dictionary. Raises
    EvidenceAlignmentExplanationValidationError on any failure. Does not mutate
    inputs.
    """
    payload_index = _index_provider_payload(provider_payload)
    output = _require_dict(raw_output, "raw_output")
    _require_exact_keys(output, _TOP_LEVEL_KEYS, "raw_output")

    summary = _require_plain_string(
        output.get("summary"),
        label="summary",
        max_length=_SUMMARY_MAX_LEN,
    )
    verified_raw = _require_list(
        output.get("verified_evidence"),
        "verified_evidence",
    )
    development_raw = _require_list(
        output.get("development_evidence"),
        "development_evidence",
    )
    missing_raw = _require_list(
        output.get("missing_evidence"),
        "missing_evidence",
    )

    seen_indexes: set[int] = set()
    verified = [
        _validate_verified_item(
            item,
            payload_index=payload_index,
            seen_indexes=seen_indexes,
        )
        for item in verified_raw
    ]
    development = [
        _validate_development_item(
            item,
            payload_index=payload_index,
            seen_indexes=seen_indexes,
        )
        for item in development_raw
    ]
    missing = [
        _validate_missing_item(
            item,
            payload_index=payload_index,
            seen_indexes=seen_indexes,
        )
        for item in missing_raw
    ]

    return {
        "summary": summary,
        "verified_evidence": verified,
        "development_evidence": development,
        "missing_evidence": missing,
    }

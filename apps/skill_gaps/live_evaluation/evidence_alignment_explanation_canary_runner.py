"""Pure Sprint 116 evidence-alignment canary runner.

The runner performs deterministic preparation and validation around one injected
telemetry provider call. It does not read settings, credentials, environment,
database state or files.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any

from apps.ai_agents.claude_provider import (
    CLAUDE_EVIDENCE_ALIGNMENT_MAX_TOKENS,
    CLAUDE_MODEL,
    ClaudeTelemetryProvider,
    ClaudeTelemetryResult,
    build_evidence_alignment_messages_create_kwargs,
    hash_request_payload,
)
from apps.skill_gaps.deterministic_evidence_alignment import (
    EvidenceAlignmentOutcome,
    summarise_evidence_alignment,
)
from apps.skill_gaps.deterministic_explanation_payload import (
    build_evidence_alignment_explanation_payload,
)
from apps.skill_gaps.deterministic_gap_classifier import (
    SkillLedgerEvidence,
    classify_requirements,
    normalise_requirement,
)
from apps.skill_gaps.explanation_output_validator import (
    EvidenceAlignmentExplanationValidationError,
    validate_evidence_alignment_explanation_output,
)
from apps.skill_gaps.live_evaluation.evidence_alignment_explanation_canary_contract import (
    contract_manifest_sha256,
    get_authoritative_canary_case,
    validate_canary_contract,
)

TEMPERATURE_CONFIGURATION = "NOT_EXPLICITLY_SET"
TEMPERATURE_SOURCE = "ANTHROPIC_SDK_OR_PROVIDER_DEFAULT"
TOP_P_CONFIGURATION = "NOT_EXPLICITLY_SET"
TOP_K_CONFIGURATION = "NOT_EXPLICITLY_SET"
THINKING_CONFIGURATION = "NOT_EXPLICITLY_SET"
_GENERATION_SETTING_KEYS = ("temperature", "top_p", "top_k", "thinking")

_HEX64_RE = re.compile(r"[0-9a-f]{64}")
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PROHIBITED_TEXT_PATTERNS = (
    re.compile(
        r"\b(?:hiring|readiness|suitability|qualification|qualified|proficiency)\b",
        re.I,
    ),
    re.compile(r"\b(?:api[_ -]?key|secret|bearer\s+|sk-ant-)\b", re.I),
    re.compile(r"\b(?:system prompt|developer message)\b", re.I),
)


class EvidenceAlignmentCanaryOutcome(str, Enum):
    INTEGRATION_SUCCESS_OUTPUT_ACCEPTED = "INTEGRATION_SUCCESS_OUTPUT_ACCEPTED"
    CONTROL_PASS_OUTPUT_SAFELY_REJECTED = "CONTROL_PASS_OUTPUT_SAFELY_REJECTED"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"
    INTEGRITY_FAILURE = "INTEGRITY_FAILURE"
    PRIVACY_OR_EVIDENCE_BOUNDARY_FAILURE = "PRIVACY_OR_EVIDENCE_BOUNDARY_FAILURE"
    HARNESS_DEFECT = "HARNESS_DEFECT"


@dataclass(frozen=True, slots=True)
class EvidenceAlignmentCanaryRunResult:
    """Safe immutable metadata returned by the pure canary runner."""

    outcome: EvidenceAlignmentCanaryOutcome
    case_id: str
    expected_deterministic_outcome: str
    contract_manifest_sha256: str
    contract_manifest_hash_match: bool
    request_payload_sha256: str | None
    request_payload_hash_match: bool
    hashes_are_distinct: bool
    attempted_call_count: int
    completed_call_count: int
    returned_model: str | None
    model_match: bool
    output_token_cap: int | None
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    stop_reason: str | None
    latency_ms: int | None
    parser_status: str
    validator_status: str
    validator_rejection_code: str | None
    manual_review_marker_present: bool
    persistence_count: int
    temperature_configuration: str
    temperature_source: str
    top_p_configuration: str
    top_k_configuration: str
    thinking_configuration: str
    accepted_explanation_summary: str | None
    safe_error_category: str | None
    raw_response_sha256: str | None


@dataclass(frozen=True, slots=True)
class _PreparedCanary:
    case_id: str
    expected_outcome: str
    contract_hash: str
    contract_hash_match: bool
    payload: dict[str, Any]
    request_hash: str
    request_hash_match: bool
    hashes_are_distinct: bool
    output_token_cap: int


def _base_result(
    *,
    case_id: str,
    expected_outcome: str,
    contract_hash: str,
) -> EvidenceAlignmentCanaryRunResult:
    return EvidenceAlignmentCanaryRunResult(
        outcome=EvidenceAlignmentCanaryOutcome.INTEGRITY_FAILURE,
        case_id=case_id,
        expected_deterministic_outcome=expected_outcome,
        contract_manifest_sha256=contract_hash,
        contract_manifest_hash_match=False,
        request_payload_sha256=None,
        request_payload_hash_match=False,
        hashes_are_distinct=False,
        attempted_call_count=0,
        completed_call_count=0,
        returned_model=None,
        model_match=False,
        output_token_cap=None,
        input_tokens=None,
        output_tokens=None,
        total_tokens=None,
        stop_reason=None,
        latency_ms=None,
        parser_status="not_run",
        validator_status="not_run",
        validator_rejection_code=None,
        manual_review_marker_present=False,
        persistence_count=0,
        temperature_configuration="",
        temperature_source="",
        top_p_configuration="",
        top_k_configuration="",
        thinking_configuration="",
        accepted_explanation_summary=None,
        safe_error_category=None,
        raw_response_sha256=None,
    )


def _build_authoritative_payload_and_request() -> tuple[
    dict[str, Any],
    dict[str, Any],
    str,
]:
    case = get_authoritative_canary_case()
    evidence = tuple(
        SkillLedgerEvidence(index, skill_name, evidence_level)
        for index, (skill_name, evidence_level) in enumerate(
            (
                *((skill, "VERIFIED") for skill in case.verified_skills),
                *(
                    (skill, "LEARNING_TARGET")
                    for skill in case.learning_target_skills
                ),
            ),
            start=1,
        )
    )
    raw_requirements = (
        *case.verified_skills,
        *case.learning_target_skills,
        *case.unmatched_requirements,
    )
    requirements = tuple(
        normalise_requirement(index, text)
        for index, text in enumerate(raw_requirements)
    )
    classified = classify_requirements(requirements, evidence)
    summary = summarise_evidence_alignment(classified)
    if summary.outcome is not EvidenceAlignmentOutcome.SOME_REQUIREMENTS_VERIFIED:
        raise ValueError("synthetic case produced an unexpected deterministic outcome.")
    if summary.outcome.value != case.expected_deterministic_outcome:
        raise ValueError("synthetic outcome differs from the locked contract.")
    payload = build_evidence_alignment_explanation_payload(summary)
    request_kwargs = build_evidence_alignment_messages_create_kwargs(payload)
    return payload, request_kwargs, summary.outcome.value


def _prepare_canary(
    *,
    expected_contract_manifest_sha256: str,
    expected_request_payload_sha256: str,
) -> tuple[_PreparedCanary | None, EvidenceAlignmentCanaryRunResult]:
    case = get_authoritative_canary_case()
    validate_canary_contract(case)
    contract_hash = contract_manifest_sha256()
    base = _base_result(
        case_id=case.case_id,
        expected_outcome=case.expected_deterministic_outcome,
        contract_hash=contract_hash,
    )
    contract_match = (
        isinstance(expected_contract_manifest_sha256, str)
        and _HEX64_RE.fullmatch(expected_contract_manifest_sha256) is not None
        and contract_hash == expected_contract_manifest_sha256
    )
    base = replace(base, contract_manifest_hash_match=contract_match)
    if not contract_match:
        return None, replace(base, safe_error_category="contract_manifest_hash_mismatch")

    try:
        payload, request_kwargs, _outcome = _build_authoritative_payload_and_request()
    except (TypeError, ValueError):
        return None, replace(
            base,
            outcome=EvidenceAlignmentCanaryOutcome.HARNESS_DEFECT,
            safe_error_category="deterministic_preparation_failure",
        )

    request_hash = hash_request_payload(request_kwargs)
    request_match = (
        isinstance(expected_request_payload_sha256, str)
        and _HEX64_RE.fullmatch(expected_request_payload_sha256) is not None
        and request_hash == expected_request_payload_sha256
    )
    hashes_are_distinct = contract_hash != request_hash
    base = replace(
        base,
        request_payload_sha256=request_hash,
        request_payload_hash_match=request_match,
        hashes_are_distinct=hashes_are_distinct,
        output_token_cap=request_kwargs.get("max_tokens"),
    )
    if request_kwargs.get("model") != CLAUDE_MODEL:
        return None, replace(
            base,
            outcome=EvidenceAlignmentCanaryOutcome.HARNESS_DEFECT,
            safe_error_category="request_model_mismatch",
        )
    if (
        request_kwargs.get("max_tokens") != CLAUDE_EVIDENCE_ALIGNMENT_MAX_TOKENS
        or request_kwargs.get("max_tokens") != 512
    ):
        return None, replace(
            base,
            outcome=EvidenceAlignmentCanaryOutcome.HARNESS_DEFECT,
            safe_error_category="request_token_cap_mismatch",
        )
    if any(key in request_kwargs for key in _GENERATION_SETTING_KEYS):
        return None, replace(
            base,
            outcome=EvidenceAlignmentCanaryOutcome.HARNESS_DEFECT,
            safe_error_category="generation_configuration_drift",
        )
    base = replace(
        base,
        temperature_configuration=TEMPERATURE_CONFIGURATION,
        temperature_source=TEMPERATURE_SOURCE,
        top_p_configuration=TOP_P_CONFIGURATION,
        top_k_configuration=TOP_K_CONFIGURATION,
        thinking_configuration=THINKING_CONFIGURATION,
    )
    if not request_match:
        return None, replace(base, safe_error_category="request_payload_hash_mismatch")
    if not hashes_are_distinct:
        return None, replace(base, safe_error_category="hash_type_collision")
    prepared = _PreparedCanary(
        case_id=case.case_id,
        expected_outcome=case.expected_deterministic_outcome,
        contract_hash=contract_hash,
        contract_hash_match=True,
        payload=payload,
        request_hash=request_hash,
        request_hash_match=True,
        hashes_are_distinct=True,
        output_token_cap=CLAUDE_EVIDENCE_ALIGNMENT_MAX_TOKENS,
    )
    return prepared, base


def _is_non_negative_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _iter_text(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, dict):
        return tuple(text for item in value.values() for text in _iter_text(item))
    if isinstance(value, (list, tuple)):
        return tuple(text for item in value for text in _iter_text(item))
    return ()


def _privacy_or_evidence_boundary_failure(parsed: dict[str, Any]) -> bool:
    verified_items = parsed.get("verified_evidence")
    if isinstance(verified_items, list):
        for item in verified_items:
            if not isinstance(item, dict):
                continue
            skill_names = item.get("skill_names")
            if isinstance(skill_names, list) and {
                name.casefold() for name in skill_names if isinstance(name, str)
            } & {"snowflake", "graphql"}:
                return True
    for text in _iter_text(parsed):
        if _EMAIL_RE.search(text):
            return True
        if any(pattern.search(text) for pattern in _PROHIBITED_TEXT_PATTERNS):
            return True
    return False


def _manual_review_marker_present(parsed: dict[str, Any]) -> bool:
    return any("manual review" in text.casefold() for text in _iter_text(parsed))


def _telemetry_integrity_error(
    telemetry: ClaudeTelemetryResult,
    *,
    expected_request_hash: str,
    completed_call_count: int,
) -> str | None:
    if completed_call_count != 1:
        return "completed_call_count_invalid"
    if telemetry.returned_model != CLAUDE_MODEL:
        return "returned_model_mismatch"
    if not _is_non_negative_int(telemetry.input_tokens):
        return "input_tokens_invalid"
    if not _is_non_negative_int(telemetry.output_tokens):
        return "output_tokens_invalid"
    if not isinstance(telemetry.stop_reason, str) or not telemetry.stop_reason:
        return "stop_reason_invalid"
    if not _is_non_negative_int(telemetry.latency_ms):
        return "latency_invalid"
    if (
        not isinstance(telemetry.request_payload_hash, str)
        or _HEX64_RE.fullmatch(telemetry.request_payload_hash) is None
        or telemetry.request_payload_hash != expected_request_hash
    ):
        return "telemetry_request_hash_invalid"
    return None


def _independent_raw_response_digest(
    telemetry: ClaudeTelemetryResult,
) -> tuple[str | None, str | None]:
    """Return (error_category, independently calculated digest)."""

    if (
        not isinstance(telemetry.serialised_raw_response, str)
        or not telemetry.serialised_raw_response
    ):
        return "raw_response_serialisation_unavailable", None
    independent_digest = hashlib.sha256(
        telemetry.serialised_raw_response.encode("utf-8")
    ).hexdigest()
    if (
        not isinstance(telemetry.raw_response_hash, str)
        or _HEX64_RE.fullmatch(telemetry.raw_response_hash) is None
    ):
        return "raw_response_hash_invalid", independent_digest
    if telemetry.raw_response_hash != independent_digest:
        return "raw_response_hash_mismatch", independent_digest
    return None, independent_digest


def run_evidence_alignment_explanation_canary(
    *,
    telemetry_provider: ClaudeTelemetryProvider,
    expected_contract_manifest_sha256: str,
    expected_request_payload_sha256: str,
) -> EvidenceAlignmentCanaryRunResult:
    """Run one synthetic canary call with no retry or persistence behavior."""

    prepared, base = _prepare_canary(
        expected_contract_manifest_sha256=expected_contract_manifest_sha256,
        expected_request_payload_sha256=expected_request_payload_sha256,
    )
    if prepared is None:
        return base

    attempted_call_count = 0
    completed_call_count = 0
    if attempted_call_count >= 1:
        return replace(
            base,
            outcome=EvidenceAlignmentCanaryOutcome.HARNESS_DEFECT,
            safe_error_category="provider_call_cap_reached",
        )
    attempted_call_count += 1
    try:
        telemetry = telemetry_provider(prepared.payload)
    except Exception as exc:  # noqa: BLE001 - isolate the injected provider boundary
        if isinstance(exc, (AssertionError, AttributeError, TypeError)):
            return replace(
                base,
                outcome=EvidenceAlignmentCanaryOutcome.HARNESS_DEFECT,
                attempted_call_count=attempted_call_count,
                safe_error_category="provider_contract_defect",
            )
        return replace(
            base,
            outcome=EvidenceAlignmentCanaryOutcome.PROVIDER_FAILURE,
            attempted_call_count=attempted_call_count,
            safe_error_category="provider_boundary_failure",
        )
    completed_call_count += 1

    if not isinstance(telemetry, ClaudeTelemetryResult):
        return replace(
            base,
            attempted_call_count=attempted_call_count,
            completed_call_count=completed_call_count,
            safe_error_category="telemetry_type_invalid",
        )
    integrity_error = _telemetry_integrity_error(
        telemetry,
        expected_request_hash=prepared.request_hash,
        completed_call_count=completed_call_count,
    )
    raw_error, independent_raw_digest = _independent_raw_response_digest(telemetry)
    if integrity_error is None and raw_error is not None:
        integrity_error = raw_error
    total_tokens = (
        telemetry.input_tokens + telemetry.output_tokens
        if _is_non_negative_int(telemetry.input_tokens)
        and _is_non_negative_int(telemetry.output_tokens)
        else None
    )
    result = replace(
        base,
        attempted_call_count=attempted_call_count,
        completed_call_count=completed_call_count,
        returned_model=(
            telemetry.returned_model
            if isinstance(telemetry.returned_model, str)
            else None
        ),
        model_match=telemetry.returned_model == CLAUDE_MODEL,
        input_tokens=(
            telemetry.input_tokens if _is_non_negative_int(telemetry.input_tokens) else None
        ),
        output_tokens=(
            telemetry.output_tokens
            if _is_non_negative_int(telemetry.output_tokens)
            else None
        ),
        total_tokens=total_tokens,
        stop_reason=(
            telemetry.stop_reason if isinstance(telemetry.stop_reason, str) else None
        ),
        latency_ms=(
            telemetry.latency_ms if _is_non_negative_int(telemetry.latency_ms) else None
        ),
        request_payload_hash_match=(
            telemetry.request_payload_hash == prepared.request_hash
        ),
        raw_response_sha256=independent_raw_digest,
    )
    if integrity_error is not None:
        return replace(result, safe_error_category=integrity_error)
    if telemetry.parsed_payload is None or telemetry.parse_error_category is not None:
        return replace(
            result,
            parser_status="rejected",
            safe_error_category=telemetry.parse_error_category or "parser_rejection",
        )
    if not isinstance(telemetry.parsed_payload, dict):
        return replace(
            result,
            parser_status="rejected",
            safe_error_category="parsed_payload_type_invalid",
        )

    parsed = telemetry.parsed_payload
    manual_review = _manual_review_marker_present(parsed)
    if _privacy_or_evidence_boundary_failure(parsed):
        return replace(
            result,
            outcome=EvidenceAlignmentCanaryOutcome.PRIVACY_OR_EVIDENCE_BOUNDARY_FAILURE,
            parser_status="accepted",
            validator_status="not_run",
            manual_review_marker_present=manual_review,
            safe_error_category="privacy_or_evidence_boundary",
        )
    try:
        validated = validate_evidence_alignment_explanation_output(
            parsed,
            prepared.payload,
        )
    except EvidenceAlignmentExplanationValidationError as exc:
        return replace(
            result,
            outcome=(
                EvidenceAlignmentCanaryOutcome.CONTROL_PASS_OUTPUT_SAFELY_REJECTED
            ),
            parser_status="accepted",
            validator_status="rejected",
            validator_rejection_code=exc.code.value if exc.code is not None else None,
            manual_review_marker_present=manual_review,
            safe_error_category="validator_rejection",
        )
    return replace(
        result,
        outcome=EvidenceAlignmentCanaryOutcome.INTEGRATION_SUCCESS_OUTPUT_ACCEPTED,
        parser_status="accepted",
        validator_status="accepted",
        manual_review_marker_present=manual_review,
        accepted_explanation_summary=validated["summary"],
        safe_error_category=None,
    )

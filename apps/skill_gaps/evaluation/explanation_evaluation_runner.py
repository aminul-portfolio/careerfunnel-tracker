"""Sprint 115 Phase 4: pure offline evidence-alignment explanation evaluation runner.

Deterministic case replay through the real classifier, summariser, payload builder
and output validator. No provider, network, ORM or filesystem access.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

from apps.skill_gaps.deterministic_evidence_alignment import (
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
from apps.skill_gaps.evaluation.explanation_evaluation_cases import (
    CASE_SCHEMA_VERSION,
    EVALUATION_VERSION,
    EVIDENCE_ALIGNMENT_RULE_VERSION,
    EvaluationCase,
    EvaluationCaseContractError,
    compute_case_set_hash,
    validate_and_sort_evaluation_cases,
)
from apps.skill_gaps.explanation_output_validator import (
    EvidenceAlignmentExplanationValidationError,
    ExplanationRejectionCode,
    validate_evidence_alignment_explanation_output,
)

RUNNER_VERSION = "evidence_alignment_explanation_runner_v1"
REPORT_SCHEMA_VERSION = "evidence_alignment_explanation_report_v1"


class EvaluationRunnerCode(str, Enum):
    ACCEPTED_AS_EXPECTED = "ACCEPTED_AS_EXPECTED"
    REJECTED_AS_EXPECTED = "REJECTED_AS_EXPECTED"
    UNEXPECTED_ACCEPTANCE = "UNEXPECTED_ACCEPTANCE"
    UNEXPECTED_REJECTION = "UNEXPECTED_REJECTION"
    PAYLOAD_MISMATCH = "PAYLOAD_MISMATCH"
    CASE_SCHEMA_FAILURE = "CASE_SCHEMA_FAILURE"
    RUNNER_CONTRACT_FAILURE = "RUNNER_CONTRACT_FAILURE"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"


@dataclass(frozen=True)
class EvaluationCaseRunResult:
    """Immutable per-case offline evaluation result."""

    case_id: str
    category: str
    expected_acceptance: bool
    actual_acceptance: bool
    expected_rejection_code: str | None
    actual_rejection_code: str | None
    runner_code: EvaluationRunnerCode
    passed: bool
    message: str


@dataclass(frozen=True)
class EvidenceAlignmentExplanationEvaluationReport:
    """Immutable offline evaluation report with stable SHA-256 digest."""

    report_schema_version: str
    runner_version: str
    evaluation_version: str
    case_schema_version: str
    rule_version: str
    case_set_sha256: str
    overall_result: str
    total_case_count: int
    passed_case_count: int
    failed_case_count: int
    expected_acceptance_count: int
    expected_rejection_count: int
    accepted_as_expected_count: int
    rejected_as_expected_count: int
    unexpected_acceptance_count: int
    unexpected_rejection_count: int
    payload_mismatch_count: int
    case_schema_failure_count: int
    runner_contract_failure_count: int
    provider_failure_count: int
    validator_call_count: int
    provider_call_count: int
    network_call_count: int
    orm_access_count: int
    database_write_count: int
    runner_filesystem_write_count: int
    results: tuple[EvaluationCaseRunResult, ...]
    report_sha256: str


def _immutable_to_plain(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _immutable_to_plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_immutable_to_plain(item) for item in value]
    return value


def _json_copy(value: object) -> object:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _rejection_code_value(
    code: ExplanationRejectionCode | None,
) -> str | None:
    if code is None:
        return None
    return code.value


def _build_actual_payload(case: EvaluationCase) -> dict[str, Any]:
    builder_input = case.builder_input
    if builder_input is None:
        raise EvaluationCaseContractError(
            "builder_input is required for offline evaluation execution."
        )
    requirements_raw = builder_input["requirements"]
    evidence_raw = builder_input["evidence"]
    evidence = tuple(
        SkillLedgerEvidence(
            entry_id=int(item["entry_id"]),
            skill_name=str(item["skill_name"]),
            evidence_level=str(item["evidence_level"]),
        )
        for item in evidence_raw
    )
    requirements = tuple(
        normalise_requirement(index, str(text))
        for index, text in enumerate(requirements_raw)
    )
    classified = classify_requirements(requirements, evidence)
    summary = summarise_evidence_alignment(classified)
    payload = build_evidence_alignment_explanation_payload(summary)
    if not isinstance(payload, dict):
        raise TypeError("payload builder must return a dict.")
    return payload


def _run_single_case(
    case: EvaluationCase,
) -> tuple[EvaluationCaseRunResult, int]:
    """Execute one case. Returns (result, validator_call_count_delta)."""
    expected_code = _rejection_code_value(case.expected_rejection_code)
    category = case.category.value

    try:
        actual_payload = _build_actual_payload(case)
    except Exception as exc:  # noqa: BLE001 - map to runner-owned failure
        return (
            EvaluationCaseRunResult(
                case_id=case.case_id,
                category=category,
                expected_acceptance=case.expected_acceptance,
                actual_acceptance=False,
                expected_rejection_code=expected_code,
                actual_rejection_code=None,
                runner_code=EvaluationRunnerCode.RUNNER_CONTRACT_FAILURE,
                passed=False,
                message=(
                    "Runner failed while building the deterministic payload: "
                    f"{exc.__class__.__name__}."
                ),
            ),
            0,
        )

    expected_payload = _immutable_to_plain(case.expected_provider_payload)
    if actual_payload != expected_payload:
        return (
            EvaluationCaseRunResult(
                case_id=case.case_id,
                category=category,
                expected_acceptance=case.expected_acceptance,
                actual_acceptance=False,
                expected_rejection_code=expected_code,
                actual_rejection_code=None,
                runner_code=EvaluationRunnerCode.PAYLOAD_MISMATCH,
                passed=False,
                message=(
                    "Actual payload-builder output differs from the pinned "
                    "expected provider payload."
                ),
            ),
            0,
        )

    try:
        parsed_output = json.loads(case.simulated_provider_output)
    except json.JSONDecodeError:
        return (
            EvaluationCaseRunResult(
                case_id=case.case_id,
                category=category,
                expected_acceptance=case.expected_acceptance,
                actual_acceptance=False,
                expected_rejection_code=expected_code,
                actual_rejection_code=None,
                runner_code=EvaluationRunnerCode.RUNNER_CONTRACT_FAILURE,
                passed=False,
                message="simulated_provider_output is not valid JSON.",
            ),
            0,
        )

    payload_for_validator = _json_copy(actual_payload)
    output_for_validator = _json_copy(parsed_output)

    try:
        validate_evidence_alignment_explanation_output(
            output_for_validator,
            payload_for_validator,
        )
    except EvidenceAlignmentExplanationValidationError as exc:
        actual_code = _rejection_code_value(exc.code)
        if case.expected_acceptance is False and actual_code == expected_code:
            return (
                EvaluationCaseRunResult(
                    case_id=case.case_id,
                    category=category,
                    expected_acceptance=False,
                    actual_acceptance=False,
                    expected_rejection_code=expected_code,
                    actual_rejection_code=actual_code,
                    runner_code=EvaluationRunnerCode.REJECTED_AS_EXPECTED,
                    passed=True,
                    message=(
                        "Validator rejected output with the expected "
                        "ExplanationRejectionCode."
                    ),
                ),
                1,
            )
        return (
            EvaluationCaseRunResult(
                case_id=case.case_id,
                category=category,
                expected_acceptance=case.expected_acceptance,
                actual_acceptance=False,
                expected_rejection_code=expected_code,
                actual_rejection_code=actual_code,
                runner_code=EvaluationRunnerCode.UNEXPECTED_REJECTION,
                passed=False,
                message=(
                    "Validator rejected output with an unexpected "
                    "ExplanationRejectionCode."
                ),
            ),
            1,
        )
    except Exception as exc:  # noqa: BLE001 - map to runner-owned failure
        return (
            EvaluationCaseRunResult(
                case_id=case.case_id,
                category=category,
                expected_acceptance=case.expected_acceptance,
                actual_acceptance=False,
                expected_rejection_code=expected_code,
                actual_rejection_code=None,
                runner_code=EvaluationRunnerCode.RUNNER_CONTRACT_FAILURE,
                passed=False,
                message=(
                    "Runner failed during validator execution: "
                    f"{exc.__class__.__name__}."
                ),
            ),
            1,
        )

    if case.expected_acceptance is True:
        return (
            EvaluationCaseRunResult(
                case_id=case.case_id,
                category=category,
                expected_acceptance=True,
                actual_acceptance=True,
                expected_rejection_code=None,
                actual_rejection_code=None,
                runner_code=EvaluationRunnerCode.ACCEPTED_AS_EXPECTED,
                passed=True,
                message="Validator accepted output as expected.",
            ),
            1,
        )

    return (
        EvaluationCaseRunResult(
            case_id=case.case_id,
            category=category,
            expected_acceptance=False,
            actual_acceptance=True,
            expected_rejection_code=expected_code,
            actual_rejection_code=None,
            runner_code=EvaluationRunnerCode.UNEXPECTED_ACCEPTANCE,
            passed=False,
            message="Validator accepted output that was expected to be rejected.",
        ),
        1,
    )


def evaluation_case_run_result_to_canonical_dict(
    result: EvaluationCaseRunResult,
) -> dict[str, Any]:
    return {
        "actual_acceptance": result.actual_acceptance,
        "actual_rejection_code": result.actual_rejection_code,
        "case_id": result.case_id,
        "category": result.category,
        "expected_acceptance": result.expected_acceptance,
        "expected_rejection_code": result.expected_rejection_code,
        "message": result.message,
        "passed": result.passed,
        "runner_code": result.runner_code.value,
    }


def evaluation_report_to_canonical_dict(
    report: EvidenceAlignmentExplanationEvaluationReport,
) -> dict[str, Any]:
    """Canonical report content excluding report_sha256."""
    return {
        "accepted_as_expected_count": report.accepted_as_expected_count,
        "case_schema_failure_count": report.case_schema_failure_count,
        "case_schema_version": report.case_schema_version,
        "case_set_sha256": report.case_set_sha256,
        "database_write_count": report.database_write_count,
        "evaluation_version": report.evaluation_version,
        "expected_acceptance_count": report.expected_acceptance_count,
        "expected_rejection_count": report.expected_rejection_count,
        "failed_case_count": report.failed_case_count,
        "network_call_count": report.network_call_count,
        "orm_access_count": report.orm_access_count,
        "overall_result": report.overall_result,
        "passed_case_count": report.passed_case_count,
        "payload_mismatch_count": report.payload_mismatch_count,
        "provider_call_count": report.provider_call_count,
        "provider_failure_count": report.provider_failure_count,
        "rejected_as_expected_count": report.rejected_as_expected_count,
        "report_schema_version": report.report_schema_version,
        "results": [
            evaluation_case_run_result_to_canonical_dict(item)
            for item in report.results
        ],
        "rule_version": report.rule_version,
        "runner_contract_failure_count": report.runner_contract_failure_count,
        "runner_filesystem_write_count": report.runner_filesystem_write_count,
        "runner_version": report.runner_version,
        "total_case_count": report.total_case_count,
        "unexpected_acceptance_count": report.unexpected_acceptance_count,
        "unexpected_rejection_count": report.unexpected_rejection_count,
        "validator_call_count": report.validator_call_count,
    }


def canonical_evaluation_report_bytes(
    report: EvidenceAlignmentExplanationEvaluationReport,
) -> bytes:
    text = json.dumps(
        evaluation_report_to_canonical_dict(report),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return text.encode("utf-8")


def compute_evaluation_report_hash(
    report: EvidenceAlignmentExplanationEvaluationReport,
) -> str:
    return hashlib.sha256(canonical_evaluation_report_bytes(report)).hexdigest()


def _count_runner_code(
    results: tuple[EvaluationCaseRunResult, ...],
    code: EvaluationRunnerCode,
) -> int:
    return sum(1 for item in results if item.runner_code is code)


def _assemble_report(
    *,
    case_set_sha256: str,
    results: tuple[EvaluationCaseRunResult, ...],
    validator_call_count: int,
) -> EvidenceAlignmentExplanationEvaluationReport:
    passed_case_count = sum(1 for item in results if item.passed)
    failed_case_count = len(results) - passed_case_count
    expected_acceptance_count = sum(
        1 for item in results if item.expected_acceptance is True
    )
    expected_rejection_count = sum(
        1 for item in results if item.expected_acceptance is False
    )
    overall_result = "PASS" if failed_case_count == 0 else "FAIL"
    draft = EvidenceAlignmentExplanationEvaluationReport(
        report_schema_version=REPORT_SCHEMA_VERSION,
        runner_version=RUNNER_VERSION,
        evaluation_version=EVALUATION_VERSION,
        case_schema_version=CASE_SCHEMA_VERSION,
        rule_version=EVIDENCE_ALIGNMENT_RULE_VERSION,
        case_set_sha256=case_set_sha256,
        overall_result=overall_result,
        total_case_count=len(results),
        passed_case_count=passed_case_count,
        failed_case_count=failed_case_count,
        expected_acceptance_count=expected_acceptance_count,
        expected_rejection_count=expected_rejection_count,
        accepted_as_expected_count=_count_runner_code(
            results,
            EvaluationRunnerCode.ACCEPTED_AS_EXPECTED,
        ),
        rejected_as_expected_count=_count_runner_code(
            results,
            EvaluationRunnerCode.REJECTED_AS_EXPECTED,
        ),
        unexpected_acceptance_count=_count_runner_code(
            results,
            EvaluationRunnerCode.UNEXPECTED_ACCEPTANCE,
        ),
        unexpected_rejection_count=_count_runner_code(
            results,
            EvaluationRunnerCode.UNEXPECTED_REJECTION,
        ),
        payload_mismatch_count=_count_runner_code(
            results,
            EvaluationRunnerCode.PAYLOAD_MISMATCH,
        ),
        case_schema_failure_count=_count_runner_code(
            results,
            EvaluationRunnerCode.CASE_SCHEMA_FAILURE,
        ),
        runner_contract_failure_count=_count_runner_code(
            results,
            EvaluationRunnerCode.RUNNER_CONTRACT_FAILURE,
        ),
        provider_failure_count=_count_runner_code(
            results,
            EvaluationRunnerCode.PROVIDER_FAILURE,
        ),
        validator_call_count=validator_call_count,
        provider_call_count=0,
        network_call_count=0,
        orm_access_count=0,
        database_write_count=0,
        runner_filesystem_write_count=0,
        results=results,
        report_sha256="",
    )
    digest = compute_evaluation_report_hash(draft)
    return EvidenceAlignmentExplanationEvaluationReport(
        report_schema_version=draft.report_schema_version,
        runner_version=draft.runner_version,
        evaluation_version=draft.evaluation_version,
        case_schema_version=draft.case_schema_version,
        rule_version=draft.rule_version,
        case_set_sha256=draft.case_set_sha256,
        overall_result=draft.overall_result,
        total_case_count=draft.total_case_count,
        passed_case_count=draft.passed_case_count,
        failed_case_count=draft.failed_case_count,
        expected_acceptance_count=draft.expected_acceptance_count,
        expected_rejection_count=draft.expected_rejection_count,
        accepted_as_expected_count=draft.accepted_as_expected_count,
        rejected_as_expected_count=draft.rejected_as_expected_count,
        unexpected_acceptance_count=draft.unexpected_acceptance_count,
        unexpected_rejection_count=draft.unexpected_rejection_count,
        payload_mismatch_count=draft.payload_mismatch_count,
        case_schema_failure_count=draft.case_schema_failure_count,
        runner_contract_failure_count=draft.runner_contract_failure_count,
        provider_failure_count=draft.provider_failure_count,
        validator_call_count=draft.validator_call_count,
        provider_call_count=draft.provider_call_count,
        network_call_count=draft.network_call_count,
        orm_access_count=draft.orm_access_count,
        database_write_count=draft.database_write_count,
        runner_filesystem_write_count=draft.runner_filesystem_write_count,
        results=draft.results,
        report_sha256=digest,
    )


def _schema_failure_report(
    message: str,
) -> EvidenceAlignmentExplanationEvaluationReport:
    result = EvaluationCaseRunResult(
        case_id="case-schema-failure",
        category="CASE_SCHEMA_FAILURE",
        expected_acceptance=False,
        actual_acceptance=False,
        expected_rejection_code=None,
        actual_rejection_code=None,
        runner_code=EvaluationRunnerCode.CASE_SCHEMA_FAILURE,
        passed=False,
        message=message,
    )
    return _assemble_report(
        case_set_sha256="",
        results=(result,),
        validator_call_count=0,
    )


def run_evidence_alignment_explanation_evaluation(
    cases: Iterable[EvaluationCase],
) -> EvidenceAlignmentExplanationEvaluationReport:
    """Run offline evaluation cases through the real Sprint 114 pipeline."""
    materialised = tuple(cases)
    try:
        sorted_cases = validate_and_sort_evaluation_cases(materialised)
        case_set_sha256 = compute_case_set_hash(sorted_cases)
    except EvaluationCaseContractError as exc:
        return _schema_failure_report(str(exc))

    results: list[EvaluationCaseRunResult] = []
    validator_call_count = 0
    for case in sorted_cases:
        result, delta = _run_single_case(case)
        results.append(result)
        validator_call_count += delta

    ordered = tuple(sorted(results, key=lambda item: item.case_id))
    return _assemble_report(
        case_set_sha256=case_set_sha256,
        results=ordered,
        validator_call_count=validator_call_count,
    )


def evaluation_report_to_json_dict(
    report: EvidenceAlignmentExplanationEvaluationReport,
) -> dict[str, Any]:
    """Serialisable report dict including report_sha256 for external output."""
    data = evaluation_report_to_canonical_dict(report)
    data["report_sha256"] = report.report_sha256
    return data

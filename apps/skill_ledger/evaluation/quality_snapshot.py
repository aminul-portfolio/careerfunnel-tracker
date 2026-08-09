"""Sprint 122 Phase 2: deterministic typed AI quality snapshots.

Pure transformation of existing Sprint 120/121 evaluation reports.
No evaluator execution, network, persistence, or regression comparison.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from apps.skill_ledger.evaluation.rag_evaluation_runner import (
    RagAdversarialRetrievalRunResult,
    RagFinalEvaluationReport,
    RagGenerationSafetyRunResult,
    RagRetrievalQualityRunResult,
)
from apps.skill_ledger.evaluation.tool_assistant_runner import (
    ToolAssistantCaseRunResult,
    ToolAssistantEvaluationReport,
)

QUALITY_SNAPSHOT_SCHEMA_VERSION = 1

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_CANDIDATE_SHA_RE = re.compile(r"^[0-9a-f]{7,64}$")


class QualitySnapshotContractError(ValueError):
    """Raised when a quality snapshot contract fails structural validation."""


class EvaluationFamily(str, Enum):
    RAG_FINAL = "RAG_FINAL"
    TOOL_ASSISTANT = "TOOL_ASSISTANT"


class CaseOutcome(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


def _require_non_negative_int(value: object, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise QualitySnapshotContractError(f"{field_name} must be an int.")
    if value < 0:
        raise QualitySnapshotContractError(f"{field_name} must be >= 0.")
    return value


def _require_sha256(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise QualitySnapshotContractError(
            f"{field_name} must be a lowercase 64-character hex SHA-256 digest."
        )
    return value


def _normalise_candidate_sha(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise QualitySnapshotContractError(
            "candidate_sha must be None or a hex string."
        )
    normalised = value.strip().lower()
    if not _CANDIDATE_SHA_RE.fullmatch(normalised):
        raise QualitySnapshotContractError(
            "candidate_sha must be 7..64 lowercase hexadecimal characters."
        )
    return normalised


def _jsonish(value: object) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise QualitySnapshotContractError(
                "non-finite floats are not allowed."
            )
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _jsonish(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonish(item) for item in value]
    raise QualitySnapshotContractError(
        f"unsupported fingerprint value type: {type(value).__name__}."
    )


def _canonical_bytes(payload: Mapping[str, Any]) -> bytes:
    text = json.dumps(
        _jsonish(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return text.encode("utf-8")


def _sha256_hex(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _outcome_from_passed(passed: bool) -> CaseOutcome:
    if not isinstance(passed, bool):
        raise QualitySnapshotContractError("passed must be a bool.")
    return CaseOutcome.PASS if passed else CaseOutcome.FAIL


def _normalise_case_snapshots(
    cases: Sequence[PerCaseQualitySnapshot],
) -> tuple[PerCaseQualitySnapshot, ...]:
    if not isinstance(cases, (list, tuple)):
        raise QualitySnapshotContractError("cases must be a sequence.")
    normalised: list[PerCaseQualitySnapshot] = []
    seen: set[str] = set()
    for item in cases:
        if not isinstance(item, PerCaseQualitySnapshot):
            raise QualitySnapshotContractError(
                "cases must contain PerCaseQualitySnapshot values."
            )
        if not isinstance(item.case_id, str) or not item.case_id.strip():
            raise QualitySnapshotContractError(
                "case_id must be a non-empty string."
            )
        case_id = item.case_id
        if case_id in seen:
            raise QualitySnapshotContractError(
                f"duplicate case_id is not allowed: {case_id}."
            )
        seen.add(case_id)
        normalised.append(item)
    return tuple(sorted(normalised, key=lambda value: value.case_id))


def _reconcile_counts(
    *,
    cases: tuple[PerCaseQualitySnapshot, ...],
    candidate_case_count: int,
    passed_count: int,
    failed_count: int,
) -> None:
    if candidate_case_count != len(cases):
        raise QualitySnapshotContractError(
            "candidate_case_count must equal len(cases)."
        )
    if passed_count + failed_count != candidate_case_count:
        raise QualitySnapshotContractError(
            "passed_count + failed_count must equal candidate_case_count."
        )
    actual_pass = sum(1 for item in cases if item.outcome is CaseOutcome.PASS)
    actual_fail = sum(1 for item in cases if item.outcome is CaseOutcome.FAIL)
    if passed_count != actual_pass:
        raise QualitySnapshotContractError(
            "passed_count must equal the number of PASS cases."
        )
    if failed_count != actual_fail:
        raise QualitySnapshotContractError(
            "failed_count must equal the number of FAIL cases."
        )


@dataclass(frozen=True)
class PerCaseQualitySnapshot:
    case_id: str
    outcome: CaseOutcome
    result_fingerprint: str

    def __post_init__(self) -> None:
        if not isinstance(self.case_id, str) or not self.case_id.strip():
            raise QualitySnapshotContractError(
                "case_id must be a non-empty string."
            )
        if not isinstance(self.outcome, CaseOutcome):
            raise QualitySnapshotContractError(
                "outcome must be a CaseOutcome value."
            )
        object.__setattr__(
            self,
            "result_fingerprint",
            _require_sha256(
                self.result_fingerprint,
                field_name="result_fingerprint",
            ),
        )


@dataclass(frozen=True)
class RagQualitySnapshot:
    evaluation_family: EvaluationFamily
    case_set_sha256: str
    candidate_case_count: int
    passed_count: int
    failed_count: int
    cases: tuple[PerCaseQualitySnapshot, ...]
    network_call_count: int
    live_embedding_call_count: int
    live_llm_call_count: int
    report_sha256: str

    def __post_init__(self) -> None:
        if self.evaluation_family is not EvaluationFamily.RAG_FINAL:
            raise QualitySnapshotContractError(
                "RagQualitySnapshot.evaluation_family must be RAG_FINAL."
            )
        object.__setattr__(
            self,
            "case_set_sha256",
            _require_sha256(self.case_set_sha256, field_name="case_set_sha256"),
        )
        object.__setattr__(
            self,
            "report_sha256",
            _require_sha256(self.report_sha256, field_name="report_sha256"),
        )
        cases = _normalise_case_snapshots(self.cases)
        object.__setattr__(self, "cases", cases)
        candidate_case_count = _require_non_negative_int(
            self.candidate_case_count,
            field_name="candidate_case_count",
        )
        passed_count = _require_non_negative_int(
            self.passed_count,
            field_name="passed_count",
        )
        failed_count = _require_non_negative_int(
            self.failed_count,
            field_name="failed_count",
        )
        object.__setattr__(self, "candidate_case_count", candidate_case_count)
        object.__setattr__(self, "passed_count", passed_count)
        object.__setattr__(self, "failed_count", failed_count)
        object.__setattr__(
            self,
            "network_call_count",
            _require_non_negative_int(
                self.network_call_count,
                field_name="network_call_count",
            ),
        )
        object.__setattr__(
            self,
            "live_embedding_call_count",
            _require_non_negative_int(
                self.live_embedding_call_count,
                field_name="live_embedding_call_count",
            ),
        )
        object.__setattr__(
            self,
            "live_llm_call_count",
            _require_non_negative_int(
                self.live_llm_call_count,
                field_name="live_llm_call_count",
            ),
        )
        _reconcile_counts(
            cases=cases,
            candidate_case_count=candidate_case_count,
            passed_count=passed_count,
            failed_count=failed_count,
        )


@dataclass(frozen=True)
class ToolAssistantQualitySnapshot:
    evaluation_family: EvaluationFamily
    case_set_sha256: str
    candidate_case_count: int
    passed_count: int
    failed_count: int
    cases: tuple[PerCaseQualitySnapshot, ...]
    network_call_count: int
    live_provider_call_count: int
    report_sha256: str

    def __post_init__(self) -> None:
        if self.evaluation_family is not EvaluationFamily.TOOL_ASSISTANT:
            raise QualitySnapshotContractError(
                "ToolAssistantQualitySnapshot.evaluation_family must be "
                "TOOL_ASSISTANT."
            )
        object.__setattr__(
            self,
            "case_set_sha256",
            _require_sha256(self.case_set_sha256, field_name="case_set_sha256"),
        )
        object.__setattr__(
            self,
            "report_sha256",
            _require_sha256(self.report_sha256, field_name="report_sha256"),
        )
        cases = _normalise_case_snapshots(self.cases)
        object.__setattr__(self, "cases", cases)
        candidate_case_count = _require_non_negative_int(
            self.candidate_case_count,
            field_name="candidate_case_count",
        )
        passed_count = _require_non_negative_int(
            self.passed_count,
            field_name="passed_count",
        )
        failed_count = _require_non_negative_int(
            self.failed_count,
            field_name="failed_count",
        )
        object.__setattr__(self, "candidate_case_count", candidate_case_count)
        object.__setattr__(self, "passed_count", passed_count)
        object.__setattr__(self, "failed_count", failed_count)
        object.__setattr__(
            self,
            "network_call_count",
            _require_non_negative_int(
                self.network_call_count,
                field_name="network_call_count",
            ),
        )
        object.__setattr__(
            self,
            "live_provider_call_count",
            _require_non_negative_int(
                self.live_provider_call_count,
                field_name="live_provider_call_count",
            ),
        )
        _reconcile_counts(
            cases=cases,
            candidate_case_count=candidate_case_count,
            passed_count=passed_count,
            failed_count=failed_count,
        )


@dataclass(frozen=True)
class AiQualitySnapshot:
    schema_version: int
    rag: RagQualitySnapshot
    tool_assistant: ToolAssistantQualitySnapshot
    privacy_violation_count: int
    candidate_sha: str | None

    def __post_init__(self) -> None:
        if self.schema_version != QUALITY_SNAPSHOT_SCHEMA_VERSION:
            raise QualitySnapshotContractError(
                f"schema_version must be {QUALITY_SNAPSHOT_SCHEMA_VERSION}."
            )
        if not isinstance(self.rag, RagQualitySnapshot):
            raise QualitySnapshotContractError("rag must be RagQualitySnapshot.")
        if not isinstance(self.tool_assistant, ToolAssistantQualitySnapshot):
            raise QualitySnapshotContractError(
                "tool_assistant must be ToolAssistantQualitySnapshot."
            )
        object.__setattr__(
            self,
            "privacy_violation_count",
            _require_non_negative_int(
                self.privacy_violation_count,
                field_name="privacy_violation_count",
            ),
        )
        object.__setattr__(
            self,
            "candidate_sha",
            _normalise_candidate_sha(self.candidate_sha),
        )


def fingerprint_rag_retrieval_quality_result(
    result: RagRetrievalQualityRunResult,
) -> str:
    payload = {
        "case_id": result.case_id,
        "category": result.category,
        "expected_recall_at_5": result.expected_recall_at_5,
        "mrr": result.mrr,
        "passed": result.passed,
        "ranked_local_ids": list(result.ranked_local_ids),
        "recall_at_1": result.recall_at_1,
        "recall_at_5": result.recall_at_5,
    }
    return _sha256_hex(payload)


def fingerprint_rag_adversarial_result(
    result: RagAdversarialRetrievalRunResult,
) -> str:
    payload = {
        "adversarial_mode": result.adversarial_mode,
        "case_id": result.case_id,
        "category": result.category,
        "passed": result.passed,
        "ranked_local_ids": list(result.ranked_local_ids),
    }
    return _sha256_hex(payload)


def fingerprint_rag_generation_safety_result(
    result: RagGenerationSafetyRunResult,
) -> str:
    payload = {
        "actual_acceptance": result.actual_acceptance,
        "actual_final_rendered_labels": (
            None
            if result.actual_final_rendered_labels is None
            else list(result.actual_final_rendered_labels)
        ),
        "actual_provider_called": result.actual_provider_called,
        "actual_rejection_code": result.actual_rejection_code,
        "case_id": result.case_id,
        "category": result.category,
        "evidence_fence_present": result.evidence_fence_present,
        "expected_acceptance": result.expected_acceptance,
        "expected_final_rendered_labels": (
            None
            if result.expected_final_rendered_labels is None
            else list(result.expected_final_rendered_labels)
        ),
        "expected_provider_called": result.expected_provider_called,
        "expected_rejection_code": result.expected_rejection_code,
        "passed": result.passed,
        "provider_call_count": result.provider_call_count,
        "query_fence_present": result.query_fence_present,
        "raw_evidence_sentinel_leaked": result.raw_evidence_sentinel_leaked,
        "raw_query_sentinel_leaked": result.raw_query_sentinel_leaked,
    }
    return _sha256_hex(payload)


def fingerprint_tool_assistant_case_result(
    result: ToolAssistantCaseRunResult,
) -> str:
    payload = {
        "case_id": result.case_id,
        "category": result.category,
        "expected_outcome": result.expected_outcome,
        "expected_source_refs": list(result.expected_source_refs),
        "network_call_count": result.network_call_count,
        "observed_outcome": result.observed_outcome,
        "passed": result.passed,
        "planner_calls": result.planner_calls,
        "sources_count": result.sources_count,
        "synthesis_calls": result.synthesis_calls,
        "threat_ids": list(result.threat_ids),
        "tools_executed": result.tools_executed,
        "tools_used": list(result.tools_used),
    }
    return _sha256_hex(payload)


def _per_case(
    *,
    case_id: str,
    passed: bool,
    result_fingerprint: str,
) -> PerCaseQualitySnapshot:
    return PerCaseQualitySnapshot(
        case_id=case_id,
        outcome=_outcome_from_passed(passed),
        result_fingerprint=result_fingerprint,
    )


def build_rag_quality_snapshot(
    report: RagFinalEvaluationReport,
) -> RagQualitySnapshot:
    """Build a RAG quality snapshot from an existing typed final report."""
    if not isinstance(report, RagFinalEvaluationReport):
        raise QualitySnapshotContractError(
            "report must be a RagFinalEvaluationReport."
        )
    cases: list[PerCaseQualitySnapshot] = []
    for item in report.retrieval_quality_results:
        cases.append(
            _per_case(
                case_id=item.case_id,
                passed=item.passed,
                result_fingerprint=fingerprint_rag_retrieval_quality_result(item),
            )
        )
    for item in report.adversarial_retrieval_results:
        cases.append(
            _per_case(
                case_id=item.case_id,
                passed=item.passed,
                result_fingerprint=fingerprint_rag_adversarial_result(item),
            )
        )
    for item in report.generation_safety_results:
        cases.append(
            _per_case(
                case_id=item.case_id,
                passed=item.passed,
                result_fingerprint=fingerprint_rag_generation_safety_result(item),
            )
        )
    ordered = _normalise_case_snapshots(cases)
    passed_count = sum(1 for item in ordered if item.outcome is CaseOutcome.PASS)
    failed_count = len(ordered) - passed_count
    return RagQualitySnapshot(
        evaluation_family=EvaluationFamily.RAG_FINAL,
        case_set_sha256=report.case_set_sha256,
        candidate_case_count=len(ordered),
        passed_count=passed_count,
        failed_count=failed_count,
        cases=ordered,
        network_call_count=report.network_call_count,
        live_embedding_call_count=report.live_embedding_call_count,
        live_llm_call_count=report.live_llm_call_count,
        report_sha256=report.report_sha256,
    )


def build_tool_assistant_quality_snapshot(
    report: ToolAssistantEvaluationReport,
) -> ToolAssistantQualitySnapshot:
    """Build a tool-assistant quality snapshot from an existing typed report."""
    if not isinstance(report, ToolAssistantEvaluationReport):
        raise QualitySnapshotContractError(
            "report must be a ToolAssistantEvaluationReport."
        )
    cases = [
        _per_case(
            case_id=item.case_id,
            passed=item.passed,
            result_fingerprint=fingerprint_tool_assistant_case_result(item),
        )
        for item in report.results
    ]
    ordered = _normalise_case_snapshots(cases)
    passed_count = sum(1 for item in ordered if item.outcome is CaseOutcome.PASS)
    failed_count = len(ordered) - passed_count
    return ToolAssistantQualitySnapshot(
        evaluation_family=EvaluationFamily.TOOL_ASSISTANT,
        case_set_sha256=report.case_set_sha256,
        candidate_case_count=len(ordered),
        passed_count=passed_count,
        failed_count=failed_count,
        cases=ordered,
        network_call_count=report.network_call_count,
        live_provider_call_count=report.live_provider_call_count,
        report_sha256=report.report_sha256,
    )


def build_ai_quality_snapshot(
    *,
    rag_report: RagFinalEvaluationReport,
    tool_assistant_report: ToolAssistantEvaluationReport,
    privacy_violation_count: int,
    candidate_sha: str | None,
) -> AiQualitySnapshot:
    """Compose the closed AI quality snapshot from typed evaluator reports."""
    return AiQualitySnapshot(
        schema_version=QUALITY_SNAPSHOT_SCHEMA_VERSION,
        rag=build_rag_quality_snapshot(rag_report),
        tool_assistant=build_tool_assistant_quality_snapshot(
            tool_assistant_report
        ),
        privacy_violation_count=privacy_violation_count,
        candidate_sha=candidate_sha,
    )


def _family_gating_dict_rag(snapshot: RagQualitySnapshot) -> dict[str, Any]:
    return {
        "candidate_case_count": snapshot.candidate_case_count,
        "cases": [
            {
                "case_id": item.case_id,
                "outcome": item.outcome.value,
                "result_fingerprint": item.result_fingerprint,
            }
            for item in snapshot.cases
        ],
        "case_set_sha256": snapshot.case_set_sha256,
        "evaluation_family": snapshot.evaluation_family.value,
        "failed_count": snapshot.failed_count,
        "live_embedding_call_count": snapshot.live_embedding_call_count,
        "live_llm_call_count": snapshot.live_llm_call_count,
        "network_call_count": snapshot.network_call_count,
        "passed_count": snapshot.passed_count,
    }


def _family_gating_dict_tool(
    snapshot: ToolAssistantQualitySnapshot,
) -> dict[str, Any]:
    return {
        "candidate_case_count": snapshot.candidate_case_count,
        "cases": [
            {
                "case_id": item.case_id,
                "outcome": item.outcome.value,
                "result_fingerprint": item.result_fingerprint,
            }
            for item in snapshot.cases
        ],
        "case_set_sha256": snapshot.case_set_sha256,
        "evaluation_family": snapshot.evaluation_family.value,
        "failed_count": snapshot.failed_count,
        "live_provider_call_count": snapshot.live_provider_call_count,
        "network_call_count": snapshot.network_call_count,
        "passed_count": snapshot.passed_count,
    }


def quality_snapshot_to_gating_dict(
    snapshot: AiQualitySnapshot,
) -> dict[str, Any]:
    """Authoritative gating representation. Excludes report/candidate SHA."""
    if not isinstance(snapshot, AiQualitySnapshot):
        raise QualitySnapshotContractError(
            "snapshot must be an AiQualitySnapshot."
        )
    return {
        "privacy_violation_count": snapshot.privacy_violation_count,
        "rag": _family_gating_dict_rag(snapshot.rag),
        "schema_version": snapshot.schema_version,
        "tool_assistant": _family_gating_dict_tool(snapshot.tool_assistant),
    }


def canonical_quality_snapshot_bytes(snapshot: AiQualitySnapshot) -> bytes:
    return _canonical_bytes(quality_snapshot_to_gating_dict(snapshot))


def compute_quality_snapshot_hash(snapshot: AiQualitySnapshot) -> str:
    return hashlib.sha256(canonical_quality_snapshot_bytes(snapshot)).hexdigest()


__all__ = (
    "AiQualitySnapshot",
    "CaseOutcome",
    "EvaluationFamily",
    "PerCaseQualitySnapshot",
    "QUALITY_SNAPSHOT_SCHEMA_VERSION",
    "QualitySnapshotContractError",
    "RagQualitySnapshot",
    "ToolAssistantQualitySnapshot",
    "build_ai_quality_snapshot",
    "build_rag_quality_snapshot",
    "build_tool_assistant_quality_snapshot",
    "canonical_quality_snapshot_bytes",
    "compute_quality_snapshot_hash",
    "fingerprint_rag_adversarial_result",
    "fingerprint_rag_generation_safety_result",
    "fingerprint_rag_retrieval_quality_result",
    "fingerprint_tool_assistant_case_result",
    "quality_snapshot_to_gating_dict",
)

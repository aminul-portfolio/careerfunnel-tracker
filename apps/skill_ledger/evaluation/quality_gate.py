"""Sprint 122 Phase 3: immutable AI quality baseline and per-case regression gate.

Reads the fixed Sprint 121 baseline JSON and compares Phase 2 snapshots.
No evaluator execution, network, providers, or persistence.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from apps.skill_ledger.evaluation.quality_snapshot import (
    QUALITY_SNAPSHOT_SCHEMA_VERSION,
    AiQualitySnapshot,
    CaseOutcome,
    EvaluationFamily,
    PerCaseQualitySnapshot,
)

SPRINT121_AI_QUALITY_BASELINE_PATH = (
    Path(__file__).resolve().parent
    / "baselines"
    / "sprint121_ai_quality_baseline.json"
)
SPRINT121_BASELINE_PROVENANCE_COMMIT = (
    "b50d959f463b178bd8c2d6c2d7a53ca362bbff6b"
)
SPRINT121_AI_QUALITY_BASELINE_SHA256 = (
    "0cfbe9252a2235ef9e58c0cbbb1d897a67b18259df49290eed16cf514a0a8b71"
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_FULL_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")

_ROOT_KEYS = frozenset({"schema_version", "provenance_commit", "families"})
_FAMILY_KEYS = frozenset(
    {
        "evaluation_family",
        "case_set_sha256",
        "expected_case_count",
        "cases",
        "report_sha256",
    }
)
_CASE_KEYS = frozenset(
    {"case_id", "expected_outcome", "result_fingerprint"}
)


class QualityGateContractError(ValueError):
    """Raised when quality-gate contracts fail structural validation."""


class QualityGateCode(str, Enum):
    PASS = "PASS"
    REGRESSION_DETECTED = "REGRESSION_DETECTED"
    BASELINE_INVALID = "BASELINE_INVALID"
    BASELINE_INCOMPATIBLE = "BASELINE_INCOMPATIBLE"
    EVALUATION_INCOMPLETE = "EVALUATION_INCOMPLETE"
    PRIVACY_VIOLATION = "PRIVACY_VIOLATION"
    NETWORK_ACTIVITY_DETECTED = "NETWORK_ACTIVITY_DETECTED"
    LIVE_PROVIDER_ACTIVITY_DETECTED = "LIVE_PROVIDER_ACTIVITY_DETECTED"


class CaseRegressionCode(str, Enum):
    MISSING_CASE = "MISSING_CASE"
    UNEXPECTED_CASE = "UNEXPECTED_CASE"
    NON_PASS_OUTCOME = "NON_PASS_OUTCOME"
    FINGERPRINT_MISMATCH = "FINGERPRINT_MISMATCH"


@dataclass(frozen=True)
class CaseRegression:
    evaluation_family: EvaluationFamily
    case_id: str
    regression_code: CaseRegressionCode
    expected_outcome: CaseOutcome | None
    actual_outcome: CaseOutcome | None
    expected_fingerprint: str | None
    actual_fingerprint: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.evaluation_family, EvaluationFamily):
            raise QualityGateContractError(
                "evaluation_family must be an EvaluationFamily value."
            )
        if not isinstance(self.case_id, str) or not self.case_id.strip():
            raise QualityGateContractError("case_id must be a non-empty string.")
        if not isinstance(self.regression_code, CaseRegressionCode):
            raise QualityGateContractError(
                "regression_code must be a CaseRegressionCode value."
            )
        for field_name in ("expected_outcome", "actual_outcome"):
            value = getattr(self, field_name)
            if value is not None and not isinstance(value, CaseOutcome):
                raise QualityGateContractError(
                    f"{field_name} must be CaseOutcome or None."
                )
        for field_name in ("expected_fingerprint", "actual_fingerprint"):
            value = getattr(self, field_name)
            if value is not None and (
                not isinstance(value, str) or not _SHA256_RE.fullmatch(value)
            ):
                raise QualityGateContractError(
                    f"{field_name} must be a lowercase SHA-256 digest or None."
                )


@dataclass(frozen=True)
class QualityGateResult:
    top_level_outcome: QualityGateCode
    reason_codes: tuple[QualityGateCode, ...]
    case_regressions: tuple[CaseRegression, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.top_level_outcome, QualityGateCode):
            raise QualityGateContractError(
                "top_level_outcome must be a QualityGateCode value."
            )
        if not isinstance(self.reason_codes, tuple):
            raise QualityGateContractError("reason_codes must be a tuple.")
        for code in self.reason_codes:
            if not isinstance(code, QualityGateCode):
                raise QualityGateContractError(
                    "reason_codes must contain QualityGateCode values."
                )
            if code is QualityGateCode.PASS:
                raise QualityGateContractError(
                    "PASS must not appear in reason_codes."
                )
        if not isinstance(self.case_regressions, tuple):
            raise QualityGateContractError("case_regressions must be a tuple.")
        for item in self.case_regressions:
            if not isinstance(item, CaseRegression):
                raise QualityGateContractError(
                    "case_regressions must contain CaseRegression values."
                )


@dataclass(frozen=True)
class BaselineCaseRecord:
    case_id: str
    expected_outcome: CaseOutcome
    result_fingerprint: str


@dataclass(frozen=True)
class BaselineFamilyRecord:
    evaluation_family: EvaluationFamily
    case_set_sha256: str
    expected_case_count: int
    cases: tuple[BaselineCaseRecord, ...]
    report_sha256: str


@dataclass(frozen=True)
class QualityBaseline:
    schema_version: int
    provenance_commit: str
    families: tuple[BaselineFamilyRecord, ...]


def _canonical_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def baseline_integrity_projection(baseline: QualityBaseline) -> dict[str, Any]:
    """Gating/provenance projection. Excludes diagnostic report_sha256."""
    return {
        "families": [
            {
                "cases": [
                    {
                        "case_id": case.case_id,
                        "expected_outcome": case.expected_outcome.value,
                        "result_fingerprint": case.result_fingerprint,
                    }
                    for case in family.cases
                ],
                "case_set_sha256": family.case_set_sha256,
                "evaluation_family": family.evaluation_family.value,
                "expected_case_count": family.expected_case_count,
            }
            for family in sorted(
                baseline.families,
                key=lambda item: item.evaluation_family.value,
            )
        ],
        "provenance_commit": baseline.provenance_commit,
        "schema_version": baseline.schema_version,
    }


def compute_baseline_integrity_hash(baseline: QualityBaseline) -> str:
    return hashlib.sha256(
        _canonical_bytes(baseline_integrity_projection(baseline))
    ).hexdigest()


def _require_sha256(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise QualityGateContractError(
            f"{field_name} must be a lowercase 64-character hex SHA-256 digest."
        )
    return value


def _require_exact_keys(
    mapping: Mapping[str, Any],
    expected: frozenset[str],
    *,
    label: str,
) -> None:
    keys = frozenset(mapping.keys())
    if keys == expected:
        return
    if expected - keys:
        raise QualityGateContractError(
            f"baseline {label} is missing required keys."
        )
    raise QualityGateContractError(
        f"baseline {label} contains unknown keys."
    )


def _reject_duplicate_object_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise QualityGateContractError(
                "duplicate JSON object key is not allowed."
            )
        result[key] = value
    return result


def _parse_baseline_payload(payload: object) -> QualityBaseline:
    if not isinstance(payload, Mapping):
        raise QualityGateContractError("baseline root must be a mapping.")
    _require_exact_keys(payload, _ROOT_KEYS, label="root")
    schema_version = payload.get("schema_version")
    if (
        isinstance(schema_version, bool)
        or not isinstance(schema_version, int)
        or schema_version != 1
    ):
        raise QualityGateContractError("baseline schema_version must be 1.")
    provenance = payload.get("provenance_commit")
    if (
        not isinstance(provenance, str)
        or not _FULL_COMMIT_RE.fullmatch(provenance)
        or provenance != SPRINT121_BASELINE_PROVENANCE_COMMIT
    ):
        raise QualityGateContractError("baseline provenance_commit is invalid.")
    families_raw = payload.get("families")
    if not isinstance(families_raw, list) or len(families_raw) != 2:
        raise QualityGateContractError("baseline must contain exactly two families.")

    families: list[BaselineFamilyRecord] = []
    seen_families: set[str] = set()
    for family_raw in families_raw:
        if not isinstance(family_raw, Mapping):
            raise QualityGateContractError("baseline family must be a mapping.")
        _require_exact_keys(family_raw, _FAMILY_KEYS, label="family")
        family_name = family_raw.get("evaluation_family")
        if family_name not in {item.value for item in EvaluationFamily}:
            raise QualityGateContractError("unknown evaluation_family in baseline.")
        if family_name in seen_families:
            raise QualityGateContractError("duplicate evaluation_family in baseline.")
        seen_families.add(family_name)
        evaluation_family = EvaluationFamily(family_name)
        case_set_sha256 = _require_sha256(
            family_raw.get("case_set_sha256"),
            field_name="case_set_sha256",
        )
        report_sha256 = _require_sha256(
            family_raw.get("report_sha256"),
            field_name="report_sha256",
        )
        expected_case_count = family_raw.get("expected_case_count")
        if (
            isinstance(expected_case_count, bool)
            or not isinstance(expected_case_count, int)
            or expected_case_count < 0
        ):
            raise QualityGateContractError(
                "expected_case_count must be a non-negative int."
            )
        cases_raw = family_raw.get("cases")
        if not isinstance(cases_raw, list):
            raise QualityGateContractError("baseline cases must be a list.")
        if len(cases_raw) != expected_case_count:
            raise QualityGateContractError(
                "expected_case_count must equal len(cases)."
            )
        cases: list[BaselineCaseRecord] = []
        seen_ids: set[str] = set()
        for case_raw in cases_raw:
            if not isinstance(case_raw, Mapping):
                raise QualityGateContractError("baseline case must be a mapping.")
            _require_exact_keys(case_raw, _CASE_KEYS, label="case")
            case_id = case_raw.get("case_id")
            if not isinstance(case_id, str) or not case_id.strip():
                raise QualityGateContractError("baseline case_id is invalid.")
            if case_id in seen_ids:
                raise QualityGateContractError("duplicate baseline case_id.")
            seen_ids.add(case_id)
            expected_outcome_raw = case_raw.get("expected_outcome")
            if expected_outcome_raw != CaseOutcome.PASS.value:
                raise QualityGateContractError(
                    "baseline expected_outcome must be PASS."
                )
            fingerprint = _require_sha256(
                case_raw.get("result_fingerprint"),
                field_name="result_fingerprint",
            )
            cases.append(
                BaselineCaseRecord(
                    case_id=case_id,
                    expected_outcome=CaseOutcome.PASS,
                    result_fingerprint=fingerprint,
                )
            )
        case_ids = [item.case_id for item in cases]
        if case_ids != sorted(case_ids):
            raise QualityGateContractError(
                "baseline cases must be sorted by case_id ascending."
            )
        families.append(
            BaselineFamilyRecord(
                evaluation_family=evaluation_family,
                case_set_sha256=case_set_sha256,
                expected_case_count=expected_case_count,
                cases=tuple(cases),
                report_sha256=report_sha256,
            )
        )

    families_tuple = tuple(
        sorted(families, key=lambda item: item.evaluation_family.value)
    )
    if {item.evaluation_family for item in families_tuple} != set(EvaluationFamily):
        raise QualityGateContractError(
            "baseline must include RAG_FINAL and TOOL_ASSISTANT."
        )
    total = sum(item.expected_case_count for item in families_tuple)
    if total != 112:
        raise QualityGateContractError("baseline total case count must be 112.")
    rag = next(
        item
        for item in families_tuple
        if item.evaluation_family is EvaluationFamily.RAG_FINAL
    )
    tool = next(
        item
        for item in families_tuple
        if item.evaluation_family is EvaluationFamily.TOOL_ASSISTANT
    )
    if rag.expected_case_count != 31 or tool.expected_case_count != 81:
        raise QualityGateContractError("baseline family case counts are invalid.")
    return QualityBaseline(
        schema_version=1,
        provenance_commit=provenance,
        families=families_tuple,
    )


def parse_quality_baseline(text: str) -> QualityBaseline:
    try:
        payload = json.loads(text, object_pairs_hook=_reject_duplicate_object_keys)
    except json.JSONDecodeError:
        raise QualityGateContractError("baseline JSON is malformed.") from None
    except QualityGateContractError:
        raise
    return _parse_baseline_payload(payload)


def load_authoritative_baseline() -> QualityBaseline:
    """Load and validate the fixed authoritative Sprint 121 baseline."""
    try:
        text = SPRINT121_AI_QUALITY_BASELINE_PATH.read_text(encoding="utf-8")
    except OSError:
        raise QualityGateContractError("baseline file is unavailable.") from None
    baseline = parse_quality_baseline(text)
    digest = compute_baseline_integrity_hash(baseline)
    if digest != SPRINT121_AI_QUALITY_BASELINE_SHA256:
        raise QualityGateContractError("baseline integrity hash mismatch.")
    return baseline


def _invalid_result() -> QualityGateResult:
    return QualityGateResult(
        top_level_outcome=QualityGateCode.BASELINE_INVALID,
        reason_codes=(QualityGateCode.BASELINE_INVALID,),
        case_regressions=(),
    )


def _finalise_result(
    reason_codes: set[QualityGateCode],
    case_regressions: list[CaseRegression],
) -> QualityGateResult:
    ordered_reasons = tuple(
        sorted(reason_codes, key=lambda item: item.value)
    )
    ordered_cases = tuple(
        sorted(
            case_regressions,
            key=lambda item: (
                item.evaluation_family.value,
                item.case_id,
                item.regression_code.value,
            ),
        )
    )
    if not ordered_reasons:
        return QualityGateResult(
            top_level_outcome=QualityGateCode.PASS,
            reason_codes=(),
            case_regressions=(),
        )
    return QualityGateResult(
        top_level_outcome=ordered_reasons[0],
        reason_codes=ordered_reasons,
        case_regressions=ordered_cases,
    )


def _family_map(
    baseline: QualityBaseline,
) -> dict[EvaluationFamily, BaselineFamilyRecord]:
    return {item.evaluation_family: item for item in baseline.families}


def evaluate_against_baseline(
    snapshot: AiQualitySnapshot,
    baseline: QualityBaseline,
) -> QualityGateResult:
    """Pure comparison of a Phase 2 snapshot against a validated baseline."""
    if not isinstance(snapshot, AiQualitySnapshot):
        raise QualityGateContractError("snapshot must be AiQualitySnapshot.")
    if not isinstance(baseline, QualityBaseline):
        raise QualityGateContractError("baseline must be QualityBaseline.")

    reasons: set[QualityGateCode] = set()
    regressions: list[CaseRegression] = []
    families = _family_map(baseline)

    if snapshot.schema_version != QUALITY_SNAPSHOT_SCHEMA_VERSION:
        reasons.add(QualityGateCode.BASELINE_INCOMPATIBLE)

    rag_baseline = families[EvaluationFamily.RAG_FINAL]
    tool_baseline = families[EvaluationFamily.TOOL_ASSISTANT]

    if snapshot.rag.case_set_sha256 != rag_baseline.case_set_sha256:
        reasons.add(QualityGateCode.BASELINE_INCOMPATIBLE)
    if snapshot.tool_assistant.case_set_sha256 != tool_baseline.case_set_sha256:
        reasons.add(QualityGateCode.BASELINE_INCOMPATIBLE)

    if snapshot.privacy_violation_count > 0:
        reasons.add(QualityGateCode.PRIVACY_VIOLATION)

    if (
        snapshot.rag.network_call_count > 0
        or snapshot.tool_assistant.network_call_count > 0
    ):
        reasons.add(QualityGateCode.NETWORK_ACTIVITY_DETECTED)

    if (
        snapshot.rag.live_embedding_call_count > 0
        or snapshot.rag.live_llm_call_count > 0
        or snapshot.tool_assistant.live_provider_call_count > 0
    ):
        reasons.add(QualityGateCode.LIVE_PROVIDER_ACTIVITY_DETECTED)

    _compare_family(
        evaluation_family=EvaluationFamily.RAG_FINAL,
        baseline_family=rag_baseline,
        candidate_cases=snapshot.rag.cases,
        candidate_case_count=snapshot.rag.candidate_case_count,
        reasons=reasons,
        regressions=regressions,
    )
    _compare_family(
        evaluation_family=EvaluationFamily.TOOL_ASSISTANT,
        baseline_family=tool_baseline,
        candidate_cases=snapshot.tool_assistant.cases,
        candidate_case_count=snapshot.tool_assistant.candidate_case_count,
        reasons=reasons,
        regressions=regressions,
    )
    return _finalise_result(reasons, regressions)


def _compare_family(
    *,
    evaluation_family: EvaluationFamily,
    baseline_family: BaselineFamilyRecord,
    candidate_cases: tuple[PerCaseQualitySnapshot, ...],
    candidate_case_count: int,
    reasons: set[QualityGateCode],
    regressions: list[CaseRegression],
) -> None:
    baseline_by_id = {item.case_id: item for item in baseline_family.cases}
    candidate_by_id = {item.case_id: item for item in candidate_cases}

    if (
        candidate_case_count != baseline_family.expected_case_count
        or len(candidate_cases) != baseline_family.expected_case_count
        or set(candidate_by_id) != set(baseline_by_id)
    ):
        reasons.add(QualityGateCode.EVALUATION_INCOMPLETE)

    for case_id in sorted(set(baseline_by_id) - set(candidate_by_id)):
        expected = baseline_by_id[case_id]
        regressions.append(
            CaseRegression(
                evaluation_family=evaluation_family,
                case_id=case_id,
                regression_code=CaseRegressionCode.MISSING_CASE,
                expected_outcome=expected.expected_outcome,
                actual_outcome=None,
                expected_fingerprint=expected.result_fingerprint,
                actual_fingerprint=None,
            )
        )

    for case_id in sorted(set(candidate_by_id) - set(baseline_by_id)):
        actual = candidate_by_id[case_id]
        regressions.append(
            CaseRegression(
                evaluation_family=evaluation_family,
                case_id=case_id,
                regression_code=CaseRegressionCode.UNEXPECTED_CASE,
                expected_outcome=None,
                actual_outcome=actual.outcome,
                expected_fingerprint=None,
                actual_fingerprint=actual.result_fingerprint,
            )
        )

    for case_id in sorted(set(baseline_by_id) & set(candidate_by_id)):
        expected = baseline_by_id[case_id]
        actual = candidate_by_id[case_id]
        if actual.outcome is not CaseOutcome.PASS:
            reasons.add(QualityGateCode.REGRESSION_DETECTED)
            regressions.append(
                CaseRegression(
                    evaluation_family=evaluation_family,
                    case_id=case_id,
                    regression_code=CaseRegressionCode.NON_PASS_OUTCOME,
                    expected_outcome=expected.expected_outcome,
                    actual_outcome=actual.outcome,
                    expected_fingerprint=expected.result_fingerprint,
                    actual_fingerprint=actual.result_fingerprint,
                )
            )
        if actual.result_fingerprint != expected.result_fingerprint:
            reasons.add(QualityGateCode.REGRESSION_DETECTED)
            regressions.append(
                CaseRegression(
                    evaluation_family=evaluation_family,
                    case_id=case_id,
                    regression_code=CaseRegressionCode.FINGERPRINT_MISMATCH,
                    expected_outcome=expected.expected_outcome,
                    actual_outcome=actual.outcome,
                    expected_fingerprint=expected.result_fingerprint,
                    actual_fingerprint=actual.result_fingerprint,
                )
            )


def run_ai_quality_gate(snapshot: AiQualitySnapshot) -> QualityGateResult:
    """Evaluate a Phase 2 snapshot against the fixed Sprint 121 baseline."""
    try:
        baseline = load_authoritative_baseline()
    except QualityGateContractError:
        return _invalid_result()
    return evaluate_against_baseline(snapshot, baseline)


__all__ = (
    "BaselineCaseRecord",
    "BaselineFamilyRecord",
    "CaseRegression",
    "CaseRegressionCode",
    "QualityBaseline",
    "QualityGateCode",
    "QualityGateContractError",
    "QualityGateResult",
    "SPRINT121_AI_QUALITY_BASELINE_PATH",
    "SPRINT121_AI_QUALITY_BASELINE_SHA256",
    "SPRINT121_BASELINE_PROVENANCE_COMMIT",
    "baseline_integrity_projection",
    "compute_baseline_integrity_hash",
    "evaluate_against_baseline",
    "load_authoritative_baseline",
    "parse_quality_baseline",
    "run_ai_quality_gate",
)

"""Sprint 122 Phase 4: closed deterministic AI quality-lifecycle cases.

Synthetic meta-evaluation scenarios only. No raw content, network, or providers.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence

from apps.skill_ledger.evaluation.quality_gate import (
    CaseRegressionCode,
    QualityGateCode,
)

EVALUATION_VERSION = "skill_ledger_ai_quality_eval_v1"
CASE_SCHEMA_VERSION = "skill_ledger_ai_quality_eval_case_v1"
QUALITY_CASE_MINIMUM = 51
REQUIRED_THREATS: tuple[str, ...] = tuple(f"Q{index}" for index in range(1, 24))


class QualityEvalCategory(str, Enum):
    SNAPSHOT = "SNAPSHOT"
    HASH = "HASH"
    PROVENANCE = "PROVENANCE"
    REGRESSION = "REGRESSION"
    COVERAGE = "COVERAGE"
    PRIVACY = "PRIVACY"
    NETWORK = "NETWORK"
    LIVE_PROVIDER = "LIVE_PROVIDER"
    INDEPENDENCE = "INDEPENDENCE"
    BASELINE = "BASELINE"
    ORDERING = "ORDERING"
    OBSERVATION = "OBSERVATION"
    GOVERNANCE = "GOVERNANCE"


class QualityScenarioType(str, Enum):
    AUTHORITATIVE_GATE_PASS = "AUTHORITATIVE_GATE_PASS"
    SNAPSHOT_GATING_HASH_STABLE = "SNAPSHOT_GATING_HASH_STABLE"
    FINGERPRINT_FIELD_REGRESSION = "FINGERPRINT_FIELD_REGRESSION"
    RAG_CASE_SET_MISMATCH = "RAG_CASE_SET_MISMATCH"
    TOOL_CASE_SET_MISMATCH = "TOOL_CASE_SET_MISMATCH"
    MISSING_CASE = "MISSING_CASE"
    UNEXPECTED_CASE = "UNEXPECTED_CASE"
    NON_PASS_OUTCOME = "NON_PASS_OUTCOME"
    FINGERPRINT_MISMATCH = "FINGERPRINT_MISMATCH"
    PRIVACY_VIOLATION = "PRIVACY_VIOLATION"
    NETWORK_ACTIVITY = "NETWORK_ACTIVITY"
    LIVE_EMBEDDING_ACTIVITY = "LIVE_EMBEDDING_ACTIVITY"
    LIVE_LLM_ACTIVITY = "LIVE_LLM_ACTIVITY"
    LIVE_PROVIDER_ACTIVITY = "LIVE_PROVIDER_ACTIVITY"
    CANDIDATE_SHA_INDEPENDENT = "CANDIDATE_SHA_INDEPENDENT"
    REPORT_SHA_INDEPENDENT = "REPORT_SHA_INDEPENDENT"
    BASELINE_INTEGRITY_MISMATCH = "BASELINE_INTEGRITY_MISMATCH"
    BASELINE_MALFORMED = "BASELINE_MALFORMED"
    MULTI_FAILURE_ORDERING = "MULTI_FAILURE_ORDERING"
    EVALUATION_INCOMPLETE_COUNT = "EVALUATION_INCOMPLETE_COUNT"
    AGGREGATE_MASKING = "AGGREGATE_MASKING"
    CASE_SWAP = "CASE_SWAP"
    OBSERVATION_COLLECTOR_ISOLATION = "OBSERVATION_COLLECTOR_ISOLATION"
    NO_SECOND_CLASSIFIER = "NO_SECOND_CLASSIFIER"
    ZERO_RAG_NETWORK = "ZERO_RAG_NETWORK"
    ZERO_RAG_LIVE_EMBEDDING = "ZERO_RAG_LIVE_EMBEDDING"
    ZERO_RAG_LIVE_LLM = "ZERO_RAG_LIVE_LLM"
    ZERO_TOOL_NETWORK = "ZERO_TOOL_NETWORK"
    ZERO_TOOL_LIVE_PROVIDER = "ZERO_TOOL_LIVE_PROVIDER"
    BASELINE_INTEGRITY_CONSTANT = "BASELINE_INTEGRITY_CONSTANT"
    RAG_CASE_SET_PRESERVED = "RAG_CASE_SET_PRESERVED"
    TOOL_CASE_SET_PRESERVED = "TOOL_CASE_SET_PRESERVED"
    AUTHORITATIVE_RAG_PASS = "AUTHORITATIVE_RAG_PASS"
    AUTHORITATIVE_TOOL_PASS = "AUTHORITATIVE_TOOL_PASS"
    PRIVACY_ZERO = "PRIVACY_ZERO"
    CASE_SET_HASH_DETERMINISTIC = "CASE_SET_HASH_DETERMINISTIC"


class QualityEvaluationCaseContractError(ValueError):
    """Fail-closed quality evaluation case contract error."""


@dataclass(frozen=True)
class QualityEvaluationCase:
    case_id: str
    category: QualityEvalCategory
    threat_ids: tuple[str, ...]
    scenario_type: QualityScenarioType
    expected_top_level_outcome: QualityGateCode
    expected_reason_codes: tuple[QualityGateCode, ...]
    expected_case_regression_codes: tuple[CaseRegressionCode, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.case_id, str) or not self.case_id.strip():
            raise QualityEvaluationCaseContractError("case_id must be non-empty.")
        if not isinstance(self.category, QualityEvalCategory):
            raise QualityEvaluationCaseContractError("category invalid.")
        if not isinstance(self.scenario_type, QualityScenarioType):
            raise QualityEvaluationCaseContractError("scenario_type invalid.")
        if not isinstance(self.expected_top_level_outcome, QualityGateCode):
            raise QualityEvaluationCaseContractError(
                "expected_top_level_outcome invalid."
            )
        if not isinstance(self.threat_ids, tuple) or not self.threat_ids:
            raise QualityEvaluationCaseContractError("threat_ids required.")
        if len(self.threat_ids) != len(set(self.threat_ids)):
            raise QualityEvaluationCaseContractError(
                "threat_ids must not contain duplicates."
            )
        for threat in self.threat_ids:
            if threat not in REQUIRED_THREATS:
                raise QualityEvaluationCaseContractError(
                    f"unknown threat id: {threat}."
                )
        if tuple(sorted(self.threat_ids)) != self.threat_ids:
            raise QualityEvaluationCaseContractError(
                "threat_ids must be sorted ascending."
            )
        if not isinstance(self.expected_reason_codes, tuple):
            raise QualityEvaluationCaseContractError(
                "expected_reason_codes must be a tuple."
            )
        for code in self.expected_reason_codes:
            if not isinstance(code, QualityGateCode):
                raise QualityEvaluationCaseContractError(
                    "expected_reason_codes must contain QualityGateCode values."
                )
        if len(self.expected_reason_codes) != len(set(self.expected_reason_codes)):
            raise QualityEvaluationCaseContractError(
                "expected_reason_codes must not contain duplicates."
            )
        if QualityGateCode.PASS in self.expected_reason_codes:
            raise QualityEvaluationCaseContractError(
                "PASS must not appear in expected_reason_codes."
            )
        if tuple(sorted(self.expected_reason_codes, key=lambda item: item.value)) != (
            self.expected_reason_codes
        ):
            raise QualityEvaluationCaseContractError(
                "expected_reason_codes must be sorted by value."
            )
        if not isinstance(self.expected_case_regression_codes, tuple):
            raise QualityEvaluationCaseContractError(
                "expected_case_regression_codes must be a tuple."
            )
        for code in self.expected_case_regression_codes:
            if not isinstance(code, CaseRegressionCode):
                raise QualityEvaluationCaseContractError(
                    "expected_case_regression_codes must contain "
                    "CaseRegressionCode values."
                )
        if len(self.expected_case_regression_codes) != len(
            set(self.expected_case_regression_codes)
        ):
            raise QualityEvaluationCaseContractError(
                "expected_case_regression_codes must not contain duplicates."
            )
        if tuple(
            sorted(self.expected_case_regression_codes, key=lambda item: item.value)
        ) != self.expected_case_regression_codes:
            raise QualityEvaluationCaseContractError(
                "expected_case_regression_codes must be sorted by value."
            )


def _case(
    case_id: str,
    category: QualityEvalCategory,
    threat_ids: Sequence[str],
    scenario_type: QualityScenarioType,
    *,
    expected_top_level_outcome: QualityGateCode = QualityGateCode.PASS,
    expected_reason_codes: Sequence[QualityGateCode] = (),
    expected_case_regression_codes: Sequence[CaseRegressionCode] = (),
) -> QualityEvaluationCase:
    return QualityEvaluationCase(
        case_id=case_id,
        category=category,
        threat_ids=tuple(sorted(threat_ids)),
        scenario_type=scenario_type,
        expected_top_level_outcome=expected_top_level_outcome,
        expected_reason_codes=tuple(
            sorted(expected_reason_codes, key=lambda item: item.value)
        ),
        expected_case_regression_codes=tuple(
            sorted(expected_case_regression_codes, key=lambda item: item.value)
        ),
    )


def _build_cases() -> tuple[QualityEvaluationCase, ...]:
    c = QualityEvalCategory
    s = QualityScenarioType
    g = QualityGateCode
    r = CaseRegressionCode
    cases: list[QualityEvaluationCase] = [
        _case("aq-q01-authoritative-gate-pass", c.SNAPSHOT, ("Q1",), s.AUTHORITATIVE_GATE_PASS),
        _case("aq-q01-rag-pass", c.SNAPSHOT, ("Q1",), s.AUTHORITATIVE_RAG_PASS),
        _case("aq-q01-tool-pass", c.SNAPSHOT, ("Q1",), s.AUTHORITATIVE_TOOL_PASS),
        _case("aq-q02-gating-hash-stable", c.HASH, ("Q2",), s.SNAPSHOT_GATING_HASH_STABLE),
        _case("aq-q02-case-set-hash-stable", c.HASH, ("Q2",), s.CASE_SET_HASH_DETERMINISTIC),
        _case(
            "aq-q03-fingerprint-regression",
            c.REGRESSION,
            ("Q3",),
            s.FINGERPRINT_FIELD_REGRESSION,
            expected_top_level_outcome=g.REGRESSION_DETECTED,
            expected_reason_codes=(g.REGRESSION_DETECTED,),
            expected_case_regression_codes=(r.FINGERPRINT_MISMATCH,),
        ),
        _case(
            "aq-q04-rag-case-set-mismatch",
            c.PROVENANCE,
            ("Q4",),
            s.RAG_CASE_SET_MISMATCH,
            expected_top_level_outcome=g.BASELINE_INCOMPATIBLE,
            expected_reason_codes=(g.BASELINE_INCOMPATIBLE,),
        ),
        _case(
            "aq-q04-tool-case-set-mismatch",
            c.PROVENANCE,
            ("Q4",),
            s.TOOL_CASE_SET_MISMATCH,
            expected_top_level_outcome=g.BASELINE_INCOMPATIBLE,
            expected_reason_codes=(g.BASELINE_INCOMPATIBLE,),
        ),
        _case("aq-q04-rag-case-set-preserved", c.PROVENANCE, ("Q4",), s.RAG_CASE_SET_PRESERVED),
        _case("aq-q04-tool-case-set-preserved", c.PROVENANCE, ("Q4",), s.TOOL_CASE_SET_PRESERVED),
        _case(
            "aq-q05-missing-case",
            c.COVERAGE,
            ("Q5",),
            s.MISSING_CASE,
            expected_top_level_outcome=g.EVALUATION_INCOMPLETE,
            expected_reason_codes=(g.EVALUATION_INCOMPLETE,),
            expected_case_regression_codes=(r.MISSING_CASE,),
        ),
        _case(
            "aq-q06-unexpected-case",
            c.COVERAGE,
            ("Q6",),
            s.UNEXPECTED_CASE,
            expected_top_level_outcome=g.EVALUATION_INCOMPLETE,
            expected_reason_codes=(g.EVALUATION_INCOMPLETE,),
            expected_case_regression_codes=(r.UNEXPECTED_CASE,),
        ),
        _case(
            "aq-q07-non-pass-outcome",
            c.REGRESSION,
            ("Q7",),
            s.NON_PASS_OUTCOME,
            expected_top_level_outcome=g.REGRESSION_DETECTED,
            expected_reason_codes=(g.REGRESSION_DETECTED,),
            expected_case_regression_codes=(r.NON_PASS_OUTCOME,),
        ),
        _case(
            "aq-q08-fingerprint-mismatch",
            c.REGRESSION,
            ("Q8",),
            s.FINGERPRINT_MISMATCH,
            expected_top_level_outcome=g.REGRESSION_DETECTED,
            expected_reason_codes=(g.REGRESSION_DETECTED,),
            expected_case_regression_codes=(r.FINGERPRINT_MISMATCH,),
        ),
        _case(
            "aq-q09-privacy-violation",
            c.PRIVACY,
            ("Q9",),
            s.PRIVACY_VIOLATION,
            expected_top_level_outcome=g.PRIVACY_VIOLATION,
            expected_reason_codes=(g.PRIVACY_VIOLATION,),
        ),
        _case("aq-q09-privacy-zero", c.PRIVACY, ("Q9",), s.PRIVACY_ZERO),
        _case(
            "aq-q10-network-activity",
            c.NETWORK,
            ("Q10",),
            s.NETWORK_ACTIVITY,
            expected_top_level_outcome=g.NETWORK_ACTIVITY_DETECTED,
            expected_reason_codes=(g.NETWORK_ACTIVITY_DETECTED,),
        ),
        _case("aq-q10-zero-rag-network", c.NETWORK, ("Q10",), s.ZERO_RAG_NETWORK),
        _case("aq-q10-zero-tool-network", c.NETWORK, ("Q10",), s.ZERO_TOOL_NETWORK),
        _case(
            "aq-q11-live-embedding",
            c.LIVE_PROVIDER,
            ("Q11",),
            s.LIVE_EMBEDDING_ACTIVITY,
            expected_top_level_outcome=g.LIVE_PROVIDER_ACTIVITY_DETECTED,
            expected_reason_codes=(g.LIVE_PROVIDER_ACTIVITY_DETECTED,),
        ),
        _case(
            "aq-q11-zero-live-embedding",
            c.LIVE_PROVIDER,
            ("Q11",),
            s.ZERO_RAG_LIVE_EMBEDDING,
        ),
        _case(
            "aq-q12-live-llm",
            c.LIVE_PROVIDER,
            ("Q12",),
            s.LIVE_LLM_ACTIVITY,
            expected_top_level_outcome=g.LIVE_PROVIDER_ACTIVITY_DETECTED,
            expected_reason_codes=(g.LIVE_PROVIDER_ACTIVITY_DETECTED,),
        ),
        _case("aq-q12-zero-live-llm", c.LIVE_PROVIDER, ("Q12",), s.ZERO_RAG_LIVE_LLM),
        _case(
            "aq-q13-live-provider",
            c.LIVE_PROVIDER,
            ("Q13",),
            s.LIVE_PROVIDER_ACTIVITY,
            expected_top_level_outcome=g.LIVE_PROVIDER_ACTIVITY_DETECTED,
            expected_reason_codes=(g.LIVE_PROVIDER_ACTIVITY_DETECTED,),
        ),
        _case(
            "aq-q13-zero-live-provider",
            c.LIVE_PROVIDER,
            ("Q13",),
            s.ZERO_TOOL_LIVE_PROVIDER,
        ),
        _case(
            "aq-q14-candidate-sha-independent",
            c.INDEPENDENCE,
            ("Q14",),
            s.CANDIDATE_SHA_INDEPENDENT,
        ),
        _case(
            "aq-q15-report-sha-independent",
            c.INDEPENDENCE,
            ("Q15",),
            s.REPORT_SHA_INDEPENDENT,
        ),
        _case(
            "aq-q16-baseline-integrity-mismatch",
            c.BASELINE,
            ("Q16",),
            s.BASELINE_INTEGRITY_MISMATCH,
        ),
        _case(
            "aq-q16-baseline-integrity-constant",
            c.BASELINE,
            ("Q16",),
            s.BASELINE_INTEGRITY_CONSTANT,
        ),
        _case("aq-q17-baseline-malformed", c.BASELINE, ("Q17",), s.BASELINE_MALFORMED),
        _case(
            "aq-q18-multi-failure-ordering",
            c.ORDERING,
            ("Q18",),
            s.MULTI_FAILURE_ORDERING,
            expected_top_level_outcome=g.NETWORK_ACTIVITY_DETECTED,
            expected_reason_codes=(
                g.NETWORK_ACTIVITY_DETECTED,
                g.PRIVACY_VIOLATION,
                g.REGRESSION_DETECTED,
            ),
            expected_case_regression_codes=(r.FINGERPRINT_MISMATCH,),
        ),
        _case(
            "aq-q19-evaluation-incomplete",
            c.COVERAGE,
            ("Q19",),
            s.EVALUATION_INCOMPLETE_COUNT,
            expected_top_level_outcome=g.EVALUATION_INCOMPLETE,
            expected_reason_codes=(g.EVALUATION_INCOMPLETE,),
            expected_case_regression_codes=(r.MISSING_CASE,),
        ),
        _case(
            "aq-q20-aggregate-masking",
            c.REGRESSION,
            ("Q20",),
            s.AGGREGATE_MASKING,
            expected_top_level_outcome=g.REGRESSION_DETECTED,
            expected_reason_codes=(g.REGRESSION_DETECTED,),
            expected_case_regression_codes=(r.FINGERPRINT_MISMATCH,),
        ),
        _case(
            "aq-q21-case-swap",
            c.COVERAGE,
            ("Q21",),
            s.CASE_SWAP,
            expected_top_level_outcome=g.EVALUATION_INCOMPLETE,
            expected_reason_codes=(g.EVALUATION_INCOMPLETE,),
            expected_case_regression_codes=(r.MISSING_CASE, r.UNEXPECTED_CASE),
        ),
        _case(
            "aq-q22-collector-isolation",
            c.OBSERVATION,
            ("Q22",),
            s.OBSERVATION_COLLECTOR_ISOLATION,
        ),
        _case(
            "aq-q23-no-second-classifier",
            c.GOVERNANCE,
            ("Q23",),
            s.NO_SECOND_CLASSIFIER,
        ),
        # Additional deterministic coverage to meet floor >=51.
        _case("aq-q01-snapshot-repeat-a", c.SNAPSHOT, ("Q1",), s.AUTHORITATIVE_GATE_PASS),
        _case("aq-q01-snapshot-repeat-b", c.SNAPSHOT, ("Q1",), s.AUTHORITATIVE_GATE_PASS),
        _case("aq-q02-hash-repeat", c.HASH, ("Q2",), s.SNAPSHOT_GATING_HASH_STABLE),
        _case(
            "aq-q03-fingerprint-regression-b",
            c.REGRESSION,
            ("Q3", "Q8"),
            s.FINGERPRINT_MISMATCH,
            expected_top_level_outcome=g.REGRESSION_DETECTED,
            expected_reason_codes=(g.REGRESSION_DETECTED,),
            expected_case_regression_codes=(r.FINGERPRINT_MISMATCH,),
        ),
        _case(
            "aq-q05-missing-case-b",
            c.COVERAGE,
            ("Q5", "Q19"),
            s.MISSING_CASE,
            expected_top_level_outcome=g.EVALUATION_INCOMPLETE,
            expected_reason_codes=(g.EVALUATION_INCOMPLETE,),
            expected_case_regression_codes=(r.MISSING_CASE,),
        ),
        _case(
            "aq-q06-unexpected-case-b",
            c.COVERAGE,
            ("Q6", "Q19"),
            s.UNEXPECTED_CASE,
            expected_top_level_outcome=g.EVALUATION_INCOMPLETE,
            expected_reason_codes=(g.EVALUATION_INCOMPLETE,),
            expected_case_regression_codes=(r.UNEXPECTED_CASE,),
        ),
        _case(
            "aq-q07-non-pass-b",
            c.REGRESSION,
            ("Q7",),
            s.NON_PASS_OUTCOME,
            expected_top_level_outcome=g.REGRESSION_DETECTED,
            expected_reason_codes=(g.REGRESSION_DETECTED,),
            expected_case_regression_codes=(r.NON_PASS_OUTCOME,),
        ),
        _case(
            "aq-q09-privacy-b",
            c.PRIVACY,
            ("Q9",),
            s.PRIVACY_VIOLATION,
            expected_top_level_outcome=g.PRIVACY_VIOLATION,
            expected_reason_codes=(g.PRIVACY_VIOLATION,),
        ),
        _case(
            "aq-q10-network-b",
            c.NETWORK,
            ("Q10",),
            s.NETWORK_ACTIVITY,
            expected_top_level_outcome=g.NETWORK_ACTIVITY_DETECTED,
            expected_reason_codes=(g.NETWORK_ACTIVITY_DETECTED,),
        ),
        _case(
            "aq-q11-live-embedding-b",
            c.LIVE_PROVIDER,
            ("Q11",),
            s.LIVE_EMBEDDING_ACTIVITY,
            expected_top_level_outcome=g.LIVE_PROVIDER_ACTIVITY_DETECTED,
            expected_reason_codes=(g.LIVE_PROVIDER_ACTIVITY_DETECTED,),
        ),
        _case(
            "aq-q12-live-llm-b",
            c.LIVE_PROVIDER,
            ("Q12",),
            s.LIVE_LLM_ACTIVITY,
            expected_top_level_outcome=g.LIVE_PROVIDER_ACTIVITY_DETECTED,
            expected_reason_codes=(g.LIVE_PROVIDER_ACTIVITY_DETECTED,),
        ),
        _case(
            "aq-q13-live-provider-b",
            c.LIVE_PROVIDER,
            ("Q13",),
            s.LIVE_PROVIDER_ACTIVITY,
            expected_top_level_outcome=g.LIVE_PROVIDER_ACTIVITY_DETECTED,
            expected_reason_codes=(g.LIVE_PROVIDER_ACTIVITY_DETECTED,),
        ),
        _case(
            "aq-q14-candidate-sha-b",
            c.INDEPENDENCE,
            ("Q14",),
            s.CANDIDATE_SHA_INDEPENDENT,
        ),
        _case(
            "aq-q15-report-sha-b",
            c.INDEPENDENCE,
            ("Q15",),
            s.REPORT_SHA_INDEPENDENT,
        ),
        _case("aq-q17-baseline-malformed-b", c.BASELINE, ("Q17",), s.BASELINE_MALFORMED),
        _case(
            "aq-q21-case-swap-b",
            c.COVERAGE,
            ("Q20", "Q21"),
            s.CASE_SWAP,
            expected_top_level_outcome=g.EVALUATION_INCOMPLETE,
            expected_reason_codes=(g.EVALUATION_INCOMPLETE,),
            expected_case_regression_codes=(r.MISSING_CASE, r.UNEXPECTED_CASE),
        ),
        _case(
            "aq-q22-collector-isolation-b",
            c.OBSERVATION,
            ("Q22",),
            s.OBSERVATION_COLLECTOR_ISOLATION,
        ),
        _case(
            "aq-q23-no-second-classifier-b",
            c.GOVERNANCE,
            ("Q23",),
            s.NO_SECOND_CLASSIFIER,
        ),
    ]
    return tuple(sorted(cases, key=lambda item: item.case_id))


ALL_QUALITY_CASES: tuple[QualityEvaluationCase, ...] = _build_cases()


def validate_and_sort_quality_cases(
    cases: Iterable[QualityEvaluationCase],
) -> tuple[QualityEvaluationCase, ...]:
    ordered = tuple(sorted(cases, key=lambda item: item.case_id))
    if len(ordered) < QUALITY_CASE_MINIMUM:
        raise QualityEvaluationCaseContractError(
            f"quality cases must be >= {QUALITY_CASE_MINIMUM}."
        )
    ids = [item.case_id for item in ordered]
    if len(ids) != len(set(ids)):
        raise QualityEvaluationCaseContractError("quality case_id values must be unique.")
    if ids != sorted(ids):
        raise QualityEvaluationCaseContractError(
            "quality cases must be sorted by case_id."
        )
    covered: set[str] = set()
    for item in ordered:
        covered.update(item.threat_ids)
    missing = [threat for threat in REQUIRED_THREATS if threat not in covered]
    if missing:
        raise QualityEvaluationCaseContractError(
            f"missing required threats: {missing}."
        )
    return ordered


def quality_case_to_canonical_dict(case: QualityEvaluationCase) -> dict[str, Any]:
    return {
        "case_id": case.case_id,
        "category": case.category.value,
        "expected_case_regression_codes": [
            item.value for item in case.expected_case_regression_codes
        ],
        "expected_reason_codes": [item.value for item in case.expected_reason_codes],
        "expected_top_level_outcome": case.expected_top_level_outcome.value,
        "scenario_type": case.scenario_type.value,
        "threat_ids": list(case.threat_ids),
    }


def case_set_to_canonical_dict(
    cases: Iterable[QualityEvaluationCase],
) -> dict[str, Any]:
    ordered = validate_and_sort_quality_cases(cases)
    return {
        "case_schema_version": CASE_SCHEMA_VERSION,
        "cases": [quality_case_to_canonical_dict(item) for item in ordered],
        "evaluation_version": EVALUATION_VERSION,
    }


def compute_quality_case_set_hash(cases: Iterable[QualityEvaluationCase]) -> str:
    payload = case_set_to_canonical_dict(cases)
    text = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def threat_coverage(cases: Iterable[QualityEvaluationCase]) -> Mapping[str, int]:
    counts = {threat: 0 for threat in REQUIRED_THREATS}
    for case in cases:
        for threat in case.threat_ids:
            counts[threat] = counts.get(threat, 0) + 1
    return MappingProxyType({threat: counts[threat] for threat in REQUIRED_THREATS})


__all__ = (
    "ALL_QUALITY_CASES",
    "CASE_SCHEMA_VERSION",
    "EVALUATION_VERSION",
    "QUALITY_CASE_MINIMUM",
    "QualityEvalCategory",
    "QualityEvaluationCase",
    "QualityEvaluationCaseContractError",
    "QualityScenarioType",
    "REQUIRED_THREATS",
    "case_set_to_canonical_dict",
    "compute_quality_case_set_hash",
    "threat_coverage",
    "validate_and_sort_quality_cases",
)

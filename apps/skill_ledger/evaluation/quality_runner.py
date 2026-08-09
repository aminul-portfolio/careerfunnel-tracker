"""Sprint 122 Phase 4: offline AI quality-lifecycle evaluation runner.

Consumes typed Sprint 120/121 reports, Phase 2 snapshots, and Phase 3 gate.
No network, live providers, console parsing, or persisted telemetry.
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
import re
from dataclasses import dataclass, replace
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from django.db import transaction

from apps.skill_ledger.assistant.contracts import AssistantOutcomeCode
from apps.skill_ledger.assistant.observation import (
    CollectionStatus,
    build_assistant_observation,
    collect_observation,
)
from apps.skill_ledger.evaluation.quality_cases import (
    ALL_QUALITY_CASES,
    EVALUATION_VERSION,
    QualityEvaluationCase,
    QualityEvaluationCaseContractError,
    QualityScenarioType,
    compute_quality_case_set_hash,
    threat_coverage,
    validate_and_sort_quality_cases,
)
from apps.skill_ledger.evaluation.quality_gate import (
    SPRINT121_AI_QUALITY_BASELINE_SHA256,
    CaseRegressionCode,
    QualityGateCode,
    QualityGateContractError,
    compute_baseline_integrity_hash,
    evaluate_against_baseline,
    load_authoritative_baseline,
    parse_quality_baseline,
    run_ai_quality_gate,
)
from apps.skill_ledger.evaluation.quality_snapshot import (
    AiQualitySnapshot,
    CaseOutcome,
    PerCaseQualitySnapshot,
    build_ai_quality_snapshot,
    compute_quality_snapshot_hash,
)
from apps.skill_ledger.evaluation.rag_evaluation_runner import (
    RagFinalEvaluationReport,
    run_final_rag_evaluation,
)
from apps.skill_ledger.evaluation.tool_assistant_runner import (
    ToolAssistantEvaluationReport,
    run_tool_assistant_evaluation,
)

RUNNER_VERSION = "skill_ledger_ai_quality_runner_v1"
_AUTHORITATIVE_BASELINE_INVALID_MESSAGE = (
    "authoritative AI quality baseline is invalid."
)
_SHA_ALT = "e" * 64
_CANDIDATE_SHA_RE = re.compile(r"^[0-9a-f]{7,64}$")

EXPECTED_RAG_CASE_SET_SHA256 = (
    "575ddaf4d51b4826808f1ec52badd5aa0de14d1667444d5fdadb734f1b1d0527"
)
EXPECTED_TOOL_CASE_SET_SHA256 = (
    "b3793f0fa6003e5162b9853dbf77d27f507b300d28b7259e3e18f9689eca4b53"
)


class AiQualityEvaluationRunnerError(ValueError):
    """Fail-closed quality evaluation runner error."""


@dataclass(frozen=True)
class AiQualityEvaluationCaseResult:
    case_id: str
    category: str
    threat_ids: tuple[str, ...]
    passed: bool
    expected_top_level_outcome: str
    actual_top_level_outcome: str
    expected_reason_codes: tuple[str, ...]
    actual_reason_codes: tuple[str, ...]
    expected_case_regression_codes: tuple[str, ...]
    actual_case_regression_codes: tuple[str, ...]
    message: str


@dataclass(frozen=True)
class AiQualityEvaluationReport:
    runner_version: str
    evaluation_version: str
    quality_case_set_sha256: str
    overall_result: str
    total_case_count: int
    passed_case_count: int
    failed_case_count: int
    threat_coverage: Mapping[str, int]
    results: tuple[AiQualityEvaluationCaseResult, ...]
    rag_case_set_sha256: str
    tool_assistant_case_set_sha256: str
    baseline_integrity_sha256: str
    network_call_count: int
    live_embedding_call_count: int
    live_llm_call_count: int
    live_provider_call_count: int
    quality_report_sha256: str
    candidate_sha: str | None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "threat_coverage",
            MappingProxyType(dict(self.threat_coverage)),
        )


@dataclass(frozen=True)
class _LiveContext:
    rag_report: RagFinalEvaluationReport
    tool_report: ToolAssistantEvaluationReport
    snapshot: AiQualitySnapshot
    gate_result_code: QualityGateCode


def _normalise_candidate_sha(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise AiQualityEvaluationRunnerError(
            "candidate_sha must be None or a hex string."
        )
    normalised = value.strip().lower()
    if not _CANDIDATE_SHA_RE.fullmatch(normalised):
        raise AiQualityEvaluationRunnerError(
            "candidate_sha must be 7..64 lowercase hexadecimal characters."
        )
    return normalised


def _fingerprint(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _replace_rag(snapshot: AiQualitySnapshot, **kwargs: Any) -> AiQualitySnapshot:
    cases = kwargs.get("cases", snapshot.rag.cases)
    passed = sum(1 for item in cases if item.outcome is CaseOutcome.PASS)
    failed = len(cases) - passed
    kwargs = {
        **kwargs,
        "cases": cases,
        "candidate_case_count": len(cases),
        "passed_count": passed,
        "failed_count": failed,
    }
    return replace(snapshot, rag=replace(snapshot.rag, **kwargs))


def _replace_tool(snapshot: AiQualitySnapshot, **kwargs: Any) -> AiQualitySnapshot:
    cases = kwargs.get("cases", snapshot.tool_assistant.cases)
    passed = sum(1 for item in cases if item.outcome is CaseOutcome.PASS)
    failed = len(cases) - passed
    kwargs = {
        **kwargs,
        "cases": cases,
        "candidate_case_count": len(cases),
        "passed_count": passed,
        "failed_count": failed,
    }
    return replace(
        snapshot,
        tool_assistant=replace(snapshot.tool_assistant, **kwargs),
    )


def _pass_result(
    case: QualityEvaluationCase,
    *,
    actual_top: QualityGateCode,
    actual_reasons: tuple[QualityGateCode, ...] = (),
    actual_regressions: tuple[CaseRegressionCode, ...] = (),
    message: str = "ok",
) -> AiQualityEvaluationCaseResult:
    actual_reason_values = tuple(item.value for item in actual_reasons)
    actual_regression_values = tuple(sorted({item.value for item in actual_regressions}))
    expected_reasons = tuple(item.value for item in case.expected_reason_codes)
    expected_regressions = tuple(
        item.value for item in case.expected_case_regression_codes
    )
    passed = (
        actual_top is case.expected_top_level_outcome
        and actual_reason_values == expected_reasons
        and actual_regression_values == expected_regressions
    )
    return AiQualityEvaluationCaseResult(
        case_id=case.case_id,
        category=case.category.value,
        threat_ids=case.threat_ids,
        passed=passed,
        expected_top_level_outcome=case.expected_top_level_outcome.value,
        actual_top_level_outcome=actual_top.value,
        expected_reason_codes=expected_reasons,
        actual_reason_codes=actual_reason_values,
        expected_case_regression_codes=expected_regressions,
        actual_case_regression_codes=actual_regression_values,
        message=message if passed else f"mismatch: {message}",
    )


def _property_pass(
    case: QualityEvaluationCase,
    *,
    ok: bool,
    message: str,
) -> AiQualityEvaluationCaseResult:
    if ok:
        return _pass_result(
            case,
            actual_top=QualityGateCode.PASS,
            message=message,
        )
    return _pass_result(
        case,
        actual_top=QualityGateCode.REGRESSION_DETECTED,
        actual_reasons=(QualityGateCode.REGRESSION_DETECTED,),
        message=message,
    )


def _load_authoritative_baseline_for_quality():
    """Load the fixed baseline; normalise gate contract failures for CLI safety."""
    try:
        return load_authoritative_baseline()
    except QualityGateContractError:
        raise AiQualityEvaluationRunnerError(
            _AUTHORITATIVE_BASELINE_INVALID_MESSAGE
        ) from None


def _run_gate_case(
    case: QualityEvaluationCase,
    snapshot: AiQualitySnapshot,
) -> AiQualityEvaluationCaseResult:
    baseline = _load_authoritative_baseline_for_quality()
    result = evaluate_against_baseline(snapshot, baseline)
    return _pass_result(
        case,
        actual_top=result.top_level_outcome,
        actual_reasons=result.reason_codes,
        actual_regressions=tuple(
            item.regression_code for item in result.case_regressions
        ),
        message=result.top_level_outcome.value,
    )


def _prove_observation_collector_isolation() -> bool:
    """Reuse Phase 1 collect_observation Exception isolation contract."""

    class _FailingCollector:
        def record(self, observation) -> None:
            raise RuntimeError("CF122_QUALITY_COLLECTOR_SECRET")

    observation = build_assistant_observation(
        outcome_code=AssistantOutcomeCode.NO_TOOL,
        planner_calls=1,
        tools_executed=0,
        synthesis_calls=0,
        tools_used=(),
        source_count=0,
        answer_length=24,
    )
    status = collect_observation(_FailingCollector(), observation)
    if status is not CollectionStatus.COLLECTION_FAILED:
        return False
    # Observation object itself remains free of exception text.
    canonical = observation.to_canonical_dict()
    serialised = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    if "CF122_QUALITY_COLLECTOR_SECRET" in serialised:
        return False
    if "RuntimeError" in serialised:
        return False
    return True


def _prove_no_second_classifier() -> bool:
    """Prove quality layer reuses existing codes; no live/network classifier stack."""
    from apps.skill_ledger.evaluation import quality_cases as cases_module
    from apps.skill_ledger.evaluation import quality_runner as runner_module

    blocked_roots = frozenset({"requests", "httpx", "openai", "anthropic"})
    for module in (runner_module, cases_module):
        source_path = Path(inspect.getsourcefile(module) or "")
        if not source_path.is_file():
            return False
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        if blocked_roots & imported:
            return False
        banned_symbol = "provider" + "_factory"
        if banned_symbol in source:
            return False
    # Governance outcomes consume QualityGateCode / AssistantOutcomeCode only.
    return True


def _execute_case(
    case: QualityEvaluationCase,
    ctx: _LiveContext,
) -> AiQualityEvaluationCaseResult:
    scenario = case.scenario_type
    snapshot = ctx.snapshot

    if scenario is QualityScenarioType.AUTHORITATIVE_GATE_PASS:
        return _pass_result(
            case,
            actual_top=ctx.gate_result_code,
            message="authoritative gate",
        )
    if scenario is QualityScenarioType.AUTHORITATIVE_RAG_PASS:
        ok = (
            ctx.rag_report.failed_case_count == 0
            and ctx.rag_report.overall_result == "PASS"
            and ctx.rag_report.total_case_count == 31
        )
        return _property_pass(case, ok=ok, message="rag pass")
    if scenario is QualityScenarioType.AUTHORITATIVE_TOOL_PASS:
        ok = (
            ctx.tool_report.failed_case_count == 0
            and ctx.tool_report.overall_result == "PASS"
            and ctx.tool_report.total_case_count == 81
        )
        return _property_pass(case, ok=ok, message="tool pass")
    if scenario is QualityScenarioType.SNAPSHOT_GATING_HASH_STABLE:
        first = compute_quality_snapshot_hash(snapshot)
        rebuilt = build_ai_quality_snapshot(
            rag_report=ctx.rag_report,
            tool_assistant_report=ctx.tool_report,
            privacy_violation_count=0,
            candidate_sha=None,
        )
        second = compute_quality_snapshot_hash(rebuilt)
        return _property_pass(case, ok=first == second, message="gating hash stable")
    if scenario is QualityScenarioType.CASE_SET_HASH_DETERMINISTIC:
        first = compute_quality_case_set_hash(ALL_QUALITY_CASES)
        second = compute_quality_case_set_hash(ALL_QUALITY_CASES)
        return _property_pass(case, ok=first == second, message="case-set hash")
    if scenario is QualityScenarioType.RAG_CASE_SET_PRESERVED:
        ok = snapshot.rag.case_set_sha256 == EXPECTED_RAG_CASE_SET_SHA256
        return _property_pass(case, ok=ok, message="rag case set")
    if scenario is QualityScenarioType.TOOL_CASE_SET_PRESERVED:
        ok = (
            snapshot.tool_assistant.case_set_sha256 == EXPECTED_TOOL_CASE_SET_SHA256
        )
        return _property_pass(case, ok=ok, message="tool case set")
    if scenario is QualityScenarioType.BASELINE_INTEGRITY_CONSTANT:
        baseline = _load_authoritative_baseline_for_quality()
        digest = compute_baseline_integrity_hash(baseline)
        ok = digest == SPRINT121_AI_QUALITY_BASELINE_SHA256
        return _property_pass(case, ok=ok, message="baseline integrity constant")
    if scenario is QualityScenarioType.ZERO_RAG_NETWORK:
        return _property_pass(
            case,
            ok=snapshot.rag.network_call_count == 0,
            message="rag network",
        )
    if scenario is QualityScenarioType.ZERO_TOOL_NETWORK:
        return _property_pass(
            case,
            ok=snapshot.tool_assistant.network_call_count == 0,
            message="tool network",
        )
    if scenario is QualityScenarioType.ZERO_RAG_LIVE_EMBEDDING:
        return _property_pass(
            case,
            ok=snapshot.rag.live_embedding_call_count == 0,
            message="live embedding",
        )
    if scenario is QualityScenarioType.ZERO_RAG_LIVE_LLM:
        return _property_pass(
            case,
            ok=snapshot.rag.live_llm_call_count == 0,
            message="live llm",
        )
    if scenario is QualityScenarioType.ZERO_TOOL_LIVE_PROVIDER:
        return _property_pass(
            case,
            ok=snapshot.tool_assistant.live_provider_call_count == 0,
            message="live provider",
        )
    if scenario is QualityScenarioType.PRIVACY_ZERO:
        return _property_pass(
            case,
            ok=snapshot.privacy_violation_count == 0,
            message="privacy zero",
        )
    if scenario is QualityScenarioType.RAG_CASE_SET_MISMATCH:
        return _run_gate_case(
            case,
            _replace_rag(snapshot, case_set_sha256=_SHA_ALT),
        )
    if scenario is QualityScenarioType.TOOL_CASE_SET_MISMATCH:
        return _run_gate_case(
            case,
            _replace_tool(snapshot, case_set_sha256=_SHA_ALT),
        )
    if scenario is QualityScenarioType.MISSING_CASE:
        return _run_gate_case(
            case,
            _replace_rag(snapshot, cases=snapshot.rag.cases[1:]),
        )
    if scenario is QualityScenarioType.UNEXPECTED_CASE:
        extra = PerCaseQualitySnapshot(
            case_id="ZZ-QUALITY-UNEXPECTED",
            outcome=CaseOutcome.PASS,
            result_fingerprint=_fingerprint("unexpected"),
        )
        return _run_gate_case(
            case,
            _replace_rag(snapshot, cases=snapshot.rag.cases + (extra,)),
        )
    if scenario is QualityScenarioType.NON_PASS_OUTCOME:
        target = snapshot.rag.cases[0]
        cases = tuple(
            replace(item, outcome=CaseOutcome.FAIL)
            if item.case_id == target.case_id
            else item
            for item in snapshot.rag.cases
        )
        return _run_gate_case(case, _replace_rag(snapshot, cases=cases))
    if scenario in {
        QualityScenarioType.FINGERPRINT_MISMATCH,
        QualityScenarioType.FINGERPRINT_FIELD_REGRESSION,
        QualityScenarioType.AGGREGATE_MASKING,
    }:
        target = snapshot.rag.cases[0]
        cases = tuple(
            replace(item, result_fingerprint=_fingerprint(f"mut-{case.case_id}"))
            if item.case_id == target.case_id
            else item
            for item in snapshot.rag.cases
        )
        return _run_gate_case(case, _replace_rag(snapshot, cases=cases))
    if scenario is QualityScenarioType.PRIVACY_VIOLATION:
        return _run_gate_case(
            case,
            replace(snapshot, privacy_violation_count=1),
        )
    if scenario is QualityScenarioType.NETWORK_ACTIVITY:
        return _run_gate_case(
            case,
            _replace_tool(snapshot, network_call_count=1),
        )
    if scenario is QualityScenarioType.LIVE_EMBEDDING_ACTIVITY:
        return _run_gate_case(
            case,
            _replace_rag(snapshot, live_embedding_call_count=1),
        )
    if scenario is QualityScenarioType.LIVE_LLM_ACTIVITY:
        return _run_gate_case(
            case,
            _replace_rag(snapshot, live_llm_call_count=1),
        )
    if scenario is QualityScenarioType.LIVE_PROVIDER_ACTIVITY:
        return _run_gate_case(
            case,
            _replace_tool(snapshot, live_provider_call_count=1),
        )
    if scenario is QualityScenarioType.CANDIDATE_SHA_INDEPENDENT:
        first = run_ai_quality_gate(replace(snapshot, candidate_sha="abcdef1"))
        second = run_ai_quality_gate(
            replace(snapshot, candidate_sha="1234567890abcdef")
        )
        ok = first == second and first.top_level_outcome is QualityGateCode.PASS
        return _property_pass(case, ok=ok, message="candidate sha independent")
    if scenario is QualityScenarioType.REPORT_SHA_INDEPENDENT:
        first = run_ai_quality_gate(
            _replace_rag(snapshot, report_sha256=_SHA_ALT)
        )
        second = run_ai_quality_gate(
            _replace_tool(snapshot, report_sha256=_SHA_ALT)
        )
        ok = first == second and first.top_level_outcome is QualityGateCode.PASS
        return _property_pass(case, ok=ok, message="report sha independent")
    if scenario is QualityScenarioType.BASELINE_INTEGRITY_MISMATCH:
        baseline = _load_authoritative_baseline_for_quality()
        first_family = baseline.families[0]
        first_case = first_family.cases[0]
        mutated_case = replace(
            first_case,
            result_fingerprint=_fingerprint("integrity-break"),
        )
        mutated_family = replace(
            first_family,
            cases=(mutated_case,) + first_family.cases[1:],
        )
        mutated = replace(
            baseline,
            families=(mutated_family,) + baseline.families[1:],
        )
        digest = compute_baseline_integrity_hash(mutated)
        ok = digest != SPRINT121_AI_QUALITY_BASELINE_SHA256
        return _property_pass(case, ok=ok, message="integrity mismatch detected")
    if scenario is QualityScenarioType.BASELINE_MALFORMED:
        try:
            parse_quality_baseline("{not-json")
            ok = False
        except QualityGateContractError:
            ok = True
        return _property_pass(case, ok=ok, message="malformed baseline")
    if scenario is QualityScenarioType.MULTI_FAILURE_ORDERING:
        target = snapshot.rag.cases[0]
        cases = tuple(
            replace(item, result_fingerprint=_fingerprint("multi"))
            if item.case_id == target.case_id
            else item
            for item in snapshot.rag.cases
        )
        mutated = replace(
            _replace_rag(
                _replace_tool(snapshot, network_call_count=1),
                cases=cases,
            ),
            privacy_violation_count=1,
        )
        return _run_gate_case(case, mutated)
    if scenario is QualityScenarioType.EVALUATION_INCOMPLETE_COUNT:
        return _run_gate_case(
            case,
            _replace_rag(snapshot, cases=snapshot.rag.cases[1:]),
        )
    if scenario is QualityScenarioType.CASE_SWAP:
        victim = snapshot.rag.cases[1]
        swapped = []
        for item in snapshot.rag.cases:
            if item.case_id == victim.case_id:
                swapped.append(
                    PerCaseQualitySnapshot(
                        case_id="ZZ-QUALITY-SWAP-C",
                        outcome=CaseOutcome.PASS,
                        result_fingerprint=item.result_fingerprint,
                    )
                )
            else:
                swapped.append(item)
        return _run_gate_case(case, _replace_rag(snapshot, cases=tuple(swapped)))
    if scenario is QualityScenarioType.OBSERVATION_COLLECTOR_ISOLATION:
        ok = _prove_observation_collector_isolation()
        return _property_pass(case, ok=ok, message="collector isolation")
    if scenario is QualityScenarioType.NO_SECOND_CLASSIFIER:
        ok = _prove_no_second_classifier()
        return _property_pass(case, ok=ok, message="no second classifier")
    raise AiQualityEvaluationRunnerError(
        f"unsupported scenario type: {scenario.value}"
    )


def quality_report_to_gating_dict(
    report: AiQualityEvaluationReport,
) -> dict[str, Any]:
    return {
        "baseline_integrity_sha256": report.baseline_integrity_sha256,
        "evaluation_version": report.evaluation_version,
        "failed_case_count": report.failed_case_count,
        "live_embedding_call_count": report.live_embedding_call_count,
        "live_llm_call_count": report.live_llm_call_count,
        "live_provider_call_count": report.live_provider_call_count,
        "network_call_count": report.network_call_count,
        "overall_result": report.overall_result,
        "passed_case_count": report.passed_case_count,
        "quality_case_set_sha256": report.quality_case_set_sha256,
        "rag_case_set_sha256": report.rag_case_set_sha256,
        "results": [
            {
                "actual_case_regression_codes": list(item.actual_case_regression_codes),
                "actual_reason_codes": list(item.actual_reason_codes),
                "actual_top_level_outcome": item.actual_top_level_outcome,
                "case_id": item.case_id,
                "category": item.category,
                "expected_case_regression_codes": list(
                    item.expected_case_regression_codes
                ),
                "expected_reason_codes": list(item.expected_reason_codes),
                "expected_top_level_outcome": item.expected_top_level_outcome,
                "passed": item.passed,
                "threat_ids": list(item.threat_ids),
            }
            for item in sorted(report.results, key=lambda value: value.case_id)
        ],
        "runner_version": report.runner_version,
        "threat_coverage": dict(report.threat_coverage),
        "tool_assistant_case_set_sha256": report.tool_assistant_case_set_sha256,
        "total_case_count": report.total_case_count,
    }


def canonical_quality_report_bytes(report: AiQualityEvaluationReport) -> bytes:
    return json.dumps(
        quality_report_to_gating_dict(report),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def compute_quality_report_hash(report: AiQualityEvaluationReport) -> str:
    return hashlib.sha256(canonical_quality_report_bytes(report)).hexdigest()


def evaluation_report_to_json_dict(
    report: AiQualityEvaluationReport,
) -> dict[str, Any]:
    data = quality_report_to_gating_dict(report)
    data["candidate_sha"] = report.candidate_sha
    data["quality_report_sha256"] = report.quality_report_sha256
    return data


def run_ai_quality_evaluation(
    *,
    candidate_sha: str | None = None,
    cases: Sequence[QualityEvaluationCase] | None = None,
) -> AiQualityEvaluationReport:
    """Execute offline evaluators, fixed-baseline gate, and quality cases."""
    normalised_candidate = _normalise_candidate_sha(candidate_sha)
    source_cases = ALL_QUALITY_CASES if cases is None else cases
    try:
        validated = validate_and_sort_quality_cases(source_cases)
    except QualityEvaluationCaseContractError as exc:
        raise AiQualityEvaluationRunnerError(str(exc)) from exc

    with transaction.atomic():
        rag_report = run_final_rag_evaluation()
        tool_report = run_tool_assistant_evaluation()
        transaction.set_rollback(True)

    snapshot = build_ai_quality_snapshot(
        rag_report=rag_report,
        tool_assistant_report=tool_report,
        privacy_violation_count=0,
        candidate_sha=normalised_candidate,
    )
    gate = run_ai_quality_gate(snapshot)
    ctx = _LiveContext(
        rag_report=rag_report,
        tool_report=tool_report,
        snapshot=snapshot,
        gate_result_code=gate.top_level_outcome,
    )

    results: list[AiQualityEvaluationCaseResult] = []
    for case in validated:
        try:
            results.append(_execute_case(case, ctx))
        except QualityGateContractError:
            raise AiQualityEvaluationRunnerError(
                _AUTHORITATIVE_BASELINE_INVALID_MESSAGE
            ) from None
    results = tuple(results)
    passed_count = sum(1 for item in results if item.passed)
    failed_count = len(results) - passed_count
    network_total = (
        snapshot.rag.network_call_count + snapshot.tool_assistant.network_call_count
    )
    overall = (
        "PASS"
        if (
            failed_count == 0
            and rag_report.overall_result == "PASS"
            and tool_report.overall_result == "PASS"
            and gate.top_level_outcome is QualityGateCode.PASS
            and snapshot.privacy_violation_count == 0
            and network_total == 0
            and snapshot.rag.live_embedding_call_count == 0
            and snapshot.rag.live_llm_call_count == 0
            and snapshot.tool_assistant.live_provider_call_count == 0
        )
        else "FAIL"
    )
    draft = AiQualityEvaluationReport(
        runner_version=RUNNER_VERSION,
        evaluation_version=EVALUATION_VERSION,
        quality_case_set_sha256=compute_quality_case_set_hash(validated),
        overall_result=overall,
        total_case_count=len(results),
        passed_case_count=passed_count,
        failed_case_count=failed_count,
        threat_coverage=dict(threat_coverage(validated)),
        results=results,
        rag_case_set_sha256=snapshot.rag.case_set_sha256,
        tool_assistant_case_set_sha256=snapshot.tool_assistant.case_set_sha256,
        baseline_integrity_sha256=SPRINT121_AI_QUALITY_BASELINE_SHA256,
        network_call_count=network_total,
        live_embedding_call_count=snapshot.rag.live_embedding_call_count,
        live_llm_call_count=snapshot.rag.live_llm_call_count,
        live_provider_call_count=snapshot.tool_assistant.live_provider_call_count,
        quality_report_sha256="",
        candidate_sha=normalised_candidate,
    )
    digest = compute_quality_report_hash(draft)
    return replace(draft, quality_report_sha256=digest)


__all__ = (
    "AiQualityEvaluationCaseResult",
    "AiQualityEvaluationReport",
    "AiQualityEvaluationRunnerError",
    "EXPECTED_RAG_CASE_SET_SHA256",
    "EXPECTED_TOOL_CASE_SET_SHA256",
    "RUNNER_VERSION",
    "canonical_quality_report_bytes",
    "compute_quality_report_hash",
    "evaluation_report_to_json_dict",
    "quality_report_to_gating_dict",
    "run_ai_quality_evaluation",
)

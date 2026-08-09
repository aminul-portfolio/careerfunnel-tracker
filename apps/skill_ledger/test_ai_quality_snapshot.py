"""Sprint 122 Phase 2: deterministic AI quality snapshot tests."""

from __future__ import annotations

import dataclasses
import hashlib

from django.test import SimpleTestCase

from apps.skill_ledger.evaluation.quality_snapshot import (
    QUALITY_SNAPSHOT_SCHEMA_VERSION,
    AiQualitySnapshot,
    CaseOutcome,
    EvaluationFamily,
    PerCaseQualitySnapshot,
    QualitySnapshotContractError,
    RagQualitySnapshot,
    ToolAssistantQualitySnapshot,
    build_ai_quality_snapshot,
    build_rag_quality_snapshot,
    build_tool_assistant_quality_snapshot,
    canonical_quality_snapshot_bytes,
    compute_quality_snapshot_hash,
    fingerprint_rag_adversarial_result,
    fingerprint_rag_generation_safety_result,
    fingerprint_rag_retrieval_quality_result,
    fingerprint_tool_assistant_case_result,
    quality_snapshot_to_gating_dict,
)
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

_SHA_A = "a" * 64
_SHA_B = "b" * 64
_SHA_C = "c" * 64
_SHA_D = "d" * 64


def _retrieval(
    *,
    case_id: str = "rq-b",
    passed: bool = True,
    message: str = "ok",
    recall_at_5: float = 1.0,
) -> RagRetrievalQualityRunResult:
    return RagRetrievalQualityRunResult(
        case_id=case_id,
        category="RETRIEVAL_QUALITY",
        passed=passed,
        ranked_local_ids=("L1", "L2"),
        recall_at_5=recall_at_5,
        recall_at_1=1.0,
        mrr=1.0,
        expected_recall_at_5=1.0,
        message=message,
    )


def _adversarial(
    *,
    case_id: str = "adv-a",
    passed: bool = True,
    message: str = "ok",
) -> RagAdversarialRetrievalRunResult:
    return RagAdversarialRetrievalRunResult(
        case_id=case_id,
        category="ADVERSARIAL_RETRIEVAL",
        adversarial_mode="CROSS_USER",
        passed=passed,
        ranked_local_ids=("L9",),
        message=message,
    )


def _generation(
    *,
    case_id: str = "gen-c",
    passed: bool = False,
    message: str = "fail",
) -> RagGenerationSafetyRunResult:
    return RagGenerationSafetyRunResult(
        case_id=case_id,
        category="ATTRIBUTION_SAFETY",
        passed=passed,
        expected_acceptance=False,
        actual_acceptance=False,
        expected_rejection_code="UNKNOWN_SOURCE",
        actual_rejection_code="UNKNOWN_SOURCE",
        expected_provider_called=False,
        actual_provider_called=False,
        provider_call_count=0,
        expected_final_rendered_labels=None,
        actual_final_rendered_labels=None,
        query_fence_present=True,
        evidence_fence_present=True,
        raw_query_sentinel_leaked=False,
        raw_evidence_sentinel_leaked=False,
        message=message,
    )


def _rag_report(
    *,
    case_set_sha256: str = _SHA_A,
    report_sha256: str = _SHA_B,
    retrieval=None,
    adversarial=None,
    generation=None,
    network_call_count: int = 0,
    live_embedding_call_count: int = 0,
    live_llm_call_count: int = 0,
) -> RagFinalEvaluationReport:
    retrieval = (_retrieval(),) if retrieval is None else retrieval
    adversarial = (_adversarial(),) if adversarial is None else adversarial
    generation = (_generation(),) if generation is None else generation
    all_cases = tuple(retrieval) + tuple(adversarial) + tuple(generation)
    passed = sum(1 for item in all_cases if item.passed)
    failed = len(all_cases) - passed
    return RagFinalEvaluationReport(
        runner_version="test",
        evaluation_version="test",
        case_set_sha256=case_set_sha256,
        overall_result="PASS" if failed == 0 else "FAIL",
        total_case_count=len(all_cases),
        passed_case_count=passed,
        failed_case_count=failed,
        retrieval_quality_case_count=len(retrieval),
        adversarial_retrieval_case_count=len(adversarial),
        attribution_safety_case_count=len(generation),
        unsupported_output_case_count=0,
        zero_evidence_case_count=0,
        prompt_injection_case_count=0,
        retrieval_quality_results=tuple(retrieval),
        adversarial_retrieval_results=tuple(adversarial),
        generation_safety_results=tuple(generation),
        network_call_count=network_call_count,
        live_embedding_call_count=live_embedding_call_count,
        live_llm_call_count=live_llm_call_count,
        report_sha256=report_sha256,
    )


def _tool_case(
    *,
    case_id: str = "ta-b",
    passed: bool = True,
    message: str = "ok",
    planner_calls: int = 1,
) -> ToolAssistantCaseRunResult:
    return ToolAssistantCaseRunResult(
        case_id=case_id,
        category="TOOL_SELECTION",
        threat_ids=("T1",),
        expected_outcome="OK",
        observed_outcome="OK" if passed else "FAILED",
        planner_calls=planner_calls,
        tools_executed=1 if passed else 0,
        synthesis_calls=1 if passed else 0,
        tools_used=("get_skill_ledger_summary",) if passed else (),
        sources_count=0,
        expected_source_refs=(),
        network_call_count=0,
        passed=passed,
        message=message,
    )


def _tool_report(
    *,
    case_set_sha256: str = _SHA_C,
    report_sha256: str = _SHA_D,
    results=None,
    network_call_count: int = 0,
    live_provider_call_count: int = 0,
) -> ToolAssistantEvaluationReport:
    if results is None:
        results = (_tool_case(case_id="ta-b"), _tool_case(case_id="ta-a"))
    passed = sum(1 for item in results if item.passed)
    failed = len(results) - passed
    return ToolAssistantEvaluationReport(
        runner_version="test",
        evaluation_version="test",
        case_set_sha256=case_set_sha256,
        overall_result="PASS" if failed == 0 else "FAIL",
        total_case_count=len(results),
        passed_case_count=passed,
        failed_case_count=failed,
        category_counts={"TOOL_SELECTION": len(results)},
        threat_coverage={"T1": len(results)},
        results=tuple(results),
        network_call_count=network_call_count,
        live_provider_call_count=live_provider_call_count,
        report_sha256=report_sha256,
    )


class QualitySnapshotContractTests(SimpleTestCase):
    def test_schema_version_locked(self):
        self.assertEqual(QUALITY_SNAPSHOT_SCHEMA_VERSION, 1)
        snapshot = build_ai_quality_snapshot(
            rag_report=_rag_report(),
            tool_assistant_report=_tool_report(),
            privacy_violation_count=0,
            candidate_sha=None,
        )
        self.assertEqual(snapshot.schema_version, 1)
        with self.assertRaises(QualitySnapshotContractError):
            AiQualitySnapshot(
                schema_version=2,
                rag=snapshot.rag,
                tool_assistant=snapshot.tool_assistant,
                privacy_violation_count=0,
                candidate_sha=None,
            )

    def test_snapshot_dataclasses_immutable(self):
        snapshot = build_ai_quality_snapshot(
            rag_report=_rag_report(),
            tool_assistant_report=_tool_report(),
            privacy_violation_count=0,
            candidate_sha=None,
        )
        with self.assertRaises(dataclasses.FrozenInstanceError):
            snapshot.privacy_violation_count = 9  # type: ignore[misc]
        with self.assertRaises(dataclasses.FrozenInstanceError):
            snapshot.rag.network_call_count = 1  # type: ignore[misc]
        case = snapshot.rag.cases[0]
        with self.assertRaises(dataclasses.FrozenInstanceError):
            case.case_id = "mutated"  # type: ignore[misc]

    def test_evaluation_families_are_closed(self):
        self.assertEqual(
            {item.value for item in EvaluationFamily},
            {"RAG_FINAL", "TOOL_ASSISTANT"},
        )

    def test_case_outcome_is_pass_fail_only(self):
        self.assertEqual(
            {item.value for item in CaseOutcome},
            {"PASS", "FAIL"},
        )
        self.assertFalse(hasattr(CaseOutcome, "BETTER"))
        self.assertFalse(hasattr(CaseOutcome, "WORSE"))

    def test_malformed_sha256_rejected(self):
        with self.assertRaises(QualitySnapshotContractError):
            PerCaseQualitySnapshot(
                case_id="x",
                outcome=CaseOutcome.PASS,
                result_fingerprint="not-a-hash",
            )
        with self.assertRaises(QualitySnapshotContractError):
            build_rag_quality_snapshot(
                _rag_report(case_set_sha256="ABC" + ("0" * 61))
            )

    def test_duplicate_case_ids_rejected(self):
        with self.assertRaises(QualitySnapshotContractError):
            build_rag_quality_snapshot(
                _rag_report(
                    retrieval=(_retrieval(case_id="dup"),),
                    adversarial=(_adversarial(case_id="dup"),),
                    generation=(),
                )
            )

    def test_empty_case_id_rejected(self):
        with self.assertRaises(QualitySnapshotContractError):
            build_rag_quality_snapshot(
                _rag_report(
                    retrieval=(_retrieval(case_id=""),),
                    adversarial=(),
                    generation=(),
                )
            )

    def test_deterministic_case_sorting_by_case_id(self):
        snapshot = build_rag_quality_snapshot(
            _rag_report(
                retrieval=(_retrieval(case_id="rq-z"),),
                adversarial=(_adversarial(case_id="adv-m"),),
                generation=(_generation(case_id="gen-a"),),
            )
        )
        self.assertEqual(
            [item.case_id for item in snapshot.cases],
            ["adv-m", "gen-a", "rq-z"],
        )


class QualitySnapshotFingerprintTests(SimpleTestCase):
    def test_rag_retrieval_fingerprint_deterministic(self):
        first = fingerprint_rag_retrieval_quality_result(_retrieval())
        second = fingerprint_rag_retrieval_quality_result(_retrieval())
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)
        self.assertTrue(all(ch in "0123456789abcdef" for ch in first))

    def test_fingerprint_rejects_nonfinite_floats(self):
        for label, value in (
            ("nan", float("nan")),
            ("inf", float("inf")),
            ("neg_inf", float("-inf")),
        ):
            with self.subTest(label=label):
                with self.assertRaises(QualitySnapshotContractError):
                    fingerprint_rag_retrieval_quality_result(
                        _retrieval(recall_at_5=value)
                    )

    def test_fingerprint_accepts_finite_float(self):
        digest = fingerprint_rag_retrieval_quality_result(
            _retrieval(recall_at_5=0.75)
        )
        self.assertEqual(len(digest), 64)
        self.assertTrue(all(ch in "0123456789abcdef" for ch in digest))

    def test_rag_adversarial_fingerprint_deterministic(self):
        first = fingerprint_rag_adversarial_result(_adversarial())
        second = fingerprint_rag_adversarial_result(_adversarial())
        self.assertEqual(first, second)

    def test_rag_generation_safety_fingerprint_deterministic(self):
        first = fingerprint_rag_generation_safety_result(_generation())
        second = fingerprint_rag_generation_safety_result(_generation())
        self.assertEqual(first, second)

    def test_tool_assistant_fingerprint_deterministic(self):
        first = fingerprint_tool_assistant_case_result(_tool_case())
        second = fingerprint_tool_assistant_case_result(_tool_case())
        self.assertEqual(first, second)

    def test_changing_gating_field_changes_fingerprint(self):
        base = fingerprint_rag_retrieval_quality_result(_retrieval(recall_at_5=1.0))
        changed = fingerprint_rag_retrieval_quality_result(
            _retrieval(recall_at_5=0.5)
        )
        self.assertNotEqual(base, changed)
        tool_base = fingerprint_tool_assistant_case_result(
            _tool_case(planner_calls=1)
        )
        tool_changed = fingerprint_tool_assistant_case_result(
            _tool_case(planner_calls=0, passed=False)
        )
        self.assertNotEqual(tool_base, tool_changed)

    def test_diagnostic_message_does_not_affect_fingerprint(self):
        first = fingerprint_rag_retrieval_quality_result(
            _retrieval(message="ok")
        )
        second = fingerprint_rag_retrieval_quality_result(
            _retrieval(message="DIFFERENT DIAGNOSTIC MESSAGE")
        )
        self.assertEqual(first, second)
        tool_first = fingerprint_tool_assistant_case_result(
            _tool_case(message="ok")
        )
        tool_second = fingerprint_tool_assistant_case_result(
            _tool_case(message="different diagnostic")
        )
        self.assertEqual(tool_first, tool_second)


class QualitySnapshotGatingTests(SimpleTestCase):
    def test_report_sha256_does_not_affect_gating_hash(self):
        first = build_ai_quality_snapshot(
            rag_report=_rag_report(report_sha256=_SHA_B),
            tool_assistant_report=_tool_report(report_sha256=_SHA_D),
            privacy_violation_count=0,
            candidate_sha=None,
        )
        second = build_ai_quality_snapshot(
            rag_report=_rag_report(report_sha256=_SHA_A),
            tool_assistant_report=_tool_report(report_sha256=_SHA_C),
            privacy_violation_count=0,
            candidate_sha=None,
        )
        self.assertNotEqual(first.rag.report_sha256, second.rag.report_sha256)
        self.assertEqual(
            compute_quality_snapshot_hash(first),
            compute_quality_snapshot_hash(second),
        )

    def test_candidate_sha_does_not_affect_gating_hash(self):
        first = build_ai_quality_snapshot(
            rag_report=_rag_report(),
            tool_assistant_report=_tool_report(),
            privacy_violation_count=0,
            candidate_sha="abcdef1",
        )
        second = build_ai_quality_snapshot(
            rag_report=_rag_report(),
            tool_assistant_report=_tool_report(),
            privacy_violation_count=0,
            candidate_sha="1234567890abcdef",
        )
        self.assertNotEqual(first.candidate_sha, second.candidate_sha)
        self.assertEqual(
            compute_quality_snapshot_hash(first),
            compute_quality_snapshot_hash(second),
        )

    def test_candidate_sha_invalid_arbitrary_text_rejected(self):
        with self.assertRaises(QualitySnapshotContractError):
            build_ai_quality_snapshot(
                rag_report=_rag_report(),
                tool_assistant_report=_tool_report(),
                privacy_violation_count=0,
                candidate_sha="not a git sha!!!!",
            )

    def test_candidate_case_count_reconciliation_enforced(self):
        snapshot = build_rag_quality_snapshot(_rag_report())
        with self.assertRaises(QualitySnapshotContractError):
            RagQualitySnapshot(
                evaluation_family=EvaluationFamily.RAG_FINAL,
                case_set_sha256=snapshot.case_set_sha256,
                candidate_case_count=snapshot.candidate_case_count + 1,
                passed_count=snapshot.passed_count,
                failed_count=snapshot.failed_count,
                cases=snapshot.cases,
                network_call_count=0,
                live_embedding_call_count=0,
                live_llm_call_count=0,
                report_sha256=snapshot.report_sha256,
            )

    def test_passed_failed_count_reconciliation_enforced(self):
        snapshot = build_tool_assistant_quality_snapshot(_tool_report())
        with self.assertRaises(QualitySnapshotContractError):
            ToolAssistantQualitySnapshot(
                evaluation_family=EvaluationFamily.TOOL_ASSISTANT,
                case_set_sha256=snapshot.case_set_sha256,
                candidate_case_count=snapshot.candidate_case_count,
                passed_count=snapshot.passed_count + 1,
                failed_count=max(0, snapshot.failed_count - 1),
                cases=snapshot.cases,
                network_call_count=0,
                live_provider_call_count=0,
                report_sha256=snapshot.report_sha256,
            )

    def test_family_specific_live_call_counters_preserved(self):
        rag = build_rag_quality_snapshot(
            _rag_report(
                live_embedding_call_count=2,
                live_llm_call_count=3,
                network_call_count=1,
            )
        )
        tool = build_tool_assistant_quality_snapshot(
            _tool_report(
                live_provider_call_count=4,
                network_call_count=5,
            )
        )
        self.assertEqual(rag.live_embedding_call_count, 2)
        self.assertEqual(rag.live_llm_call_count, 3)
        self.assertEqual(rag.network_call_count, 1)
        self.assertFalse(hasattr(rag, "live_provider_call_count"))
        self.assertEqual(tool.live_provider_call_count, 4)
        self.assertEqual(tool.network_call_count, 5)
        self.assertFalse(hasattr(tool, "live_embedding_call_count"))

    def test_case_set_sha256_preserved_exactly_from_report(self):
        rag_report = _rag_report(case_set_sha256=_SHA_A)
        tool_report = _tool_report(case_set_sha256=_SHA_C)
        snapshot = build_ai_quality_snapshot(
            rag_report=rag_report,
            tool_assistant_report=tool_report,
            privacy_violation_count=0,
            candidate_sha=None,
        )
        self.assertEqual(snapshot.rag.case_set_sha256, _SHA_A)
        self.assertEqual(snapshot.tool_assistant.case_set_sha256, _SHA_C)
        self.assertIs(snapshot.rag.case_set_sha256, rag_report.case_set_sha256)

    def test_gating_canonical_bytes_deterministic(self):
        snapshot = build_ai_quality_snapshot(
            rag_report=_rag_report(),
            tool_assistant_report=_tool_report(),
            privacy_violation_count=1,
            candidate_sha="abcdef0",
        )
        first = canonical_quality_snapshot_bytes(snapshot)
        second = canonical_quality_snapshot_bytes(snapshot)
        self.assertEqual(first, second)
        self.assertEqual(
            hashlib.sha256(first).hexdigest(),
            compute_quality_snapshot_hash(snapshot),
        )
        gating = quality_snapshot_to_gating_dict(snapshot)
        self.assertNotIn("candidate_sha", gating)
        self.assertNotIn("report_sha256", gating)
        self.assertNotIn("report_sha256", gating["rag"])
        self.assertNotIn("report_sha256", gating["tool_assistant"])

    def test_privacy_violation_count_participates_in_gating_hash(self):
        first = build_ai_quality_snapshot(
            rag_report=_rag_report(),
            tool_assistant_report=_tool_report(),
            privacy_violation_count=0,
            candidate_sha=None,
        )
        second = build_ai_quality_snapshot(
            rag_report=_rag_report(),
            tool_assistant_report=_tool_report(),
            privacy_violation_count=1,
            candidate_sha=None,
        )
        self.assertNotEqual(
            compute_quality_snapshot_hash(first),
            compute_quality_snapshot_hash(second),
        )

    def test_builder_consumes_typed_reports_without_console_or_file_parsing(self):
        import ast
        import inspect
        from pathlib import Path

        from apps.skill_ledger.evaluation import quality_snapshot as module

        source = Path(inspect.getsourcefile(module)).read_text(encoding="utf-8")
        self.assertNotIn("run_final_rag_evaluation", source)
        self.assertNotIn("run_tool_assistant_evaluation", source)
        self.assertNotIn("open(", source)
        tree = ast.parse(source)
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        forbidden = {"requests", "httpx", "socket", "urllib", "subprocess"}
        self.assertEqual(forbidden.intersection(imported), set())
        snapshot = build_ai_quality_snapshot(
            rag_report=_rag_report(),
            tool_assistant_report=_tool_report(),
            privacy_violation_count=0,
            candidate_sha=None,
        )
        self.assertIsInstance(snapshot, AiQualitySnapshot)

    def test_raw_structured_evaluation_payload_not_stored_in_per_case(self):
        snapshot = build_ai_quality_snapshot(
            rag_report=_rag_report(),
            tool_assistant_report=_tool_report(),
            privacy_violation_count=0,
            candidate_sha=None,
        )
        fields = {item.name for item in dataclasses.fields(PerCaseQualitySnapshot)}
        self.assertEqual(fields, {"case_id", "outcome", "result_fingerprint"})
        for case in snapshot.rag.cases + snapshot.tool_assistant.cases:
            self.assertFalse(hasattr(case, "message"))
            self.assertFalse(hasattr(case, "ranked_local_ids"))
            self.assertFalse(hasattr(case, "tools_used"))
            self.assertFalse(hasattr(case, "threat_ids"))
            self.assertFalse(hasattr(case, "metadata"))

    def test_bool_rejected_for_privacy_violation_count(self):
        with self.assertRaises(QualitySnapshotContractError):
            build_ai_quality_snapshot(
                rag_report=_rag_report(),
                tool_assistant_report=_tool_report(),
                privacy_violation_count=True,  # type: ignore[arg-type]
                candidate_sha=None,
            )

"""Sprint 122 Phase 4: offline AI quality-lifecycle evaluation tests."""

from __future__ import annotations

import ast
import inspect
import json
import re
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import transaction
from django.test import SimpleTestCase, TestCase

from apps.skill_ledger.evaluation import quality_runner as quality_runner_module
from apps.skill_ledger.evaluation.quality_cases import (
    ALL_QUALITY_CASES,
    QUALITY_CASE_MINIMUM,
    REQUIRED_THREATS,
    QualityEvalCategory,
    QualityEvaluationCase,
    QualityEvaluationCaseContractError,
    QualityScenarioType,
    compute_quality_case_set_hash,
    threat_coverage,
    validate_and_sort_quality_cases,
)
from apps.skill_ledger.evaluation.quality_gate import (
    SPRINT121_AI_QUALITY_BASELINE_PATH,
    SPRINT121_AI_QUALITY_BASELINE_SHA256,
    CaseRegressionCode,
    QualityGateCode,
    QualityGateContractError,
    run_ai_quality_gate,
)
from apps.skill_ledger.evaluation.quality_runner import (
    EXPECTED_RAG_CASE_SET_SHA256,
    EXPECTED_TOOL_CASE_SET_SHA256,
    AiQualityEvaluationReport,
    AiQualityEvaluationRunnerError,
    compute_quality_report_hash,
    evaluation_report_to_json_dict,
    run_ai_quality_evaluation,
)
from apps.skill_ledger.evaluation.quality_snapshot import (
    build_ai_quality_snapshot,
)
from apps.skill_ledger.evaluation.rag_evaluation_runner import (
    run_final_rag_evaluation,
)
from apps.skill_ledger.evaluation.tool_assistant_runner import (
    run_tool_assistant_evaluation,
)
from apps.skill_ledger.management.commands.evaluate_skill_ledger_ai_quality import (
    RESULTS_FILENAME,
    SUMMARY_FILENAME,
    resolve_external_output_dir,
)
from apps.skill_ledger.models import EvidenceEmbedding, SkillEntry

_REPO_ROOT = Path(settings.BASE_DIR).resolve()
_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "django-ci.yml"
_HEAD_SHA = "af15f857b55ee885b9e107338e93018f9bbcb324"
_EXPECTED_QUALITY_CASE_SET_SHA256 = (
    "d0915f0c1d7855d31089c4958d71bf373252d2d1529ce8db42427fe628ed3027"
)
_EXPECTED_QUALITY_REPORT_SHA256 = (
    "0232fab5f40801e777cc4f600cc2d20abaf703c026ce0e5973a0418af5205d5e"
)
User = get_user_model()


def _db_counts() -> tuple[int, int, int]:
    return (
        User.objects.count(),
        SkillEntry.objects.count(),
        EvidenceEmbedding.objects.count(),
    )


class QualityCaseContractTests(SimpleTestCase):
    def test_quality_case_set_meets_minimum(self):
        self.assertGreaterEqual(len(ALL_QUALITY_CASES), QUALITY_CASE_MINIMUM)
        self.assertGreaterEqual(len(ALL_QUALITY_CASES), 51)

    def test_q1_through_q23_complete_threat_coverage(self):
        covered = {threat for case in ALL_QUALITY_CASES for threat in case.threat_ids}
        self.assertEqual(covered, set(REQUIRED_THREATS))
        coverage = threat_coverage(ALL_QUALITY_CASES)
        self.assertEqual(list(coverage.keys()), list(REQUIRED_THREATS))
        for threat in REQUIRED_THREATS:
            self.assertGreaterEqual(coverage[threat], 1)

    def test_quality_case_ids_unique(self):
        ids = [case.case_id for case in ALL_QUALITY_CASES]
        self.assertEqual(len(ids), len(set(ids)))

    def test_quality_cases_sorted_by_case_id(self):
        ids = [case.case_id for case in ALL_QUALITY_CASES]
        self.assertEqual(ids, sorted(ids))
        validate_and_sort_quality_cases(ALL_QUALITY_CASES)

    def test_deterministic_quality_case_set_sha(self):
        first = compute_quality_case_set_hash(ALL_QUALITY_CASES)
        second = compute_quality_case_set_hash(ALL_QUALITY_CASES)
        self.assertEqual(first, second)
        self.assertRegex(first, r"^[0-9a-f]{64}$")
        self.assertEqual(first, _EXPECTED_QUALITY_CASE_SET_SHA256)

    def test_duplicate_threat_ids_rejected(self):
        with self.assertRaises(QualityEvaluationCaseContractError):
            QualityEvaluationCase(
                case_id="bad-dup-threat",
                category=QualityEvalCategory.SNAPSHOT,
                threat_ids=("Q1", "Q1"),
                scenario_type=QualityScenarioType.AUTHORITATIVE_GATE_PASS,
                expected_top_level_outcome=QualityGateCode.PASS,
                expected_reason_codes=(),
                expected_case_regression_codes=(),
            )

    def test_invalid_expected_reason_code_type_rejected(self):
        with self.assertRaises(QualityEvaluationCaseContractError):
            QualityEvaluationCase(
                case_id="bad-reason-type",
                category=QualityEvalCategory.SNAPSHOT,
                threat_ids=("Q1",),
                scenario_type=QualityScenarioType.AUTHORITATIVE_GATE_PASS,
                expected_top_level_outcome=QualityGateCode.PASS,
                expected_reason_codes=("REGRESSION_DETECTED",),  # type: ignore[arg-type]
                expected_case_regression_codes=(),
            )

    def test_duplicate_expected_reason_codes_rejected(self):
        with self.assertRaises(QualityEvaluationCaseContractError):
            QualityEvaluationCase(
                case_id="bad-dup-reason",
                category=QualityEvalCategory.REGRESSION,
                threat_ids=("Q8",),
                scenario_type=QualityScenarioType.FINGERPRINT_MISMATCH,
                expected_top_level_outcome=QualityGateCode.REGRESSION_DETECTED,
                expected_reason_codes=(
                    QualityGateCode.REGRESSION_DETECTED,
                    QualityGateCode.REGRESSION_DETECTED,
                ),
                expected_case_regression_codes=(CaseRegressionCode.FINGERPRINT_MISMATCH,),
            )

    def test_invalid_expected_regression_code_type_rejected(self):
        with self.assertRaises(QualityEvaluationCaseContractError):
            QualityEvaluationCase(
                case_id="bad-regression-type",
                category=QualityEvalCategory.REGRESSION,
                threat_ids=("Q8",),
                scenario_type=QualityScenarioType.FINGERPRINT_MISMATCH,
                expected_top_level_outcome=QualityGateCode.REGRESSION_DETECTED,
                expected_reason_codes=(QualityGateCode.REGRESSION_DETECTED,),
                expected_case_regression_codes=("FINGERPRINT_MISMATCH",),  # type: ignore[arg-type]
            )

    def test_duplicate_expected_regression_codes_rejected(self):
        with self.assertRaises(QualityEvaluationCaseContractError):
            QualityEvaluationCase(
                case_id="bad-dup-regression",
                category=QualityEvalCategory.REGRESSION,
                threat_ids=("Q8",),
                scenario_type=QualityScenarioType.FINGERPRINT_MISMATCH,
                expected_top_level_outcome=QualityGateCode.REGRESSION_DETECTED,
                expected_reason_codes=(QualityGateCode.REGRESSION_DETECTED,),
                expected_case_regression_codes=(
                    CaseRegressionCode.FINGERPRINT_MISMATCH,
                    CaseRegressionCode.FINGERPRINT_MISMATCH,
                ),
            )


class QualityEvaluationRunnerTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report = run_ai_quality_evaluation(candidate_sha=_HEAD_SHA)

    def test_report_overall_pass_for_authoritative_offline_state(self):
        self.assertEqual(self.report.overall_result, "PASS")
        self.assertEqual(self.report.failed_case_count, 0)
        self.assertEqual(self.report.passed_case_count, self.report.total_case_count)

    def test_quality_report_hash_deterministic(self):
        again = run_ai_quality_evaluation(candidate_sha=_HEAD_SHA)
        self.assertEqual(
            self.report.quality_report_sha256,
            again.quality_report_sha256,
        )
        self.assertEqual(
            compute_quality_report_hash(self.report),
            self.report.quality_report_sha256,
        )
        self.assertEqual(
            self.report.quality_report_sha256,
            _EXPECTED_QUALITY_REPORT_SHA256,
        )

    def test_threat_coverage_is_immutable(self):
        with self.assertRaises(TypeError):
            self.report.threat_coverage["Q1"] = 999  # type: ignore[index]

    def test_candidate_sha_does_not_affect_quality_report_hash(self):
        alt = run_ai_quality_evaluation(candidate_sha="abcdef1")
        self.assertEqual(
            self.report.quality_report_sha256,
            alt.quality_report_sha256,
        )
        self.assertNotEqual(self.report.candidate_sha, alt.candidate_sha)

    def test_rag_case_set_sha_matches_baseline_provenance(self):
        self.assertEqual(self.report.rag_case_set_sha256, EXPECTED_RAG_CASE_SET_SHA256)

    def test_tool_case_set_sha_matches_baseline_provenance(self):
        self.assertEqual(
            self.report.tool_assistant_case_set_sha256,
            EXPECTED_TOOL_CASE_SET_SHA256,
        )

    def test_baseline_integrity_sha_matches_phase3_constant(self):
        self.assertEqual(
            self.report.baseline_integrity_sha256,
            SPRINT121_AI_QUALITY_BASELINE_SHA256,
        )
        self.assertEqual(
            self.report.baseline_integrity_sha256,
            "0cfbe9252a2235ef9e58c0cbbb1d897a67b18259df49290eed16cf514a0a8b71",
        )

    def test_zero_rag_network_calls_enforced(self):
        self.assertEqual(self.report.network_call_count, 0)

    def test_zero_rag_live_embedding_calls_enforced(self):
        self.assertEqual(self.report.live_embedding_call_count, 0)

    def test_zero_rag_live_llm_calls_enforced(self):
        self.assertEqual(self.report.live_llm_call_count, 0)

    def test_zero_tool_network_calls_enforced(self):
        self.assertEqual(self.report.network_call_count, 0)

    def test_zero_tool_live_provider_calls_enforced(self):
        self.assertEqual(self.report.live_provider_call_count, 0)

    def test_q21_case_swap_scenario_fails_as_expected(self):
        result = next(
            item
            for item in self.report.results
            if item.case_id == "aq-q21-case-swap"
        )
        self.assertTrue(result.passed)
        self.assertEqual(
            result.actual_top_level_outcome,
            QualityGateCode.EVALUATION_INCOMPLETE.value,
        )
        self.assertIn("MISSING_CASE", result.actual_case_regression_codes)
        self.assertIn("UNEXPECTED_CASE", result.actual_case_regression_codes)

    def test_q22_collector_exception_isolation_scenario_passes(self):
        result = next(
            item
            for item in self.report.results
            if item.case_id == "aq-q22-collector-isolation"
        )
        self.assertTrue(result.passed)

    def test_q23_no_second_classifier_scenario_passes(self):
        result = next(
            item
            for item in self.report.results
            if item.case_id == "aq-q23-no-second-classifier"
        )
        self.assertTrue(result.passed)

    def test_deterministic_multi_failure_reason_ordering(self):
        result = next(
            item
            for item in self.report.results
            if item.case_id == "aq-q18-multi-failure-ordering"
        )
        self.assertTrue(result.passed)
        self.assertEqual(
            result.actual_reason_codes,
            (
                QualityGateCode.NETWORK_ACTIVITY_DETECTED.value,
                QualityGateCode.PRIVACY_VIOLATION.value,
                QualityGateCode.REGRESSION_DETECTED.value,
            ),
        )
        self.assertEqual(
            result.actual_top_level_outcome,
            QualityGateCode.NETWORK_ACTIVITY_DETECTED.value,
        )

    def test_results_sorted_by_case_id(self):
        ids = [item.case_id for item in self.report.results]
        self.assertEqual(ids, sorted(ids))

    def test_output_contains_no_raw_prompts_evidence_or_user_data(self):
        payload = json.dumps(evaluation_report_to_json_dict(self.report))
        forbidden = (
            "request_text",
            "prompt",
            "answer",
            "skill_name",
            "project_link",
            "traceback",
            "@",
            "http://",
            "https://",
            "password",
            "api_key",
        )
        lowered = payload.casefold()
        for token in forbidden:
            self.assertNotIn(token.casefold(), lowered)

    def test_invalid_candidate_sha_rejected(self):
        with self.assertRaises(AiQualityEvaluationRunnerError):
            run_ai_quality_evaluation(candidate_sha="NOT_HEX")


class QualityRunnerSafetyTests(SimpleTestCase):
    def test_quality_runner_uses_typed_evaluator_reports_not_console_parsing(self):
        source = Path(inspect.getsourcefile(quality_runner_module)).read_text(
            encoding="utf-8"
        )
        self.assertIn("run_final_rag_evaluation", source)
        self.assertIn("run_tool_assistant_evaluation", source)
        self.assertIn("build_ai_quality_snapshot", source)
        self.assertIn("run_ai_quality_gate", source)
        self.assertNotIn("stdout", source.casefold())
        self.assertNotIn("stderr", source.casefold())
        self.assertNotIn("subprocess", source)

    def test_quality_runner_has_no_live_network_provider_dependency(self):
        source_path = Path(inspect.getsourcefile(quality_runner_module))
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertFalse({"requests", "httpx", "openai", "anthropic"} & imported)
        self.assertNotIn("provider" + "_factory", source)


class ManagementCommandPathTests(SimpleTestCase):
    def test_management_command_rejects_repository_root_output(self):
        with self.assertRaises(CommandError):
            resolve_external_output_dir(str(_REPO_ROOT))

    def test_management_command_rejects_repository_child_output(self):
        child = _REPO_ROOT / "apps" / "skill_ledger"
        with self.assertRaises(CommandError):
            resolve_external_output_dir(str(child))


class ManagementCommandExecutionTests(TestCase):
    def test_management_command_accepts_external_output_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            external = Path(tmp).resolve()
            self.assertFalse(_REPO_ROOT in external.parents or external == _REPO_ROOT)
            before = _db_counts()
            call_command(
                "evaluate_skill_ledger_ai_quality",
                candidate_sha=_HEAD_SHA,
                output_dir=str(external),
            )
            after = _db_counts()
            self.assertEqual(before, after)
            results_path = external / RESULTS_FILENAME
            summary_path = external / SUMMARY_FILENAME
            self.assertTrue(results_path.is_file())
            self.assertTrue(summary_path.is_file())
            payload = json.loads(results_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["overall_result"], "PASS")
            self.assertEqual(payload["candidate_sha"], _HEAD_SHA)
            self.assertRegex(payload["quality_report_sha256"], r"^[0-9a-f]{64}$")

    def test_management_command_writes_deterministic_safe_json_result(self):
        with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
            call_command(
                "evaluate_skill_ledger_ai_quality",
                candidate_sha=_HEAD_SHA,
                output_dir=str(Path(tmp1).resolve()),
            )
            call_command(
                "evaluate_skill_ledger_ai_quality",
                candidate_sha=_HEAD_SHA,
                output_dir=str(Path(tmp2).resolve()),
            )
            text_a = (Path(tmp1) / RESULTS_FILENAME).read_text(encoding="utf-8")
            text_b = (Path(tmp2) / RESULTS_FILENAME).read_text(encoding="utf-8")
            self.assertEqual(text_a, text_b)
            payload = json.loads(text_a)
            blob = json.dumps(payload)
            self.assertNotIn("traceback", blob.casefold())
            self.assertNotIn("request_text", blob.casefold())

    def test_command_candidate_sha_is_informational_only(self):
        with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
            call_command(
                "evaluate_skill_ledger_ai_quality",
                candidate_sha=_HEAD_SHA,
                output_dir=str(Path(tmp1).resolve()),
            )
            call_command(
                "evaluate_skill_ledger_ai_quality",
                candidate_sha="1234567890abcdef",
                output_dir=str(Path(tmp2).resolve()),
            )
            a = json.loads((Path(tmp1) / RESULTS_FILENAME).read_text(encoding="utf-8"))
            b = json.loads((Path(tmp2) / RESULTS_FILENAME).read_text(encoding="utf-8"))
            self.assertEqual(a["quality_report_sha256"], b["quality_report_sha256"])
            self.assertEqual(a["quality_case_set_sha256"], b["quality_case_set_sha256"])
            self.assertEqual(a["overall_result"], b["overall_result"])
            self.assertNotEqual(a["candidate_sha"], b["candidate_sha"])

    def test_invalid_candidate_sha_rejected_by_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(CommandError):
                call_command(
                    "evaluate_skill_ledger_ai_quality",
                    candidate_sha="BAD",
                    output_dir=str(Path(tmp).resolve()),
                )

    def test_command_fails_when_evaluation_overall_result_is_fail(self):
        failing = AiQualityEvaluationReport(
            runner_version="x",
            evaluation_version="y",
            quality_case_set_sha256="a" * 64,
            overall_result="FAIL",
            total_case_count=1,
            passed_case_count=0,
            failed_case_count=1,
            threat_coverage={},
            results=(),
            rag_case_set_sha256="b" * 64,
            tool_assistant_case_set_sha256="c" * 64,
            baseline_integrity_sha256="d" * 64,
            network_call_count=0,
            live_embedding_call_count=0,
            live_llm_call_count=0,
            live_provider_call_count=0,
            quality_report_sha256="e" * 64,
            candidate_sha=_HEAD_SHA,
        )
        with tempfile.TemporaryDirectory() as tmp:
            with patch(
                "apps.skill_ledger.management.commands."
                "evaluate_skill_ledger_ai_quality.run_ai_quality_evaluation",
                return_value=failing,
            ):
                with self.assertRaises(CommandError):
                    call_command(
                        "evaluate_skill_ledger_ai_quality",
                        candidate_sha=_HEAD_SHA,
                        output_dir=str(Path(tmp).resolve()),
                    )


class WorkflowQualityStepTests(SimpleTestCase):
    def test_workflow_has_exactly_one_additive_quality_step(self):
        text = _WORKFLOW.read_text(encoding="utf-8")
        matches = re.findall(r"evaluate_skill_ledger_ai_quality", text)
        self.assertEqual(len(matches), 1)
        self.assertEqual(text.count("Offline AI quality evaluation"), 1)
        self.assertNotIn("continue-on-error", text)

    def test_quality_step_is_after_django_tests(self):
        text = _WORKFLOW.read_text(encoding="utf-8")
        tests_idx = text.index("- name: Django tests")
        quality_idx = text.index("- name: Offline AI quality evaluation")
        self.assertLess(tests_idx, quality_idx)

    def test_quality_step_uses_github_sha(self):
        text = _WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('--candidate-sha "${{ github.sha }}"', text)

    def test_quality_step_uses_runner_temp_outside_repo_output(self):
        text = _WORKFLOW.read_text(encoding="utf-8")
        self.assertIn(
            '${{ runner.temp }}/careerfunnel-ai-quality',
            text,
        )

    def test_quality_step_does_not_use_continue_on_error(self):
        text = _WORKFLOW.read_text(encoding="utf-8")
        quality_block = text.split("- name: Offline AI quality evaluation", 1)[1]
        self.assertNotIn("continue-on-error", quality_block)
        self.assertIn("jobs:\n  django-ci:", text)
        self.assertEqual(text.count("\n  django-ci:"), 1)
        self.assertEqual(text.count("name: Django CI"), 1)


class DatabaseNonPersistenceTests(TestCase):
    def test_runner_preserves_user_count(self):
        before = User.objects.count()
        report = run_ai_quality_evaluation(candidate_sha=_HEAD_SHA)
        self.assertEqual(report.overall_result, "PASS")
        self.assertEqual(before, User.objects.count())

    def test_runner_preserves_skill_entry_count(self):
        before = SkillEntry.objects.count()
        report = run_ai_quality_evaluation(candidate_sha=_HEAD_SHA)
        self.assertEqual(report.overall_result, "PASS")
        self.assertEqual(before, SkillEntry.objects.count())

    def test_runner_preserves_evidence_embedding_count(self):
        before = EvidenceEmbedding.objects.count()
        report = run_ai_quality_evaluation(candidate_sha=_HEAD_SHA)
        self.assertEqual(report.overall_result, "PASS")
        self.assertEqual(before, EvidenceEmbedding.objects.count())

    def test_management_command_preserves_database_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            before = _db_counts()
            call_command(
                "evaluate_skill_ledger_ai_quality",
                candidate_sha=_HEAD_SHA,
                output_dir=str(Path(tmp).resolve()),
            )
            after = _db_counts()
            self.assertEqual(before, after)


class ExactRegressionMatchingTests(SimpleTestCase):
    def test_extra_regression_code_causes_scenario_failure(self):
        case = QualityEvaluationCase(
            case_id="aq-exact-regression-probe",
            category=QualityEvalCategory.REGRESSION,
            threat_ids=("Q8",),
            scenario_type=QualityScenarioType.FINGERPRINT_MISMATCH,
            expected_top_level_outcome=QualityGateCode.REGRESSION_DETECTED,
            expected_reason_codes=(QualityGateCode.REGRESSION_DETECTED,),
            expected_case_regression_codes=(CaseRegressionCode.FINGERPRINT_MISMATCH,),
        )
        result = quality_runner_module._pass_result(
            case,
            actual_top=QualityGateCode.REGRESSION_DETECTED,
            actual_reasons=(QualityGateCode.REGRESSION_DETECTED,),
            actual_regressions=(
                CaseRegressionCode.FINGERPRINT_MISMATCH,
                CaseRegressionCode.NON_PASS_OUTCOME,
            ),
            message="extra regression probe",
        )
        self.assertFalse(result.passed)
        self.assertEqual(
            result.expected_case_regression_codes,
            (CaseRegressionCode.FINGERPRINT_MISMATCH.value,),
        )
        self.assertEqual(
            result.actual_case_regression_codes,
            (
                CaseRegressionCode.FINGERPRINT_MISMATCH.value,
                CaseRegressionCode.NON_PASS_OUTCOME.value,
            ),
        )


class RollbackBoundarySourceTests(SimpleTestCase):
    def test_rag_and_tool_evaluators_share_same_rollback_boundary(self):
        source = Path(inspect.getsourcefile(quality_runner_module)).read_text(
            encoding="utf-8"
        )
        marker = (
            "with transaction.atomic():\n"
            "        rag_report = run_final_rag_evaluation()\n"
            "        tool_report = run_tool_assistant_evaluation()\n"
            "        transaction.set_rollback(True)"
        )
        self.assertIn(marker, source)


class AuthoritativeBaselineErrorNormalisationTests(TestCase):
    _SAFE_MESSAGE = "authoritative AI quality baseline is invalid."

    def test_quality_gate_contract_error_becomes_runner_error(self):
        with patch(
            "apps.skill_ledger.evaluation.quality_runner.load_authoritative_baseline",
            side_effect=QualityGateContractError(
                "SECRET_BASELINE_PARSE_FAIL {not-json} "
                f"{SPRINT121_AI_QUALITY_BASELINE_PATH}"
            ),
        ):
            with self.assertRaises(AiQualityEvaluationRunnerError) as ctx:
                run_ai_quality_evaluation(candidate_sha=_HEAD_SHA)
        message = str(ctx.exception)
        self.assertEqual(message, self._SAFE_MESSAGE)
        self.assertNotIn("QualityGateContractError", message)
        self.assertNotIn("traceback", message.casefold())
        self.assertNotIn("SECRET_BASELINE_PARSE_FAIL", message)
        self.assertNotIn("{not-json}", message)
        self.assertNotIn(str(SPRINT121_AI_QUALITY_BASELINE_PATH), message)
        self.assertNotIn("baselines", message.casefold())

    def test_management_command_converts_runner_baseline_error_to_command_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch(
                "apps.skill_ledger.evaluation.quality_runner.load_authoritative_baseline",
                side_effect=QualityGateContractError(
                    "SECRET_BASELINE_PARSE_FAIL {not-json} "
                    f"{SPRINT121_AI_QUALITY_BASELINE_PATH}"
                ),
            ):
                with self.assertRaises(CommandError) as ctx:
                    call_command(
                        "evaluate_skill_ledger_ai_quality",
                        candidate_sha=_HEAD_SHA,
                        output_dir=str(Path(tmp).resolve()),
                    )
        message = str(ctx.exception)
        self.assertEqual(message, self._SAFE_MESSAGE)
        self.assertNotIn("QualityGateContractError", message)
        self.assertNotIn("traceback", message.casefold())
        self.assertNotIn("SECRET_BASELINE_PARSE_FAIL", message)
        self.assertNotIn("{not-json}", message)
        self.assertNotIn(str(SPRINT121_AI_QUALITY_BASELINE_PATH), message)
        self.assertNotIn("baselines", message.casefold())


class BaselineIntegrityMismatchFileErrorTests(TestCase):
    _SAFE_MESSAGE = "authoritative AI quality baseline is invalid."

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with transaction.atomic():
            rag_report = run_final_rag_evaluation()
            tool_report = run_tool_assistant_evaluation()
            transaction.set_rollback(True)
        snapshot = build_ai_quality_snapshot(
            rag_report=rag_report,
            tool_assistant_report=tool_report,
            privacy_violation_count=0,
            candidate_sha=_HEAD_SHA,
        )
        gate = run_ai_quality_gate(snapshot)
        cls.ctx = quality_runner_module._LiveContext(
            rag_report=rag_report,
            tool_report=tool_report,
            snapshot=snapshot,
            gate_result_code=gate.top_level_outcome,
        )
        cls.case = next(
            case
            for case in ALL_QUALITY_CASES
            if case.scenario_type
            is QualityScenarioType.BASELINE_INTEGRITY_MISMATCH
        )

    def _assert_safe_message(self, message: str) -> None:
        self.assertEqual(message, self._SAFE_MESSAGE)
        lowered = message.casefold()
        for token in (
            "QualityGateContractError",
            "JSONDecodeError",
            "FileNotFoundError",
            "OSError",
            "traceback",
            "{not-json",
            "SECRET_",
            str(SPRINT121_AI_QUALITY_BASELINE_PATH),
            "sprint121_ai_quality_baseline.json",
        ):
            self.assertNotIn(token.casefold(), lowered)

    def _patch_baseline_read_text(self, *, return_value=None, side_effect=None):
        original = Path.read_text
        baseline = SPRINT121_AI_QUALITY_BASELINE_PATH.resolve()

        def _read_text(self, *args, **kwargs):
            if Path(self).resolve() == baseline:
                if side_effect is not None:
                    raise side_effect
                return return_value
            return original(self, *args, **kwargs)

        return patch.object(Path, "read_text", _read_text)

    def test_integrity_mismatch_malformed_baseline_raises_runner_error(self):
        with self._patch_baseline_read_text(
            return_value="{not-json SECRET_MALFORMED_PAYLOAD"
        ):
            with self.assertRaises(AiQualityEvaluationRunnerError) as ctx:
                quality_runner_module._execute_case(self.case, self.ctx)
        self._assert_safe_message(str(ctx.exception))

    def test_integrity_mismatch_missing_baseline_raises_runner_error(self):
        with self._patch_baseline_read_text(
            side_effect=FileNotFoundError(
                f"SECRET_MISSING {SPRINT121_AI_QUALITY_BASELINE_PATH}"
            )
        ):
            with self.assertRaises(AiQualityEvaluationRunnerError) as ctx:
                quality_runner_module._execute_case(self.case, self.ctx)
        self._assert_safe_message(str(ctx.exception))

    def test_integrity_mismatch_unreadable_baseline_raises_runner_error(self):
        with self._patch_baseline_read_text(
            side_effect=OSError(
                f"SECRET_UNREADABLE {SPRINT121_AI_QUALITY_BASELINE_PATH}"
            )
        ):
            with self.assertRaises(AiQualityEvaluationRunnerError) as ctx:
                quality_runner_module._execute_case(self.case, self.ctx)
        self._assert_safe_message(str(ctx.exception))

    def test_integrity_mismatch_baseline_failure_becomes_command_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self._patch_baseline_read_text(
                return_value="{not-json SECRET_COMMAND_PAYLOAD"
            ):
                with self.assertRaises(CommandError) as ctx:
                    call_command(
                        "evaluate_skill_ledger_ai_quality",
                        candidate_sha=_HEAD_SHA,
                        output_dir=str(Path(tmp).resolve()),
                    )
        self._assert_safe_message(str(ctx.exception))

    def test_integrity_mismatch_scenario_no_longer_reads_baseline_file_directly(self):
        source = Path(inspect.getsourcefile(quality_runner_module)).read_text(
            encoding="utf-8"
        )
        self.assertNotIn("SPRINT121_AI_QUALITY_BASELINE_PATH.read_text", source)
        self.assertIn("_load_authoritative_baseline_for_quality()", source)
        self.assertIn("BASELINE_INTEGRITY_MISMATCH", source)

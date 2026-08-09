"""Sprint 121 Phase 4: offline tool-assistant evaluation harness tests."""

from __future__ import annotations

import ast
import importlib
import inspect
import json
import tempfile
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import transaction
from django.test import TestCase

from apps.skill_ledger.assistant.contracts import (
    AssistantOutcomeCode,
    PlannerDecision,
    PlannerOutcome,
    ToolCallRequest,
)
from apps.skill_ledger.assistant.orchestration import run_skill_ledger_assistant
from apps.skill_ledger.evaluation.rag_evaluation_fixtures import (
    FixedVectorEmbeddingProvider,
)
from apps.skill_ledger.evaluation.tool_assistant_cases import (
    ALL_TOOL_ASSISTANT_CASES,
    CATEGORY_MINIMUMS,
    REQUIRED_THREATS,
    ExecutionSeam,
    ToolAssistantEvalCategory,
    category_counts,
    compute_case_set_hash,
    threat_coverage,
    validate_and_sort_tool_assistant_cases,
)
from apps.skill_ledger.evaluation.tool_assistant_runner import (
    run_tool_assistant_case,
    run_tool_assistant_evaluation,
)
from apps.skill_ledger.models import EvidenceEmbedding, SkillEntry
from apps.skill_ledger.rag_generation import (
    UNTRUSTED_RAG_EVIDENCE_BEGIN,
    UNTRUSTED_RAG_QUERY_BEGIN,
)

User = get_user_model()


class ToolAssistantEvaluationCatalogueTests(TestCase):
    def test_catalogue_floors_threats_and_unique_ids(self):
        cases = validate_and_sort_tool_assistant_cases(ALL_TOOL_ASSISTANT_CASES)
        self.assertGreaterEqual(len(cases), 65)
        counts = category_counts(cases)
        for category, minimum in CATEGORY_MINIMUMS.items():
            self.assertGreaterEqual(counts[category], minimum, category)
        coverage = threat_coverage(cases)
        for threat in REQUIRED_THREATS:
            self.assertGreaterEqual(coverage[threat], 1, threat)
        ids = [case.case_id for case in cases]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(
            {case.category for case in cases},
            set(ToolAssistantEvalCategory),
        )
        for case in cases:
            if case.category is ToolAssistantEvalCategory.TOOL_SELECTION:
                self.assertNotIn("T18", case.threat_ids)
            if case.category is ToolAssistantEvalCategory.NO_TOOL:
                self.assertNotIn("T8", case.threat_ids)
        by_id = {case.case_id: case for case in cases}
        self.assertEqual(by_id["ta-call-budget-005"].threat_ids, ())
        self.assertEqual(by_id["ta-call-budget-006"].threat_ids, ())
        self.assertEqual(by_id["ta-ownership-001"].threat_ids, ())
        self.assertEqual(by_id["ta-grounded-source-002"].threat_ids, ())
        self.assertEqual(by_id["ta-grounded-source-012"].threat_ids, ("T16",))
        self.assertEqual(by_id["ta-prompt-injection-007"].threat_ids, ())
        sentinel_case = by_id["ta-prompt-injection-008"]
        self.assertEqual(sentinel_case.threat_ids, ("T24",))
        self.assertIn(UNTRUSTED_RAG_QUERY_BEGIN, sentinel_case.request_text)
        self.assertIn(UNTRUSTED_RAG_EVIDENCE_BEGIN, sentinel_case.request_text)
        cases_source = Path(
            inspect.getsourcefile(
                importlib.import_module(
                    "apps.skill_ledger.evaluation.tool_assistant_cases"
                )
            )
        ).read_text(encoding="utf-8")
        injection_008_block = cases_source.split("ta-prompt-injection-008", 1)[1].split(
            "ta-grounded-source-001", 1
        )[0]
        self.assertNotIn("<<<UNTRUSTED_RAG_QUERY_DATA_BEGIN>>>", injection_008_block)
        self.assertNotIn(
            "<<<UNTRUSTED_RAG_EVIDENCE_DATA_BEGIN>>>", injection_008_block
        )
        self.assertIn("UNTRUSTED_RAG_QUERY_BEGIN", injection_008_block)
        self.assertIn("UNTRUSTED_RAG_EVIDENCE_BEGIN", injection_008_block)

    def test_case_set_hash_is_deterministic(self):
        first = compute_case_set_hash(ALL_TOOL_ASSISTANT_CASES)
        second = compute_case_set_hash(ALL_TOOL_ASSISTANT_CASES)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)


class ToolAssistantEvaluationRunnerTests(TestCase):
    def test_runner_all_scenarios_pass_without_network_or_live_provider(self):
        with (
            patch("socket.socket") as socket_ctor,
            patch("urllib.request.urlopen") as urlopen,
        ):
            report = run_tool_assistant_evaluation()
            socket_ctor.assert_not_called()
            urlopen.assert_not_called()
        self.assertEqual(report.overall_result, "PASS")
        self.assertGreaterEqual(report.total_case_count, 65)
        self.assertEqual(report.failed_case_count, 0)
        self.assertEqual(report.network_call_count, 0)
        self.assertEqual(report.live_provider_call_count, 0)
        self.assertEqual(
            report.case_set_sha256,
            compute_case_set_hash(ALL_TOOL_ASSISTANT_CASES),
        )
        failed = [item for item in report.results if not item.passed]
        self.assertEqual(failed, [])
        self.assertTrue(all(item.network_call_count == 0 for item in report.results))
        t21 = next(item for item in report.results if "T21" in item.threat_ids)
        self.assertEqual(t21.observed_outcome, "FAILED")
        self.assertEqual(t21.tools_executed, 0)
        self.assertEqual(t21.synthesis_calls, 0)

    def test_network_probe_seam_fails_case_and_aggregate_evaluation(self):
        base = next(
            item
            for item in ALL_TOOL_ASSISTANT_CASES
            if item.case_id == "ta-tool-selection-001"
        )
        probed = replace(base, execution_seam=ExecutionSeam.NETWORK_PROBE)
        result = run_tool_assistant_case(probed)
        self.assertFalse(result.passed)
        self.assertGreater(result.network_call_count, 0)
        self.assertIn("network_call_count=", result.message)

        mutated = (probed,) + tuple(
            item
            for item in ALL_TOOL_ASSISTANT_CASES
            if item.case_id != "ta-tool-selection-001"
        )
        report = run_tool_assistant_evaluation(cases=mutated)
        self.assertEqual(report.overall_result, "FAIL")
        self.assertGreaterEqual(report.failed_case_count, 1)
        self.assertGreater(report.network_call_count, 0)
        probed_result = next(
            item for item in report.results if item.case_id == probed.case_id
        )
        self.assertFalse(probed_result.passed)
        self.assertGreater(probed_result.network_call_count, 0)

    def test_report_hash_deterministic_across_repeated_runs(self):
        first = run_tool_assistant_evaluation()
        second = run_tool_assistant_evaluation()
        self.assertEqual(first.case_set_sha256, second.case_set_sha256)
        self.assertEqual(first.report_sha256, second.report_sha256)
        self.assertEqual(first.overall_result, "PASS")
        self.assertEqual(second.overall_result, "PASS")

    def test_one_failing_case_makes_overall_fail(self):
        base = ALL_TOOL_ASSISTANT_CASES[0]
        broken = replace(base, expected_outcome="FAILED")
        mutated = (broken,) + ALL_TOOL_ASSISTANT_CASES[1:]
        report = run_tool_assistant_evaluation(cases=mutated)
        self.assertEqual(report.overall_result, "FAIL")
        self.assertGreaterEqual(report.failed_case_count, 1)

    def test_preexisting_username_collision_preserves_user(self):
        case = next(
            item
            for item in ALL_TOOL_ASSISTANT_CASES
            if item.case_id == "ta-tool-selection-001"
        )
        suffix = case.case_id.replace("-", "_")
        username = f"cf121_eval_owner_synthetic_{suffix}"
        preexisting = User.objects.create_user(
            username=username,
            email="preexisting@example.invalid",
            password="PreexistingPass12345",
        )
        preexisting_pk = preexisting.pk
        result = run_tool_assistant_case(case)
        self.assertFalse(result.passed)
        self.assertEqual(result.observed_outcome, "FIXTURE_COLLISION")
        surviving = User.objects.get(pk=preexisting_pk)
        self.assertEqual(surviving.username, username)
        self.assertEqual(surviving.email, "preexisting@example.invalid")

    def test_missing_and_cross_user_share_opaque_contract(self):
        owner = User.objects.create_user(
            username="cf121_opaque_owner",
            password="StrongPass12345",
        )
        other = User.objects.create_user(
            username="cf121_opaque_other",
            password="StrongPass12345",
        )
        other_entry = SkillEntry.objects.create(
            user=other,
            skill_name="Secret",
            category=SkillEntry.Category.OTHER,
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
        )
        provider = FixedVectorEmbeddingProvider([1.0, 0.0])

        class FixedPlanner:
            def __init__(self, decision):
                self.decision = decision
                self.calls = 0

            def plan(self, *, request_text, tool_definitions):
                self.calls += 1
                return self.decision

        def run_detail(skill_entry_id: int):
            planner = FixedPlanner(
                PlannerDecision(
                    outcome=PlannerOutcome.TOOL_PLAN,
                    calls=(
                        ToolCallRequest(
                            tool_name="get_skill_entry_detail",
                            arguments={"skill_entry_id": skill_entry_id},
                        ),
                    ),
                )
            )
            return run_skill_ledger_assistant(
                request_text="opaque ownership",
                user=owner,
                planner=planner,
                synthesis_provider=None,
                embedding_provider=provider,
            )

        cross = run_detail(other_entry.pk)
        missing = run_detail(9_999_990_121)
        self.assertEqual(cross.result.code, AssistantOutcomeCode.REJECTED)
        self.assertEqual(missing.result.code, AssistantOutcomeCode.REJECTED)
        self.assertEqual(cross.result.answer, missing.result.answer)
        self.assertEqual(cross.tools_executed, 0)
        self.assertEqual(missing.tools_executed, 0)
        self.assertEqual(cross.synthesis_calls, 0)
        self.assertEqual(missing.synthesis_calls, 0)
        self.assertEqual(cross.result.tools_used, ())
        self.assertEqual(missing.result.tools_used, ())
        self.assertEqual(cross.result.sources_used, ())
        self.assertEqual(missing.result.sources_used, ())

    def test_evaluation_modules_have_no_provider_factory_or_destructive_cleanup(self):
        module_paths = [
            Path(
                inspect.getsourcefile(
                    importlib.import_module(
                        "apps.skill_ledger.evaluation.tool_assistant_cases"
                    )
                )
            ),
            Path(
                inspect.getsourcefile(
                    importlib.import_module(
                        "apps.skill_ledger.evaluation.tool_assistant_runner"
                    )
                )
            ),
            Path(
                inspect.getsourcefile(
                    importlib.import_module(
                        "apps.skill_ledger.management.commands."
                        "evaluate_skill_ledger_tool_assistant"
                    )
                )
            ),
        ]
        forbidden = {
            "provider_factory",
            "openai",
            "anthropic",
            "httpx",
            "requests",
        }
        for path in module_paths:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            imported: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported.add(alias.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".")[0])
            overlap = forbidden.intersection(imported)
            self.assertEqual(overlap, set(), path.name)
            self.assertNotIn("_raw_delete", source)
            self.assertNotIn("_delete_synthetic_users", source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and node.id == "provider_factory":
                    self.fail(f"provider_factory name used in {path.name}")
                if isinstance(node, ast.Attribute) and node.attr == "provider_factory":
                    self.fail(f"provider_factory attribute used in {path.name}")


class ToolAssistantEvaluationCommandTests(TestCase):
    def test_management_command_success_prints_hashes_and_rolls_back(self):
        before_users = User.objects.count()
        before_entries = SkillEntry.objects.count()
        before_embeddings = EvidenceEmbedding.objects.count()
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            results_path = output_dir / "tool_assistant_evaluation_results.json"
            summary_path = output_dir / "tool_assistant_evaluation_summary.txt"
            with (
                patch("socket.socket") as socket_ctor,
                patch("urllib.request.urlopen") as urlopen,
            ):
                call_command(
                    "evaluate_skill_ledger_tool_assistant",
                    "--output-dir",
                    str(output_dir),
                )
                socket_ctor.assert_not_called()
                urlopen.assert_not_called()
            self.assertTrue(results_path.exists())
            self.assertTrue(summary_path.exists())
            first_json_bytes = results_path.read_bytes()
            first_summary_bytes = summary_path.read_bytes()
            payload = json.loads(first_json_bytes.decode("utf-8"))
            self.assertEqual(payload["overall_result"], "PASS")
            self.assertEqual(payload["failed_case_count"], 0)
            self.assertEqual(len(payload["case_set_sha256"]), 64)
            self.assertEqual(len(payload["report_sha256"]), 64)
            first_case_hash = payload["case_set_sha256"]
            first_report_hash = payload["report_sha256"]
            results_path.unlink()
            summary_path.unlink()
            call_command(
                "evaluate_skill_ledger_tool_assistant",
                "--output-dir",
                str(output_dir),
            )
            second_json_bytes = results_path.read_bytes()
            second_summary_bytes = summary_path.read_bytes()
            self.assertEqual(first_json_bytes, second_json_bytes)
            self.assertEqual(first_summary_bytes, second_summary_bytes)
            payload_two = json.loads(second_json_bytes.decode("utf-8"))
            self.assertEqual(payload_two["case_set_sha256"], first_case_hash)
            self.assertEqual(payload_two["report_sha256"], first_report_hash)
        self.assertEqual(User.objects.count(), before_users)
        self.assertEqual(SkillEntry.objects.count(), before_entries)
        self.assertEqual(EvidenceEmbedding.objects.count(), before_embeddings)
        self.assertFalse(
            User.objects.filter(username__startswith="cf121_eval_").exists()
        )

    def test_management_command_failure_is_nonzero_and_leaves_no_residue(self):
        before_users = User.objects.count()
        before_entries = SkillEntry.objects.count()
        before_embeddings = EvidenceEmbedding.objects.count()
        with transaction.atomic():
            real_report = run_tool_assistant_evaluation()
            failing_report = replace(
                real_report,
                overall_result="FAIL",
                passed_case_count=max(0, real_report.passed_case_count - 1),
                failed_case_count=1,
            )
            transaction.set_rollback(True)
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            results_path = output_dir / "tool_assistant_evaluation_results.json"
            summary_path = output_dir / "tool_assistant_evaluation_summary.txt"
            with patch(
                "apps.skill_ledger.management.commands."
                "evaluate_skill_ledger_tool_assistant.run_tool_assistant_evaluation",
                return_value=failing_report,
            ):
                with self.assertRaises(CommandError):
                    call_command(
                        "evaluate_skill_ledger_tool_assistant",
                        "--output-dir",
                        str(output_dir),
                    )
            self.assertFalse(results_path.exists())
            self.assertFalse(summary_path.exists())
        self.assertEqual(User.objects.count(), before_users)
        self.assertEqual(SkillEntry.objects.count(), before_entries)
        self.assertEqual(EvidenceEmbedding.objects.count(), before_embeddings)

    def test_management_command_rejects_repository_output_dir(self):
        with self.assertRaises(CommandError):
            call_command(
                "evaluate_skill_ledger_tool_assistant",
                "--output-dir",
                str(Path(settings.BASE_DIR)),
            )

    def test_console_only_command_rolls_back_synthetic_fixtures(self):
        before_users = User.objects.count()
        before_entries = SkillEntry.objects.count()
        before_embeddings = EvidenceEmbedding.objects.count()
        call_command("evaluate_skill_ledger_tool_assistant")
        self.assertEqual(User.objects.count(), before_users)
        self.assertEqual(SkillEntry.objects.count(), before_entries)
        self.assertEqual(EvidenceEmbedding.objects.count(), before_embeddings)

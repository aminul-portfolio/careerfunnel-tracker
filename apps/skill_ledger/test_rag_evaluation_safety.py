"""Sprint 120 Phase 2+3: grounding, attribution, prompt-injection, and report tests."""

from __future__ import annotations

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
from django.test import SimpleTestCase, TestCase

from apps.skill_ledger.evaluation.rag_evaluation_cases import (
    ALL_EVALUATION_CASES,
    ATTRIBUTION_SAFETY_CASES,
    PHASE1_EVALUATION_CASES,
    PHASE2_SAFETY_CASES,
    PHASE3_PROMPT_INJECTION_CASES,
    PROMPT_INJECTION_CASES,
    UNSUPPORTED_OUTPUT_CASES,
    ZERO_EVIDENCE_CASES,
    RagEvalCategory,
    RagGenerationSafetyCase,
    compute_case_set_hash,
    validate_and_sort_rag_evaluation_cases,
)
from apps.skill_ledger.evaluation.rag_evaluation_runner import (
    canonical_final_evaluation_report_bytes,
    compute_final_evaluation_report_hash,
    final_evaluation_report_to_canonical_dict,
    run_final_rag_evaluation,
    run_generation_safety_case,
    run_phase2_safety_evaluation,
    run_phase3_prompt_injection_evaluation,
)
from apps.skill_ledger.models import EvidenceEmbedding, SkillEntry
from apps.skill_ledger.rag_generation import (
    UNTRUSTED_RAG_EVIDENCE_BEGIN,
    UNTRUSTED_RAG_EVIDENCE_END,
    UNTRUSTED_RAG_QUERY_BEGIN,
    UNTRUSTED_RAG_QUERY_END,
    RagRejectionCode,
    neutralise_untrusted_rag_sentinels,
)

User = get_user_model()


class RagEvaluationSafetyContractTests(SimpleTestCase):
    def test_phase2_case_counts(self):
        self.assertEqual(len(ATTRIBUTION_SAFETY_CASES), 8)
        self.assertEqual(len(UNSUPPORTED_OUTPUT_CASES), 4)
        self.assertEqual(len(ZERO_EVIDENCE_CASES), 2)
        self.assertEqual(len(PHASE2_SAFETY_CASES), 14)
        self.assertEqual(len(PHASE1_EVALUATION_CASES), 9)
        self.assertEqual(len(PROMPT_INJECTION_CASES), 8)
        self.assertEqual(len(PHASE3_PROMPT_INJECTION_CASES), 8)
        self.assertEqual(len(ALL_EVALUATION_CASES), 31)

    def test_unique_case_ids_across_phase1_and_phase2(self):
        ids = [case.case_id for case in ALL_EVALUATION_CASES]
        self.assertEqual(len(ids), len(set(ids)))

    def test_all_phase2_cases_are_synthetic(self):
        for case in PHASE2_SAFETY_CASES:
            self.assertIsInstance(case, RagGenerationSafetyCase)
            self.assertIs(case.is_synthetic, True)

    def test_cumulative_case_hash_determinism(self):
        first = compute_case_set_hash(ALL_EVALUATION_CASES)
        second = compute_case_set_hash(ALL_EVALUATION_CASES)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)

    def test_cumulative_case_hash_order_invariance(self):
        forward = compute_case_set_hash(ALL_EVALUATION_CASES)
        reversed_cases = tuple(reversed(ALL_EVALUATION_CASES))
        backward = compute_case_set_hash(reversed_cases)
        self.assertEqual(forward, backward)
        sorted_again = validate_and_sort_rag_evaluation_cases(reversed_cases)
        self.assertEqual(
            [case.case_id for case in sorted_again],
            sorted(case.case_id for case in ALL_EVALUATION_CASES),
        )


class RagEvaluationAttributionSafetyTests(TestCase):
    def _case(self, case_id: str) -> RagGenerationSafetyCase:
        return next(item for item in ATTRIBUTION_SAFETY_CASES if item.case_id == case_id)

    def test_valid_attribution_accepted(self):
        result = run_generation_safety_case(self._case("AT-01"))
        self.assertTrue(result.passed, result.message)
        self.assertTrue(result.actual_acceptance)
        self.assertEqual(result.provider_call_count, 1)
        self.assertEqual(result.actual_final_rendered_labels, ("PythonPandas",))

    def test_unknown_source_999_rejected(self):
        result = run_generation_safety_case(self._case("AT-02"))
        self.assertTrue(result.passed, result.message)
        self.assertEqual(result.actual_rejection_code, RagRejectionCode.UNKNOWN_SOURCE.value)
        self.assertIsNone(result.actual_final_rendered_labels)

    def test_duplicate_source_rejected(self):
        result = run_generation_safety_case(self._case("AT-03"))
        self.assertTrue(result.passed, result.message)
        self.assertEqual(
            result.actual_rejection_code,
            RagRejectionCode.DUPLICATE_SOURCE.value,
        )

    def test_learning_target_promotion_rejected(self):
        result = run_generation_safety_case(self._case("AT-04"))
        self.assertTrue(result.passed, result.message)
        self.assertEqual(
            result.actual_rejection_code,
            RagRejectionCode.EVIDENCE_LEVEL_MISMATCH.value,
        )

    def test_studying_promotion_rejected(self):
        result = run_generation_safety_case(self._case("AT-05"))
        self.assertTrue(result.passed, result.message)
        self.assertEqual(
            result.actual_rejection_code,
            RagRejectionCode.EVIDENCE_LEVEL_MISMATCH.value,
        )

    def test_no_evidence_promotion_rejected(self):
        result = run_generation_safety_case(self._case("AT-06"))
        self.assertTrue(result.passed, result.message)
        self.assertEqual(
            result.actual_rejection_code,
            RagRejectionCode.EVIDENCE_LEVEL_MISMATCH.value,
        )

    def test_display_label_mismatch_rejected(self):
        result = run_generation_safety_case(self._case("AT-07"))
        self.assertTrue(result.passed, result.message)
        self.assertEqual(
            result.actual_rejection_code,
            RagRejectionCode.DISPLAY_LABEL_MISMATCH.value,
        )

    def test_trusted_label_reconstruction(self):
        case = self._case("AT-08")
        result = run_generation_safety_case(case)
        self.assertTrue(result.passed, result.message)
        self.assertTrue(result.actual_acceptance)
        trusted = result.actual_final_rendered_labels
        self.assertIsNotNone(trusted)
        assert trusted is not None
        self.assertEqual(trusted, case.expected_final_rendered_labels)
        provider_facing = neutralise_untrusted_rag_sentinels(trusted[0])
        self.assertNotEqual(trusted[0], provider_facing)


class RagEvaluationUnsupportedOutputTests(TestCase):
    def _case(self, case_id: str) -> RagGenerationSafetyCase:
        return next(item for item in UNSUPPORTED_OUTPUT_CASES if item.case_id == case_id)

    def test_wrong_schema_rejected(self):
        result = run_generation_safety_case(self._case("UO-01"))
        self.assertTrue(result.passed, result.message)
        self.assertEqual(result.actual_rejection_code, RagRejectionCode.INVALID_OUTPUT.value)

    def test_empty_sources_rejected(self):
        result = run_generation_safety_case(self._case("UO-02"))
        self.assertTrue(result.passed, result.message)
        self.assertEqual(
            result.actual_rejection_code,
            RagRejectionCode.INVALID_SOURCES_USED.value,
        )

    def test_claim_safety_rejected(self):
        result = run_generation_safety_case(self._case("UO-03"))
        self.assertTrue(result.passed, result.message)
        self.assertEqual(
            result.actual_rejection_code,
            RagRejectionCode.CLAIM_SAFETY_REJECTION.value,
        )

    def test_bool_source_identifier_rejected(self):
        result = run_generation_safety_case(self._case("UO-04"))
        self.assertTrue(result.passed, result.message)
        self.assertEqual(
            result.actual_rejection_code,
            RagRejectionCode.INVALID_SOURCES_USED.value,
        )


class RagEvaluationZeroEvidenceTests(TestCase):
    def _case(self, case_id: str) -> RagGenerationSafetyCase:
        return next(item for item in ZERO_EVIDENCE_CASES if item.case_id == case_id)

    def test_zero_retrieval_provider_call_count_is_zero(self):
        result = run_generation_safety_case(self._case("ZE-01"))
        self.assertTrue(result.passed, result.message)
        self.assertEqual(result.provider_call_count, 0)
        self.assertFalse(result.actual_provider_called)
        self.assertEqual(
            result.actual_rejection_code,
            RagRejectionCode.NO_RETRIEVED_EVIDENCE.value,
        )
        self.assertIsNone(result.actual_final_rendered_labels)

    def test_provider_none_call_count_is_zero(self):
        result = run_generation_safety_case(self._case("ZE-02"))
        self.assertTrue(result.passed, result.message)
        self.assertEqual(result.provider_call_count, 0)
        self.assertFalse(result.actual_provider_called)
        self.assertEqual(
            result.actual_rejection_code,
            RagRejectionCode.PROVIDER_UNAVAILABLE.value,
        )
        self.assertIsNone(result.actual_final_rendered_labels)


class RagEvaluationSafetyRegressionTests(TestCase):
    def test_rejected_outputs_have_no_validated_payload(self):
        rejected = [
            case
            for case in PHASE2_SAFETY_CASES
            if case.expected_acceptance is False
        ]
        self.assertGreaterEqual(len(rejected), 12)
        for case in rejected:
            result = run_generation_safety_case(case)
            self.assertTrue(result.passed, result.message)
            self.assertIsNone(result.actual_final_rendered_labels)

    def test_phase2_runner_passes_without_network_or_persistence(self):
        before_entries = SkillEntry.objects.count()
        before_embeddings = EvidenceEmbedding.objects.count()
        with (
            patch("socket.socket") as socket_ctor,
            patch("urllib.request.urlopen") as urlopen,
        ):
            report = run_phase2_safety_evaluation()
            socket_ctor.assert_not_called()
            urlopen.assert_not_called()
        self.assertEqual(report.overall_result, "PASS")
        self.assertEqual(report.total_case_count, 14)
        self.assertEqual(report.failed_case_count, 0)
        self.assertEqual(report.network_call_count, 0)
        self.assertEqual(report.live_embedding_call_count, 0)
        self.assertEqual(report.live_llm_call_count, 0)
        self.assertEqual(SkillEntry.objects.count(), before_entries)
        self.assertEqual(EvidenceEmbedding.objects.count(), before_embeddings)
        categories = {item.category for item in report.generation_safety_results}
        self.assertEqual(
            categories,
            {
                RagEvalCategory.ATTRIBUTION_SAFETY.value,
                RagEvalCategory.UNSUPPORTED_OUTPUT.value,
                RagEvalCategory.ZERO_EVIDENCE.value,
            },
        )
        for item in report.generation_safety_results:
            self.assertTrue(item.passed, item.message)
            if not item.expected_acceptance:
                self.assertIsNone(item.actual_final_rendered_labels)


class RagEvaluationPromptInjectionTests(TestCase):
    def _case(self, case_id: str) -> RagGenerationSafetyCase:
        return next(item for item in PROMPT_INJECTION_CASES if item.case_id == case_id)

    def test_prompt_injection_cases_are_synthetic_and_unique(self):
        self.assertEqual(len(PROMPT_INJECTION_CASES), 8)
        ids = [case.case_id for case in PROMPT_INJECTION_CASES]
        self.assertEqual(ids, [f"PI-0{index}" for index in range(1, 9)])
        for case in PROMPT_INJECTION_CASES:
            self.assertIs(case.is_synthetic, True)
            self.assertEqual(case.category, RagEvalCategory.PROMPT_INJECTION)

    def test_pi01_query_delimiter_defence(self):
        result = run_generation_safety_case(self._case("PI-01"))
        self.assertTrue(result.passed, result.message)
        self.assertTrue(result.actual_acceptance)
        self.assertEqual(result.provider_call_count, 1)
        self.assertIs(result.query_fence_present, True)
        self.assertIs(result.evidence_fence_present, True)
        self.assertIs(result.raw_query_sentinel_leaked, False)
        self.assertIs(result.raw_evidence_sentinel_leaked, False)

    def test_pi02_evidence_delimiter_defence(self):
        case = self._case("PI-02")
        result = run_generation_safety_case(case)
        self.assertTrue(result.passed, result.message)
        self.assertTrue(result.actual_acceptance)
        self.assertIs(result.query_fence_present, True)
        self.assertIs(result.evidence_fence_present, True)
        self.assertIs(result.raw_query_sentinel_leaked, False)
        self.assertIs(result.raw_evidence_sentinel_leaked, False)
        trusted = result.actual_final_rendered_labels
        self.assertEqual(trusted, case.expected_final_rendered_labels)
        assert trusted is not None
        self.assertNotEqual(
            trusted[0],
            neutralise_untrusted_rag_sentinels(trusted[0]),
        )

    def test_pi03_unknown_source_rejection(self):
        result = run_generation_safety_case(self._case("PI-03"))
        self.assertTrue(result.passed, result.message)
        self.assertEqual(result.actual_rejection_code, RagRejectionCode.UNKNOWN_SOURCE.value)
        self.assertIsNone(result.actual_final_rendered_labels)

    def test_pi04_evidence_level_promotion_rejection(self):
        result = run_generation_safety_case(self._case("PI-04"))
        self.assertTrue(result.passed, result.message)
        self.assertEqual(
            result.actual_rejection_code,
            RagRejectionCode.EVIDENCE_LEVEL_MISMATCH.value,
        )

    def test_pi05_claim_safety_rejection(self):
        result = run_generation_safety_case(self._case("PI-05"))
        self.assertTrue(result.passed, result.message)
        self.assertEqual(
            result.actual_rejection_code,
            RagRejectionCode.CLAIM_SAFETY_REJECTION.value,
        )

    def test_pi06_empty_attribution_rejection(self):
        result = run_generation_safety_case(self._case("PI-06"))
        self.assertTrue(result.passed, result.message)
        self.assertEqual(
            result.actual_rejection_code,
            RagRejectionCode.INVALID_SOURCES_USED.value,
        )

    def test_pi07_duplicate_source_rejection(self):
        result = run_generation_safety_case(self._case("PI-07"))
        self.assertTrue(result.passed, result.message)
        self.assertEqual(
            result.actual_rejection_code,
            RagRejectionCode.DUPLICATE_SOURCE.value,
        )

    def test_pi08_display_label_override_rejection(self):
        result = run_generation_safety_case(self._case("PI-08"))
        self.assertTrue(result.passed, result.message)
        self.assertEqual(
            result.actual_rejection_code,
            RagRejectionCode.DISPLAY_LABEL_MISMATCH.value,
        )


class RagEvaluationDelimiterNeutralisationTests(SimpleTestCase):
    def test_direct_neutralise_untrusted_rag_sentinels(self):
        raw = (
            f"alpha {UNTRUSTED_RAG_QUERY_BEGIN} {UNTRUSTED_RAG_QUERY_END} "
            f"{UNTRUSTED_RAG_EVIDENCE_BEGIN} {UNTRUSTED_RAG_EVIDENCE_END} "
            f"{UNTRUSTED_RAG_QUERY_BEGIN} omega"
        )
        first = neutralise_untrusted_rag_sentinels(raw)
        second = neutralise_untrusted_rag_sentinels(raw)
        self.assertEqual(first, second)
        self.assertIn("alpha", first)
        self.assertIn("omega", first)
        for token in (
            UNTRUSTED_RAG_QUERY_BEGIN,
            UNTRUSTED_RAG_QUERY_END,
            UNTRUSTED_RAG_EVIDENCE_BEGIN,
            UNTRUSTED_RAG_EVIDENCE_END,
        ):
            self.assertNotIn(token, first)
        self.assertIn("[UNTRUSTED_RAG_QUERY_DATA_BEGIN_ESCAPED]", first)
        self.assertIn("[UNTRUSTED_RAG_EVIDENCE_DATA_END_ESCAPED]", first)


class RagEvaluationFinalReportTests(TestCase):
    def test_final_evaluation_case_inventory(self):
        report = run_final_rag_evaluation()
        self.assertEqual(report.total_case_count, 31)
        self.assertEqual(report.retrieval_quality_case_count, 5)
        self.assertEqual(report.adversarial_retrieval_case_count, 4)
        self.assertEqual(report.attribution_safety_case_count, 8)
        self.assertEqual(report.unsupported_output_case_count, 4)
        self.assertEqual(report.zero_evidence_case_count, 2)
        self.assertEqual(report.prompt_injection_case_count, 8)
        self.assertEqual(report.passed_case_count, 31)
        self.assertEqual(report.failed_case_count, 0)
        self.assertEqual(report.overall_result, "PASS")
        self.assertEqual(report.network_call_count, 0)
        self.assertEqual(report.live_embedding_call_count, 0)
        self.assertEqual(report.live_llm_call_count, 0)

    def test_final_report_hash_stability_and_canonicalisation(self):
        report = run_final_rag_evaluation()
        self.assertEqual(report.overall_result, "PASS")
        self.assertEqual(report.total_case_count, 31)
        self.assertEqual(report.failed_case_count, 0)
        self.assertEqual(report.prompt_injection_case_count, 8)
        self.assertEqual(len(report.report_sha256), 64)
        self.assertTrue(all(ch in "0123456789abcdef" for ch in report.report_sha256))
        self.assertEqual(
            compute_final_evaluation_report_hash(report),
            report.report_sha256,
        )
        first_bytes = canonical_final_evaluation_report_bytes(report)
        second_bytes = canonical_final_evaluation_report_bytes(report)
        self.assertEqual(first_bytes, second_bytes)
        canonical = final_evaluation_report_to_canonical_dict(report)
        self.assertNotIn("report_sha256", canonical)
        # Order-invariant nesting: reshuffling result tuples must not change digest.
        shuffled = replace(
            report,
            retrieval_quality_results=tuple(reversed(report.retrieval_quality_results)),
            adversarial_retrieval_results=tuple(
                reversed(report.adversarial_retrieval_results)
            ),
            generation_safety_results=tuple(
                reversed(report.generation_safety_results)
            ),
            report_sha256="",
        )
        self.assertEqual(
            compute_final_evaluation_report_hash(shuffled),
            report.report_sha256,
        )
        serialized = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
        for forbidden in (
            "timestamp",
            "duration",
            "hostname",
            "repository_path",
            "proof_path",
            "output_path",
            "C:\\\\",
            "/tmp/",
        ):
            self.assertNotIn(forbidden, serialized.casefold())
        for item in report.retrieval_quality_results:
            self.assertEqual(item.recall_at_5, 1.0)

    def test_phase3_runner_passes_without_network(self):
        with (
            patch("socket.socket") as socket_ctor,
            patch("urllib.request.urlopen") as urlopen,
        ):
            report = run_phase3_prompt_injection_evaluation()
            socket_ctor.assert_not_called()
            urlopen.assert_not_called()
        self.assertEqual(report.overall_result, "PASS")
        self.assertEqual(report.total_case_count, 8)
        self.assertEqual(report.failed_case_count, 0)
        for item in report.generation_safety_results:
            self.assertTrue(item.passed, item.message)
            if not item.expected_acceptance:
                self.assertIsNone(item.actual_final_rendered_labels)

    def test_case_set_hash_matches_final_report(self):
        report = run_final_rag_evaluation()
        self.assertEqual(
            report.case_set_sha256,
            compute_case_set_hash(ALL_EVALUATION_CASES),
        )


class RagEvaluationManagementCommandTests(TestCase):
    def test_management_command_rejects_repository_output_dir(self):
        with self.assertRaises(CommandError):
            call_command(
                "evaluate_skill_ledger_rag",
                "--output-dir",
                str(Path(settings.BASE_DIR)),
            )

    def test_management_command_writes_reports_without_persistence(self):
        before_users = User.objects.count()
        before_entries = SkillEntry.objects.count()
        before_embeddings = EvidenceEmbedding.objects.count()
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            with (
                patch("socket.socket") as socket_ctor,
                patch("urllib.request.urlopen") as urlopen,
            ):
                call_command("evaluate_skill_ledger_rag", "--output-dir", str(output_dir))
                socket_ctor.assert_not_called()
                urlopen.assert_not_called()
            results_path = output_dir / "rag_evaluation_results.json"
            summary_path = output_dir / "rag_evaluation_summary.txt"
            self.assertTrue(results_path.exists())
            self.assertTrue(summary_path.exists())
            payload = json.loads(results_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["overall_result"], "PASS")
            self.assertEqual(payload["total_case_count"], 31)
            self.assertEqual(payload["failed_case_count"], 0)
            self.assertEqual(len(payload["case_set_sha256"]), 64)
            self.assertEqual(len(payload["report_sha256"]), 64)
            first_case_hash = payload["case_set_sha256"]
            first_report_hash = payload["report_sha256"]
            results_path.unlink()
            summary_path.unlink()
            call_command("evaluate_skill_ledger_rag", "--output-dir", str(output_dir))
            payload_two = json.loads(results_path.read_text(encoding="utf-8"))
            self.assertEqual(payload_two["case_set_sha256"], first_case_hash)
            self.assertEqual(payload_two["report_sha256"], first_report_hash)
            self.assertEqual(payload_two["overall_result"], "PASS")
        self.assertEqual(User.objects.count(), before_users)
        self.assertEqual(SkillEntry.objects.count(), before_entries)
        self.assertEqual(EvidenceEmbedding.objects.count(), before_embeddings)

    def test_management_command_failed_evaluation_writes_no_reports(self):
        before_users = User.objects.count()
        before_entries = SkillEntry.objects.count()
        before_embeddings = EvidenceEmbedding.objects.count()
        with transaction.atomic():
            real_report = run_final_rag_evaluation()
            failing_report = replace(
                real_report,
                overall_result="FAIL",
                passed_case_count=30,
                failed_case_count=1,
            )
            transaction.set_rollback(True)
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            results_path = output_dir / "rag_evaluation_results.json"
            summary_path = output_dir / "rag_evaluation_summary.txt"
            with patch(
                "apps.skill_ledger.management.commands.evaluate_skill_ledger_rag.run_final_rag_evaluation",
                return_value=failing_report,
            ):
                with self.assertRaises(CommandError):
                    call_command(
                        "evaluate_skill_ledger_rag",
                        "--output-dir",
                        str(output_dir),
                    )
            self.assertFalse(results_path.exists())
            self.assertFalse(summary_path.exists())
        self.assertEqual(User.objects.count(), before_users)
        self.assertEqual(SkillEntry.objects.count(), before_entries)
        self.assertEqual(EvidenceEmbedding.objects.count(), before_embeddings)

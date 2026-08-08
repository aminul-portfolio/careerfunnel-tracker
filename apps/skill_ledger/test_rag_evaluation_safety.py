"""Sprint 120 Phase 2: grounding, attribution, and fail-closed safety evaluation tests."""

from __future__ import annotations

from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from apps.skill_ledger.evaluation.rag_evaluation_cases import (
    ALL_EVALUATION_CASES,
    ATTRIBUTION_SAFETY_CASES,
    PHASE1_EVALUATION_CASES,
    PHASE2_SAFETY_CASES,
    UNSUPPORTED_OUTPUT_CASES,
    ZERO_EVIDENCE_CASES,
    RagEvalCategory,
    RagGenerationSafetyCase,
    compute_case_set_hash,
    validate_and_sort_rag_evaluation_cases,
)
from apps.skill_ledger.evaluation.rag_evaluation_runner import (
    run_generation_safety_case,
    run_phase2_safety_evaluation,
)
from apps.skill_ledger.models import EvidenceEmbedding, SkillEntry
from apps.skill_ledger.rag_generation import (
    RagRejectionCode,
    neutralise_untrusted_rag_sentinels,
)


class RagEvaluationSafetyContractTests(SimpleTestCase):
    def test_phase2_case_counts(self):
        self.assertEqual(len(ATTRIBUTION_SAFETY_CASES), 8)
        self.assertEqual(len(UNSUPPORTED_OUTPUT_CASES), 4)
        self.assertEqual(len(ZERO_EVIDENCE_CASES), 2)
        self.assertEqual(len(PHASE2_SAFETY_CASES), 14)
        self.assertEqual(len(PHASE1_EVALUATION_CASES), 9)
        self.assertEqual(len(ALL_EVALUATION_CASES), 23)

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

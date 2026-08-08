"""Sprint 120 Phase 1: RAG retrieval evaluation runner and fixture tests."""

from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.skill_ledger.embedding_cache import is_cache_current
from apps.skill_ledger.evaluation.rag_evaluation_cases import (
    ADVERSARIAL_RETRIEVAL_CASES,
    RETRIEVAL_QUALITY_CASES,
    AdversarialRetrievalMode,
)
from apps.skill_ledger.evaluation.rag_evaluation_fixtures import (
    FixedVectorEmbeddingProvider,
    ensure_current_fixed_embedding_cache,
)
from apps.skill_ledger.evaluation.rag_evaluation_runner import (
    run_adversarial_retrieval_case,
    run_phase1_retrieval_evaluation,
    run_retrieval_quality_case,
)
from apps.skill_ledger.models import EvidenceEmbedding, SkillEntry
from apps.skill_ledger.rag_retrieval import TOP_K

User = get_user_model()


class RagEvaluationCacheHelperTests(TestCase):
    def test_cache_helper_produces_current_row(self):
        user = User.objects.create_user(username="rag_eval_cache", password="pass")
        entry = SkillEntry.objects.create(
            user=user,
            skill_name="CacheHelperSkill",
            category=SkillEntry.Category.PROGRAMMING,
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
            sprint_reference="Sprint 120",
        )
        provider = FixedVectorEmbeddingProvider((1.0, 0.0))
        row = ensure_current_fixed_embedding_cache(
            entry,
            provider=provider,
            vector=(0.0, 1.0),
        )
        self.assertTrue(is_cache_current(row, entry))
        self.assertEqual(row.embedding_provider, provider.provider_name)
        self.assertEqual(row.embedding_model, provider.model_name)
        self.assertEqual(row.embedding_dimensions, provider.dimensions)
        self.assertEqual(row.embedding_vector, [0.0, 1.0])


class RagEvaluationRetrievalQualityTests(TestCase):
    def test_every_rq_corpus_exceeds_top_k(self):
        self.assertEqual(len(RETRIEVAL_QUALITY_CASES), 5)
        for case in RETRIEVAL_QUALITY_CASES:
            self.assertGreater(len(case.corpus), TOP_K)

    def test_recall_at_5_hard_gate_over_all_rq_cases(self):
        for case in RETRIEVAL_QUALITY_CASES:
            result = run_retrieval_quality_case(case)
            self.assertTrue(result.passed, result.message)
            self.assertEqual(result.recall_at_5, 1.0)
            self.assertEqual(result.expected_recall_at_5, 1.0)

    def test_recall_at_1_advisory_is_computed(self):
        case = next(item for item in RETRIEVAL_QUALITY_CASES if item.case_id == "RQ-01")
        result = run_retrieval_quality_case(case)
        self.assertIn(result.recall_at_1, (0.0, 1.0))
        self.assertEqual(result.recall_at_1, 1.0)
        self.assertEqual(result.ranked_local_ids[0], "rq01_relevant")

    def test_mrr_advisory_is_computed(self):
        case = next(item for item in RETRIEVAL_QUALITY_CASES if item.case_id == "RQ-04")
        result = run_retrieval_quality_case(case)
        self.assertGreater(result.mrr, 0.0)
        self.assertLessEqual(result.mrr, 1.0)
        self.assertEqual(result.ranked_local_ids[:3], ("rq04_near", "rq04_mid", "rq04_far"))

    def test_deterministic_tie_break_pk_ascending(self):
        case = next(item for item in RETRIEVAL_QUALITY_CASES if item.case_id == "RQ-03")
        result = run_retrieval_quality_case(case)
        self.assertTrue(result.passed, result.message)
        self.assertEqual(result.ranked_local_ids[0], "rq03_tie_low")
        self.assertEqual(result.ranked_local_ids[1], "rq03_tie_high")


class RagEvaluationAdversarialRetrievalTests(TestCase):
    def test_cross_user_isolation(self):
        case = next(
            item
            for item in ADVERSARIAL_RETRIEVAL_CASES
            if item.adversarial_mode is AdversarialRetrievalMode.CROSS_USER
        )
        result = run_adversarial_retrieval_case(case)
        self.assertTrue(result.passed, result.message)
        self.assertIn("ar01_owner", result.ranked_local_ids)
        self.assertNotIn("ar01_other", result.ranked_local_ids)

    def test_stale_cache_exclusion(self):
        case = next(
            item
            for item in ADVERSARIAL_RETRIEVAL_CASES
            if item.adversarial_mode is AdversarialRetrievalMode.STALE_CACHE
        )
        result = run_adversarial_retrieval_case(case)
        self.assertTrue(result.passed, result.message)
        self.assertIn("ar02_fresh", result.ranked_local_ids)
        self.assertNotIn("ar02_stale", result.ranked_local_ids)

    def test_isolated_missing_cache_exclusion(self):
        case = next(
            item
            for item in ADVERSARIAL_RETRIEVAL_CASES
            if item.adversarial_mode is AdversarialRetrievalMode.MISSING_CACHE
        )
        result = run_adversarial_retrieval_case(case)
        self.assertTrue(result.passed, result.message)
        self.assertIn("ar03_cached", result.ranked_local_ids)
        self.assertNotIn("ar03_missing", result.ranked_local_ids)
        # Prove the SkillEntry exists but has no matching provider/model cache row.
        missing_entry = SkillEntry.objects.get(skill_name="MissingPython")
        self.assertFalse(
            EvidenceEmbedding.objects.filter(
                skill_entry=missing_entry,
                embedding_provider=FixedVectorEmbeddingProvider.PROVIDER_NAME,
                embedding_model=FixedVectorEmbeddingProvider.MODEL_NAME,
            ).exists()
        )

    def test_provider_model_mismatch_exclusion(self):
        case = next(
            item
            for item in ADVERSARIAL_RETRIEVAL_CASES
            if item.adversarial_mode is AdversarialRetrievalMode.PROVIDER_MODEL_MISMATCH
        )
        result = run_adversarial_retrieval_case(case)
        self.assertTrue(result.passed, result.message)
        self.assertIn("ar04_match", result.ranked_local_ids)
        self.assertNotIn("ar04_mismatch", result.ranked_local_ids)

    def test_phase1_runner_passes_all_cases_without_network(self):
        with (
            patch("socket.socket") as socket_ctor,
            patch("urllib.request.urlopen") as urlopen,
        ):
            report = run_phase1_retrieval_evaluation()
            socket_ctor.assert_not_called()
            urlopen.assert_not_called()
        self.assertEqual(report.overall_result, "PASS")
        self.assertEqual(report.total_case_count, 9)
        self.assertEqual(report.failed_case_count, 0)
        self.assertEqual(report.network_call_count, 0)
        self.assertEqual(report.live_embedding_call_count, 0)
        self.assertEqual(report.live_llm_call_count, 0)
        self.assertEqual(len(report.retrieval_quality_results), 5)
        self.assertEqual(len(report.adversarial_retrieval_results), 4)
        for item in report.retrieval_quality_results:
            self.assertEqual(item.recall_at_5, 1.0)
            self.assertTrue(item.passed)
        for item in report.adversarial_retrieval_results:
            self.assertTrue(item.passed)

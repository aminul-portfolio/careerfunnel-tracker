"""Sprint 120 Phase 1: RAG evaluation case contract tests."""

from __future__ import annotations

from django.test import SimpleTestCase

from apps.skill_ledger.evaluation.rag_evaluation_cases import (
    ADVERSARIAL_RETRIEVAL_CASES,
    CASE_SCHEMA_VERSION,
    PHASE1_EVALUATION_CASES,
    RETRIEVAL_QUALITY_CASES,
    RagCorpusMember,
    RagEvalCategory,
    RagEvaluationCaseContractError,
    RagRetrievalQualityCase,
    compute_case_set_hash,
    validate_and_sort_rag_evaluation_cases,
)
from apps.skill_ledger.evaluation.rag_evaluation_metrics import (
    RagEvaluationMetricError,
    mean_reciprocal_rank,
    recall_at_1,
    recall_at_5,
)
from apps.skill_ledger.rag_retrieval import TOP_K


def _member(local_id: str, vector=(1.0, 0.0)) -> RagCorpusMember:
    return RagCorpusMember(
        local_id=local_id,
        skill_name=f"Skill-{local_id}",
        category="programming",
        evidence_level="VERIFIED",
        sprint_reference="Sprint 120",
        document_vector=vector,
    )


def _rq(
    *,
    case_id: str = "RQ-TEST",
    corpus=None,
    relevant=("a",),
    query_vector=(1.0, 0.0),
    is_synthetic: bool = True,
    schema_version: str = CASE_SCHEMA_VERSION,
    expected_recall_at_5: float = 1.0,
) -> RagRetrievalQualityCase:
    if corpus is None:
        corpus = (
            _member("a", (1.0, 0.0)),
            _member("b", (0.0, 1.0)),
            _member("c", (0.1, 0.9)),
            _member("d", (0.2, 0.8)),
            _member("e", (0.3, 0.7)),
            _member("f", (0.4, 0.6)),
        )
    return RagRetrievalQualityCase(
        case_id=case_id,
        schema_version=schema_version,
        category=RagEvalCategory.RETRIEVAL_QUALITY,
        description="contract test case",
        is_synthetic=is_synthetic,
        corpus=corpus,
        query_text="contract-query",
        query_vector=query_vector,
        expected_relevant_local_ids=relevant,
        expected_recall_at_5=expected_recall_at_5,
        safety_assertions=("contract",),
    )


class RagEvaluationContractTests(SimpleTestCase):
    def test_case_schema_version_is_locked(self):
        self.assertEqual(CASE_SCHEMA_VERSION, "skill_ledger_rag_eval_case_v1")
        for case in PHASE1_EVALUATION_CASES:
            self.assertEqual(case.schema_version, CASE_SCHEMA_VERSION)

    def test_synthetic_only_enforcement(self):
        with self.assertRaises(RagEvaluationCaseContractError):
            _rq(is_synthetic=False)

    def test_unique_case_ids_across_phase1_set(self):
        ids = [case.case_id for case in PHASE1_EVALUATION_CASES]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(RETRIEVAL_QUALITY_CASES), 5)
        self.assertEqual(len(ADVERSARIAL_RETRIEVAL_CASES), 4)
        self.assertEqual(len(PHASE1_EVALUATION_CASES), 9)

    def test_canonical_hash_determinism(self):
        first = compute_case_set_hash(PHASE1_EVALUATION_CASES)
        second = compute_case_set_hash(PHASE1_EVALUATION_CASES)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)
        self.assertTrue(all(ch in "0123456789abcdef" for ch in first))

    def test_case_set_hash_is_order_invariant(self):
        forward = compute_case_set_hash(PHASE1_EVALUATION_CASES)
        reversed_cases = tuple(reversed(PHASE1_EVALUATION_CASES))
        backward = compute_case_set_hash(reversed_cases)
        self.assertEqual(forward, backward)
        sorted_again = validate_and_sort_rag_evaluation_cases(reversed_cases)
        self.assertEqual(
            [case.case_id for case in sorted_again],
            sorted(case.case_id for case in PHASE1_EVALUATION_CASES),
        )

    def test_duplicate_case_ids_rejected(self):
        with self.assertRaises(RagEvaluationCaseContractError):
            validate_and_sort_rag_evaluation_cases(
                (RETRIEVAL_QUALITY_CASES[0], RETRIEVAL_QUALITY_CASES[0])
            )

    def test_retrieval_corpus_must_exceed_top_k(self):
        self.assertEqual(TOP_K, 5)
        for case in RETRIEVAL_QUALITY_CASES:
            self.assertGreater(len(case.corpus), TOP_K)
        small = (
            _member("a"),
            _member("b"),
            _member("c"),
            _member("d"),
            _member("e"),
        )
        with self.assertRaises(RagEvaluationCaseContractError):
            _rq(corpus=small, relevant=("a",))

    def test_empty_relevant_set_rejected(self):
        with self.assertRaises(RagEvaluationCaseContractError):
            _rq(relevant=())

    def test_relevant_id_must_exist_in_corpus(self):
        with self.assertRaises(RagEvaluationCaseContractError):
            _rq(relevant=("missing",))

    def test_wrong_schema_version_rejected(self):
        with self.assertRaises(RagEvaluationCaseContractError):
            _rq(schema_version="wrong_schema")

    def test_finite_vectors_only_reject_bool_nan_inf(self):
        with self.assertRaises(RagEvaluationCaseContractError):
            _member("bad", (True, 0.0))
        with self.assertRaises(RagEvaluationCaseContractError):
            _rq(query_vector=(float("nan"), 1.0))
        with self.assertRaises(RagEvaluationCaseContractError):
            _rq(query_vector=(float("inf"), 1.0))
        with self.assertRaises(RagEvaluationCaseContractError):
            _member("dims", (1.0, 0.0, 0.0))

    def test_zero_vectors_rejected(self):
        with self.assertRaises(RagEvaluationCaseContractError):
            _member("zero", (0.0, 0.0))
        with self.assertRaises(RagEvaluationCaseContractError):
            _rq(query_vector=(0.0, 0.0))

    def test_duplicate_local_id_in_corpus_rejected(self):
        corpus = (
            _member("dup"),
            _member("dup"),
            _member("c"),
            _member("d"),
            _member("e"),
            _member("f"),
        )
        with self.assertRaises(RagEvaluationCaseContractError):
            _rq(corpus=corpus, relevant=("dup",))

    def test_recall_at_5_formula(self):
        self.assertEqual(
            recall_at_5(("a", "b"), ("a", "x", "b", "y", "z", "q")),
            1.0,
        )
        self.assertEqual(
            recall_at_5(("a", "b"), ("a", "x", "y", "z", "q")),
            0.5,
        )
        with self.assertRaises(RagEvaluationMetricError):
            recall_at_5((), ("a",))

    def test_recall_at_1_and_mrr_advisory_formulas(self):
        self.assertEqual(recall_at_1(("a", "b"), ("a", "b")), 1.0)
        self.assertEqual(recall_at_1(("a", "b"), ("x", "a")), 0.0)
        self.assertEqual(mean_reciprocal_rank(("a",), ("x", "a", "y")), 0.5)
        self.assertEqual(mean_reciprocal_rank(("a",), ("x", "y")), 0.0)

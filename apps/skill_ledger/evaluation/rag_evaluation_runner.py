"""Sprint 120 Phase 1: offline RAG retrieval evaluation runner.

Maps synthetic local IDs to runtime SkillEntry PKs, populates CURRENT cache
rows (except dedicated adversarial exceptions), calls
retrieve_owned_skill_evidence, and scores immutable results.
No network, live embedding provider, LLM, or management-command I/O.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from django.contrib.auth import get_user_model

from apps.skill_ledger.models import SkillEntry
from apps.skill_ledger.rag_retrieval import retrieve_owned_skill_evidence

from .rag_evaluation_cases import (
    EVALUATION_VERSION,
    AdversarialRetrievalMode,
    RagAdversarialRetrievalCase,
    RagCorpusMember,
    RagEvalCase,
    RagEvalCategory,
    RagEvaluationCaseContractError,
    RagRetrievalQualityCase,
    compute_case_set_hash,
    validate_and_sort_rag_evaluation_cases,
)
from .rag_evaluation_fixtures import (
    FixedVectorEmbeddingProvider,
    RagEvaluationFixtureError,
    ensure_current_fixed_embedding_cache,
    write_mismatched_provider_embedding_cache,
    write_stale_fixed_embedding_cache,
)
from .rag_evaluation_metrics import (
    RagEvaluationMetricError,
    mean_reciprocal_rank,
    recall_at_1,
    recall_at_5,
)

RUNNER_VERSION = "skill_ledger_rag_eval_runner_v1"
User = get_user_model()


class RagEvaluationRunnerError(ValueError):
    """Fail-closed runner failure."""


@dataclass(frozen=True)
class RagRetrievalQualityRunResult:
    case_id: str
    category: str
    passed: bool
    ranked_local_ids: tuple[str, ...]
    recall_at_5: float
    recall_at_1: float
    mrr: float
    expected_recall_at_5: float
    message: str


@dataclass(frozen=True)
class RagAdversarialRetrievalRunResult:
    case_id: str
    category: str
    adversarial_mode: str
    passed: bool
    ranked_local_ids: tuple[str, ...]
    message: str


@dataclass(frozen=True)
class RagRetrievalEvaluationReport:
    runner_version: str
    evaluation_version: str
    case_set_sha256: str
    overall_result: str
    total_case_count: int
    passed_case_count: int
    failed_case_count: int
    retrieval_quality_results: tuple[RagRetrievalQualityRunResult, ...]
    adversarial_retrieval_results: tuple[RagAdversarialRetrievalRunResult, ...]
    network_call_count: int
    live_embedding_call_count: int
    live_llm_call_count: int


def _create_skill_entry(user, member: RagCorpusMember) -> SkillEntry:
    return SkillEntry.objects.create(
        user=user,
        skill_name=member.skill_name,
        category=member.category,
        evidence_level=member.evidence_level,
        sprint_reference=member.sprint_reference,
    )


def _materialise_corpus(
    user,
    corpus: Sequence[RagCorpusMember],
) -> dict[str, SkillEntry]:
    mapping: dict[str, SkillEntry] = {}
    for member in corpus:
        mapping[member.local_id] = _create_skill_entry(user, member)
    return mapping


def _populate_current_cache(
    *,
    corpus: Sequence[RagCorpusMember],
    local_to_entry: dict[str, SkillEntry],
    provider: FixedVectorEmbeddingProvider,
    skip_local_ids: set[str] | None = None,
) -> None:
    skipped = skip_local_ids or set()
    for member in corpus:
        if member.local_id in skipped:
            continue
        ensure_current_fixed_embedding_cache(
            local_to_entry[member.local_id],
            provider=provider,
            vector=member.document_vector,
        )


def _rank_to_local_ids(
    ranked_entry_ids: Sequence[int],
    entry_to_local: dict[int, str],
) -> tuple[str, ...]:
    mapped: list[str] = []
    for entry_id in ranked_entry_ids:
        local_id = entry_to_local.get(entry_id)
        if local_id is None:
            raise RagEvaluationRunnerError(
                f"retrieved SkillEntry pk {entry_id} has no synthetic local_id mapping."
            )
        mapped.append(local_id)
    return tuple(mapped)


def run_retrieval_quality_case(
    case: RagRetrievalQualityCase,
    *,
    username_suffix: str = "",
) -> RagRetrievalQualityRunResult:
    if not isinstance(case, RagRetrievalQualityCase):
        raise RagEvaluationRunnerError("case must be RagRetrievalQualityCase.")
    if case.is_synthetic is not True:
        raise RagEvaluationCaseContractError("is_synthetic must be exactly True.")

    user = User.objects.create_user(
        username=f"rag_eval_rq_{case.case_id}{username_suffix}",
        password="pass",
    )
    local_to_entry = _materialise_corpus(user, case.corpus)
    entry_to_local = {entry.pk: local_id for local_id, entry in local_to_entry.items()}
    provider = FixedVectorEmbeddingProvider(case.query_vector)
    _populate_current_cache(
        corpus=case.corpus,
        local_to_entry=local_to_entry,
        provider=provider,
    )

    ranked = retrieve_owned_skill_evidence(
        user,
        case.query_text,
        provider=provider,
    )
    ranked_local_ids = _rank_to_local_ids(
        [item.skill_entry_id for item in ranked],
        entry_to_local,
    )

    try:
        actual_recall_at_5 = recall_at_5(
            case.expected_relevant_local_ids,
            ranked_local_ids,
        )
        actual_recall_at_1 = recall_at_1(
            case.expected_relevant_local_ids,
            ranked_local_ids,
        )
        actual_mrr = mean_reciprocal_rank(
            case.expected_relevant_local_ids,
            ranked_local_ids,
        )
    except RagEvaluationMetricError as exc:
        return RagRetrievalQualityRunResult(
            case_id=case.case_id,
            category=case.category.value,
            passed=False,
            ranked_local_ids=ranked_local_ids,
            recall_at_5=0.0,
            recall_at_1=0.0,
            mrr=0.0,
            expected_recall_at_5=case.expected_recall_at_5,
            message=f"metric failure: {exc}",
        )

    passed = actual_recall_at_5 == 1.0
    message = (
        "Recall@5 hard gate passed."
        if passed
        else (
            f"Recall@5 hard gate failed: actual={actual_recall_at_5} "
            f"expected={case.expected_recall_at_5}; ranked={ranked_local_ids}."
        )
    )
    return RagRetrievalQualityRunResult(
        case_id=case.case_id,
        category=case.category.value,
        passed=passed,
        ranked_local_ids=ranked_local_ids,
        recall_at_5=actual_recall_at_5,
        recall_at_1=actual_recall_at_1,
        mrr=actual_mrr,
        expected_recall_at_5=case.expected_recall_at_5,
        message=message,
    )


def run_adversarial_retrieval_case(
    case: RagAdversarialRetrievalCase,
    *,
    username_suffix: str = "",
) -> RagAdversarialRetrievalRunResult:
    if not isinstance(case, RagAdversarialRetrievalCase):
        raise RagEvaluationRunnerError("case must be RagAdversarialRetrievalCase.")
    if case.is_synthetic is not True:
        raise RagEvaluationCaseContractError("is_synthetic must be exactly True.")

    owner = User.objects.create_user(
        username=f"rag_eval_ar_owner_{case.case_id}{username_suffix}",
        password="pass",
    )
    local_to_entry = _materialise_corpus(owner, case.corpus)
    entry_to_local = {entry.pk: local_id for local_id, entry in local_to_entry.items()}
    provider = FixedVectorEmbeddingProvider(case.query_vector)
    exception_ids = set(case.cache_exception_local_ids)

    if case.adversarial_mode is AdversarialRetrievalMode.CROSS_USER:
        other = User.objects.create_user(
            username=f"rag_eval_ar_other_{case.case_id}{username_suffix}",
            password="pass",
        )
        other_map = _materialise_corpus(other, case.other_user_corpus)
        _populate_current_cache(
            corpus=case.corpus,
            local_to_entry=local_to_entry,
            provider=provider,
        )
        _populate_current_cache(
            corpus=case.other_user_corpus,
            local_to_entry=other_map,
            provider=provider,
        )
        for local_id, entry in other_map.items():
            entry_to_local[entry.pk] = local_id
    elif case.adversarial_mode is AdversarialRetrievalMode.STALE_CACHE:
        _populate_current_cache(
            corpus=case.corpus,
            local_to_entry=local_to_entry,
            provider=provider,
            skip_local_ids=exception_ids,
        )
        for member in case.corpus:
            if member.local_id in exception_ids:
                write_stale_fixed_embedding_cache(
                    local_to_entry[member.local_id],
                    provider=provider,
                    vector=member.document_vector,
                )
    elif case.adversarial_mode is AdversarialRetrievalMode.MISSING_CACHE:
        _populate_current_cache(
            corpus=case.corpus,
            local_to_entry=local_to_entry,
            provider=provider,
            skip_local_ids=exception_ids,
        )
    elif case.adversarial_mode is AdversarialRetrievalMode.PROVIDER_MODEL_MISMATCH:
        _populate_current_cache(
            corpus=case.corpus,
            local_to_entry=local_to_entry,
            provider=provider,
            skip_local_ids=exception_ids,
        )
        for member in case.corpus:
            if member.local_id in exception_ids:
                write_mismatched_provider_embedding_cache(
                    local_to_entry[member.local_id],
                    provider=provider,
                    vector=member.document_vector,
                )
    else:
        raise RagEvaluationRunnerError(
            f"unsupported adversarial_mode: {case.adversarial_mode}."
        )

    ranked = retrieve_owned_skill_evidence(
        owner,
        case.query_text,
        provider=provider,
    )
    ranked_local_ids = _rank_to_local_ids(
        [item.skill_entry_id for item in ranked],
        entry_to_local,
    )
    ranked_set = set(ranked_local_ids)

    missing_expected = [
        local_id
        for local_id in case.expected_retrieved_local_ids
        if local_id not in ranked_set
    ]
    leaked_forbidden = [
        local_id for local_id in case.forbidden_local_ids if local_id in ranked_set
    ]
    passed = not missing_expected and not leaked_forbidden
    if passed:
        message = "Adversarial retrieval assertions passed."
    else:
        message = (
            "Adversarial retrieval assertions failed: "
            f"missing_expected={missing_expected}; leaked_forbidden={leaked_forbidden}; "
            f"ranked={ranked_local_ids}."
        )
    return RagAdversarialRetrievalRunResult(
        case_id=case.case_id,
        category=case.category.value,
        adversarial_mode=case.adversarial_mode.value,
        passed=passed,
        ranked_local_ids=ranked_local_ids,
        message=message,
    )


def run_phase1_retrieval_evaluation(
    cases: Iterable[RagEvalCase] | None = None,
) -> RagRetrievalEvaluationReport:
    """Run Phase 1 retrieval-quality + adversarial-retrieval evaluation."""
    from .rag_evaluation_cases import PHASE1_EVALUATION_CASES

    selected = (
        list(cases)
        if cases is not None
        else list(PHASE1_EVALUATION_CASES)
    )
    try:
        sorted_cases = validate_and_sort_rag_evaluation_cases(selected)
        case_set_sha256 = compute_case_set_hash(sorted_cases)
    except RagEvaluationCaseContractError as exc:
        raise RagEvaluationRunnerError(f"case contract failure: {exc}") from exc

    rq_results: list[RagRetrievalQualityRunResult] = []
    ar_results: list[RagAdversarialRetrievalRunResult] = []
    for case in sorted_cases:
        if isinstance(case, RagRetrievalQualityCase):
            if case.category is not RagEvalCategory.RETRIEVAL_QUALITY:
                raise RagEvaluationRunnerError(
                    f"unexpected category for retrieval case {case.case_id}."
                )
            rq_results.append(run_retrieval_quality_case(case))
        elif isinstance(case, RagAdversarialRetrievalCase):
            if case.category is not RagEvalCategory.ADVERSARIAL_RETRIEVAL:
                raise RagEvaluationRunnerError(
                    f"unexpected category for adversarial case {case.case_id}."
                )
            ar_results.append(run_adversarial_retrieval_case(case))
        else:
            raise RagEvaluationRunnerError(
                f"unsupported Phase 1 case type for {getattr(case, 'case_id', '?')}."
            )

    all_passed = all(item.passed for item in rq_results) and all(
        item.passed for item in ar_results
    )
    total = len(rq_results) + len(ar_results)
    passed_count = sum(1 for item in rq_results if item.passed) + sum(
        1 for item in ar_results if item.passed
    )
    return RagRetrievalEvaluationReport(
        runner_version=RUNNER_VERSION,
        evaluation_version=EVALUATION_VERSION,
        case_set_sha256=case_set_sha256,
        overall_result="PASS" if all_passed else "FAIL",
        total_case_count=total,
        passed_case_count=passed_count,
        failed_case_count=total - passed_count,
        retrieval_quality_results=tuple(rq_results),
        adversarial_retrieval_results=tuple(ar_results),
        network_call_count=0,
        live_embedding_call_count=0,
        live_llm_call_count=0,
    )


# Re-export fixture error for callers that only import the runner.
__all__ = (
    "RagAdversarialRetrievalRunResult",
    "RagEvaluationFixtureError",
    "RagEvaluationRunnerError",
    "RagRetrievalEvaluationReport",
    "RagRetrievalQualityRunResult",
    "RUNNER_VERSION",
    "run_adversarial_retrieval_case",
    "run_phase1_retrieval_evaluation",
    "run_retrieval_quality_case",
)

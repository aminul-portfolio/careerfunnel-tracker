"""Sprint 120: offline RAG evaluation runner.

Phase 1: retrieval-quality + adversarial-retrieval scoring.
Phase 2: grounded generation attribution / unsupported-output / zero-evidence
evaluation via real Sprint 119 generate_grounded_rag_answer.
No network, live embedding provider, LLM, or management-command I/O.
"""

from __future__ import annotations

import copy
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from django.contrib.auth import get_user_model

from apps.skill_ledger.models import SkillEntry
from apps.skill_ledger.rag_generation import (
    UNTRUSTED_RAG_EVIDENCE_BEGIN,
    UNTRUSTED_RAG_QUERY_BEGIN,
    build_grounding_payload,
    generate_grounded_rag_answer,
)
from apps.skill_ledger.rag_retrieval import (
    RetrievedSkillEvidence,
    retrieve_owned_skill_evidence,
)

from .rag_evaluation_cases import (
    EVALUATION_VERSION,
    AdversarialRetrievalMode,
    RagAdversarialRetrievalCase,
    RagCorpusMember,
    RagEvalCase,
    RagEvalCategory,
    RagEvaluationCaseContractError,
    RagGenerationSafetyCase,
    RagRetrievalQualityCase,
    RagRetrievedEvidenceSeed,
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
_SYNTHETIC_CONTENT_SHA256 = "a" * 64
_SYNTHETIC_PK_BASE = 1000


class RagEvaluationRunnerError(ValueError):
    """Fail-closed runner failure."""


class CountingFixedExplanationProvider:
    """Evaluation-local ExplanationProvider returning predetermined dict output."""

    def __init__(self, output: Mapping[str, Any]):
        self._output = copy.deepcopy(_plain_jsonish(output))
        self.call_count = 0
        self.last_payload: dict[str, Any] | None = None

    def __call__(self, payload: dict) -> dict:
        self.call_count += 1
        self.last_payload = payload
        return copy.deepcopy(self._output)


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
class RagGenerationSafetyRunResult:
    case_id: str
    category: str
    passed: bool
    expected_acceptance: bool
    actual_acceptance: bool
    expected_rejection_code: str | None
    actual_rejection_code: str | None
    expected_provider_called: bool
    actual_provider_called: bool
    provider_call_count: int
    expected_final_rendered_labels: tuple[str, ...] | None
    actual_final_rendered_labels: tuple[str, ...] | None
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


@dataclass(frozen=True)
class RagGenerationSafetyEvaluationReport:
    runner_version: str
    evaluation_version: str
    case_set_sha256: str
    overall_result: str
    total_case_count: int
    passed_case_count: int
    failed_case_count: int
    generation_safety_results: tuple[RagGenerationSafetyRunResult, ...]
    network_call_count: int
    live_embedding_call_count: int
    live_llm_call_count: int


def _plain_jsonish(value: object) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain_jsonish(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain_jsonish(item) for item in value]
    return value


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


def _build_retrieved_from_seeds(
    seeds: Sequence[RagRetrievedEvidenceSeed],
) -> tuple[tuple[RetrievedSkillEvidence, ...], dict[str, int]]:
    local_to_pk: dict[str, int] = {}
    retrieved: list[RetrievedSkillEvidence] = []
    for index, seed in enumerate(seeds, start=1):
        pk = _SYNTHETIC_PK_BASE + index
        if pk == 999:
            raise RagEvaluationRunnerError(
                "synthetic PK collision with reserved invented source 999."
            )
        local_to_pk[seed.local_id] = pk
        retrieved.append(
            RetrievedSkillEvidence(
                skill_entry_id=pk,
                skill_name=seed.skill_name,
                category=seed.category,
                evidence_level=seed.evidence_level,
                sprint_reference=seed.sprint_reference,
                content_sha256=_SYNTHETIC_CONTENT_SHA256,
                similarity_score=1.0,
            )
        )
    return tuple(retrieved), local_to_pk


def _remap_simulated_provider_output(
    output: Mapping[str, Any] | None,
    local_to_pk: dict[str, int],
) -> dict[str, Any] | None:
    if output is None:
        return None
    remapped = _plain_jsonish(output)
    sources = remapped.get("sources_used")
    if isinstance(sources, list):
        for item in sources:
            if not isinstance(item, dict):
                continue
            source_identifier = item.get("source_identifier")
            if isinstance(source_identifier, str) and source_identifier in local_to_pk:
                item["source_identifier"] = local_to_pk[source_identifier]
    return remapped


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


def run_generation_safety_case(
    case: RagGenerationSafetyCase,
) -> RagGenerationSafetyRunResult:
    if not isinstance(case, RagGenerationSafetyCase):
        raise RagEvaluationRunnerError("case must be RagGenerationSafetyCase.")
    if case.is_synthetic is not True:
        raise RagEvaluationCaseContractError("is_synthetic must be exactly True.")

    retrieved, local_to_pk = _build_retrieved_from_seeds(case.retrieved_seed)
    remapped_output = _remap_simulated_provider_output(
        case.simulated_provider_output,
        local_to_pk,
    )

    counting_provider: CountingFixedExplanationProvider | None = None
    provider = None
    if case.inject_provider:
        if remapped_output is None:
            raise RagEvaluationRunnerError(
                "inject_provider=True requires remappable simulated_provider_output."
            )
        counting_provider = CountingFixedExplanationProvider(remapped_output)
        provider = counting_provider

    # Prove production grounding construction is reachable for non-empty retrieval.
    if retrieved:
        grounding = build_grounding_payload(case.query_text, retrieved)
        if UNTRUSTED_RAG_QUERY_BEGIN not in grounding["query"]:
            raise RagEvaluationRunnerError("grounding payload missing query fence.")
        if UNTRUSTED_RAG_EVIDENCE_BEGIN not in grounding["retrieved_evidence_fenced"]:
            raise RagEvaluationRunnerError("grounding payload missing evidence fence.")

    outcome = generate_grounded_rag_answer(
        case.query_text,
        retrieved,
        provider=provider,
    )
    provider_call_count = (
        counting_provider.call_count if counting_provider is not None else 0
    )
    actual_acceptance = outcome.ok is True
    actual_rejection_code = None if outcome.code is None else outcome.code.value
    actual_labels: tuple[str, ...] | None = None
    if outcome.validated is not None:
        actual_labels = tuple(
            item.display_label for item in outcome.validated.sources_used
        )

    failures: list[str] = []
    if actual_acceptance != case.expected_acceptance:
        failures.append(
            f"acceptance expected={case.expected_acceptance} actual={actual_acceptance}"
        )
    if actual_rejection_code != case.expected_rejection_code:
        failures.append(
            "rejection_code expected="
            f"{case.expected_rejection_code} actual={actual_rejection_code}"
        )
    if outcome.provider_called != case.expected_provider_called:
        failures.append(
            "provider_called expected="
            f"{case.expected_provider_called} actual={outcome.provider_called}"
        )
    expected_calls = 1 if case.expected_provider_called else 0
    if provider_call_count != expected_calls:
        failures.append(
            f"provider_call_count expected={expected_calls} actual={provider_call_count}"
        )
    if case.expected_acceptance is False and outcome.validated is not None:
        failures.append("rejected outcome unexpectedly retained validated payload")
    if case.expected_final_rendered_labels is not None:
        if actual_labels != case.expected_final_rendered_labels:
            failures.append(
                "final labels expected="
                f"{case.expected_final_rendered_labels} actual={actual_labels}"
            )

    passed = not failures
    message = (
        "Generation safety assertions passed."
        if passed
        else "Generation safety assertions failed: " + "; ".join(failures)
    )
    return RagGenerationSafetyRunResult(
        case_id=case.case_id,
        category=case.category.value,
        passed=passed,
        expected_acceptance=case.expected_acceptance,
        actual_acceptance=actual_acceptance,
        expected_rejection_code=case.expected_rejection_code,
        actual_rejection_code=actual_rejection_code,
        expected_provider_called=case.expected_provider_called,
        actual_provider_called=outcome.provider_called,
        provider_call_count=provider_call_count,
        expected_final_rendered_labels=case.expected_final_rendered_labels,
        actual_final_rendered_labels=actual_labels,
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


def run_phase2_safety_evaluation(
    cases: Iterable[RagGenerationSafetyCase] | None = None,
) -> RagGenerationSafetyEvaluationReport:
    """Run Phase 2 attribution / unsupported-output / zero-evidence evaluation."""
    from .rag_evaluation_cases import PHASE2_SAFETY_CASES

    selected = (
        list(cases)
        if cases is not None
        else list(PHASE2_SAFETY_CASES)
    )
    try:
        sorted_cases = validate_and_sort_rag_evaluation_cases(selected)
        case_set_sha256 = compute_case_set_hash(sorted_cases)
    except RagEvaluationCaseContractError as exc:
        raise RagEvaluationRunnerError(f"case contract failure: {exc}") from exc

    results: list[RagGenerationSafetyRunResult] = []
    for case in sorted_cases:
        if not isinstance(case, RagGenerationSafetyCase):
            raise RagEvaluationRunnerError(
                f"unsupported Phase 2 case type for {getattr(case, 'case_id', '?')}."
            )
        if case.category not in {
            RagEvalCategory.ATTRIBUTION_SAFETY,
            RagEvalCategory.UNSUPPORTED_OUTPUT,
            RagEvalCategory.ZERO_EVIDENCE,
        }:
            raise RagEvaluationRunnerError(
                f"unexpected category for safety case {case.case_id}."
            )
        results.append(run_generation_safety_case(case))

    all_passed = all(item.passed for item in results)
    total = len(results)
    passed_count = sum(1 for item in results if item.passed)
    return RagGenerationSafetyEvaluationReport(
        runner_version=RUNNER_VERSION,
        evaluation_version=EVALUATION_VERSION,
        case_set_sha256=case_set_sha256,
        overall_result="PASS" if all_passed else "FAIL",
        total_case_count=total,
        passed_case_count=passed_count,
        failed_case_count=total - passed_count,
        generation_safety_results=tuple(results),
        network_call_count=0,
        live_embedding_call_count=0,
        live_llm_call_count=0,
    )


# Re-export fixture error for callers that only import the runner.
__all__ = (
    "CountingFixedExplanationProvider",
    "RagAdversarialRetrievalRunResult",
    "RagEvaluationFixtureError",
    "RagEvaluationRunnerError",
    "RagGenerationSafetyEvaluationReport",
    "RagGenerationSafetyRunResult",
    "RagRetrievalEvaluationReport",
    "RagRetrievalQualityRunResult",
    "RUNNER_VERSION",
    "run_adversarial_retrieval_case",
    "run_generation_safety_case",
    "run_phase1_retrieval_evaluation",
    "run_phase2_safety_evaluation",
    "run_retrieval_quality_case",
)

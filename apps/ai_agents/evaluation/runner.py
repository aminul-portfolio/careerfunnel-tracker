"""Offline and structured-replay evaluation runner for Phase 2B."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from typing import Any

from apps.ai_agents.services import (
    analyze_job_posting,
    build_cv_tailoring_advisor,
    build_cv_tailoring_semantic_prompt,
    build_openai_fit_scoring_prompt,
    parse_ai_fit_scoring_payload,
    parse_cv_tailoring_semantic_payload,
)

from .cases import (
    EvaluationCase,
    EvaluationCaseSet,
    OfflineResponse,
    ReplayBundle,
    ReplayResponse,
    sha256_hex,
)

PHASE_ID = "p1-phase2b"
PROMPT_CONTRACT_LIMITATION = (
    "This hash identifies the Phase 2B payload/parser contract, "
    "not the complete provider wire prompt."
)

FIT_BUILDER_FQN = "apps.ai_agents.services.build_openai_fit_scoring_prompt"
FIT_PARSER_FQN = "apps.ai_agents.services.parse_ai_fit_scoring_payload"
CV_BUILDER_FQN = "apps.ai_agents.services.build_cv_tailoring_semantic_prompt"
CV_PARSER_FQN = "apps.ai_agents.services.parse_cv_tailoring_semantic_payload"
FIT_PARSER_CONTRACT_ID = "ai_fit_scoring_payload_v1"
CV_PARSER_CONTRACT_ID = "cv_tailoring_semantic_payload_v1"

# Only fields whose structure unambiguously presents a skill as matched,
# verified or backed by existing candidate evidence. Advisory or planning
# fields (for example recommended_cv_angle, semantic_experience_angles,
# gaps, risks and reasoning) must never trigger LEARNING_TARGET_AS_VERIFIED.
VERIFIED_LEARNING_TARGET_FIELDS = frozenset(
    {
        "evidence_matches",
        "matched_skills",
        "semantic_matched_skills",
        "recommended_projects",
        "semantic_project_highlights",
        "strongest_projects",
    }
)


@dataclass(frozen=True)
class CaseEvaluationResult:
    case_id: str
    surface: str
    result_type: str
    outcome: str
    parser_status: str
    human_groundedness: int | None
    breach_codes: tuple[str, ...]
    safe_error_category: str | None
    prompt_contract_hash: str


@dataclass(frozen=True)
class EvaluationRunResult:
    mode: str
    case_set_hash: str
    prompt_contract_hashes: dict[str, str]
    prompt_contract_hash_limitation: str
    case_count: int
    pass_count: int
    fail_count: int
    review_required_count: int
    hard_breach_counts: dict[str, int]
    overall_result: str
    results: tuple[CaseEvaluationResult, ...]
    partial: bool = False


class EvaluationRunnerError(RuntimeError):
    """Unexpected mid-run failure after evaluation has started."""

    def __init__(
        self,
        message: str,
        *,
        partial_result: EvaluationRunResult | None = None,
    ) -> None:
        super().__init__(message)
        self.partial_result = partial_result


def _normalise_phrase(value: str) -> str:
    return " ".join(value.casefold().split())


def _collect_strings(value: object) -> list[str]:
    found: list[str] = []
    if isinstance(value, str):
        found.append(value)
    elif isinstance(value, dict):
        for item in value.values():
            found.extend(_collect_strings(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            found.extend(_collect_strings(item))
    return found


def _to_serialisable(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, dict):
        return {str(key): _to_serialisable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_serialisable(item) for item in value]
    return value


def _build_payload_and_contract(
    case: EvaluationCase,
) -> tuple[dict[str, Any], str]:
    if case.surface == "fit":
        baseline = analyze_job_posting(
            company_name=case.company_name,
            job_title=case.job_title,
            location=case.location,
            job_posting=case.job_description,
        )
        payload = build_openai_fit_scoring_prompt(
            company_name=case.company_name,
            job_title=case.job_title,
            location=case.location,
            job_description=case.job_description,
            rule_based_analysis=baseline,
        )
        builder = FIT_BUILDER_FQN
        parser = FIT_PARSER_FQN
        parser_contract = FIT_PARSER_CONTRACT_ID
    else:
        rule_based = build_cv_tailoring_advisor(
            company_name=case.company_name,
            job_title=case.job_title,
            location=case.location,
            job_description=case.job_description,
            cv_evidence="",
            provider_callable=None,
        )
        payload = build_cv_tailoring_semantic_prompt(
            company_name=case.company_name,
            job_title=case.job_title,
            location=case.location,
            job_description=case.job_description,
            cv_evidence="",
            rule_based_result=rule_based,
        )
        builder = CV_BUILDER_FQN
        parser = CV_PARSER_FQN
        parser_contract = CV_PARSER_CONTRACT_ID

    manifest = {
        "surface": case.surface,
        "payload_builder": builder,
        "parser": parser,
        "payload_top_level_keys": sorted(payload.keys()),
        "parser_contract_id": parser_contract,
        "phase": PHASE_ID,
        "limitation": PROMPT_CONTRACT_LIMITATION,
    }
    return payload, sha256_hex(manifest)


def _select_envelope(
    case: EvaluationCase,
    *,
    mode: str,
    replay_by_id: dict[str, ReplayResponse],
) -> OfflineResponse:
    if mode == "offline":
        return case.offline_response
    response = replay_by_id[case.case_id]
    return OfflineResponse(
        result_type=response.result_type,
        payload=response.payload,
        error_class=response.error_class,
    )


def _phrase_present(haystacks: list[str], needle: str) -> bool:
    target = _normalise_phrase(needle)
    if not target:
        return False
    return any(target in _normalise_phrase(item) for item in haystacks)


def _field_strings(parsed: dict[str, Any], field_names: frozenset[str]) -> list[str]:
    values: list[str] = []
    for field_name in field_names:
        if field_name in parsed:
            values.extend(_collect_strings(parsed[field_name]))
    return values


def _detect_breaches(
    case: EvaluationCase,
    parsed: dict[str, Any],
) -> list[str]:
    breaches: list[str] = []
    all_strings = _collect_strings(parsed)
    for phrase in case.forbidden_claims:
        if _phrase_present(all_strings, phrase):
            breaches.append("FORBIDDEN_CLAIM")
            break
    verified_strings = _field_strings(parsed, VERIFIED_LEARNING_TARGET_FIELDS)
    for skill in case.learning_target_skills:
        if _phrase_present(verified_strings, skill):
            breaches.append("LEARNING_TARGET_AS_VERIFIED")
            break
    for claim in case.unsupported_material_claims:
        if _phrase_present(all_strings, claim):
            breaches.append("UNSUPPORTED_MATERIAL_CLAIM")
            break
    return breaches


def _assign_outcome(
    *,
    breach_codes: list[str],
    result_type: str,
    parser_failed: bool,
    human_groundedness: int | None,
) -> str:
    if breach_codes or result_type in {"timeout", "provider_error"} or parser_failed:
        return "FAIL"
    if human_groundedness is None or human_groundedness in (0, 1):
        return "REVIEW_REQUIRED"
    return "PASS"


def evaluate_case(
    case: EvaluationCase,
    *,
    mode: str,
    replay_by_id: dict[str, ReplayResponse],
) -> CaseEvaluationResult:
    _payload, prompt_contract_hash = _build_payload_and_contract(case)
    del _payload  # payload construction is required for contract hashing/reuse
    envelope = _select_envelope(case, mode=mode, replay_by_id=replay_by_id)

    if envelope.result_type == "timeout":
        return CaseEvaluationResult(
            case_id=case.case_id,
            surface=case.surface,
            result_type="timeout",
            outcome="FAIL",
            parser_status="not_run",
            human_groundedness=case.human_groundedness,
            breach_codes=("TIMEOUT",),
            safe_error_category="timeout",
            prompt_contract_hash=prompt_contract_hash,
        )
    if envelope.result_type == "provider_error":
        return CaseEvaluationResult(
            case_id=case.case_id,
            surface=case.surface,
            result_type="provider_error",
            outcome="FAIL",
            parser_status="not_run",
            human_groundedness=case.human_groundedness,
            breach_codes=("PROVIDER_ERROR",),
            safe_error_category="provider_error",
            prompt_contract_hash=prompt_contract_hash,
        )

    assert envelope.payload is not None
    try:
        if case.surface == "fit":
            parsed_obj = parse_ai_fit_scoring_payload(envelope.payload)
        else:
            parsed_obj = parse_cv_tailoring_semantic_payload(envelope.payload)
    except ValueError:
        return CaseEvaluationResult(
            case_id=case.case_id,
            surface=case.surface,
            result_type="payload",
            outcome="FAIL",
            parser_status="rejected",
            human_groundedness=case.human_groundedness,
            breach_codes=("CONTRACT_INVALID",),
            safe_error_category="parser_rejection",
            prompt_contract_hash=prompt_contract_hash,
        )

    parsed = _to_serialisable(parsed_obj)
    assert isinstance(parsed, dict)
    breach_codes = _detect_breaches(case, parsed)
    outcome = _assign_outcome(
        breach_codes=breach_codes,
        result_type="payload",
        parser_failed=False,
        human_groundedness=case.human_groundedness,
    )
    return CaseEvaluationResult(
        case_id=case.case_id,
        surface=case.surface,
        result_type="payload",
        outcome=outcome,
        parser_status="accepted",
        human_groundedness=case.human_groundedness,
        breach_codes=tuple(breach_codes),
        safe_error_category=None,
        prompt_contract_hash=prompt_contract_hash,
    )


def _overall_result(results: list[CaseEvaluationResult]) -> str:
    if any(item.outcome == "FAIL" for item in results):
        return "FAIL"
    if any(item.outcome == "REVIEW_REQUIRED" for item in results):
        return "REVIEW_REQUIRED"
    return "PASS"


def _hard_breach_counts(results: list[CaseEvaluationResult]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in results:
        for code in item.breach_codes:
            counts[code] = counts.get(code, 0) + 1
    return dict(sorted(counts.items()))


def run_evaluation(
    case_set: EvaluationCaseSet,
    *,
    mode: str,
    replay_bundle: ReplayBundle | None = None,
) -> EvaluationRunResult:
    if mode not in {"offline", "replay"}:
        raise ValueError(f"Unsupported evaluation mode: {mode}")
    if mode == "live":
        raise ValueError("Live mode is unsupported in Phase 2B.")
    if mode == "replay" and replay_bundle is None:
        raise ValueError("Replay mode requires a validated replay bundle.")
    if mode == "offline" and replay_bundle is not None:
        raise ValueError("Offline mode must not receive a replay bundle.")
    if not case_set.cases:
        raise ValueError(
            "evaluation_requires_at_least_one_case: "
            "evaluation requires at least one case."
        )

    replay_by_id: dict[str, ReplayResponse] = {}
    if replay_bundle is not None:
        replay_by_id = {
            response.case_id: response for response in replay_bundle.responses
        }

    results: list[CaseEvaluationResult] = []
    prompt_contract_hashes: dict[str, str] = {}
    try:
        for case in case_set.cases:
            result = evaluate_case(
                case,
                mode=mode,
                replay_by_id=replay_by_id,
            )
            results.append(result)
            prompt_contract_hashes[case.case_id] = result.prompt_contract_hash
    except EvaluationRunnerError:
        raise
    except Exception as exc:
        partial = EvaluationRunResult(
            mode=mode,
            case_set_hash=case_set.case_set_hash,
            prompt_contract_hashes=prompt_contract_hashes,
            prompt_contract_hash_limitation=PROMPT_CONTRACT_LIMITATION,
            case_count=len(results),
            pass_count=sum(1 for item in results if item.outcome == "PASS"),
            fail_count=sum(1 for item in results if item.outcome == "FAIL"),
            review_required_count=sum(
                1 for item in results if item.outcome == "REVIEW_REQUIRED"
            ),
            hard_breach_counts=_hard_breach_counts(results),
            overall_result=_overall_result(results) if results else "FAIL",
            results=tuple(results),
            partial=True,
        )
        raise EvaluationRunnerError(
            f"Unexpected evaluation failure: {exc.__class__.__name__}",
            partial_result=partial,
        ) from exc

    return EvaluationRunResult(
        mode=mode,
        case_set_hash=case_set.case_set_hash,
        prompt_contract_hashes=prompt_contract_hashes,
        prompt_contract_hash_limitation=PROMPT_CONTRACT_LIMITATION,
        case_count=len(results),
        pass_count=sum(1 for item in results if item.outcome == "PASS"),
        fail_count=sum(1 for item in results if item.outcome == "FAIL"),
        review_required_count=sum(
            1 for item in results if item.outcome == "REVIEW_REQUIRED"
        ),
        hard_breach_counts=_hard_breach_counts(results),
        overall_result=_overall_result(results),
        results=tuple(results),
        partial=False,
    )

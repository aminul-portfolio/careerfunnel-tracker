"""Controlled live-provider evaluation runner for Phase 2C (mocked-transport ready)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Callable

import anthropic

from apps.ai_agents.claude_provider import (
    CLAUDE_MAX_TOKENS,
    CLAUDE_MODEL,
    ClaudeTelemetryProvider,
    ClaudeTelemetryResult,
    build_cv_messages_create_kwargs,
    build_fit_messages_create_kwargs,
    canonical_request_payload_bytes,
    hash_request_payload,
)
from apps.ai_agents.services import (
    parse_ai_fit_scoring_payload,
    parse_cv_tailoring_semantic_payload,
)

from .cases import (
    CaseValidationError,
    EvaluationCase,
    EvaluationCaseSet,
    _scan_for_prohibited_content,
)
from .live_reporting import hash_request_id
from .runner import (
    VERIFIED_LEARNING_TARGET_FIELDS,
    _assign_outcome,
    _build_payload_and_contract,
    _detect_breaches,
    _field_strings,
    _phrase_present,
    _to_serialisable,
)

PRICING_PROFILE_ID = "p1-phase2c-haiku-20251001-v1"
PRICING_PROFILE_EFFECTIVE_DATE = date(2025, 10, 1).isoformat()
INPUT_USD_PER_MILLION = Decimal("1.00")
OUTPUT_USD_PER_MILLION = Decimal("5.00")
MAXIMUM_OPERATOR_CEILING_USD = Decimal("5.00")
MINIMUM_CALL_CAP = 1
MAXIMUM_CALL_CAP = 30
ACCEPTABLE_STOP_REASON = "end_turn"
TRUNCATION_STOP_REASONS = frozenset(
    {"max_tokens", "model_context_window_exceeded"}
)
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

POSITIVE_EVIDENCE_FIELDS = VERIFIED_LEARNING_TARGET_FIELDS | frozenset(
    {
        "evidence_matches",
        "matched_skills",
        "semantic_matched_skills",
        "recommended_projects",
        "semantic_project_highlights",
        "strongest_projects",
    }
)


class LiveEvaluationError(RuntimeError):
    """Fail-closed live evaluation error with optional partial result."""

    def __init__(
        self,
        message: str,
        *,
        category: str,
        partial_result: LiveEvaluationRunResult | None = None,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.partial_result = partial_result


@dataclass(frozen=True)
class LiveCaseResult:
    case_id: str
    surface: str
    model: str | None
    hashed_request_id: str | None
    stop_reason: str | None
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int | None
    actual_cost_usd: Decimal | None
    pricing_profile_id: str
    contract_manifest_hash: str
    request_payload_hash: str | None
    raw_response_hash: str | None
    parser_status: str
    outcome: str
    breach_codes: tuple[str, ...]
    safe_error_category: str | None
    stage: int = 1


@dataclass(frozen=True)
class LiveEvaluationRunResult:
    case_set_hash: str
    pricing_profile_id: str
    pricing_profile_effective_date: str
    input_unit_price_usd_per_million: Decimal
    output_unit_price_usd_per_million: Decimal
    monetary_ceiling_usd: Decimal
    projected_max_cost_usd: Decimal
    actual_spend_usd: Decimal
    call_cap: int
    calls_made: int
    case_count: int
    pass_count: int
    fail_count: int
    review_required_count: int
    hard_breach_counts: dict[str, int]
    overall_result: str
    stop_reason: str | None
    held_after_stage: int | None
    results: tuple[LiveCaseResult, ...]
    partial: bool = False
    actual_spend_complete: bool = True


@dataclass(frozen=True)
class PreparedLiveCase:
    case: EvaluationCase
    prompt_payload: dict[str, Any]
    contract_manifest_hash: str
    request_kwargs: dict[str, Any]
    request_payload_hash: str
    projected_cost_usd: Decimal


@dataclass(frozen=True)
class PreparedLiveEvaluationPlan:
    """Immutable pre-flight plan built without provider composition or network I/O."""

    case_set: EvaluationCaseSet
    call_cap: int
    monetary_ceiling_usd: Decimal
    projected_max_cost_usd: Decimal
    prepared_cases: tuple[PreparedLiveCase, ...]


def calculate_token_cost(
    *,
    input_tokens: int,
    output_tokens: int,
    input_unit_price: Decimal = INPUT_USD_PER_MILLION,
    output_unit_price: Decimal = OUTPUT_USD_PER_MILLION,
) -> Decimal:
    """Exact Decimal cost. Do not round or quantise the result."""
    million = Decimal("1000000")
    return (Decimal(input_tokens) / million) * input_unit_price + (
        Decimal(output_tokens) / million
    ) * output_unit_price


def estimate_input_tokens_from_request_kwargs(request_kwargs: dict[str, Any]) -> int:
    """Conservative operational estimate: UTF-8 byte length of the exact request."""
    return len(canonical_request_payload_bytes(request_kwargs))


def projected_call_cost_usd(request_kwargs: dict[str, Any]) -> Decimal:
    estimated_input = estimate_input_tokens_from_request_kwargs(request_kwargs)
    return calculate_token_cost(
        input_tokens=estimated_input,
        output_tokens=CLAUDE_MAX_TOKENS,
    )


def normalise_hex_hash(value: str) -> str:
    return str(value).strip().casefold()


def is_valid_hex64_hash(value: object) -> bool:
    if not isinstance(value, str):
        return False
    return bool(_HEX64_RE.fullmatch(normalise_hex_hash(value)))


def validate_expected_case_set_hash(value: object) -> str:
    """Validate and normalise an independently supplied case-set hash."""
    if not isinstance(value, str) or not is_valid_hex64_hash(value):
        raise LiveEvaluationError(
            "case_set_hash_mismatch",
            category="case_set_hash_mismatch",
        )
    return normalise_hex_hash(value)


def validate_monetary_ceiling_usd(value: object) -> Decimal:
    """Parse and validate a finite positive monetary ceiling at or below US$5.00."""
    try:
        if isinstance(value, Decimal):
            ceiling = value
        else:
            ceiling = Decimal(str(value))
    except Exception as exc:
        raise LiveEvaluationError(
            "invalid_monetary_ceiling",
            category="invalid_monetary_ceiling",
        ) from exc
    if not ceiling.is_finite():
        raise LiveEvaluationError(
            "invalid_monetary_ceiling",
            category="invalid_monetary_ceiling",
        )
    if ceiling <= Decimal("0"):
        raise LiveEvaluationError(
            "invalid_monetary_ceiling",
            category="invalid_monetary_ceiling",
        )
    if ceiling > MAXIMUM_OPERATOR_CEILING_USD:
        raise LiveEvaluationError(
            "invalid_monetary_ceiling",
            category="invalid_monetary_ceiling",
        )
    return ceiling


def canary_stages(
    cases: tuple[EvaluationCase, ...],
) -> list[tuple[int, tuple[EvaluationCase, ...]]]:
    remaining = list(cases)
    stages: list[tuple[int, tuple[EvaluationCase, ...]]] = []
    if not remaining:
        return stages
    stages.append((1, (remaining.pop(0),)))
    if remaining:
        batch = tuple(remaining[:4])
        del remaining[:4]
        stages.append((2, batch))
    if remaining:
        stages.append((3, tuple(remaining)))
    return stages


def _request_kwargs_for_case(
    case: EvaluationCase,
    prompt_payload: dict[str, Any],
) -> dict[str, Any]:
    if case.surface == "fit":
        return build_fit_messages_create_kwargs(prompt_payload)
    return build_cv_messages_create_kwargs(prompt_payload)


def _validate_run_controls(
    case_set: EvaluationCaseSet,
    *,
    call_cap: int,
    monetary_ceiling_usd: Decimal,
) -> None:
    if not isinstance(call_cap, int) or isinstance(call_cap, bool):
        raise LiveEvaluationError(
            "call_cap must be an integer.",
            category="invalid_call_cap",
        )
    if call_cap < MINIMUM_CALL_CAP or call_cap > MAXIMUM_CALL_CAP:
        raise LiveEvaluationError(
            f"call_cap must be between {MINIMUM_CALL_CAP} and {MAXIMUM_CALL_CAP}.",
            category="invalid_call_cap",
        )
    validate_monetary_ceiling_usd(monetary_ceiling_usd)
    if len(case_set.cases) > call_cap:
        raise LiveEvaluationError(
            "case count exceeds approved call cap.",
            category="call_cap_breach",
        )
    if not case_set.cases:
        raise LiveEvaluationError(
            "evaluation_requires_at_least_one_case",
            category="empty_case_set",
        )


def _manual_review_breaches(case: EvaluationCase, parsed: dict[str, Any]) -> list[str]:
    if case.surface == "fit":
        notes = parsed.get("claim_safety_notes")
        if not isinstance(notes, list) or not notes:
            return ["MISSING_MANUAL_REVIEW_MARKER"]
        joined = " ".join(str(item) for item in notes).casefold()
        if "manual review" not in joined:
            return ["MISSING_MANUAL_REVIEW_MARKER"]
        return []
    if parsed.get("manual_review_required") is not True:
        return ["MISSING_MANUAL_REVIEW_MARKER"]
    return []


def _fabricated_and_unsupported(
    case: EvaluationCase,
    parsed: dict[str, Any],
) -> list[str]:
    breaches: list[str] = []
    positive = _field_strings(parsed, POSITIVE_EVIDENCE_FIELDS)
    all_strings: list[str] = []
    from .runner import _collect_strings

    all_strings = _collect_strings(parsed)
    for claim in case.unsupported_material_claims:
        if _phrase_present(positive, claim):
            breaches.append("FABRICATED_EVIDENCE")
            break
    for claim in case.unsupported_material_claims:
        if _phrase_present(all_strings, claim) and not _phrase_present(positive, claim):
            breaches.append("UNSUPPORTED_MATERIAL_CLAIM")
            break
    return breaches


def _live_breach_codes(case: EvaluationCase, parsed: dict[str, Any]) -> list[str]:
    # Reuse Phase 2B checks but replace unsupported handling with live rules.
    base = [code for code in _detect_breaches(case, parsed) if code != "UNSUPPORTED_MATERIAL_CLAIM"]
    base.extend(_fabricated_and_unsupported(case, parsed))
    base.extend(_manual_review_breaches(case, parsed))
    # Deduplicate while preserving order
    seen: set[str] = set()
    ordered: list[str] = []
    for code in base:
        if code not in seen:
            seen.add(code)
            ordered.append(code)
    return ordered


def _scan_output_for_secrets(parsed: dict[str, Any], *, case_id: str) -> None:
    _scan_for_prohibited_content(parsed, field_path="parsed_output", case_id=case_id)


def _payload_scan_breach_codes(
    case: EvaluationCase,
    telemetry: ClaudeTelemetryResult,
) -> tuple[str, ...]:
    """Scan complete provider JSON immediately after telemetry return."""
    if not isinstance(telemetry.parsed_payload, dict):
        return ()
    try:
        _scan_for_prohibited_content(
            telemetry.parsed_payload,
            field_path="parsed_payload",
            case_id=case.case_id,
        )
    except CaseValidationError:
        return ("OUTPUT_SECRET_OR_PERSONAL_DATA",)
    return ()


def _merge_breach_codes(*groups: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for group in groups:
        for code in group:
            if code not in seen:
                seen.add(code)
                ordered.append(code)
    return tuple(ordered)


def _sanitise_token(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _sanitise_latency_ms(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _sanitise_optional_string(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    return value


def _sanitise_optional_hex_hash(value: object) -> str | None:
    if not is_valid_hex64_hash(value):
        return None
    assert isinstance(value, str)
    return normalise_hex_hash(value)


def _sanitise_hashed_request_id(raw_request_id: object) -> str | None:
    if not isinstance(raw_request_id, str) or not raw_request_id:
        return None
    return hash_request_id(raw_request_id)


def _overall_result(results: list[LiveCaseResult]) -> str:
    if any(item.outcome == "FAIL" for item in results):
        return "FAIL"
    if any(item.outcome == "REVIEW_REQUIRED" for item in results):
        return "REVIEW_REQUIRED"
    return "PASS"


def _hard_breach_counts(results: list[LiveCaseResult]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in results:
        for code in item.breach_codes:
            counts[code] = counts.get(code, 0) + 1
    return dict(sorted(counts.items()))


def _build_run_result(
    *,
    case_set: EvaluationCaseSet,
    monetary_ceiling_usd: Decimal,
    projected_max_cost_usd: Decimal,
    actual_spend_usd: Decimal,
    call_cap: int,
    calls_made: int,
    results: list[LiveCaseResult],
    stop_reason: str | None,
    held_after_stage: int | None,
    partial: bool,
    actual_spend_complete: bool = True,
) -> LiveEvaluationRunResult:
    return LiveEvaluationRunResult(
        case_set_hash=case_set.case_set_hash,
        pricing_profile_id=PRICING_PROFILE_ID,
        pricing_profile_effective_date=PRICING_PROFILE_EFFECTIVE_DATE,
        input_unit_price_usd_per_million=INPUT_USD_PER_MILLION,
        output_unit_price_usd_per_million=OUTPUT_USD_PER_MILLION,
        monetary_ceiling_usd=monetary_ceiling_usd,
        projected_max_cost_usd=projected_max_cost_usd,
        actual_spend_usd=actual_spend_usd,
        call_cap=call_cap,
        calls_made=calls_made,
        case_count=len(results),
        pass_count=sum(1 for item in results if item.outcome == "PASS"),
        fail_count=sum(1 for item in results if item.outcome == "FAIL"),
        review_required_count=sum(
            1 for item in results if item.outcome == "REVIEW_REQUIRED"
        ),
        hard_breach_counts=_hard_breach_counts(results),
        overall_result=_overall_result(results) if results else "FAIL",
        stop_reason=stop_reason,
        held_after_stage=held_after_stage,
        results=tuple(results),
        partial=partial,
        actual_spend_complete=actual_spend_complete,
    )


def _classify_provider_exception(exc: BaseException) -> tuple[str, bool]:
    """Return (safe_category, stop_complete_run)."""
    if isinstance(exc, anthropic.AuthenticationError):
        return "authentication_failure", True
    if isinstance(exc, anthropic.RateLimitError):
        return "rate_limit", True
    if isinstance(exc, TimeoutError):
        return "timeout", False
    if isinstance(exc, anthropic.APITimeoutError):
        return "timeout", False
    if isinstance(exc, anthropic.APIError):
        return "provider_error", False
    return "provider_error", False


def prepare_live_evaluation_plan(
    case_set: EvaluationCaseSet,
    *,
    call_cap: int,
    monetary_ceiling_usd: Decimal,
    expected_case_set_hash: str,
) -> PreparedLiveEvaluationPlan:
    """Pure, network-free pre-flight. Must run before provider composition."""
    _validate_run_controls(
        case_set,
        call_cap=call_cap,
        monetary_ceiling_usd=monetary_ceiling_usd,
    )
    normalised_expected = validate_expected_case_set_hash(expected_case_set_hash)
    if normalised_expected != normalise_hex_hash(case_set.case_set_hash):
        raise LiveEvaluationError(
            "case_set_hash_mismatch",
            category="case_set_hash_mismatch",
        )

    for case in case_set.cases:
        try:
            _scan_for_prohibited_content(
                {
                    "company_name": case.company_name,
                    "job_title": case.job_title,
                    "location": case.location,
                    "job_description": case.job_description,
                },
                field_path=f"case.{case.case_id}",
                case_id=case.case_id,
            )
        except CaseValidationError as exc:
            raise LiveEvaluationError(
                "secret_or_personal_data_in_input",
                category="secret_or_personal_data_in_input",
            ) from exc

    prepared_cases: list[PreparedLiveCase] = []
    for case in case_set.cases:
        prompt_payload, contract_hash = _build_payload_and_contract(case)
        request_kwargs = _request_kwargs_for_case(case, prompt_payload)
        projected = projected_call_cost_usd(request_kwargs)
        prepared_cases.append(
            PreparedLiveCase(
                case=case,
                prompt_payload=prompt_payload,
                contract_manifest_hash=contract_hash,
                request_kwargs=request_kwargs,
                request_payload_hash=hash_request_payload(request_kwargs),
                projected_cost_usd=projected,
            )
        )

    projected_max_cost = sum(
        (item.projected_cost_usd for item in prepared_cases),
        Decimal("0"),
    )
    if projected_max_cost > monetary_ceiling_usd:
        raise LiveEvaluationError(
            "projected_cost_breach",
            category="projected_cost_breach",
        )

    return PreparedLiveEvaluationPlan(
        case_set=case_set,
        call_cap=call_cap,
        monetary_ceiling_usd=monetary_ceiling_usd,
        projected_max_cost_usd=projected_max_cost,
        prepared_cases=tuple(prepared_cases),
    )


def _require_usage_tokens(telemetry: ClaudeTelemetryResult) -> tuple[int, int]:
    """Fail closed on missing or invalid usage telemetry. Never substitute zero."""
    for label, value in (
        ("input_tokens", telemetry.input_tokens),
        ("output_tokens", telemetry.output_tokens),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise LiveEvaluationError(
                "invalid_usage_telemetry",
                category="invalid_usage_telemetry",
            )
    assert isinstance(telemetry.input_tokens, int)
    assert isinstance(telemetry.output_tokens, int)
    return telemetry.input_tokens, telemetry.output_tokens


def _request_payload_hash_matches(
    telemetry: ClaudeTelemetryResult,
    *,
    expected_request_payload_hash: str,
) -> bool:
    got = telemetry.request_payload_hash
    if not is_valid_hex64_hash(got):
        return False
    assert isinstance(got, str)
    return normalise_hex_hash(got) == normalise_hex_hash(expected_request_payload_hash)


def execute_live_evaluation_plan(
    plan: PreparedLiveEvaluationPlan,
    *,
    fit_telemetry_provider: ClaudeTelemetryProvider,
    cv_telemetry_provider: ClaudeTelemetryProvider,
    raw_evidence_writer: Callable[..., Any] | None = None,
) -> LiveEvaluationRunResult:
    case_set = plan.case_set
    call_cap = plan.call_cap
    monetary_ceiling_usd = plan.monetary_ceiling_usd
    projected_max_cost = plan.projected_max_cost_usd
    prepared_by_id = {item.case.case_id: item for item in plan.prepared_cases}

    results: list[LiveCaseResult] = []
    actual_spend = Decimal("0")
    actual_spend_complete = True
    calls_made = 0
    hold_after_stage: int | None = None
    stop_reason: str | None = None

    try:
        for stage_number, stage_cases in canary_stages(case_set.cases):
            if hold_after_stage is not None:
                break
            stage_hold = False
            for case in stage_cases:
                prepared = prepared_by_id[case.case_id]
                case = prepared.case
                prompt_payload = prepared.prompt_payload
                contract_hash = prepared.contract_manifest_hash
                projected = prepared.projected_cost_usd
                remaining = monetary_ceiling_usd - actual_spend
                if projected > remaining:
                    stop_reason = "projected_cost_breach"
                    raise LiveEvaluationError(
                        "projected_cost_breach",
                        category="projected_cost_breach",
                        partial_result=_build_run_result(
                            case_set=case_set,
                            monetary_ceiling_usd=monetary_ceiling_usd,
                            projected_max_cost_usd=projected_max_cost,
                            actual_spend_usd=actual_spend,
                            call_cap=call_cap,
                            calls_made=calls_made,
                            results=results,
                            stop_reason=stop_reason,
                            held_after_stage=hold_after_stage,
                            partial=True,
                        ),
                    )
                if calls_made >= call_cap:
                    stop_reason = "call_cap_breach"
                    raise LiveEvaluationError(
                        "call_cap_breach",
                        category="call_cap_breach",
                        partial_result=_build_run_result(
                            case_set=case_set,
                            monetary_ceiling_usd=monetary_ceiling_usd,
                            projected_max_cost_usd=projected_max_cost,
                            actual_spend_usd=actual_spend,
                            call_cap=call_cap,
                            calls_made=calls_made,
                            results=results,
                            stop_reason=stop_reason,
                            held_after_stage=hold_after_stage,
                            partial=True,
                        ),
                    )

                provider = (
                    fit_telemetry_provider
                    if case.surface == "fit"
                    else cv_telemetry_provider
                )
                # Count every provider attempt exactly once, immediately before invoke.
                calls_made += 1
                try:
                    telemetry = provider(prompt_payload)
                except Exception as exc:  # noqa: BLE001 - classified safely below
                    category, stop_run = _classify_provider_exception(exc)
                    actual_spend_complete = False
                    if stop_run:
                        stop_reason = category
                        raise LiveEvaluationError(
                            category,
                            category=category,
                            partial_result=_build_run_result(
                                case_set=case_set,
                                monetary_ceiling_usd=monetary_ceiling_usd,
                                projected_max_cost_usd=projected_max_cost,
                                actual_spend_usd=actual_spend,
                                call_cap=call_cap,
                                calls_made=calls_made,
                                results=results,
                                stop_reason=stop_reason,
                                held_after_stage=hold_after_stage,
                                partial=True,
                                actual_spend_complete=actual_spend_complete,
                            ),
                        ) from exc
                    result = LiveCaseResult(
                        case_id=case.case_id,
                        surface=case.surface,
                        model=None,
                        hashed_request_id=None,
                        stop_reason=None,
                        input_tokens=None,
                        output_tokens=None,
                        latency_ms=None,
                        actual_cost_usd=None,
                        pricing_profile_id=PRICING_PROFILE_ID,
                        contract_manifest_hash=contract_hash,
                        request_payload_hash=None,
                        raw_response_hash=None,
                        parser_status="not_run",
                        outcome="FAIL",
                        breach_codes=(
                            "TIMEOUT" if category == "timeout" else "PROVIDER_ERROR",
                        ),
                        safe_error_category=category,
                        stage=stage_number,
                    )
                    results.append(result)
                    stage_hold = True
                    continue

                # Every returned ClaudeTelemetryResult produces exactly one case result.
                payload_breaches = _payload_scan_breach_codes(case, telemetry)

                if telemetry.returned_model != CLAUDE_MODEL:
                    actual_spend_complete = False
                    breach_codes = _merge_breach_codes(
                        ("UNEXPECTED_RETURNED_MODEL",),
                        payload_breaches,
                    )
                    _append_redacted_result_and_write_raw(
                        results,
                        raw_evidence_writer,
                        case=case,
                        telemetry=telemetry,
                        contract_hash=contract_hash,
                        call_cost=None,
                        stage_number=stage_number,
                        outcome="FAIL",
                        breach_codes=breach_codes,
                        parser_status="not_run",
                        safe_error_category="unexpected_returned_model",
                    )
                    stop_reason = "unexpected_returned_model"
                    raise LiveEvaluationError(
                        "unexpected_returned_model",
                        category="unexpected_returned_model",
                        partial_result=_build_run_result(
                            case_set=case_set,
                            monetary_ceiling_usd=monetary_ceiling_usd,
                            projected_max_cost_usd=projected_max_cost,
                            actual_spend_usd=actual_spend,
                            call_cap=call_cap,
                            calls_made=calls_made,
                            results=results,
                            stop_reason=stop_reason,
                            held_after_stage=hold_after_stage,
                            partial=True,
                            actual_spend_complete=actual_spend_complete,
                        ),
                    )

                try:
                    input_tokens, output_tokens = _require_usage_tokens(telemetry)
                except LiveEvaluationError as exc:
                    actual_spend_complete = False
                    breach_codes = _merge_breach_codes(
                        ("INVALID_USAGE_TELEMETRY",),
                        payload_breaches,
                    )
                    _append_redacted_result_and_write_raw(
                        results,
                        raw_evidence_writer,
                        case=case,
                        telemetry=telemetry,
                        contract_hash=contract_hash,
                        call_cost=None,
                        stage_number=stage_number,
                        outcome="FAIL",
                        breach_codes=breach_codes,
                        parser_status="not_run",
                        safe_error_category="invalid_usage_telemetry",
                    )
                    stop_reason = "invalid_usage_telemetry"
                    raise LiveEvaluationError(
                        "invalid_usage_telemetry",
                        category="invalid_usage_telemetry",
                        partial_result=_build_run_result(
                            case_set=case_set,
                            monetary_ceiling_usd=monetary_ceiling_usd,
                            projected_max_cost_usd=projected_max_cost,
                            actual_spend_usd=actual_spend,
                            call_cap=call_cap,
                            calls_made=calls_made,
                            results=results,
                            stop_reason=stop_reason,
                            held_after_stage=hold_after_stage,
                            partial=True,
                            actual_spend_complete=actual_spend_complete,
                        ),
                    ) from exc

                call_cost = calculate_token_cost(
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
                actual_spend += call_cost

                hash_matches = _request_payload_hash_matches(
                    telemetry,
                    expected_request_payload_hash=prepared.request_payload_hash,
                )
                cost_breach = actual_spend >= monetary_ceiling_usd
                if not hash_matches or cost_breach:
                    breach_groups: list[tuple[str, ...]] = []
                    if cost_breach:
                        breach_groups.append(("ACTUAL_COST_BREACH",))
                    if not hash_matches:
                        breach_groups.append(("REQUEST_PAYLOAD_HASH_MISMATCH",))
                    breach_codes = _merge_breach_codes(
                        *breach_groups,
                        payload_breaches,
                    )
                    if cost_breach:
                        stop_reason = "actual_cost_breach"
                        safe_error_category = "actual_cost_breach"
                    else:
                        stop_reason = "request_payload_hash_mismatch"
                        safe_error_category = "request_payload_hash_mismatch"
                    _append_redacted_result_and_write_raw(
                        results,
                        raw_evidence_writer,
                        case=case,
                        telemetry=telemetry,
                        contract_hash=contract_hash,
                        call_cost=call_cost,
                        stage_number=stage_number,
                        outcome="FAIL",
                        breach_codes=breach_codes,
                        parser_status="not_run",
                        safe_error_category=safe_error_category,
                    )
                    raise LiveEvaluationError(
                        stop_reason,
                        category=safe_error_category,
                        partial_result=_build_run_result(
                            case_set=case_set,
                            monetary_ceiling_usd=monetary_ceiling_usd,
                            projected_max_cost_usd=projected_max_cost,
                            actual_spend_usd=actual_spend,
                            call_cap=call_cap,
                            calls_made=calls_made,
                            results=results,
                            stop_reason=stop_reason,
                            held_after_stage=hold_after_stage,
                            partial=True,
                            actual_spend_complete=actual_spend_complete,
                        ),
                    )

                case_result, should_hold = _evaluate_telemetry_case(
                    case=case,
                    telemetry=telemetry,
                    contract_hash=contract_hash,
                    call_cost=call_cost,
                    stage_number=stage_number,
                    payload_breach_codes=payload_breaches,
                )
                results.append(case_result)
                _attempt_raw_evidence_write(
                    raw_evidence_writer,
                    case=case,
                    telemetry=telemetry,
                )
                if should_hold:
                    stage_hold = True

            if stage_hold:
                hold_after_stage = stage_number
                stop_reason = stop_reason or "stage_hold"
                break

    except LiveEvaluationError as exc:
        if (
            exc.category == "raw_evidence_write_failure"
            and exc.partial_result is None
        ):
            cause = exc.__cause__ if exc.__cause__ is not None else exc
            raise LiveEvaluationError(
                "raw_evidence_write_failure",
                category="raw_evidence_write_failure",
                partial_result=_build_run_result(
                    case_set=case_set,
                    monetary_ceiling_usd=monetary_ceiling_usd,
                    projected_max_cost_usd=projected_max_cost,
                    actual_spend_usd=actual_spend,
                    call_cap=call_cap,
                    calls_made=calls_made,
                    results=results,
                    stop_reason="raw_evidence_write_failure",
                    held_after_stage=hold_after_stage,
                    partial=True,
                    actual_spend_complete=actual_spend_complete,
                ),
            ) from cause
        raise
    except Exception as exc:  # noqa: BLE001
        partial = _build_run_result(
            case_set=case_set,
            monetary_ceiling_usd=monetary_ceiling_usd,
            projected_max_cost_usd=projected_max_cost,
            actual_spend_usd=actual_spend,
            call_cap=call_cap,
            calls_made=calls_made,
            results=results,
            stop_reason="unexpected_evaluation_failure",
            held_after_stage=hold_after_stage,
            partial=True,
            actual_spend_complete=actual_spend_complete,
        )
        raise LiveEvaluationError(
            f"Unexpected evaluation failure: {exc.__class__.__name__}",
            category="unexpected_evaluation_failure",
            partial_result=partial,
        ) from exc

    return _build_run_result(
        case_set=case_set,
        monetary_ceiling_usd=monetary_ceiling_usd,
        projected_max_cost_usd=projected_max_cost,
        actual_spend_usd=actual_spend,
        call_cap=call_cap,
        calls_made=calls_made,
        results=results,
        stop_reason=stop_reason,
        held_after_stage=hold_after_stage,
        partial=False,
        actual_spend_complete=actual_spend_complete,
    )


def run_live_evaluation(
    case_set: EvaluationCaseSet,
    *,
    call_cap: int,
    monetary_ceiling_usd: Decimal,
    fit_telemetry_provider: ClaudeTelemetryProvider,
    cv_telemetry_provider: ClaudeTelemetryProvider,
    expected_case_set_hash: str,
    raw_evidence_writer: Callable[..., Any] | None = None,
) -> LiveEvaluationRunResult:
    plan = prepare_live_evaluation_plan(
        case_set,
        call_cap=call_cap,
        monetary_ceiling_usd=monetary_ceiling_usd,
        expected_case_set_hash=expected_case_set_hash,
    )
    return execute_live_evaluation_plan(
        plan,
        fit_telemetry_provider=fit_telemetry_provider,
        cv_telemetry_provider=cv_telemetry_provider,
        raw_evidence_writer=raw_evidence_writer,
    )


def _attempt_raw_evidence_write(
    raw_evidence_writer: Callable[..., Any] | None,
    *,
    case: EvaluationCase,
    telemetry: ClaudeTelemetryResult,
) -> None:
    if raw_evidence_writer is None:
        return
    try:
        raw_evidence_writer(
            case_id=case.case_id,
            raw_request_id=telemetry.raw_request_id,
            serialised_raw_response=telemetry.serialised_raw_response,
            raw_response_hash=telemetry.raw_response_hash,
        )
    except LiveEvaluationError:
        raise
    except Exception as exc:
        raise LiveEvaluationError(
            "raw_evidence_write_failure",
            category="raw_evidence_write_failure",
        ) from exc


def _case_result_from_telemetry(
    *,
    case: EvaluationCase,
    telemetry: ClaudeTelemetryResult,
    contract_hash: str,
    call_cost: Decimal | None,
    stage_number: int,
    outcome: str,
    breach_codes: tuple[str, ...],
    parser_status: str,
    safe_error_category: str | None,
) -> LiveCaseResult:
    return LiveCaseResult(
        case_id=case.case_id,
        surface=case.surface,
        model=_sanitise_optional_string(telemetry.returned_model),
        hashed_request_id=_sanitise_hashed_request_id(telemetry.raw_request_id),
        stop_reason=_sanitise_optional_string(telemetry.stop_reason),
        input_tokens=_sanitise_token(telemetry.input_tokens),
        output_tokens=_sanitise_token(telemetry.output_tokens),
        latency_ms=_sanitise_latency_ms(telemetry.latency_ms),
        actual_cost_usd=call_cost,
        pricing_profile_id=PRICING_PROFILE_ID,
        contract_manifest_hash=contract_hash,
        request_payload_hash=_sanitise_optional_hex_hash(
            telemetry.request_payload_hash
        ),
        raw_response_hash=_sanitise_optional_hex_hash(telemetry.raw_response_hash),
        parser_status=parser_status,
        outcome=outcome,
        breach_codes=breach_codes,
        safe_error_category=safe_error_category,
        stage=stage_number,
    )


def _append_redacted_result_and_write_raw(
    results: list[LiveCaseResult],
    raw_evidence_writer: Callable[..., Any] | None,
    *,
    case: EvaluationCase,
    telemetry: ClaudeTelemetryResult,
    contract_hash: str,
    call_cost: Decimal | None,
    stage_number: int,
    outcome: str,
    breach_codes: tuple[str, ...],
    parser_status: str,
    safe_error_category: str | None,
) -> LiveCaseResult:
    """Append strictly redacted result, then attempt one raw-evidence write."""
    recorded = _case_result_from_telemetry(
        case=case,
        telemetry=telemetry,
        contract_hash=contract_hash,
        call_cost=call_cost,
        stage_number=stage_number,
        outcome=outcome,
        breach_codes=breach_codes,
        parser_status=parser_status,
        safe_error_category=safe_error_category,
    )
    results.append(recorded)
    _attempt_raw_evidence_write(
        raw_evidence_writer,
        case=case,
        telemetry=telemetry,
    )
    return recorded


def _evaluate_telemetry_case(
    *,
    case: EvaluationCase,
    telemetry: ClaudeTelemetryResult,
    contract_hash: str,
    call_cost: Decimal,
    stage_number: int,
    payload_breach_codes: tuple[str, ...],
) -> tuple[LiveCaseResult, bool]:
    """Build a strictly redacted case result; caller appends and writes raw evidence."""
    stop_reason = telemetry.stop_reason

    if stop_reason in TRUNCATION_STOP_REASONS:
        breach_codes = _merge_breach_codes(
            ("TRUNCATION",),
            payload_breach_codes,
        )
        return (
            _case_result_from_telemetry(
                case=case,
                telemetry=telemetry,
                contract_hash=contract_hash,
                call_cost=call_cost,
                stage_number=stage_number,
                outcome="FAIL",
                breach_codes=breach_codes,
                parser_status="rejected",
                safe_error_category="truncation",
            ),
            True,
        )

    if stop_reason != ACCEPTABLE_STOP_REASON:
        breach_codes = _merge_breach_codes(
            ("UNEXPECTED_STOP_REASON",),
            payload_breach_codes,
        )
        return (
            _case_result_from_telemetry(
                case=case,
                telemetry=telemetry,
                contract_hash=contract_hash,
                call_cost=call_cost,
                stage_number=stage_number,
                outcome="FAIL",
                breach_codes=breach_codes,
                parser_status="not_run",
                safe_error_category="unexpected_stop_reason",
            ),
            True,
        )

    if "OUTPUT_SECRET_OR_PERSONAL_DATA" in payload_breach_codes:
        breach_codes = _merge_breach_codes((), payload_breach_codes)
        return (
            _case_result_from_telemetry(
                case=case,
                telemetry=telemetry,
                contract_hash=contract_hash,
                call_cost=call_cost,
                stage_number=stage_number,
                outcome="FAIL",
                breach_codes=breach_codes,
                parser_status="accepted",
                safe_error_category="output_secret_or_personal_data",
            ),
            True,
        )

    if telemetry.parsed_payload is None or telemetry.parse_error_category:
        breach_codes = _merge_breach_codes(
            ("CONTRACT_INVALID",),
            payload_breach_codes,
        )
        return (
            _case_result_from_telemetry(
                case=case,
                telemetry=telemetry,
                contract_hash=contract_hash,
                call_cost=call_cost,
                stage_number=stage_number,
                outcome="FAIL",
                breach_codes=breach_codes,
                parser_status="rejected",
                safe_error_category=telemetry.parse_error_category or "parser_rejection",
            ),
            True,
        )

    if not isinstance(telemetry.parsed_payload, dict):
        breach_codes = _merge_breach_codes(
            ("CONTRACT_INVALID",),
            payload_breach_codes,
        )
        return (
            _case_result_from_telemetry(
                case=case,
                telemetry=telemetry,
                contract_hash=contract_hash,
                call_cost=call_cost,
                stage_number=stage_number,
                outcome="FAIL",
                breach_codes=breach_codes,
                parser_status="rejected",
                safe_error_category="parser_rejection",
            ),
            True,
        )

    early_manual = _manual_review_breaches(case, telemetry.parsed_payload)
    if early_manual:
        breach_codes = _merge_breach_codes(
            tuple(early_manual),
            payload_breach_codes,
        )
        return (
            _case_result_from_telemetry(
                case=case,
                telemetry=telemetry,
                contract_hash=contract_hash,
                call_cost=call_cost,
                stage_number=stage_number,
                outcome="FAIL",
                breach_codes=breach_codes,
                parser_status="accepted",
                safe_error_category="missing_manual_review_marker",
            ),
            True,
        )

    try:
        if case.surface == "fit":
            parsed_obj = parse_ai_fit_scoring_payload(telemetry.parsed_payload)
        else:
            parsed_obj = parse_cv_tailoring_semantic_payload(telemetry.parsed_payload)
    except ValueError:
        breach_codes = _merge_breach_codes(
            ("CONTRACT_INVALID",),
            payload_breach_codes,
        )
        return (
            _case_result_from_telemetry(
                case=case,
                telemetry=telemetry,
                contract_hash=contract_hash,
                call_cost=call_cost,
                stage_number=stage_number,
                outcome="FAIL",
                breach_codes=breach_codes,
                parser_status="rejected",
                safe_error_category="parser_rejection",
            ),
            True,
        )

    parsed = _to_serialisable(parsed_obj)
    assert isinstance(parsed, dict)

    try:
        _scan_output_for_secrets(parsed, case_id=case.case_id)
    except CaseValidationError:
        breach_codes = _merge_breach_codes(
            ("OUTPUT_SECRET_OR_PERSONAL_DATA",),
            payload_breach_codes,
        )
        return (
            _case_result_from_telemetry(
                case=case,
                telemetry=telemetry,
                contract_hash=contract_hash,
                call_cost=call_cost,
                stage_number=stage_number,
                outcome="FAIL",
                breach_codes=breach_codes,
                parser_status="accepted",
                safe_error_category="output_secret_or_personal_data",
            ),
            True,
        )

    claim_breaches = _live_breach_codes(case, parsed)
    if claim_breaches:
        breach_codes = _merge_breach_codes(
            tuple(claim_breaches),
            payload_breach_codes,
        )
        return (
            _case_result_from_telemetry(
                case=case,
                telemetry=telemetry,
                contract_hash=contract_hash,
                call_cost=call_cost,
                stage_number=stage_number,
                outcome="FAIL",
                breach_codes=breach_codes,
                parser_status="accepted",
                safe_error_category=claim_breaches[0].lower(),
            ),
            True,
        )

    outcome = _assign_outcome(
        breach_codes=[],
        result_type="payload",
        parser_failed=False,
        human_groundedness=case.human_groundedness,
    )
    breach_codes = _merge_breach_codes((), payload_breach_codes)
    return (
        _case_result_from_telemetry(
            case=case,
            telemetry=telemetry,
            contract_hash=contract_hash,
            call_cost=call_cost,
            stage_number=stage_number,
            outcome=outcome,
            breach_codes=breach_codes,
            parser_status="accepted",
            safe_error_category=None,
        ),
        False,
    )

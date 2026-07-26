"""Case-set and replay-bundle loading for Phase 2B offline evaluation."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CASE_SET_SCHEMA_VERSION = "p1-phase2b-case-set-v1"
REPLAY_BUNDLE_SCHEMA_VERSION = "p1-phase2b-replay-v1"

ALLOWED_SURFACES = frozenset({"fit", "cv_jpa", "cv_agent_pack"})
ALLOWED_RESULT_TYPES = frozenset({"payload", "timeout", "provider_error"})
ALLOWED_OUTCOMES = frozenset({"PASS", "FAIL", "REVIEW_REQUIRED"})

CASE_SET_TOP_LEVEL_KEYS = frozenset({"schema_version", "cases"})
CASE_KEYS = frozenset(
    {
        "case_id",
        "surface",
        "company_name",
        "job_title",
        "location",
        "job_description",
        "expected_supported_findings",
        "expected_skill_gaps",
        "forbidden_claims",
        "learning_target_skills",
        "unsupported_material_claims",
        "human_groundedness",
        "offline_response",
    }
)
OFFLINE_RESPONSE_KEYS = frozenset({"result_type", "payload", "error_class"})
REPLAY_BUNDLE_TOP_LEVEL_KEYS = frozenset(
    {"schema_version", "case_set_hash", "responses", "bundle_hash"}
)
REPLAY_RESPONSE_KEYS = frozenset({"case_id", "result_type", "payload", "error_class"})

PROHIBITED_STRUCTURED_KEYS = frozenset(
    {
        "notes",
        "application_notes",
        "cv_version",
        "cover_letter_version",
        "full_cv",
        "cv_body",
        "cover_letter",
        "cover_letter_body",
        "api_key",
        "anthropic_api_key",
        "secret",
        "password",
        "access_token",
        "refresh_token",
    }
)

SECRET_LIKE_PATTERNS = (
    "ANTHROPIC_API_KEY=",
    "OPENAI_API_KEY=",
    "sk-ant-",
    "-----BEGIN PRIVATE KEY-----",
    "-----BEGIN RSA PRIVATE KEY-----",
)

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_DIGIT_RE = re.compile(r"\d")


class CaseValidationError(ValueError):
    """Safe validation failure for case-set or replay-bundle loading."""


@dataclass(frozen=True)
class OfflineResponse:
    result_type: str
    payload: dict[str, Any] | None
    error_class: str | None


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    surface: str
    company_name: str
    job_title: str
    location: str
    job_description: str
    expected_supported_findings: tuple[str, ...]
    expected_skill_gaps: tuple[str, ...]
    forbidden_claims: tuple[str, ...]
    learning_target_skills: tuple[str, ...]
    unsupported_material_claims: tuple[str, ...]
    human_groundedness: int | None
    offline_response: OfflineResponse


@dataclass(frozen=True)
class EvaluationCaseSet:
    schema_version: str
    cases: tuple[EvaluationCase, ...]
    case_set_hash: str


@dataclass(frozen=True)
class ReplayResponse:
    case_id: str
    result_type: str
    payload: dict[str, Any] | None
    error_class: str | None


@dataclass(frozen=True)
class ReplayBundle:
    schema_version: str
    case_set_hash: str
    responses: tuple[ReplayResponse, ...]
    bundle_hash: str


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _safe_error(
    *,
    case_id: str | None,
    field_path: str,
    category: str,
) -> CaseValidationError:
    prefix = f"case_id={case_id}; " if case_id else ""
    return CaseValidationError(
        f"{prefix}field_path={field_path}; category={category}"
    )


def _safe_case_id_for_error_context(
    raw_value: object,
    *,
    field_path: str,
) -> str | None:
    """Return a case identifier safe for error context, or None.

    Untrusted identifiers that are secret-like or contain personal contact
    data are rejected without being echoed in the exception.
    """
    if not isinstance(raw_value, str) or not raw_value.strip():
        return None
    if _contains_secret_like(raw_value):
        raise _safe_error(
            case_id=None,
            field_path=field_path,
            category="secret_like_case_id",
        )
    if _contains_personal_contact(raw_value):
        raise _safe_error(
            case_id=None,
            field_path=field_path,
            category="personal_contact_case_id",
        )
    return raw_value


def _require_exact_keys(
    data: dict[str, Any],
    allowed: frozenset[str],
    *,
    field_path: str,
    case_id: str | None = None,
) -> None:
    keys = set(data.keys())
    missing = sorted(allowed - keys)
    unknown_count = len(keys - allowed)
    if missing:
        raise _safe_error(
            case_id=case_id,
            field_path=field_path,
            category=f"missing_required_keys:{','.join(missing)}",
        )
    if unknown_count:
        # Unknown keys are untrusted input; never echo their names or values.
        raise _safe_error(
            case_id=case_id,
            field_path=field_path,
            category=f"unknown_keys_present;unknown_key_count:{unknown_count}",
        )


def _require_string(
    value: object,
    *,
    field_path: str,
    case_id: str | None = None,
    allow_empty: bool = False,
) -> str:
    if not isinstance(value, str):
        raise _safe_error(
            case_id=case_id,
            field_path=field_path,
            category="expected_string",
        )
    if not allow_empty and not value.strip():
        raise _safe_error(
            case_id=case_id,
            field_path=field_path,
            category="empty_string",
        )
    return value


def _require_string_list(
    value: object,
    *,
    field_path: str,
    case_id: str | None = None,
    require_non_empty_items: bool = False,
) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise _safe_error(
            case_id=case_id,
            field_path=field_path,
            category="expected_list",
        )
    items: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise _safe_error(
                case_id=case_id,
                field_path=f"{field_path}[{index}]",
                category="expected_string",
            )
        if require_non_empty_items and not item.strip():
            raise _safe_error(
                case_id=case_id,
                field_path=f"{field_path}[{index}]",
                category="empty_string",
            )
        items.append(item)
    return tuple(items)


def _contains_secret_like(text: str) -> bool:
    lowered = text.lower()
    return any(pattern.lower() in lowered for pattern in SECRET_LIKE_PATTERNS)


def _contains_personal_contact(text: str) -> bool:
    if EMAIL_RE.search(text):
        return True
    digits = PHONE_DIGIT_RE.findall(text)
    return len(digits) >= 7 and bool(
        re.search(r"(?:\+?\d[\d\s().-]{5,}\d)", text)
    )


def _scan_for_prohibited_content(
    value: object,
    *,
    field_path: str,
    case_id: str | None,
) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise _safe_error(
                    case_id=case_id,
                    field_path=field_path,
                    category="non_string_dict_key",
                )
            key_lower = key.lower()
            if key_lower in PROHIBITED_STRUCTURED_KEYS:
                raise _safe_error(
                    case_id=case_id,
                    field_path=f"{field_path}.{key}" if field_path else key,
                    category="prohibited_structured_field",
                )
            # Untrusted key names must pass all key-level checks before
            # they are embedded in a child field path or error message.
            if _contains_secret_like(key):
                raise _safe_error(
                    case_id=case_id,
                    field_path=field_path,
                    category="secret_like_key",
                )
            if _contains_personal_contact(key):
                raise _safe_error(
                    case_id=case_id,
                    field_path=field_path,
                    category="personal_contact_key",
                )
            child_path = f"{field_path}.{key}" if field_path else key
            _scan_for_prohibited_content(
                item,
                field_path=child_path,
                case_id=case_id,
            )
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _scan_for_prohibited_content(
                item,
                field_path=f"{field_path}[{index}]",
                case_id=case_id,
            )
        return
    if isinstance(value, str):
        if _contains_secret_like(value):
            raise _safe_error(
                case_id=case_id,
                field_path=field_path,
                category="secret_like_content",
            )
        if _contains_personal_contact(value):
            raise _safe_error(
                case_id=case_id,
                field_path=field_path,
                category="personal_contact_data",
            )


def _parse_offline_response(
    raw: object,
    *,
    case_id: str,
    field_path: str,
) -> OfflineResponse:
    if not isinstance(raw, dict):
        raise _safe_error(
            case_id=case_id,
            field_path=field_path,
            category="expected_object",
        )
    _require_exact_keys(
        raw,
        OFFLINE_RESPONSE_KEYS,
        field_path=field_path,
        case_id=case_id,
    )
    result_type = _require_string(
        raw["result_type"],
        field_path=f"{field_path}.result_type",
        case_id=case_id,
    )
    if result_type not in ALLOWED_RESULT_TYPES:
        raise _safe_error(
            case_id=case_id,
            field_path=f"{field_path}.result_type",
            category="invalid_result_type",
        )
    payload = raw["payload"]
    error_class = raw["error_class"]
    if result_type == "payload":
        if not isinstance(payload, dict):
            raise _safe_error(
                case_id=case_id,
                field_path=f"{field_path}.payload",
                category="payload_must_be_object",
            )
        if error_class is not None:
            raise _safe_error(
                case_id=case_id,
                field_path=f"{field_path}.error_class",
                category="error_class_must_be_null",
            )
        return OfflineResponse(
            result_type=result_type,
            payload=payload,
            error_class=None,
        )
    if payload is not None:
        raise _safe_error(
            case_id=case_id,
            field_path=f"{field_path}.payload",
            category="payload_must_be_null",
        )
    if not isinstance(error_class, str) or not error_class.strip():
        raise _safe_error(
            case_id=case_id,
            field_path=f"{field_path}.error_class",
            category="error_class_required",
        )
    return OfflineResponse(
        result_type=result_type,
        payload=None,
        error_class=error_class,
    )


def _parse_case(raw: object, *, index: int) -> EvaluationCase:
    field_path = f"cases[{index}]"
    if not isinstance(raw, dict):
        raise _safe_error(
            case_id=None,
            field_path=field_path,
            category="expected_object",
        )
    provisional_id = _safe_case_id_for_error_context(
        raw.get("case_id"),
        field_path=f"{field_path}.case_id",
    )
    _require_exact_keys(
        raw,
        CASE_KEYS,
        field_path=field_path,
        case_id=provisional_id,
    )
    case_id = _require_string(
        raw["case_id"],
        field_path=f"{field_path}.case_id",
    )
    surface = _require_string(
        raw["surface"],
        field_path=f"{field_path}.surface",
        case_id=case_id,
    )
    if surface not in ALLOWED_SURFACES:
        raise _safe_error(
            case_id=case_id,
            field_path=f"{field_path}.surface",
            category="invalid_surface",
        )
    company_name = _require_string(
        raw["company_name"],
        field_path=f"{field_path}.company_name",
        case_id=case_id,
        allow_empty=True,
    )
    job_title = _require_string(
        raw["job_title"],
        field_path=f"{field_path}.job_title",
        case_id=case_id,
    )
    location = _require_string(
        raw["location"],
        field_path=f"{field_path}.location",
        case_id=case_id,
        allow_empty=True,
    )
    job_description = _require_string(
        raw["job_description"],
        field_path=f"{field_path}.job_description",
        case_id=case_id,
    )
    expected_supported_findings = _require_string_list(
        raw["expected_supported_findings"],
        field_path=f"{field_path}.expected_supported_findings",
        case_id=case_id,
    )
    expected_skill_gaps = _require_string_list(
        raw["expected_skill_gaps"],
        field_path=f"{field_path}.expected_skill_gaps",
        case_id=case_id,
    )
    forbidden_claims = _require_string_list(
        raw["forbidden_claims"],
        field_path=f"{field_path}.forbidden_claims",
        case_id=case_id,
        require_non_empty_items=True,
    )
    learning_target_skills = _require_string_list(
        raw["learning_target_skills"],
        field_path=f"{field_path}.learning_target_skills",
        case_id=case_id,
        require_non_empty_items=True,
    )
    unsupported_material_claims = _require_string_list(
        raw["unsupported_material_claims"],
        field_path=f"{field_path}.unsupported_material_claims",
        case_id=case_id,
        require_non_empty_items=True,
    )
    groundedness = raw["human_groundedness"]
    if groundedness is not None and groundedness not in (0, 1, 2):
        raise _safe_error(
            case_id=case_id,
            field_path=f"{field_path}.human_groundedness",
            category="invalid_human_groundedness",
        )
    if groundedness is not None and isinstance(groundedness, bool):
        raise _safe_error(
            case_id=case_id,
            field_path=f"{field_path}.human_groundedness",
            category="invalid_human_groundedness",
        )
    offline_response = _parse_offline_response(
        raw["offline_response"],
        case_id=case_id,
        field_path=f"{field_path}.offline_response",
    )
    _scan_for_prohibited_content(raw, field_path=field_path, case_id=case_id)
    return EvaluationCase(
        case_id=case_id,
        surface=surface,
        company_name=company_name,
        job_title=job_title,
        location=location,
        job_description=job_description,
        expected_supported_findings=expected_supported_findings,
        expected_skill_gaps=expected_skill_gaps,
        forbidden_claims=forbidden_claims,
        learning_target_skills=learning_target_skills,
        unsupported_material_claims=unsupported_material_claims,
        human_groundedness=groundedness,
        offline_response=offline_response,
    )


def case_set_to_canonical_dict(case_set_data: dict[str, Any]) -> dict[str, Any]:
    return case_set_data


def compute_case_set_hash_from_data(data: dict[str, Any]) -> str:
    return sha256_hex(data)


def load_case_set_from_mapping(data: object) -> EvaluationCaseSet:
    if not isinstance(data, dict):
        raise _safe_error(
            case_id=None,
            field_path="$",
            category="expected_object",
        )
    _require_exact_keys(data, CASE_SET_TOP_LEVEL_KEYS, field_path="$")
    schema_version = _require_string(
        data["schema_version"],
        field_path="schema_version",
    )
    if schema_version != CASE_SET_SCHEMA_VERSION:
        raise _safe_error(
            case_id=None,
            field_path="schema_version",
            category="unsupported_schema_version",
        )
    cases_raw = data["cases"]
    if not isinstance(cases_raw, list):
        raise _safe_error(
            case_id=None,
            field_path="cases",
            category="expected_list",
        )
    if not cases_raw:
        raise _safe_error(
            case_id=None,
            field_path="cases",
            category="empty_case_set",
        )
    cases: list[EvaluationCase] = []
    seen_ids: set[str] = set()
    for index, raw_case in enumerate(cases_raw):
        case = _parse_case(raw_case, index=index)
        if case.case_id in seen_ids:
            raise _safe_error(
                case_id=case.case_id,
                field_path=f"cases[{index}].case_id",
                category="duplicate_case_id",
            )
        seen_ids.add(case.case_id)
        cases.append(case)
    case_set_hash = compute_case_set_hash_from_data(data)
    return EvaluationCaseSet(
        schema_version=schema_version,
        cases=tuple(cases),
        case_set_hash=case_set_hash,
    )


def load_case_set(path: Path) -> EvaluationCaseSet:
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CaseValidationError(
            f"field_path=$; category=invalid_json; detail={exc.__class__.__name__}"
        ) from exc
    return load_case_set_from_mapping(data)


def _parse_replay_response(raw: object, *, index: int) -> ReplayResponse:
    field_path = f"responses[{index}]"
    if not isinstance(raw, dict):
        raise _safe_error(
            case_id=None,
            field_path=field_path,
            category="expected_object",
        )
    provisional_id = _safe_case_id_for_error_context(
        raw.get("case_id"),
        field_path=f"{field_path}.case_id",
    )
    _require_exact_keys(
        raw,
        REPLAY_RESPONSE_KEYS,
        field_path=field_path,
        case_id=provisional_id,
    )
    case_id = _require_string(
        raw["case_id"],
        field_path=f"{field_path}.case_id",
    )
    envelope = _parse_offline_response(
        {
            "result_type": raw["result_type"],
            "payload": raw["payload"],
            "error_class": raw["error_class"],
        },
        case_id=case_id,
        field_path=field_path,
    )
    _scan_for_prohibited_content(raw, field_path=field_path, case_id=case_id)
    return ReplayResponse(
        case_id=case_id,
        result_type=envelope.result_type,
        payload=envelope.payload,
        error_class=envelope.error_class,
    )


def compute_replay_bundle_hash(data: dict[str, Any]) -> str:
    without_hash = {
        key: value for key, value in data.items() if key != "bundle_hash"
    }
    return sha256_hex(without_hash)


def load_replay_bundle_from_mapping(
    data: object,
    *,
    expected_case_ids: frozenset[str],
    expected_case_set_hash: str,
) -> ReplayBundle:
    if not isinstance(data, dict):
        raise _safe_error(
            case_id=None,
            field_path="$",
            category="expected_object",
        )
    _require_exact_keys(data, REPLAY_BUNDLE_TOP_LEVEL_KEYS, field_path="$")
    schema_version = _require_string(
        data["schema_version"],
        field_path="schema_version",
    )
    if schema_version != REPLAY_BUNDLE_SCHEMA_VERSION:
        raise _safe_error(
            case_id=None,
            field_path="schema_version",
            category="unsupported_schema_version",
        )
    case_set_hash = _require_string(
        data["case_set_hash"],
        field_path="case_set_hash",
    )
    if case_set_hash != expected_case_set_hash:
        raise _safe_error(
            case_id=None,
            field_path="case_set_hash",
            category="case_set_hash_mismatch",
        )
    responses_raw = data["responses"]
    if not isinstance(responses_raw, list):
        raise _safe_error(
            case_id=None,
            field_path="responses",
            category="expected_list",
        )
    responses: list[ReplayResponse] = []
    seen_ids: set[str] = set()
    for index, raw in enumerate(responses_raw):
        response = _parse_replay_response(raw, index=index)
        if response.case_id in seen_ids:
            raise _safe_error(
                case_id=response.case_id,
                field_path=f"responses[{index}].case_id",
                category="duplicate_case_id",
            )
        if response.case_id not in expected_case_ids:
            raise _safe_error(
                case_id=response.case_id,
                field_path=f"responses[{index}].case_id",
                category="unknown_case_id",
            )
        seen_ids.add(response.case_id)
        responses.append(response)
    missing = sorted(expected_case_ids - seen_ids)
    if missing:
        raise _safe_error(
            case_id=None,
            field_path="responses",
            category=f"missing_case_responses:{','.join(missing)}",
        )
    expected_bundle_hash = compute_replay_bundle_hash(data)
    provided_hash = _require_string(
        data["bundle_hash"],
        field_path="bundle_hash",
    )
    if provided_hash != expected_bundle_hash:
        raise _safe_error(
            case_id=None,
            field_path="bundle_hash",
            category="bundle_hash_mismatch",
        )
    return ReplayBundle(
        schema_version=schema_version,
        case_set_hash=case_set_hash,
        responses=tuple(responses),
        bundle_hash=provided_hash,
    )


def load_replay_bundle(
    path: Path,
    *,
    expected_case_ids: frozenset[str],
    expected_case_set_hash: str,
) -> ReplayBundle:
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CaseValidationError(
            f"field_path=$; category=invalid_json; detail={exc.__class__.__name__}"
        ) from exc
    return load_replay_bundle_from_mapping(
        data,
        expected_case_ids=expected_case_ids,
        expected_case_set_hash=expected_case_set_hash,
    )

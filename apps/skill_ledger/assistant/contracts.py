"""Sprint 121 Phase 1: pure typed contracts for bounded tool orchestration.

Code-defined, non-persistent, database-free. No handlers, no execution,
no Django model imports.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping


class AssistantContractError(ValueError):
    """Raised when a Sprint 121 contract fails structural validation."""


class PlannerOutcome(str, Enum):
    NO_TOOL = "NO_TOOL"
    TOOL_PLAN = "TOOL_PLAN"


class OwnershipPolicy(str, Enum):
    AUTHENTICATED_USER = "AUTHENTICATED_USER"
    USER_SCOPED_OBJECT = "USER_SCOPED_OBJECT"


class ToolCallStatus(str, Enum):
    """Distinguish success (including empty payload) from non-execution."""

    SUCCESS = "SUCCESS"
    SUCCESS_WITH_ZERO_RESULTS = "SUCCESS_WITH_ZERO_RESULTS"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    NOT_EXECUTED = "NOT_EXECUTED"


class AssistantOutcomeCode(str, Enum):
    """Safe high-level assistant outcome codes (Phase 1 structural only)."""

    OK = "OK"
    NO_TOOL = "NO_TOOL"
    EVIDENCE_INSUFFICIENT = "EVIDENCE_INSUFFICIENT"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


_MAX_PLAN_CALLS = 2


def _require_non_empty_str(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AssistantContractError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _freeze_jsonish(value: Any) -> Any:
    """Recursively freeze only deterministic JSON-compatible values."""
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise AssistantContractError(
                "non-finite float values are not allowed in contracts."
            )
        return value
    if isinstance(value, (bytes, bytearray)):
        raise AssistantContractError(
            "bytes values are not allowed in contracts."
        )
    if isinstance(value, (set, frozenset)):
        raise AssistantContractError(
            "set values are not allowed in contracts."
        )
    if callable(value):
        raise AssistantContractError(
            "callable values are not allowed in contracts."
        )
    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise AssistantContractError(
                    "mapping keys must be strings."
                )
            frozen[key] = _freeze_jsonish(item)
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_jsonish(item) for item in value)
    raise AssistantContractError(
        "arbitrary Python objects are not allowed in contracts."
    )


def _normalise_argument_names(names: object) -> frozenset[str]:
    if names is None:
        return frozenset()
    if isinstance(names, str):
        raise AssistantContractError(
            "allowed_argument_names must be a collection of strings, not a string."
        )
    try:
        sequence = list(names)
    except TypeError as exc:
        raise AssistantContractError(
            "allowed_argument_names must be an iterable of strings."
        ) from exc
    normalised: list[str] = []
    seen: set[str] = set()
    for item in sequence:
        if not isinstance(item, str) or not item.strip():
            raise AssistantContractError(
                "allowed_argument_names entries must be non-empty strings."
            )
        name = item.strip()
        if name in seen:
            raise AssistantContractError(
                f"duplicate allowed argument name: {name}."
            )
        seen.add(name)
        normalised.append(name)
    return frozenset(normalised)


def _normalise_source_ids(source_ids: object) -> tuple[int, ...]:
    if source_ids is None:
        return ()
    if isinstance(source_ids, (str, bytes)):
        raise AssistantContractError("source_ids must be a sequence of integers.")
    try:
        sequence = list(source_ids)
    except TypeError as exc:
        raise AssistantContractError(
            "source_ids must be a sequence of integers."
        ) from exc
    normalised: list[int] = []
    seen: set[int] = set()
    for item in sequence:
        if isinstance(item, bool) or not isinstance(item, int):
            raise AssistantContractError(
                "source_ids entries must be integers (SkillEntry PKs)."
            )
        if item <= 0:
            raise AssistantContractError(
                "source_ids entries must be positive integers."
            )
        if item in seen:
            raise AssistantContractError(
                f"duplicate source_id is not allowed: {item}."
            )
        seen.add(item)
        normalised.append(item)
    return tuple(normalised)


def _normalise_tools_used(tools_used: object) -> tuple[str, ...]:
    if tools_used is None:
        return ()
    if isinstance(tools_used, str):
        raise AssistantContractError("tools_used must be a sequence of tool names.")
    try:
        sequence = list(tools_used)
    except TypeError as exc:
        raise AssistantContractError(
            "tools_used must be a sequence of tool names."
        ) from exc
    normalised: list[str] = []
    for item in sequence:
        normalised.append(_require_non_empty_str(item, field_name="tools_used item"))
    return tuple(normalised)


@dataclass(frozen=True)
class ToolDefinition:
    """Immutable declarative tool policy metadata (no handler binding)."""

    name: str
    description: str
    read_only: bool
    maximum_calls: int
    allowed_argument_names: frozenset[str]
    result_size_limit: int
    ownership_policy: OwnershipPolicy

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "name",
            _require_non_empty_str(self.name, field_name="name"),
        )
        object.__setattr__(
            self,
            "description",
            _require_non_empty_str(self.description, field_name="description"),
        )
        if not isinstance(self.read_only, bool):
            raise AssistantContractError("read_only must be a bool.")
        if (
            isinstance(self.maximum_calls, bool)
            or not isinstance(self.maximum_calls, int)
            or self.maximum_calls < 1
        ):
            raise AssistantContractError("maximum_calls must be an integer >= 1.")
        if (
            isinstance(self.result_size_limit, bool)
            or not isinstance(self.result_size_limit, int)
            or self.result_size_limit <= 0
        ):
            raise AssistantContractError(
                "result_size_limit must be a positive integer."
            )
        if not isinstance(self.ownership_policy, OwnershipPolicy):
            raise AssistantContractError(
                "ownership_policy must be an OwnershipPolicy value."
            )
        object.__setattr__(
            self,
            "allowed_argument_names",
            _normalise_argument_names(self.allowed_argument_names),
        )


@dataclass(frozen=True)
class ToolCallRequest:
    """Fully specified independent tool call (no chaining fields)."""

    tool_name: str
    arguments: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "tool_name",
            _require_non_empty_str(self.tool_name, field_name="tool_name"),
        )
        if not isinstance(self.arguments, Mapping):
            raise AssistantContractError("arguments must be a mapping.")
        forbidden = {
            "user",
            "user_id",
            "depends_on",
            "previous_result",
            "result_reference",
            "runtime_expression",
            "callback",
            "callable",
            "function_path",
        }
        string_keys = [
            key for key in self.arguments.keys() if isinstance(key, str)
        ]
        overlap = forbidden.intersection(string_keys)
        if overlap:
            raise AssistantContractError(
                f"arguments contain forbidden keys: {sorted(overlap)}."
            )
        object.__setattr__(self, "arguments", _freeze_jsonish(self.arguments))


@dataclass(frozen=True)
class ToolCallResult:
    """Immutable tool execution outcome (not persisted)."""

    tool_name: str
    status: ToolCallStatus
    rejection_code: str | None
    payload: Mapping[str, Any] | None
    source_ids: tuple[int, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "tool_name",
            _require_non_empty_str(self.tool_name, field_name="tool_name"),
        )
        if not isinstance(self.status, ToolCallStatus):
            raise AssistantContractError("status must be a ToolCallStatus value.")
        if self.rejection_code is not None:
            object.__setattr__(
                self,
                "rejection_code",
                _require_non_empty_str(
                    self.rejection_code,
                    field_name="rejection_code",
                ),
            )
        success_statuses = {
            ToolCallStatus.SUCCESS,
            ToolCallStatus.SUCCESS_WITH_ZERO_RESULTS,
        }
        if self.status in success_statuses:
            if self.rejection_code is not None:
                raise AssistantContractError(
                    "successful ToolCallResult must not set rejection_code."
                )
        else:
            if self.rejection_code is None:
                raise AssistantContractError(
                    "non-success ToolCallResult requires rejection_code."
                )
            if self.payload is not None:
                raise AssistantContractError(
                    "non-success ToolCallResult must not include payload."
                )
        if self.payload is None:
            object.__setattr__(self, "payload", None)
        else:
            if not isinstance(self.payload, Mapping):
                raise AssistantContractError("payload must be a mapping or None.")
            object.__setattr__(self, "payload", _freeze_jsonish(self.payload))
        normalised_source_ids = _normalise_source_ids(self.source_ids)
        empty_source_statuses = {
            ToolCallStatus.REJECTED,
            ToolCallStatus.FAILED,
            ToolCallStatus.NOT_EXECUTED,
            ToolCallStatus.SUCCESS_WITH_ZERO_RESULTS,
        }
        if self.status in empty_source_statuses and normalised_source_ids:
            raise AssistantContractError(
                f"{self.status.value} ToolCallResult requires empty source_ids."
            )
        object.__setattr__(self, "source_ids", normalised_source_ids)

    @property
    def ok(self) -> bool:
        return self.status in {
            ToolCallStatus.SUCCESS,
            ToolCallStatus.SUCCESS_WITH_ZERO_RESULTS,
        }


@dataclass(frozen=True)
class PlannerDecision:
    """Structural planner decision: NO_TOOL or 1..2 independent calls."""

    outcome: PlannerOutcome
    calls: tuple[ToolCallRequest, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, PlannerOutcome):
            raise AssistantContractError("outcome must be a PlannerOutcome value.")
        if isinstance(self.calls, ToolCallRequest):
            raise AssistantContractError("calls must be a sequence of ToolCallRequest.")
        try:
            call_items = tuple(self.calls)
        except TypeError as exc:
            raise AssistantContractError(
                "calls must be a sequence of ToolCallRequest."
            ) from exc
        for item in call_items:
            if not isinstance(item, ToolCallRequest):
                raise AssistantContractError(
                    "calls entries must be ToolCallRequest instances."
                )
        object.__setattr__(self, "calls", call_items)
        if self.outcome is PlannerOutcome.NO_TOOL:
            if call_items:
                raise AssistantContractError(
                    "NO_TOOL PlannerDecision requires empty calls."
                )
            return
        if self.outcome is PlannerOutcome.TOOL_PLAN:
            if len(call_items) < 1 or len(call_items) > _MAX_PLAN_CALLS:
                raise AssistantContractError(
                    "TOOL_PLAN PlannerDecision requires 1 or 2 calls."
                )
            return
        raise AssistantContractError(f"unsupported PlannerOutcome: {self.outcome}.")


@dataclass(frozen=True)
class AssistantResult:
    """Safe structural assistant response contract (Phase 1 only)."""

    ok: bool
    code: AssistantOutcomeCode
    answer: str
    tools_used: tuple[str, ...]
    sources_used: tuple[int, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.ok, bool):
            raise AssistantContractError("ok must be a bool.")
        if not isinstance(self.code, AssistantOutcomeCode):
            raise AssistantContractError("code must be an AssistantOutcomeCode value.")
        if not isinstance(self.answer, str):
            raise AssistantContractError("answer must be a string.")
        object.__setattr__(
            self,
            "tools_used",
            _normalise_tools_used(self.tools_used),
        )
        object.__setattr__(
            self,
            "sources_used",
            _normalise_source_ids(self.sources_used),
        )

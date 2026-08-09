"""Sprint 121 Phase 2: generic bounded executor for Skill Ledger tools.

Atomic full-plan validation before any tool execution. No retries, no
replanning, no runtime-dependent second-call arguments.

Public execution boundary: execute_plan only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from apps.skill_ledger.embedding_provider import EmbeddingProvider

from .contracts import (
    OwnershipPolicy,
    PlannerDecision,
    PlannerOutcome,
    ToolCallRequest,
    ToolCallResult,
    ToolCallStatus,
    ToolDefinition,
)
from .registry import (
    MAX_PLAN_CALLS,
    QUERY_MAX_LENGTH,
    TOOL_NAME_SEARCH_SKILL_EVIDENCE,
    TOOL_REGISTRY,
    TOP_K_MAX,
    TOP_K_MIN,
    get_tool_definition,
)
from .tools import (
    TOOL_HANDLERS,
    ToolHandlerError,
    owned_skill_entry_exists,
)


class ExecutorCode(str, Enum):
    OK = "OK"
    NO_TOOL = "NO_TOOL"
    TOOL_NOT_ALLOWED = "TOOL_NOT_ALLOWED"
    INVALID_ARGUMENTS = "INVALID_ARGUMENTS"
    CALL_BUDGET_EXCEEDED = "CALL_BUDGET_EXCEEDED"
    DUPLICATE_TOOL_CALL = "DUPLICATE_TOOL_CALL"
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    OBJECT_UNAVAILABLE = "OBJECT_UNAVAILABLE"
    TOOL_UNAVAILABLE = "TOOL_UNAVAILABLE"
    TOOL_EXECUTION_FAILED = "TOOL_EXECUTION_FAILED"
    RESULT_SIZE_LIMIT_EXCEEDED = "RESULT_SIZE_LIMIT_EXCEEDED"


@dataclass(frozen=True)
class ExecutorBatchResult:
    """Deterministic batch outcome for one planner decision."""

    ok: bool
    code: ExecutorCode
    results: tuple[ToolCallResult, ...]

    @property
    def tools_executed(self) -> int:
        """Count of handler attempts represented in results (success or failure)."""
        return len(self.results)


@dataclass(frozen=True)
class _ValidatedPlanCall:
    request: ToolCallRequest
    definition: ToolDefinition


@dataclass(frozen=True)
class _ValidatedPlan:
    """Internal plan that passed atomic validation; not a public API."""

    user: Any
    embedding_provider: EmbeddingProvider | None
    calls: tuple[_ValidatedPlanCall, ...]


def _plain_jsonish(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain_jsonish(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain_jsonish(item) for item in value]
    return value


def measure_tool_call_result_size(result: ToolCallResult) -> int:
    """Byte size of canonical JSON for ToolCallResult public fields."""
    payload = {
        "tool_name": result.tool_name,
        "status": result.status.value,
        "rejection_code": result.rejection_code,
        "payload": None if result.payload is None else _plain_jsonish(result.payload),
        "source_ids": list(result.source_ids),
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return len(encoded)


def _reject(
    code: ExecutorCode,
    *,
    results: Sequence[ToolCallResult] = (),
) -> ExecutorBatchResult:
    return ExecutorBatchResult(ok=False, code=code, results=tuple(results))


def _ok(
    code: ExecutorCode,
    *,
    results: Sequence[ToolCallResult] = (),
) -> ExecutorBatchResult:
    return ExecutorBatchResult(ok=True, code=code, results=tuple(results))


def _failed_requested_tool(tool_name: str, code: ExecutorCode) -> ToolCallResult:
    return ToolCallResult(
        tool_name=tool_name,
        status=ToolCallStatus.FAILED,
        rejection_code=code.value,
        payload=None,
        source_ids=(),
    )


def _require_authenticated_user(user) -> ExecutorCode | None:
    if user is None or not getattr(user, "is_authenticated", False):
        return ExecutorCode.AUTHENTICATION_REQUIRED
    if getattr(user, "pk", None) is None:
        return ExecutorCode.AUTHENTICATION_REQUIRED
    return None


def _validate_search_semantics(arguments: Mapping[str, Any]) -> ExecutorCode | None:
    query = arguments.get("query")
    top_k = arguments.get("top_k")
    if not isinstance(query, str) or not query.strip():
        return ExecutorCode.INVALID_ARGUMENTS
    if len(query.strip()) > QUERY_MAX_LENGTH:
        return ExecutorCode.INVALID_ARGUMENTS
    if isinstance(top_k, bool) or not isinstance(top_k, int):
        return ExecutorCode.INVALID_ARGUMENTS
    if top_k < TOP_K_MIN or top_k > TOP_K_MAX:
        return ExecutorCode.INVALID_ARGUMENTS
    return None


def _validate_detail_semantics(arguments: Mapping[str, Any]) -> ExecutorCode | None:
    skill_entry_id = arguments.get("skill_entry_id")
    if isinstance(skill_entry_id, bool) or not isinstance(skill_entry_id, int):
        return ExecutorCode.INVALID_ARGUMENTS
    if skill_entry_id <= 0:
        return ExecutorCode.INVALID_ARGUMENTS
    return None


def _validate_plan(
    decision: PlannerDecision,
    *,
    user,
    embedding_provider: EmbeddingProvider | None = None,
) -> _ValidatedPlan | ExecutorBatchResult:
    """Atomically validate the entire plan. Internal only."""
    if not isinstance(decision, PlannerDecision):
        return _reject(ExecutorCode.INVALID_ARGUMENTS)

    auth_error = _require_authenticated_user(user)
    if auth_error is not None:
        return _reject(auth_error)

    if decision.outcome is PlannerOutcome.NO_TOOL:
        if decision.calls:
            return _reject(ExecutorCode.INVALID_ARGUMENTS)
        return _ValidatedPlan(user=user, embedding_provider=embedding_provider, calls=())

    if decision.outcome is not PlannerOutcome.TOOL_PLAN:
        return _reject(ExecutorCode.INVALID_ARGUMENTS)

    calls = decision.calls
    if len(calls) < 1 or len(calls) > MAX_PLAN_CALLS:
        return _reject(ExecutorCode.CALL_BUDGET_EXCEEDED)

    seen_tools: set[str] = set()
    validated_calls: list[_ValidatedPlanCall] = []

    for request in calls:
        if not isinstance(request, ToolCallRequest):
            return _reject(ExecutorCode.INVALID_ARGUMENTS)

        definition = get_tool_definition(request.tool_name)
        if definition is None or request.tool_name not in TOOL_HANDLERS:
            return _reject(ExecutorCode.TOOL_NOT_ALLOWED)
        if definition.name not in TOOL_REGISTRY:
            return _reject(ExecutorCode.TOOL_NOT_ALLOWED)
        if not definition.read_only:
            return _reject(ExecutorCode.TOOL_NOT_ALLOWED)

        if request.tool_name in seen_tools:
            return _reject(ExecutorCode.DUPLICATE_TOOL_CALL)
        seen_tools.add(request.tool_name)

        tool_count = sum(1 for item in calls if item.tool_name == request.tool_name)
        if tool_count > definition.maximum_calls:
            return _reject(ExecutorCode.DUPLICATE_TOOL_CALL)

        argument_keys = frozenset(request.arguments.keys())
        if argument_keys != definition.allowed_argument_names:
            return _reject(ExecutorCode.INVALID_ARGUMENTS)

        if request.tool_name == TOOL_NAME_SEARCH_SKILL_EVIDENCE:
            semantic_error = _validate_search_semantics(request.arguments)
            if semantic_error is not None:
                return _reject(semantic_error)
            if embedding_provider is None:
                return _reject(ExecutorCode.TOOL_UNAVAILABLE)
        elif request.tool_name == "get_skill_entry_detail":
            semantic_error = _validate_detail_semantics(request.arguments)
            if semantic_error is not None:
                return _reject(semantic_error)
            if definition.ownership_policy is OwnershipPolicy.USER_SCOPED_OBJECT:
                skill_entry_id = request.arguments["skill_entry_id"]
                try:
                    exists = owned_skill_entry_exists(
                        user=user,
                        skill_entry_id=skill_entry_id,
                    )
                except ToolHandlerError as exc:
                    code = (
                        ExecutorCode(exc.code)
                        if exc.code in ExecutorCode.__members__
                        else ExecutorCode.INVALID_ARGUMENTS
                    )
                    return _reject(code)
                if not exists:
                    return _reject(ExecutorCode.OBJECT_UNAVAILABLE)
        elif request.tool_name == "get_skill_ledger_summary":
            if argument_keys:
                return _reject(ExecutorCode.INVALID_ARGUMENTS)

        validated_calls.append(
            _ValidatedPlanCall(request=request, definition=definition)
        )

    return _ValidatedPlan(
        user=user,
        embedding_provider=embedding_provider,
        calls=tuple(validated_calls),
    )


def _execute_validated_plan(validated: _ValidatedPlan) -> ExecutorBatchResult:
    """Execute an internally validated plan in declared order. Internal only."""
    if not validated.calls:
        return _ok(ExecutorCode.NO_TOOL, results=())

    results: list[ToolCallResult] = []
    for plan_call in validated.calls:
        requested_name = plan_call.request.tool_name
        handler = TOOL_HANDLERS.get(requested_name)
        if handler is None:
            return _reject(ExecutorCode.TOOL_NOT_ALLOWED, results=results)
        try:
            result = handler(
                plan_call.request,
                user=validated.user,
                embedding_provider=validated.embedding_provider,
            )
        except ToolHandlerError as exc:
            code = (
                ExecutorCode(exc.code)
                if exc.code in ExecutorCode.__members__
                else ExecutorCode.TOOL_EXECUTION_FAILED
            )
            failed = ToolCallResult(
                tool_name=requested_name,
                status=ToolCallStatus.FAILED,
                rejection_code=code.value,
                payload=None,
                source_ids=(),
            )
            results.append(failed)
            return _reject(code, results=results)
        except Exception:
            failed = _failed_requested_tool(
                requested_name,
                ExecutorCode.TOOL_EXECUTION_FAILED,
            )
            results.append(failed)
            return _reject(ExecutorCode.TOOL_EXECUTION_FAILED, results=results)

        if not isinstance(result, ToolCallResult):
            failed = _failed_requested_tool(
                requested_name,
                ExecutorCode.TOOL_EXECUTION_FAILED,
            )
            results.append(failed)
            return _reject(ExecutorCode.TOOL_EXECUTION_FAILED, results=results)

        if result.tool_name != requested_name:
            failed = _failed_requested_tool(
                requested_name,
                ExecutorCode.TOOL_EXECUTION_FAILED,
            )
            results.append(failed)
            return _reject(ExecutorCode.TOOL_EXECUTION_FAILED, results=results)

        size = measure_tool_call_result_size(result)
        if size > plan_call.definition.result_size_limit:
            oversized = _failed_requested_tool(
                requested_name,
                ExecutorCode.RESULT_SIZE_LIMIT_EXCEEDED,
            )
            results.append(oversized)
            return _reject(ExecutorCode.RESULT_SIZE_LIMIT_EXCEEDED, results=results)

        if not result.ok:
            results.append(result)
            code = (
                ExecutorCode(result.rejection_code)
                if result.rejection_code in ExecutorCode.__members__
                else ExecutorCode.TOOL_EXECUTION_FAILED
            )
            return _reject(code, results=results)

        results.append(result)

    return _ok(ExecutorCode.OK, results=results)


def execute_plan(
    decision: PlannerDecision,
    *,
    user,
    embedding_provider: EmbeddingProvider | None = None,
) -> ExecutorBatchResult:
    """Public boundary: validate the full plan, then execute internally."""
    validated = _validate_plan(
        decision,
        user=user,
        embedding_provider=embedding_provider,
    )
    if isinstance(validated, ExecutorBatchResult):
        return validated
    return _execute_validated_plan(validated)

"""Sprint 121 Phase 3: bounded Skill Ledger assistant orchestration.

One planner call -> Phase 2 execute_plan -> optional one synthesis call.
Service/evaluation only. No routes, persistence, or live providers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence

from apps.ai_agents.provider_contracts import ExplanationProvider
from apps.skill_ledger.embedding_provider import EmbeddingProvider

from .contracts import (
    AssistantOutcomeCode,
    AssistantResult,
    PlannerDecision,
    PlannerOutcome,
    ToolDefinition,
)
from .executor import ExecutorCode, execute_plan
from .registry import TOOL_REGISTRY
from .synthesis_validation import (
    MAX_ANSWER_LENGTH,
    SynthesisValidationError,
    build_synthesis_payload,
    has_search_zero_evidence,
    successful_tool_names,
    validate_synthesis_output,
)

PLANNER_CALLS_MAX = 1
SYNTHESIS_CALLS_MAX = 1

_SAFE_NO_TOOL_ANSWER = (
    "No Skill Ledger tool was selected for this request."
)
_SAFE_EVIDENCE_INSUFFICIENT_ANSWER = (
    "No usable Skill Ledger evidence matched the request."
)
_SAFE_REJECTED_ANSWER = (
    "The Skill Ledger assistant request was safely rejected."
)
_SAFE_FAILED_ANSWER = (
    "The Skill Ledger assistant request failed closed."
)

_POLICY_REJECTION_CODES = frozenset(
    {
        ExecutorCode.TOOL_NOT_ALLOWED,
        ExecutorCode.INVALID_ARGUMENTS,
        ExecutorCode.CALL_BUDGET_EXCEEDED,
        ExecutorCode.DUPLICATE_TOOL_CALL,
        ExecutorCode.AUTHENTICATION_REQUIRED,
        ExecutorCode.OBJECT_UNAVAILABLE,
    }
)

_EXECUTION_FAILURE_CODES = frozenset(
    {
        ExecutorCode.TOOL_UNAVAILABLE,
        ExecutorCode.TOOL_EXECUTION_FAILED,
        ExecutorCode.RESULT_SIZE_LIMIT_EXCEEDED,
    }
)


class PlannerProvider(Protocol):
    """Domain-specific planner: request + closed tool schemas -> PlannerDecision."""

    def plan(
        self,
        *,
        request_text: str,
        tool_definitions: Sequence[Mapping[str, Any]],
    ) -> PlannerDecision: ...


# Synthesis uses the existing ExplanationProvider protocol (dict in, dict out).
# Distinct from PlannerProvider; do not conflate planning with synthesis.


@dataclass(frozen=True)
class AssistantOrchestrationResult:
    """AssistantResult plus deterministic orchestration telemetry for tests."""

    result: AssistantResult
    planner_calls: int
    synthesis_calls: int
    tools_executed: int


def _tool_definition_schemas() -> tuple[dict[str, Any], ...]:
    schemas: list[dict[str, Any]] = []
    for name in (
        "search_skill_evidence",
        "get_skill_ledger_summary",
        "get_skill_entry_detail",
    ):
        definition: ToolDefinition = TOOL_REGISTRY[name]
        schemas.append(
            {
                "name": definition.name,
                "description": definition.description,
                "read_only": definition.read_only,
                "maximum_calls": definition.maximum_calls,
                "allowed_argument_names": sorted(definition.allowed_argument_names),
                "result_size_limit": definition.result_size_limit,
                "ownership_policy": definition.ownership_policy.value,
            }
        )
    return tuple(schemas)


def _assistant(
    *,
    ok: bool,
    code: AssistantOutcomeCode,
    answer: str,
    tools_used: tuple[str, ...] = (),
    sources_used: tuple[int, ...] = (),
    planner_calls: int,
    synthesis_calls: int,
    tools_executed: int,
) -> AssistantOrchestrationResult:
    return AssistantOrchestrationResult(
        result=AssistantResult(
            ok=ok,
            code=code,
            answer=answer,
            tools_used=tools_used,
            sources_used=sources_used,
        ),
        planner_calls=planner_calls,
        synthesis_calls=synthesis_calls,
        tools_executed=tools_executed,
    )


def run_skill_ledger_assistant(
    *,
    request_text: str,
    user,
    planner: PlannerProvider | None,
    synthesis_provider: ExplanationProvider | None,
    embedding_provider: EmbeddingProvider | None = None,
) -> AssistantOrchestrationResult:
    """Bounded one-shot planner + optional synthesis orchestration."""
    # Authenticated-only service boundary: before planner or executor.
    if (
        user is None
        or not getattr(user, "is_authenticated", False)
        or getattr(user, "pk", None) is None
    ):
        return _assistant(
            ok=False,
            code=AssistantOutcomeCode.REJECTED,
            answer=_SAFE_REJECTED_ANSWER,
            planner_calls=0,
            synthesis_calls=0,
            tools_executed=0,
        )

    if not isinstance(request_text, str) or not request_text.strip():
        return _assistant(
            ok=False,
            code=AssistantOutcomeCode.REJECTED,
            answer=_SAFE_REJECTED_ANSWER,
            planner_calls=0,
            synthesis_calls=0,
            tools_executed=0,
        )

    if planner is None:
        return _assistant(
            ok=False,
            code=AssistantOutcomeCode.FAILED,
            answer=_SAFE_FAILED_ANSWER,
            planner_calls=0,
            synthesis_calls=0,
            tools_executed=0,
        )

    try:
        decision = planner.plan(
            request_text=request_text.strip(),
            tool_definitions=_tool_definition_schemas(),
        )
    except Exception:
        return _assistant(
            ok=False,
            code=AssistantOutcomeCode.FAILED,
            answer=_SAFE_FAILED_ANSWER,
            planner_calls=1,
            synthesis_calls=0,
            tools_executed=0,
        )

    if not isinstance(decision, PlannerDecision):
        return _assistant(
            ok=False,
            code=AssistantOutcomeCode.FAILED,
            answer=_SAFE_FAILED_ANSWER,
            planner_calls=1,
            synthesis_calls=0,
            tools_executed=0,
        )

    if decision.outcome is PlannerOutcome.NO_TOOL:
        return _assistant(
            ok=True,
            code=AssistantOutcomeCode.NO_TOOL,
            answer=_SAFE_NO_TOOL_ANSWER,
            tools_used=(),
            sources_used=(),
            planner_calls=1,
            synthesis_calls=0,
            tools_executed=0,
        )

    try:
        batch = execute_plan(
            decision,
            user=user,
            embedding_provider=embedding_provider,
        )
    except Exception:
        return _assistant(
            ok=False,
            code=AssistantOutcomeCode.FAILED,
            answer=_SAFE_FAILED_ANSWER,
            tools_used=(),
            sources_used=(),
            planner_calls=1,
            synthesis_calls=0,
            tools_executed=0,
        )

    if not batch.ok:
        if (
            batch.tools_executed == 0
            and batch.code in _POLICY_REJECTION_CODES
        ):
            outcome = AssistantOutcomeCode.REJECTED
            answer = _SAFE_REJECTED_ANSWER
        else:
            outcome = AssistantOutcomeCode.FAILED
            answer = _SAFE_FAILED_ANSWER
        return _assistant(
            ok=False,
            code=outcome,
            answer=answer,
            tools_used=(),
            sources_used=(),
            planner_calls=1,
            synthesis_calls=0,
            tools_executed=batch.tools_executed,
        )

    if has_search_zero_evidence(batch.results):
        return _assistant(
            ok=True,
            code=AssistantOutcomeCode.EVIDENCE_INSUFFICIENT,
            answer=_SAFE_EVIDENCE_INSUFFICIENT_ANSWER,
            tools_used=successful_tool_names(batch.results),
            sources_used=(),
            planner_calls=1,
            synthesis_calls=0,
            tools_executed=batch.tools_executed,
        )

    if synthesis_provider is None:
        return _assistant(
            ok=False,
            code=AssistantOutcomeCode.FAILED,
            answer=_SAFE_FAILED_ANSWER,
            tools_used=(),
            sources_used=(),
            planner_calls=1,
            synthesis_calls=0,
            tools_executed=batch.tools_executed,
        )

    try:
        payload = build_synthesis_payload(
            request_text=request_text.strip(),
            results=batch.results,
        )
    except SynthesisValidationError:
        return _assistant(
            ok=False,
            code=AssistantOutcomeCode.FAILED,
            answer=_SAFE_FAILED_ANSWER,
            tools_used=(),
            sources_used=(),
            planner_calls=1,
            synthesis_calls=0,
            tools_executed=batch.tools_executed,
        )
    except Exception:
        return _assistant(
            ok=False,
            code=AssistantOutcomeCode.FAILED,
            answer=_SAFE_FAILED_ANSWER,
            tools_used=(),
            sources_used=(),
            planner_calls=1,
            synthesis_calls=0,
            tools_executed=batch.tools_executed,
        )

    try:
        raw_output = synthesis_provider(payload)
    except Exception:
        return _assistant(
            ok=False,
            code=AssistantOutcomeCode.FAILED,
            answer=_SAFE_FAILED_ANSWER,
            tools_used=(),
            sources_used=(),
            planner_calls=1,
            synthesis_calls=1,
            tools_executed=batch.tools_executed,
        )

    try:
        validated = validate_synthesis_output(
            raw_output,
            results=batch.results,
        )
    except SynthesisValidationError:
        return _assistant(
            ok=False,
            code=AssistantOutcomeCode.FAILED,
            answer=_SAFE_FAILED_ANSWER,
            tools_used=(),
            sources_used=(),
            planner_calls=1,
            synthesis_calls=1,
            tools_executed=batch.tools_executed,
        )

    return _assistant(
        ok=True,
        code=AssistantOutcomeCode.OK,
        answer=validated.answer,
        tools_used=validated.tools_used,
        sources_used=validated.sources_used,
        planner_calls=1,
        synthesis_calls=1,
        tools_executed=batch.tools_executed,
    )


__all__ = (
    "AssistantOrchestrationResult",
    "MAX_ANSWER_LENGTH",
    "PLANNER_CALLS_MAX",
    "PlannerProvider",
    "SYNTHESIS_CALLS_MAX",
    "run_skill_ledger_assistant",
)

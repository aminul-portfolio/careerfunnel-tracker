"""Sprint 121 bounded tool-calling assistant package (Phase 1 contracts/registry).

Import-safe: no DB queries, providers, network, or dynamic registration.
"""

from .contracts import (
    AssistantContractError,
    AssistantOutcomeCode,
    AssistantResult,
    OwnershipPolicy,
    PlannerDecision,
    PlannerOutcome,
    ToolCallRequest,
    ToolCallResult,
    ToolCallStatus,
    ToolDefinition,
)
from .registry import (
    DETAIL_RESULT_SIZE_LIMIT,
    MAX_CALLS_PER_TOOL,
    MAX_PLAN_CALLS,
    QUERY_MAX_LENGTH,
    REGISTERED_TOOL_NAMES,
    SEARCH_RESULT_SIZE_LIMIT,
    SUMMARY_RESULT_SIZE_LIMIT,
    TOOL_NAME_GET_SKILL_ENTRY_DETAIL,
    TOOL_NAME_GET_SKILL_LEDGER_SUMMARY,
    TOOL_NAME_SEARCH_SKILL_EVIDENCE,
    TOOL_REGISTRY,
    TOP_K_MAX,
    TOP_K_MIN,
    get_tool_definition,
    registered_tool_count,
)

__all__ = (
    "AssistantContractError",
    "AssistantOutcomeCode",
    "AssistantResult",
    "DETAIL_RESULT_SIZE_LIMIT",
    "MAX_CALLS_PER_TOOL",
    "MAX_PLAN_CALLS",
    "OwnershipPolicy",
    "PlannerDecision",
    "PlannerOutcome",
    "QUERY_MAX_LENGTH",
    "REGISTERED_TOOL_NAMES",
    "SEARCH_RESULT_SIZE_LIMIT",
    "SUMMARY_RESULT_SIZE_LIMIT",
    "TOOL_NAME_GET_SKILL_ENTRY_DETAIL",
    "TOOL_NAME_GET_SKILL_LEDGER_SUMMARY",
    "TOOL_NAME_SEARCH_SKILL_EVIDENCE",
    "TOOL_REGISTRY",
    "TOP_K_MAX",
    "TOP_K_MIN",
    "ToolCallRequest",
    "ToolCallResult",
    "ToolCallStatus",
    "ToolDefinition",
    "get_tool_definition",
    "registered_tool_count",
)

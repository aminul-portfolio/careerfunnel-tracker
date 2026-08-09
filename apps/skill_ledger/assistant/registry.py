"""Sprint 121 Phase 1: closed static Skill Ledger tool registry.

Exactly three read-only tools. No dynamic discovery, no handlers, no DB.
"""

from __future__ import annotations

from types import MappingProxyType

from .contracts import OwnershipPolicy, ToolDefinition

# Locked Sprint 121 plan/tool limits (executor enforces in Phase 2).
MAX_PLAN_CALLS = 2
MAX_CALLS_PER_TOOL = 1

# search_skill_evidence semantic limits (Phase 2 validation constants).
QUERY_MAX_LENGTH = 1000
TOP_K_MIN = 1
TOP_K_MAX = 5

TOOL_NAME_SEARCH_SKILL_EVIDENCE = "search_skill_evidence"
TOOL_NAME_GET_SKILL_LEDGER_SUMMARY = "get_skill_ledger_summary"
TOOL_NAME_GET_SKILL_ENTRY_DETAIL = "get_skill_entry_detail"

SEARCH_RESULT_SIZE_LIMIT = 16384
SUMMARY_RESULT_SIZE_LIMIT = 4096
DETAIL_RESULT_SIZE_LIMIT = 8192

_FORBIDDEN_ARGUMENT_NAMES = frozenset(
    {
        "user",
        "user_id",
        "email",
        "command",
        "code",
        "sql",
        "path",
        "url_to_fetch",
    }
)


def _build_registry() -> MappingProxyType[str, ToolDefinition]:
    definitions = (
        ToolDefinition(
            name=TOOL_NAME_SEARCH_SKILL_EVIDENCE,
            description=(
                "Search the authenticated user's Skill Ledger evidence using "
                "ownership-scoped offline retrieval. Returns ranked evidence "
                "items only; does not regenerate embeddings or call live providers."
            ),
            read_only=True,
            maximum_calls=MAX_CALLS_PER_TOOL,
            allowed_argument_names=frozenset({"query", "top_k"}),
            result_size_limit=SEARCH_RESULT_SIZE_LIMIT,
            ownership_policy=OwnershipPolicy.AUTHENTICATED_USER,
        ),
        ToolDefinition(
            name=TOOL_NAME_GET_SKILL_LEDGER_SUMMARY,
            description=(
                "Return an ownership-scoped Skill Ledger evidence summary for "
                "the authenticated user. No filter or field-selector arguments."
            ),
            read_only=True,
            maximum_calls=MAX_CALLS_PER_TOOL,
            allowed_argument_names=frozenset(),
            result_size_limit=SUMMARY_RESULT_SIZE_LIMIT,
            ownership_policy=OwnershipPolicy.AUTHENTICATED_USER,
        ),
        ToolDefinition(
            name=TOOL_NAME_GET_SKILL_ENTRY_DETAIL,
            description=(
                "Return an allowlisted projection of one user-owned SkillEntry. "
                "notes are excluded. Missing and non-owned IDs share one opaque "
                "rejection contract."
            ),
            read_only=True,
            maximum_calls=MAX_CALLS_PER_TOOL,
            allowed_argument_names=frozenset({"skill_entry_id"}),
            result_size_limit=DETAIL_RESULT_SIZE_LIMIT,
            ownership_policy=OwnershipPolicy.USER_SCOPED_OBJECT,
        ),
    )
    mapping: dict[str, ToolDefinition] = {}
    for definition in definitions:
        if definition.name in mapping:
            raise RuntimeError(f"duplicate tool registry name: {definition.name}")
        overlap = definition.allowed_argument_names & _FORBIDDEN_ARGUMENT_NAMES
        if overlap:
            raise RuntimeError(
                f"tool {definition.name} allows forbidden arguments: {sorted(overlap)}"
            )
        if not definition.read_only:
            raise RuntimeError(f"tool {definition.name} must be read_only.")
        if definition.maximum_calls != MAX_CALLS_PER_TOOL:
            raise RuntimeError(
                f"tool {definition.name} maximum_calls must be {MAX_CALLS_PER_TOOL}."
            )
        mapping[definition.name] = definition
    if len(mapping) != 3:
        raise RuntimeError("TOOL_REGISTRY must contain exactly three tools.")
    return MappingProxyType(mapping)


TOOL_REGISTRY: MappingProxyType[str, ToolDefinition] = _build_registry()

REGISTERED_TOOL_NAMES: tuple[str, ...] = (
    TOOL_NAME_SEARCH_SKILL_EVIDENCE,
    TOOL_NAME_GET_SKILL_LEDGER_SUMMARY,
    TOOL_NAME_GET_SKILL_ENTRY_DETAIL,
)


def get_tool_definition(tool_name: str) -> ToolDefinition | None:
    """Return a registered ToolDefinition, or None for unknown tools."""
    if not isinstance(tool_name, str):
        return None
    return TOOL_REGISTRY.get(tool_name)


def registered_tool_count() -> int:
    """Return the closed registry size (always 3 in Sprint 121)."""
    return len(TOOL_REGISTRY)

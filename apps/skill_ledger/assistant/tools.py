"""Sprint 121 Phase 2: static read-only Skill Ledger tool handlers.

No dynamic discovery. Handlers bind only the three registry tool names.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Callable, Mapping

from apps.skill_ledger.embedding_provider import EmbeddingProvider
from apps.skill_ledger.models import SkillEntry
from apps.skill_ledger.rag_retrieval import retrieve_owned_skill_evidence

from .contracts import ToolCallRequest, ToolCallResult, ToolCallStatus
from .registry import (
    QUERY_MAX_LENGTH,
    TOOL_NAME_GET_SKILL_ENTRY_DETAIL,
    TOOL_NAME_GET_SKILL_LEDGER_SUMMARY,
    TOOL_NAME_SEARCH_SKILL_EVIDENCE,
    TOP_K_MAX,
    TOP_K_MIN,
)

ToolHandler = Callable[..., ToolCallResult]


class ToolHandlerError(ValueError):
    """Raised for semantic argument failures inside a tool handler."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


def _require_authenticated_user(user) -> None:
    if user is None or not getattr(user, "is_authenticated", False):
        raise ToolHandlerError(
            "authenticated user is required.",
            code="AUTHENTICATION_REQUIRED",
        )
    if getattr(user, "pk", None) is None:
        raise ToolHandlerError(
            "authenticated user is required.",
            code="AUTHENTICATION_REQUIRED",
        )


def _validate_search_arguments(arguments: Mapping[str, Any]) -> tuple[str, int]:
    query = arguments.get("query")
    top_k = arguments.get("top_k")
    if not isinstance(query, str) or not query.strip():
        raise ToolHandlerError(
            "query must be a non-empty string.",
            code="INVALID_ARGUMENTS",
        )
    cleaned_query = query.strip()
    if len(cleaned_query) > QUERY_MAX_LENGTH:
        raise ToolHandlerError(
            "query exceeds maximum length.",
            code="INVALID_ARGUMENTS",
        )
    if isinstance(top_k, bool) or not isinstance(top_k, int):
        raise ToolHandlerError(
            "top_k must be an integer.",
            code="INVALID_ARGUMENTS",
        )
    if top_k < TOP_K_MIN or top_k > TOP_K_MAX:
        raise ToolHandlerError(
            "top_k must be between 1 and 5 inclusive.",
            code="INVALID_ARGUMENTS",
        )
    return cleaned_query, top_k


def _validate_detail_skill_entry_id(arguments: Mapping[str, Any]) -> int:
    skill_entry_id = arguments.get("skill_entry_id")
    if isinstance(skill_entry_id, bool) or not isinstance(skill_entry_id, int):
        raise ToolHandlerError(
            "skill_entry_id must be an integer.",
            code="INVALID_ARGUMENTS",
        )
    if skill_entry_id <= 0:
        raise ToolHandlerError(
            "skill_entry_id must be a positive integer.",
            code="INVALID_ARGUMENTS",
        )
    return skill_entry_id


def search_skill_evidence(
    request: ToolCallRequest,
    *,
    user,
    embedding_provider: EmbeddingProvider | None,
) -> ToolCallResult:
    """Ownership-scoped offline retrieval; never regenerates embeddings."""
    _require_authenticated_user(user)
    if embedding_provider is None:
        raise ToolHandlerError(
            "embedding provider is required for search_skill_evidence.",
            code="TOOL_UNAVAILABLE",
        )
    query, top_k = _validate_search_arguments(request.arguments)
    retrieved = retrieve_owned_skill_evidence(
        user,
        query,
        provider=embedding_provider,
    )
    selected = retrieved[:top_k]
    items = [
        {
            "skill_entry_id": item.skill_entry_id,
            "skill_name": item.skill_name,
            "category": item.category,
            "evidence_level": item.evidence_level,
            "sprint_reference": item.sprint_reference,
            "similarity_score": item.similarity_score,
        }
        for item in selected
    ]
    source_ids = tuple(item.skill_entry_id for item in selected)
    if not items:
        return ToolCallResult(
            tool_name=TOOL_NAME_SEARCH_SKILL_EVIDENCE,
            status=ToolCallStatus.SUCCESS_WITH_ZERO_RESULTS,
            rejection_code=None,
            payload={"items": []},
            source_ids=(),
        )
    return ToolCallResult(
        tool_name=TOOL_NAME_SEARCH_SKILL_EVIDENCE,
        status=ToolCallStatus.SUCCESS,
        rejection_code=None,
        payload={"items": items},
        source_ids=source_ids,
    )


def get_skill_ledger_summary(
    request: ToolCallRequest,
    *,
    user,
    embedding_provider: EmbeddingProvider | None = None,
) -> ToolCallResult:
    """Deterministic owned-only aggregate summary (no model instances)."""
    del embedding_provider  # unused; signature kept uniform for the handler map
    _require_authenticated_user(user)
    if dict(request.arguments):
        raise ToolHandlerError(
            "get_skill_ledger_summary accepts no arguments.",
            code="INVALID_ARGUMENTS",
        )

    owned = SkillEntry.objects.for_user(user)
    evidence_level_counts = {
        value: 0 for value, _label in SkillEntry.EvidenceLevel.choices
    }
    category_counts = {value: 0 for value, _label in SkillEntry.Category.choices}

    for evidence_level, category in owned.values_list("evidence_level", "category"):
        if evidence_level in evidence_level_counts:
            evidence_level_counts[evidence_level] += 1
        if category in category_counts:
            category_counts[category] += 1

    # Deterministic key order via sorted keys when serialised with sort_keys.
    payload = {
        "total_entries": owned.count(),
        "evidence_level_counts": dict(
            sorted(evidence_level_counts.items(), key=lambda item: item[0])
        ),
        "category_counts": dict(sorted(category_counts.items(), key=lambda item: item[0])),
    }
    return ToolCallResult(
        tool_name=TOOL_NAME_GET_SKILL_LEDGER_SUMMARY,
        status=ToolCallStatus.SUCCESS,
        rejection_code=None,
        payload=payload,
        source_ids=(),
    )


def get_skill_entry_detail(
    request: ToolCallRequest,
    *,
    user,
    embedding_provider: EmbeddingProvider | None = None,
) -> ToolCallResult:
    """Fresh ownership-scoped PK lookup; notes excluded; no URL fetch."""
    del embedding_provider
    _require_authenticated_user(user)
    skill_entry_id = _validate_detail_skill_entry_id(request.arguments)
    entry = (
        SkillEntry.objects.for_user(user)
        .filter(pk=skill_entry_id)
        .first()
    )
    if entry is None:
        return ToolCallResult(
            tool_name=TOOL_NAME_GET_SKILL_ENTRY_DETAIL,
            status=ToolCallStatus.REJECTED,
            rejection_code="OBJECT_UNAVAILABLE",
            payload=None,
            source_ids=(),
        )
    payload = {
        "skill_entry_id": entry.pk,
        "skill_name": entry.skill_name,
        "category": entry.category,
        "evidence_level": entry.evidence_level,
        "sprint_reference": entry.sprint_reference,
        "project_link": entry.project_link,
    }
    return ToolCallResult(
        tool_name=TOOL_NAME_GET_SKILL_ENTRY_DETAIL,
        status=ToolCallStatus.SUCCESS,
        rejection_code=None,
        payload=payload,
        source_ids=(entry.pk,),
    )


def owned_skill_entry_exists(*, user, skill_entry_id: int) -> bool:
    """Pre-authorisation existence check only; never returns a model instance."""
    _require_authenticated_user(user)
    if isinstance(skill_entry_id, bool) or not isinstance(skill_entry_id, int):
        raise ToolHandlerError(
            "skill_entry_id must be an integer.",
            code="INVALID_ARGUMENTS",
        )
    if skill_entry_id <= 0:
        raise ToolHandlerError(
            "skill_entry_id must be a positive integer.",
            code="INVALID_ARGUMENTS",
        )
    return SkillEntry.objects.for_user(user).filter(pk=skill_entry_id).exists()


TOOL_HANDLERS: MappingProxyType[str, ToolHandler] = MappingProxyType(
    {
        TOOL_NAME_SEARCH_SKILL_EVIDENCE: search_skill_evidence,
        TOOL_NAME_GET_SKILL_LEDGER_SUMMARY: get_skill_ledger_summary,
        TOOL_NAME_GET_SKILL_ENTRY_DETAIL: get_skill_entry_detail,
    }
)

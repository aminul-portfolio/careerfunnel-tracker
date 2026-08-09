"""Sprint 122 Phase 1: privacy-safe in-process assistant observation primitives.

Engineering observability only. No persistence, network, providers, or content.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from .contracts import AssistantOutcomeCode
from .registry import TOOL_REGISTRY

OBSERVATION_SCHEMA_VERSION = 1

_ALLOWED_TOOL_NAMES = frozenset(TOOL_REGISTRY.keys())


class ObservationContractError(ValueError):
    """Raised when an observation contract fails structural validation."""


class CollectionStatus(str, Enum):
    DISABLED = "DISABLED"
    RECORDED = "RECORDED"
    COLLECTION_FAILED = "COLLECTION_FAILED"


@dataclass(frozen=True)
class AssistantObservation:
    """Closed non-content observation of one assistant orchestration result."""

    schema_version: int
    outcome_code: AssistantOutcomeCode
    planner_calls: int
    tools_executed: int
    synthesis_calls: int
    tools_used: tuple[str, ...]
    source_count: int
    answer_length: int

    def __post_init__(self) -> None:
        if self.schema_version != OBSERVATION_SCHEMA_VERSION:
            raise ObservationContractError(
                f"schema_version must be {OBSERVATION_SCHEMA_VERSION}."
            )
        if not isinstance(self.outcome_code, AssistantOutcomeCode):
            raise ObservationContractError(
                "outcome_code must be an AssistantOutcomeCode value."
            )
        for field_name in (
            "planner_calls",
            "tools_executed",
            "synthesis_calls",
            "source_count",
            "answer_length",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise ObservationContractError(f"{field_name} must be an int.")
            if value < 0:
                raise ObservationContractError(f"{field_name} must be >= 0.")
        if not isinstance(self.tools_used, tuple):
            raise ObservationContractError("tools_used must be a tuple.")
        normalised: list[str] = []
        for name in self.tools_used:
            if not isinstance(name, str) or name not in _ALLOWED_TOOL_NAMES:
                raise ObservationContractError(
                    "tools_used must contain only closed registry tool names."
                )
            normalised.append(name)
        object.__setattr__(self, "tools_used", tuple(normalised))

    def to_canonical_dict(self) -> dict[str, object]:
        """Allowlisted observation fields only. No answer/source content."""
        return {
            "answer_length": self.answer_length,
            "outcome_code": self.outcome_code.value,
            "planner_calls": self.planner_calls,
            "schema_version": self.schema_version,
            "source_count": self.source_count,
            "synthesis_calls": self.synthesis_calls,
            "tools_executed": self.tools_executed,
            "tools_used": list(self.tools_used),
        }


class ObservationCollector(Protocol):
    """Minimal collector protocol for optional in-process observation."""

    def record(self, observation: AssistantObservation) -> None: ...


class NullObservationCollector:
    """No-op collector: no persistence, I/O, network, files, or DB writes."""

    def record(self, observation: AssistantObservation) -> None:
        return None


class InMemoryObservationCollector:
    """Process-memory collector for tests/evaluation only."""

    def __init__(self) -> None:
        self._observations: list[AssistantObservation] = []

    def record(self, observation: AssistantObservation) -> None:
        if not isinstance(observation, AssistantObservation):
            raise ObservationContractError(
                "InMemoryObservationCollector requires AssistantObservation."
            )
        self._observations.append(observation)

    @property
    def observations(self) -> tuple[AssistantObservation, ...]:
        return tuple(self._observations)


def build_assistant_observation(
    *,
    outcome_code: AssistantOutcomeCode,
    planner_calls: int,
    tools_executed: int,
    synthesis_calls: int,
    tools_used: tuple[str, ...],
    source_count: int,
    answer_length: int,
) -> AssistantObservation:
    """Build an observation from already-final allowlisted counters only."""
    return AssistantObservation(
        schema_version=OBSERVATION_SCHEMA_VERSION,
        outcome_code=outcome_code,
        planner_calls=planner_calls,
        tools_executed=tools_executed,
        synthesis_calls=synthesis_calls,
        tools_used=tuple(tools_used),
        source_count=source_count,
        answer_length=answer_length,
    )


def collect_observation(
    collector: ObservationCollector | None,
    observation: AssistantObservation,
) -> CollectionStatus:
    """Invoke collector only. Collector failure never escapes this boundary."""
    if collector is None:
        return CollectionStatus.DISABLED
    try:
        collector.record(observation)
    except Exception:
        return CollectionStatus.COLLECTION_FAILED
    return CollectionStatus.RECORDED


__all__ = (
    "AssistantObservation",
    "CollectionStatus",
    "InMemoryObservationCollector",
    "NullObservationCollector",
    "OBSERVATION_SCHEMA_VERSION",
    "ObservationCollector",
    "ObservationContractError",
    "build_assistant_observation",
    "collect_observation",
)

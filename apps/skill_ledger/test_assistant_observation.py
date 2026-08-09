"""Sprint 122 Phase 1: privacy-safe assistant observation tests."""

from __future__ import annotations

import dataclasses
from typing import Any, Mapping, Sequence

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.skill_ledger.assistant.contracts import (
    AssistantOutcomeCode,
    PlannerDecision,
    PlannerOutcome,
    ToolCallRequest,
)
from apps.skill_ledger.assistant.observation import (
    OBSERVATION_SCHEMA_VERSION,
    AssistantObservation,
    CollectionStatus,
    InMemoryObservationCollector,
    NullObservationCollector,
    ObservationContractError,
    build_assistant_observation,
    collect_observation,
)
from apps.skill_ledger.assistant.orchestration import run_skill_ledger_assistant
from apps.skill_ledger.evaluation.rag_evaluation_fixtures import (
    FixedVectorEmbeddingProvider,
    ensure_current_fixed_embedding_cache,
)
from apps.skill_ledger.models import SkillEntry

User = get_user_model()

_SENSITIVE_COLLECTOR_MARKER = "CF122_SECRET_COLLECTOR_BOOM_/tmp/secret"


class FixedPlanner:
    def __init__(self, decision: PlannerDecision):
        self.decision = decision
        self.calls = 0

    def plan(
        self,
        *,
        request_text: str,
        tool_definitions: Sequence[Mapping[str, Any]],
    ) -> PlannerDecision:
        self.calls += 1
        return self.decision


class BoomPlanner:
    def plan(self, *, request_text: str, tool_definitions: Sequence[Mapping[str, Any]]):
        raise RuntimeError("planner boom")


class CountingSynthesis:
    def __init__(self, output: dict[str, Any]):
        self.calls = 0
        self.output = output

    def __call__(self, payload: dict) -> dict:
        self.calls += 1
        return self.output


class FailingObservationCollector:
    """Deterministic test-only collector that raises a sensitive exception."""

    def record(self, observation: AssistantObservation) -> None:
        raise RuntimeError(_SENSITIVE_COLLECTOR_MARKER)


def _no_tool() -> PlannerDecision:
    return PlannerDecision(outcome=PlannerOutcome.NO_TOOL, calls=())


def _plan(*requests: ToolCallRequest) -> PlannerDecision:
    return PlannerDecision(outcome=PlannerOutcome.TOOL_PLAN, calls=requests)


def _summary() -> ToolCallRequest:
    return ToolCallRequest(tool_name="get_skill_ledger_summary", arguments={})


class AssistantObservationContractTests(TestCase):
    def test_assistant_observation_is_immutable(self):
        observation = build_assistant_observation(
            outcome_code=AssistantOutcomeCode.NO_TOOL,
            planner_calls=1,
            tools_executed=0,
            synthesis_calls=0,
            tools_used=(),
            source_count=0,
            answer_length=12,
        )
        with self.assertRaises(dataclasses.FrozenInstanceError):
            observation.answer_length = 99  # type: ignore[misc]

    def test_schema_version_is_locked(self):
        self.assertEqual(OBSERVATION_SCHEMA_VERSION, 1)
        with self.assertRaises(ObservationContractError):
            AssistantObservation(
                schema_version=2,
                outcome_code=AssistantOutcomeCode.OK,
                planner_calls=0,
                tools_executed=0,
                synthesis_calls=0,
                tools_used=(),
                source_count=0,
                answer_length=0,
            )

    def test_outcome_code_uses_existing_assistant_outcome_code(self):
        observation = build_assistant_observation(
            outcome_code=AssistantOutcomeCode.FAILED,
            planner_calls=1,
            tools_executed=0,
            synthesis_calls=0,
            tools_used=(),
            source_count=0,
            answer_length=5,
        )
        self.assertIsInstance(observation.outcome_code, AssistantOutcomeCode)
        self.assertEqual(observation.outcome_code, AssistantOutcomeCode.FAILED)

    def test_observation_has_no_arbitrary_metadata_field(self):
        fields = {item.name for item in dataclasses.fields(AssistantObservation)}
        self.assertNotIn("metadata", fields)
        self.assertEqual(
            fields,
            {
                "schema_version",
                "outcome_code",
                "planner_calls",
                "tools_executed",
                "synthesis_calls",
                "tools_used",
                "source_count",
                "answer_length",
            },
        )

    def test_canonical_dict_contains_only_allowlisted_fields(self):
        observation = build_assistant_observation(
            outcome_code=AssistantOutcomeCode.OK,
            planner_calls=1,
            tools_executed=1,
            synthesis_calls=1,
            tools_used=("get_skill_ledger_summary",),
            source_count=2,
            answer_length=40,
        )
        payload = observation.to_canonical_dict()
        self.assertEqual(
            set(payload.keys()),
            {
                "schema_version",
                "outcome_code",
                "planner_calls",
                "tools_executed",
                "synthesis_calls",
                "tools_used",
                "source_count",
                "answer_length",
            },
        )
        self.assertNotIn("answer", payload)
        self.assertNotIn("sources_used", payload)
        self.assertNotIn("request_text", payload)
        self.assertNotIn("metadata", payload)

    def test_tools_used_rejects_non_registry_names(self):
        with self.assertRaises(ObservationContractError):
            build_assistant_observation(
                outcome_code=AssistantOutcomeCode.OK,
                planner_calls=1,
                tools_executed=1,
                synthesis_calls=0,
                tools_used=("delete_skill_entry",),
                source_count=0,
                answer_length=1,
            )


class ObservationCollectorTests(TestCase):
    def test_null_observation_collector_performs_no_recording(self):
        collector = NullObservationCollector()
        observation = build_assistant_observation(
            outcome_code=AssistantOutcomeCode.NO_TOOL,
            planner_calls=1,
            tools_executed=0,
            synthesis_calls=0,
            tools_used=(),
            source_count=0,
            answer_length=3,
        )
        self.assertIsNone(collector.record(observation))
        self.assertFalse(hasattr(collector, "observations"))

    def test_in_memory_collector_records_one_observation(self):
        collector = InMemoryObservationCollector()
        observation = build_assistant_observation(
            outcome_code=AssistantOutcomeCode.NO_TOOL,
            planner_calls=1,
            tools_executed=0,
            synthesis_calls=0,
            tools_used=(),
            source_count=0,
            answer_length=3,
        )
        status = collect_observation(collector, observation)
        self.assertEqual(status, CollectionStatus.RECORDED)
        self.assertEqual(collector.observations, (observation,))

    def test_in_memory_collector_preserves_deterministic_ordering(self):
        collector = InMemoryObservationCollector()
        first = build_assistant_observation(
            outcome_code=AssistantOutcomeCode.NO_TOOL,
            planner_calls=1,
            tools_executed=0,
            synthesis_calls=0,
            tools_used=(),
            source_count=0,
            answer_length=1,
        )
        second = build_assistant_observation(
            outcome_code=AssistantOutcomeCode.FAILED,
            planner_calls=1,
            tools_executed=0,
            synthesis_calls=0,
            tools_used=(),
            source_count=0,
            answer_length=2,
        )
        collect_observation(collector, first)
        collect_observation(collector, second)
        self.assertEqual(collector.observations, (first, second))

    def test_collection_helper_returns_disabled_when_collector_is_none(self):
        observation = build_assistant_observation(
            outcome_code=AssistantOutcomeCode.REJECTED,
            planner_calls=0,
            tools_executed=0,
            synthesis_calls=0,
            tools_used=(),
            source_count=0,
            answer_length=4,
        )
        self.assertEqual(
            collect_observation(None, observation),
            CollectionStatus.DISABLED,
        )

    def test_collection_helper_returns_recorded_for_successful_collection(self):
        observation = build_assistant_observation(
            outcome_code=AssistantOutcomeCode.OK,
            planner_calls=1,
            tools_executed=1,
            synthesis_calls=1,
            tools_used=("get_skill_ledger_summary",),
            source_count=0,
            answer_length=10,
        )
        self.assertEqual(
            collect_observation(InMemoryObservationCollector(), observation),
            CollectionStatus.RECORDED,
        )

    def test_failing_collector_maps_to_collection_failed(self):
        observation = build_assistant_observation(
            outcome_code=AssistantOutcomeCode.NO_TOOL,
            planner_calls=1,
            tools_executed=0,
            synthesis_calls=0,
            tools_used=(),
            source_count=0,
            answer_length=1,
        )
        status = collect_observation(FailingObservationCollector(), observation)
        self.assertEqual(status, CollectionStatus.COLLECTION_FAILED)

    def test_failing_collector_exception_text_is_not_stored_in_observation(self):
        observation = build_assistant_observation(
            outcome_code=AssistantOutcomeCode.NO_TOOL,
            planner_calls=1,
            tools_executed=0,
            synthesis_calls=0,
            tools_used=(),
            source_count=0,
            answer_length=1,
        )
        collect_observation(FailingObservationCollector(), observation)
        canonical = observation.to_canonical_dict()
        blob = repr(observation) + repr(canonical)
        self.assertNotIn(_SENSITIVE_COLLECTOR_MARKER, blob)
        self.assertNotIn("CF122_SECRET", blob)


class AssistantObservationIntegrationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="sprint122_obs_owner",
            password="StrongPass12345",
        )
        self.owned = SkillEntry.objects.create(
            user=self.owner,
            skill_name="SQL",
            category=SkillEntry.Category.PROGRAMMING,
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
        )
        self.provider = FixedVectorEmbeddingProvider([1.0, 0.0])
        ensure_current_fixed_embedding_cache(
            self.owned,
            provider=self.provider,
            vector=[1.0, 0.0],
        )

    def _run(
        self,
        *,
        planner,
        synthesis,
        request_text: str = "summarise ledger",
        observation_collector=None,
    ):
        return run_skill_ledger_assistant(
            request_text=request_text,
            user=self.owner,
            planner=planner,
            synthesis_provider=synthesis,
            embedding_provider=self.provider,
            observation_collector=observation_collector,
        )

    def test_observation_captures_planner_tools_synthesis_counters(self):
        collector = InMemoryObservationCollector()
        planner = FixedPlanner(_plan(_summary()))
        synthesis = CountingSynthesis(
            {
                "answer": "Ledger summary grounded in tools.",
                "tools_used": ["get_skill_ledger_summary"],
                "sources_used": [],
            }
        )
        outcome = self._run(
            planner=planner,
            synthesis=synthesis,
            observation_collector=collector,
        )
        self.assertEqual(outcome.result.code, AssistantOutcomeCode.OK)
        observation = collector.observations[0]
        self.assertEqual(observation.planner_calls, outcome.planner_calls)
        self.assertEqual(observation.tools_executed, outcome.tools_executed)
        self.assertEqual(observation.synthesis_calls, outcome.synthesis_calls)
        self.assertEqual(observation.tools_used, outcome.result.tools_used)

    def test_observation_captures_source_count_only(self):
        collector = InMemoryObservationCollector()
        planner = FixedPlanner(
            _plan(
                ToolCallRequest(
                    tool_name="get_skill_entry_detail",
                    arguments={"skill_entry_id": self.owned.pk},
                )
            )
        )
        synthesis = CountingSynthesis(
            {
                "answer": "Owned detail is available.",
                "tools_used": ["get_skill_entry_detail"],
                "sources_used": [
                    {
                        "source_identifier": self.owned.pk,
                        "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
                    }
                ],
            }
        )
        outcome = self._run(
            planner=planner,
            synthesis=synthesis,
            observation_collector=collector,
        )
        observation = collector.observations[0]
        self.assertEqual(observation.source_count, len(outcome.result.sources_used))
        self.assertGreater(observation.source_count, 0)
        canonical = observation.to_canonical_dict()
        self.assertNotIn("sources_used", canonical)
        self.assertFalse(hasattr(observation, "sources_used"))
        for value in canonical.values():
            if isinstance(value, (list, tuple)):
                self.assertNotIn(self.owned.pk, value)
        self.assertIsInstance(canonical["source_count"], int)
        self.assertNotEqual(
            type(outcome.result.sources_used),
            type(observation.source_count),
        )

    def test_observation_captures_answer_length_only(self):
        collector = InMemoryObservationCollector()
        answer = "Ledger summary grounded in tools."
        planner = FixedPlanner(_plan(_summary()))
        synthesis = CountingSynthesis(
            {
                "answer": answer,
                "tools_used": ["get_skill_ledger_summary"],
                "sources_used": [],
            }
        )
        outcome = self._run(
            planner=planner,
            synthesis=synthesis,
            observation_collector=collector,
        )
        observation = collector.observations[0]
        self.assertEqual(observation.answer_length, len(outcome.result.answer))
        self.assertEqual(observation.answer_length, len(answer))
        self.assertNotIn(answer, observation.to_canonical_dict().values())

    def test_observation_does_not_contain_answer_content(self):
        collector = InMemoryObservationCollector()
        secret_answer = "SECRET_ANSWER_MUST_NOT_ENTER_OBSERVATION"
        planner = FixedPlanner(_plan(_summary()))
        synthesis = CountingSynthesis(
            {
                "answer": secret_answer,
                "tools_used": ["get_skill_ledger_summary"],
                "sources_used": [],
            }
        )
        self._run(
            planner=planner,
            synthesis=synthesis,
            observation_collector=collector,
        )
        observation = collector.observations[0]
        blob = repr(observation) + str(observation.to_canonical_dict())
        self.assertNotIn(secret_answer, blob)

    def test_observation_does_not_contain_source_ids(self):
        collector = InMemoryObservationCollector()
        planner = FixedPlanner(
            _plan(
                ToolCallRequest(
                    tool_name="get_skill_entry_detail",
                    arguments={"skill_entry_id": self.owned.pk},
                )
            )
        )
        synthesis = CountingSynthesis(
            {
                "answer": "Owned detail is available.",
                "tools_used": ["get_skill_entry_detail"],
                "sources_used": [
                    {
                        "source_identifier": self.owned.pk,
                        "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
                    }
                ],
            }
        )
        outcome = self._run(
            planner=planner,
            synthesis=synthesis,
            observation_collector=collector,
        )
        observation = collector.observations[0]
        self.assertEqual(outcome.result.sources_used, (self.owned.pk,))
        canonical = observation.to_canonical_dict()
        self.assertNotIn("sources_used", canonical)
        self.assertFalse(hasattr(observation, "sources_used"))
        for value in canonical.values():
            if isinstance(value, (list, tuple)):
                self.assertNotIn(self.owned.pk, value)
        self.assertEqual(observation.source_count, 1)
        self.assertEqual(observation.source_count, len(outcome.result.sources_used))
        self.assertIsNot(observation.source_count, outcome.result.sources_used)

    def test_observation_does_not_contain_query_or_prompt_text(self):
        collector = InMemoryObservationCollector()
        secret_query = "SECRET_QUERY_PROMPT_MUST_NOT_OBSERVE"
        planner = FixedPlanner(_no_tool())
        synthesis = CountingSynthesis(
            {"answer": "unused", "tools_used": [], "sources_used": []}
        )
        self._run(
            planner=planner,
            synthesis=synthesis,
            request_text=secret_query,
            observation_collector=collector,
        )
        observation = collector.observations[0]
        blob = repr(observation) + str(observation.to_canonical_dict())
        self.assertNotIn(secret_query, blob)
        self.assertNotIn("request_text", blob)
        self.assertNotIn("prompt", blob.casefold())

    def test_default_no_collector_behaves_like_sprint_121(self):
        planner = FixedPlanner(_no_tool())
        synthesis = CountingSynthesis(
            {"answer": "unused", "tools_used": [], "sources_used": []}
        )
        outcome = self._run(planner=planner, synthesis=synthesis)
        self.assertEqual(outcome.result.code, AssistantOutcomeCode.NO_TOOL)
        self.assertEqual(outcome.planner_calls, 1)
        self.assertEqual(outcome.tools_executed, 0)
        self.assertEqual(outcome.synthesis_calls, 0)

    def test_null_vs_in_memory_behavioural_equivalence_differential(self):
        """Mandatory Null vs InMemory behavioural equivalence (same inputs)."""
        request_text = "summarise ledger for equivalence"
        planner_a = FixedPlanner(_plan(_summary()))
        planner_b = FixedPlanner(_plan(_summary()))
        synthesis_output = {
            "answer": "Ledger summary grounded in tools.",
            "tools_used": ["get_skill_ledger_summary"],
            "sources_used": [],
        }
        synthesis_a = CountingSynthesis(dict(synthesis_output))
        synthesis_b = CountingSynthesis(dict(synthesis_output))

        outcome_null = self._run(
            planner=planner_a,
            synthesis=synthesis_a,
            request_text=request_text,
            observation_collector=NullObservationCollector(),
        )
        memory = InMemoryObservationCollector()
        outcome_memory = self._run(
            planner=planner_b,
            synthesis=synthesis_b,
            request_text=request_text,
            observation_collector=memory,
        )

        self.assertEqual(outcome_null.result.answer, outcome_memory.result.answer)
        self.assertEqual(outcome_null.result.code, outcome_memory.result.code)
        self.assertEqual(
            outcome_null.result.tools_used,
            outcome_memory.result.tools_used,
        )
        self.assertEqual(
            outcome_null.result.sources_used,
            outcome_memory.result.sources_used,
        )
        self.assertEqual(outcome_null.planner_calls, outcome_memory.planner_calls)
        self.assertEqual(outcome_null.tools_executed, outcome_memory.tools_executed)
        self.assertEqual(
            outcome_null.synthesis_calls,
            outcome_memory.synthesis_calls,
        )
        self.assertEqual(len(memory.observations), 1)
        self.assertEqual(
            memory.observations[0].outcome_code,
            outcome_memory.result.code,
        )

    def test_failing_collector_does_not_swallow_genuine_assistant_failure(self):
        """Mandatory Q22 isolation: collector failure never rewrites assistant failure."""
        planner = BoomPlanner()
        synthesis = CountingSynthesis(
            {"answer": "should not run", "tools_used": [], "sources_used": []}
        )
        baseline = self._run(
            planner=BoomPlanner(),
            synthesis=CountingSynthesis(
                {"answer": "should not run", "tools_used": [], "sources_used": []}
            ),
            observation_collector=None,
        )
        with_failing = self._run(
            planner=planner,
            synthesis=synthesis,
            observation_collector=FailingObservationCollector(),
        )

        self.assertEqual(baseline.result.code, AssistantOutcomeCode.FAILED)
        self.assertEqual(with_failing.result.code, AssistantOutcomeCode.FAILED)
        self.assertEqual(with_failing.result.answer, baseline.result.answer)
        self.assertEqual(with_failing.result.tools_used, baseline.result.tools_used)
        self.assertEqual(
            with_failing.result.sources_used,
            baseline.result.sources_used,
        )
        self.assertEqual(with_failing.planner_calls, baseline.planner_calls)
        self.assertEqual(with_failing.tools_executed, baseline.tools_executed)
        self.assertEqual(with_failing.synthesis_calls, baseline.synthesis_calls)
        self.assertNotIn(_SENSITIVE_COLLECTOR_MARKER, with_failing.result.answer)
        self.assertNotIn("CF122_SECRET", with_failing.result.answer)
        self.assertNotIn("/tmp/secret", with_failing.result.answer)

    def test_failing_collector_does_not_alter_successful_assistant_result(self):
        planner = FixedPlanner(_no_tool())
        synthesis = CountingSynthesis(
            {"answer": "unused", "tools_used": [], "sources_used": []}
        )
        baseline = self._run(
            planner=FixedPlanner(_no_tool()),
            synthesis=CountingSynthesis(
                {"answer": "unused", "tools_used": [], "sources_used": []}
            ),
        )
        with_failing = self._run(
            planner=planner,
            synthesis=synthesis,
            observation_collector=FailingObservationCollector(),
        )
        self.assertEqual(with_failing.result.code, baseline.result.code)
        self.assertEqual(with_failing.result.answer, baseline.result.answer)
        self.assertEqual(with_failing.planner_calls, baseline.planner_calls)
        self.assertNotIn(_SENSITIVE_COLLECTOR_MARKER, with_failing.result.answer)

    def test_observation_module_has_no_network_or_provider_imports(self):
        import ast
        import inspect
        from pathlib import Path

        from apps.skill_ledger.assistant import observation as observation_module

        source = Path(inspect.getsourcefile(observation_module)).read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        forbidden = {"requests", "httpx", "socket", "urllib", "provider_factory"}
        self.assertEqual(forbidden.intersection(imported), set())
        self.assertNotIn("provider_factory", source)

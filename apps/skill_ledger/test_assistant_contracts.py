"""Sprint 121 Phase 1: typed contracts and closed tool registry tests."""

from __future__ import annotations

from django.test import SimpleTestCase

from apps.skill_ledger.assistant.contracts import (
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
from apps.skill_ledger.assistant.registry import (
    DETAIL_RESULT_SIZE_LIMIT,
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


class ClosedToolRegistryTests(SimpleTestCase):
    def test_registry_contains_exactly_three_tools(self):
        self.assertEqual(registered_tool_count(), 3)
        self.assertEqual(len(TOOL_REGISTRY), 3)

    def test_registry_contains_exactly_locked_tool_names(self):
        self.assertEqual(
            REGISTERED_TOOL_NAMES,
            (
                TOOL_NAME_SEARCH_SKILL_EVIDENCE,
                TOOL_NAME_GET_SKILL_LEDGER_SUMMARY,
                TOOL_NAME_GET_SKILL_ENTRY_DETAIL,
            ),
        )
        self.assertEqual(
            set(TOOL_REGISTRY.keys()),
            {
                "search_skill_evidence",
                "get_skill_ledger_summary",
                "get_skill_entry_detail",
            },
        )

    def test_all_registered_tools_are_read_only(self):
        for name, definition in TOOL_REGISTRY.items():
            with self.subTest(tool=name):
                self.assertIs(definition.read_only, True)

    def test_all_registered_tools_maximum_calls_one(self):
        for name, definition in TOOL_REGISTRY.items():
            with self.subTest(tool=name):
                self.assertEqual(definition.maximum_calls, 1)

    def test_search_tool_argument_names_exactly_query_and_top_k(self):
        definition = TOOL_REGISTRY[TOOL_NAME_SEARCH_SKILL_EVIDENCE]
        self.assertEqual(definition.allowed_argument_names, frozenset({"query", "top_k"}))
        self.assertEqual(definition.ownership_policy, OwnershipPolicy.AUTHENTICATED_USER)
        self.assertEqual(QUERY_MAX_LENGTH, 1000)
        self.assertEqual(TOP_K_MIN, 1)
        self.assertEqual(TOP_K_MAX, 5)

    def test_summary_tool_allows_zero_arguments(self):
        definition = TOOL_REGISTRY[TOOL_NAME_GET_SKILL_LEDGER_SUMMARY]
        self.assertEqual(definition.allowed_argument_names, frozenset())
        self.assertEqual(definition.ownership_policy, OwnershipPolicy.AUTHENTICATED_USER)

    def test_detail_tool_argument_names_exactly_skill_entry_id(self):
        definition = TOOL_REGISTRY[TOOL_NAME_GET_SKILL_ENTRY_DETAIL]
        self.assertEqual(
            definition.allowed_argument_names,
            frozenset({"skill_entry_id"}),
        )
        self.assertEqual(definition.ownership_policy, OwnershipPolicy.USER_SCOPED_OBJECT)

    def test_no_registered_tool_permits_user_or_user_id(self):
        forbidden = {"user", "user_id"}
        for name, definition in TOOL_REGISTRY.items():
            with self.subTest(tool=name):
                self.assertTrue(definition.allowed_argument_names.isdisjoint(forbidden))

    def test_result_size_limits_match_locked_values(self):
        self.assertEqual(
            TOOL_REGISTRY[TOOL_NAME_SEARCH_SKILL_EVIDENCE].result_size_limit,
            SEARCH_RESULT_SIZE_LIMIT,
        )
        self.assertEqual(SEARCH_RESULT_SIZE_LIMIT, 16384)
        self.assertEqual(
            TOOL_REGISTRY[TOOL_NAME_GET_SKILL_LEDGER_SUMMARY].result_size_limit,
            SUMMARY_RESULT_SIZE_LIMIT,
        )
        self.assertEqual(SUMMARY_RESULT_SIZE_LIMIT, 4096)
        self.assertEqual(
            TOOL_REGISTRY[TOOL_NAME_GET_SKILL_ENTRY_DETAIL].result_size_limit,
            DETAIL_RESULT_SIZE_LIMIT,
        )
        self.assertEqual(DETAIL_RESULT_SIZE_LIMIT, 8192)

    def test_unknown_tool_lookup_returns_none(self):
        self.assertIsNone(get_tool_definition("write_skill_entry"))
        self.assertIsNotNone(get_tool_definition(TOOL_NAME_SEARCH_SKILL_EVIDENCE))


class PlannerDecisionContractTests(SimpleTestCase):
    def _request(self, tool_name: str = "search_skill_evidence") -> ToolCallRequest:
        return ToolCallRequest(tool_name=tool_name, arguments={"query": "sql", "top_k": 3})

    def test_planner_accepts_no_tool_with_zero_calls(self):
        decision = PlannerDecision(outcome=PlannerOutcome.NO_TOOL, calls=())
        self.assertEqual(decision.outcome, PlannerOutcome.NO_TOOL)
        self.assertEqual(decision.calls, ())

    def test_planner_rejects_no_tool_with_calls(self):
        with self.assertRaises(AssistantContractError):
            PlannerDecision(outcome=PlannerOutcome.NO_TOOL, calls=(self._request(),))

    def test_planner_accepts_tool_plan_with_one_call(self):
        decision = PlannerDecision(
            outcome=PlannerOutcome.TOOL_PLAN,
            calls=(self._request(),),
        )
        self.assertEqual(len(decision.calls), 1)

    def test_planner_accepts_tool_plan_with_two_calls(self):
        decision = PlannerDecision(
            outcome=PlannerOutcome.TOOL_PLAN,
            calls=(
                self._request("search_skill_evidence"),
                ToolCallRequest(
                    tool_name="get_skill_ledger_summary",
                    arguments={},
                ),
            ),
        )
        self.assertEqual(len(decision.calls), 2)

    def test_planner_rejects_tool_plan_with_zero_calls(self):
        with self.assertRaises(AssistantContractError):
            PlannerDecision(outcome=PlannerOutcome.TOOL_PLAN, calls=())

    def test_planner_rejects_tool_plan_with_more_than_two_calls(self):
        with self.assertRaises(AssistantContractError):
            PlannerDecision(
                outcome=PlannerOutcome.TOOL_PLAN,
                calls=(
                    self._request("search_skill_evidence"),
                    ToolCallRequest(
                        tool_name="get_skill_ledger_summary",
                        arguments={},
                    ),
                    ToolCallRequest(
                        tool_name="get_skill_entry_detail",
                        arguments={"skill_entry_id": 1},
                    ),
                ),
            )


class ContractImmutabilityAndValidationTests(SimpleTestCase):
    def test_tool_definition_allowed_argument_names_are_immutable(self):
        mutable = ["query", "top_k"]
        definition = ToolDefinition(
            name="search_skill_evidence",
            description="test tool",
            read_only=True,
            maximum_calls=1,
            allowed_argument_names=mutable,
            result_size_limit=16384,
            ownership_policy=OwnershipPolicy.AUTHENTICATED_USER,
        )
        mutable.append("user_id")
        self.assertEqual(definition.allowed_argument_names, frozenset({"query", "top_k"}))
        with self.assertRaises(AttributeError):
            definition.allowed_argument_names.add("user_id")  # type: ignore[attr-defined]

    def test_tool_call_request_arguments_are_defensively_frozen(self):
        mutable_args = {"query": "sql", "top_k": 2}
        request = ToolCallRequest(tool_name="search_skill_evidence", arguments=mutable_args)
        mutable_args["query"] = "mutated"
        mutable_args["user_id"] = 99
        self.assertEqual(request.arguments["query"], "sql")
        self.assertNotIn("user_id", request.arguments)
        with self.assertRaises(TypeError):
            request.arguments["query"] = "again"  # type: ignore[index]

    def test_tool_call_result_source_ids_and_payload_are_immutable(self):
        mutable_ids = [11, 22]
        mutable_payload = {"items": [{"id": 11}]}
        result = ToolCallResult(
            tool_name="search_skill_evidence",
            status=ToolCallStatus.SUCCESS,
            rejection_code=None,
            payload=mutable_payload,
            source_ids=mutable_ids,
        )
        mutable_ids.append(33)
        mutable_payload["items"].append({"id": 33})
        self.assertEqual(result.source_ids, (11, 22))
        self.assertEqual(len(result.payload["items"]), 1)
        with self.assertRaises(TypeError):
            result.payload["extra"] = 1  # type: ignore[index]

    def test_success_with_zero_results_is_ok_and_distinct_from_rejected(self):
        zero = ToolCallResult(
            tool_name="search_skill_evidence",
            status=ToolCallStatus.SUCCESS_WITH_ZERO_RESULTS,
            rejection_code=None,
            payload={"items": []},
            source_ids=(),
        )
        rejected = ToolCallResult(
            tool_name="search_skill_evidence",
            status=ToolCallStatus.REJECTED,
            rejection_code="UNKNOWN_TOOL",
            payload=None,
            source_ids=(),
        )
        self.assertTrue(zero.ok)
        self.assertFalse(rejected.ok)
        self.assertNotEqual(zero.status, rejected.status)

    def test_tool_definition_rejects_empty_name_and_invalid_limits(self):
        with self.assertRaises(AssistantContractError):
            ToolDefinition(
                name="",
                description="x",
                read_only=True,
                maximum_calls=1,
                allowed_argument_names=frozenset(),
                result_size_limit=1,
                ownership_policy=OwnershipPolicy.AUTHENTICATED_USER,
            )
        with self.assertRaises(AssistantContractError):
            ToolDefinition(
                name="t",
                description="",
                read_only=True,
                maximum_calls=1,
                allowed_argument_names=frozenset(),
                result_size_limit=1,
                ownership_policy=OwnershipPolicy.AUTHENTICATED_USER,
            )
        with self.assertRaises(AssistantContractError):
            ToolDefinition(
                name="t",
                description="d",
                read_only=True,
                maximum_calls=0,
                allowed_argument_names=frozenset(),
                result_size_limit=1,
                ownership_policy=OwnershipPolicy.AUTHENTICATED_USER,
            )
        with self.assertRaises(AssistantContractError):
            ToolDefinition(
                name="t",
                description="d",
                read_only=True,
                maximum_calls=1,
                allowed_argument_names=frozenset(),
                result_size_limit=0,
                ownership_policy=OwnershipPolicy.AUTHENTICATED_USER,
            )

    def test_tool_definition_rejects_duplicate_argument_names(self):
        with self.assertRaises(AssistantContractError):
            ToolDefinition(
                name="t",
                description="d",
                read_only=True,
                maximum_calls=1,
                allowed_argument_names=["query", "query"],
                result_size_limit=1,
                ownership_policy=OwnershipPolicy.AUTHENTICATED_USER,
            )

    def test_tool_call_request_rejects_forbidden_runtime_dependency_keys(self):
        with self.assertRaises(AssistantContractError):
            ToolCallRequest(
                tool_name="search_skill_evidence",
                arguments={"query": "x", "depends_on": "other"},
            )
        with self.assertRaises(AssistantContractError):
            ToolCallRequest(
                tool_name="search_skill_evidence",
                arguments={"query": "x", "user_id": 1},
            )

    def test_assistant_result_structural_contract(self):
        result = AssistantResult(
            ok=True,
            code=AssistantOutcomeCode.OK,
            answer="summary",
            tools_used=["search_skill_evidence"],
            sources_used=[7],
        )
        self.assertEqual(result.tools_used, ("search_skill_evidence",))
        self.assertEqual(result.sources_used, (7,))

    def test_evidence_insufficient_outcome_is_distinct_from_no_tool(self):
        self.assertEqual(
            AssistantOutcomeCode.EVIDENCE_INSUFFICIENT.value,
            "EVIDENCE_INSUFFICIENT",
        )
        self.assertNotEqual(
            AssistantOutcomeCode.EVIDENCE_INSUFFICIENT,
            AssistantOutcomeCode.NO_TOOL,
        )
        result = AssistantResult(
            ok=True,
            code=AssistantOutcomeCode.EVIDENCE_INSUFFICIENT,
            answer="No usable Skill Ledger evidence matched the request.",
            tools_used=["search_skill_evidence"],
            sources_used=(),
        )
        self.assertEqual(result.code, AssistantOutcomeCode.EVIDENCE_INSUFFICIENT)
        self.assertNotEqual(result.code, AssistantOutcomeCode.NO_TOOL)


class StrictJsonishAndSourceIdInvariantTests(SimpleTestCase):
    def test_callable_argument_value_rejected(self):
        with self.assertRaises(AssistantContractError):
            ToolCallRequest(
                tool_name="search_skill_evidence",
                arguments={"query": "sql", "top_k": len},
            )

    def test_arbitrary_object_argument_value_rejected(self):
        with self.assertRaises(AssistantContractError):
            ToolCallRequest(
                tool_name="search_skill_evidence",
                arguments={"query": object()},
            )

    def test_bytes_argument_value_rejected(self):
        with self.assertRaises(AssistantContractError):
            ToolCallRequest(
                tool_name="search_skill_evidence",
                arguments={"query": b"sql"},
            )

    def test_non_string_mapping_key_rejected(self):
        with self.assertRaises(AssistantContractError):
            ToolCallRequest(
                tool_name="search_skill_evidence",
                arguments={1: "sql"},
            )

    def test_nan_rejected(self):
        with self.assertRaises(AssistantContractError):
            ToolCallRequest(
                tool_name="search_skill_evidence",
                arguments={"query": "sql", "score": float("nan")},
            )

    def test_positive_infinity_rejected(self):
        with self.assertRaises(AssistantContractError):
            ToolCallRequest(
                tool_name="search_skill_evidence",
                arguments={"query": "sql", "score": float("inf")},
            )

    def test_negative_infinity_rejected(self):
        with self.assertRaises(AssistantContractError):
            ToolCallRequest(
                tool_name="search_skill_evidence",
                arguments={"query": "sql", "score": float("-inf")},
            )

    def test_nested_supported_structures_remain_recursively_immutable(self):
        mutable_nested = {
            "query": "sql",
            "filters": [{"category": "programming"}, {"category": "cloud"}],
            "meta": {"top_k": 2, "active": True, "score": 1.5, "note": None},
        }
        request = ToolCallRequest(
            tool_name="search_skill_evidence",
            arguments=mutable_nested,
        )
        mutable_nested["filters"].append({"category": "other"})
        mutable_nested["meta"]["top_k"] = 99
        self.assertEqual(request.arguments["filters"][0]["category"], "programming")
        self.assertEqual(len(request.arguments["filters"]), 2)
        self.assertEqual(request.arguments["meta"]["top_k"], 2)
        with self.assertRaises(TypeError):
            request.arguments["meta"]["top_k"] = 3  # type: ignore[index]
        with self.assertRaises(TypeError):
            request.arguments["filters"][0]["category"] = "x"  # type: ignore[index]

    def test_source_id_zero_rejected(self):
        with self.assertRaises(AssistantContractError):
            ToolCallResult(
                tool_name="search_skill_evidence",
                status=ToolCallStatus.SUCCESS,
                rejection_code=None,
                payload={"items": []},
                source_ids=[0],
            )

    def test_negative_source_id_rejected(self):
        with self.assertRaises(AssistantContractError):
            ToolCallResult(
                tool_name="search_skill_evidence",
                status=ToolCallStatus.SUCCESS,
                rejection_code=None,
                payload={"items": []},
                source_ids=[-1],
            )

    def test_duplicate_source_ids_rejected(self):
        with self.assertRaises(AssistantContractError):
            ToolCallResult(
                tool_name="search_skill_evidence",
                status=ToolCallStatus.SUCCESS,
                rejection_code=None,
                payload={"items": []},
                source_ids=[7, 7],
            )

    def test_rejected_result_with_source_ids_rejected(self):
        with self.assertRaises(AssistantContractError):
            ToolCallResult(
                tool_name="get_skill_entry_detail",
                status=ToolCallStatus.REJECTED,
                rejection_code="NOT_FOUND",
                payload=None,
                source_ids=[1],
            )

    def test_failed_result_with_source_ids_rejected(self):
        with self.assertRaises(AssistantContractError):
            ToolCallResult(
                tool_name="get_skill_entry_detail",
                status=ToolCallStatus.FAILED,
                rejection_code="EXECUTOR_ERROR",
                payload=None,
                source_ids=[1],
            )

    def test_not_executed_result_with_source_ids_rejected(self):
        with self.assertRaises(AssistantContractError):
            ToolCallResult(
                tool_name="get_skill_entry_detail",
                status=ToolCallStatus.NOT_EXECUTED,
                rejection_code="PLAN_REJECTED",
                payload=None,
                source_ids=[1],
            )

    def test_success_with_zero_results_with_source_ids_rejected(self):
        with self.assertRaises(AssistantContractError):
            ToolCallResult(
                tool_name="search_skill_evidence",
                status=ToolCallStatus.SUCCESS_WITH_ZERO_RESULTS,
                rejection_code=None,
                payload={"items": []},
                source_ids=[1],
            )

"""Sprint 121 Phase 2: read-only tools and bounded executor tests."""

from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from apps.skill_ledger.assistant.contracts import (
    PlannerDecision,
    PlannerOutcome,
    ToolCallRequest,
    ToolCallResult,
    ToolCallStatus,
)
from apps.skill_ledger.assistant.executor import (
    ExecutorCode,
    execute_plan,
    measure_tool_call_result_size,
)
from apps.skill_ledger.assistant.registry import (
    QUERY_MAX_LENGTH,
    REGISTERED_TOOL_NAMES,
    TOOL_REGISTRY,
    TOP_K_MAX,
    TOP_K_MIN,
)
from apps.skill_ledger.assistant.tools import TOOL_HANDLERS
from apps.skill_ledger.embedding_cache import regenerate_evidence_embedding
from apps.skill_ledger.evaluation.rag_evaluation_fixtures import (
    FixedVectorEmbeddingProvider,
    ensure_current_fixed_embedding_cache,
    write_stale_fixed_embedding_cache,
)
from apps.skill_ledger.models import EvidenceEmbedding, SkillEntry

User = get_user_model()


def _plan(*requests: ToolCallRequest) -> PlannerDecision:
    return PlannerDecision(outcome=PlannerOutcome.TOOL_PLAN, calls=requests)


def _search(*, query: str = "sql", top_k: int = 3) -> ToolCallRequest:
    return ToolCallRequest(
        tool_name="search_skill_evidence",
        arguments={"query": query, "top_k": top_k},
    )


def _summary() -> ToolCallRequest:
    return ToolCallRequest(tool_name="get_skill_ledger_summary", arguments={})


def _detail(skill_entry_id: int) -> ToolCallRequest:
    return ToolCallRequest(
        tool_name="get_skill_entry_detail",
        arguments={"skill_entry_id": skill_entry_id},
    )


class AssistantExecutorTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="sprint121_owner",
            password="StrongPass12345",
        )
        self.other = User.objects.create_user(
            username="sprint121_other",
            password="StrongPass12345",
        )
        self.provider = FixedVectorEmbeddingProvider([1.0, 0.0])
        self.doc_vector = [1.0, 0.0]
        self.owned = SkillEntry.objects.create(
            user=self.owner,
            skill_name="SQL",
            category=SkillEntry.Category.PROGRAMMING,
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
            sprint_reference="Sprint 90",
            project_link="https://example.invalid/sql",
            notes="SECRET_NOTES_MUST_NOT_ESCAPE",
        )
        ensure_current_fixed_embedding_cache(
            self.owned,
            provider=self.provider,
            vector=self.doc_vector,
        )

    def test_handler_map_exactly_equals_closed_registry_names(self):
        self.assertEqual(set(TOOL_HANDLERS.keys()), set(REGISTERED_TOOL_NAMES))
        self.assertEqual(set(TOOL_HANDLERS.keys()), set(TOOL_REGISTRY.keys()))
        self.assertEqual(len(TOOL_HANDLERS), 3)

    def test_all_handlers_are_read_only_registry_paths(self):
        for name in TOOL_HANDLERS:
            self.assertIs(TOOL_REGISTRY[name].read_only, True)

    def test_known_search_executes_with_injected_offline_provider(self):
        result = execute_plan(
            _plan(_search(query="sql", top_k=1)),
            user=self.owner,
            embedding_provider=self.provider,
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.code, ExecutorCode.OK)
        self.assertEqual(len(result.results), 1)
        tool_result = result.results[0]
        self.assertEqual(tool_result.status, ToolCallStatus.SUCCESS)
        self.assertEqual(tool_result.source_ids, (self.owned.pk,))
        item = tool_result.payload["items"][0]
        self.assertEqual(item["skill_entry_id"], self.owned.pk)
        self.assertNotIn("notes", item)
        self.assertNotIn("content_sha256", item)
        self.assertNotIn("project_link", item)

    def test_search_respects_top_k_one_and_five(self):
        extras = []
        for index in range(4):
            entry = SkillEntry.objects.create(
                user=self.owner,
                skill_name=f"Skill-{index}",
                category=SkillEntry.Category.OTHER,
                evidence_level=SkillEntry.EvidenceLevel.STUDYING,
            )
            ensure_current_fixed_embedding_cache(
                entry,
                provider=self.provider,
                vector=self.doc_vector,
            )
            extras.append(entry)
        one = execute_plan(
            _plan(_search(top_k=1)),
            user=self.owner,
            embedding_provider=self.provider,
        )
        five = execute_plan(
            _plan(_search(top_k=5)),
            user=self.owner,
            embedding_provider=self.provider,
        )
        self.assertEqual(len(one.results[0].payload["items"]), 1)
        self.assertEqual(len(five.results[0].payload["items"]), 5)
        self.assertEqual(TOP_K_MIN, 1)
        self.assertEqual(TOP_K_MAX, 5)

    def test_search_rejects_invalid_top_k_and_query(self):
        cases = [
            _search(top_k=0),
            _search(top_k=6),
            ToolCallRequest(
                tool_name="search_skill_evidence",
                arguments={"query": "sql", "top_k": True},
            ),
            _search(query="   "),
            _search(query="x" * (QUERY_MAX_LENGTH + 1)),
        ]
        for request in cases:
            with self.subTest(request=request.arguments):
                batch = execute_plan(
                    _plan(request),
                    user=self.owner,
                    embedding_provider=self.provider,
                )
                self.assertFalse(batch.ok)
                self.assertEqual(batch.code, ExecutorCode.INVALID_ARGUMENTS)
                self.assertEqual(batch.results, ())

    def test_search_excludes_cross_user_evidence(self):
        other_entry = SkillEntry.objects.create(
            user=self.other,
            skill_name="Other SQL",
            category=SkillEntry.Category.PROGRAMMING,
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
        )
        ensure_current_fixed_embedding_cache(
            other_entry,
            provider=self.provider,
            vector=self.doc_vector,
        )
        batch = execute_plan(
            _plan(_search(top_k=5)),
            user=self.owner,
            embedding_provider=self.provider,
        )
        ids = batch.results[0].source_ids
        self.assertIn(self.owned.pk, ids)
        self.assertNotIn(other_entry.pk, ids)

    def test_search_preserves_stale_ineligible_exclusion(self):
        stale_entry = SkillEntry.objects.create(
            user=self.owner,
            skill_name="Stale Skill",
            category=SkillEntry.Category.CLOUD,
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
        )
        write_stale_fixed_embedding_cache(
            stale_entry,
            provider=self.provider,
            vector=self.doc_vector,
        )
        batch = execute_plan(
            _plan(_search(top_k=5)),
            user=self.owner,
            embedding_provider=self.provider,
        )
        self.assertNotIn(stale_entry.pk, batch.results[0].source_ids)

    def test_search_zero_results_success_with_zero(self):
        EvidenceEmbedding.objects.all().delete()
        batch = execute_plan(
            _plan(_search(top_k=3)),
            user=self.owner,
            embedding_provider=self.provider,
        )
        self.assertTrue(batch.ok)
        tool_result = batch.results[0]
        self.assertEqual(tool_result.status, ToolCallStatus.SUCCESS_WITH_ZERO_RESULTS)
        self.assertEqual(list(tool_result.payload["items"]), [])
        self.assertEqual(tool_result.source_ids, ())

    def test_search_missing_provider_fails_before_execution(self):
        with patch(
            "apps.skill_ledger.assistant.tools.retrieve_owned_skill_evidence"
        ) as mocked:
            batch = execute_plan(
                _plan(_search()),
                user=self.owner,
                embedding_provider=None,
            )
            mocked.assert_not_called()
        self.assertFalse(batch.ok)
        self.assertEqual(batch.code, ExecutorCode.TOOL_UNAVAILABLE)
        self.assertEqual(batch.results, ())

    def test_summary_owned_only_deterministic_and_safe(self):
        SkillEntry.objects.create(
            user=self.other,
            skill_name="Other",
            category=SkillEntry.Category.CLOUD,
            evidence_level=SkillEntry.EvidenceLevel.LEARNING_TARGET,
        )
        SkillEntry.objects.create(
            user=self.owner,
            skill_name="Python",
            category=SkillEntry.Category.PROGRAMMING,
            evidence_level=SkillEntry.EvidenceLevel.STUDYING,
        )
        batch = execute_plan(_plan(_summary()), user=self.owner)
        self.assertTrue(batch.ok)
        payload = batch.results[0].payload
        self.assertEqual(payload["total_entries"], 2)
        counts = payload["evidence_level_counts"]
        for value, _label in SkillEntry.EvidenceLevel.choices:
            self.assertIn(value, counts)
        self.assertEqual(counts[SkillEntry.EvidenceLevel.VERIFIED], 1)
        self.assertEqual(counts[SkillEntry.EvidenceLevel.STUDYING], 1)
        self.assertEqual(counts[SkillEntry.EvidenceLevel.LEARNING_TARGET], 0)
        self.assertEqual(counts[SkillEntry.EvidenceLevel.NO_EVIDENCE], 0)
        category_keys = list(payload["category_counts"].keys())
        self.assertEqual(category_keys, sorted(category_keys))
        self.assertEqual(
            payload["category_counts"][SkillEntry.Category.PROGRAMMING],
            2,
        )
        self.assertNotIn("verified_entries", payload)
        self.assertNotIn("notes", payload)
        self.assertNotIn("project_link", payload)
        self.assertTrue(hasattr(payload["evidence_level_counts"], "keys"))
        self.assertFalse(hasattr(payload["evidence_level_counts"], "save"))
        self.assertEqual(batch.results[0].source_ids, ())

    def test_empty_ledger_summary_succeeds(self):
        SkillEntry.objects.filter(user=self.owner).delete()
        batch = execute_plan(_plan(_summary()), user=self.owner)
        self.assertTrue(batch.ok)
        self.assertEqual(batch.results[0].payload["total_entries"], 0)
        self.assertEqual(batch.results[0].status, ToolCallStatus.SUCCESS)

    def test_detail_allowlisted_fields_exclude_notes(self):
        batch = execute_plan(_plan(_detail(self.owned.pk)), user=self.owner)
        self.assertTrue(batch.ok)
        payload = batch.results[0].payload
        self.assertEqual(
            set(payload.keys()),
            {
                "skill_entry_id",
                "skill_name",
                "category",
                "evidence_level",
                "sprint_reference",
                "project_link",
            },
        )
        self.assertEqual(payload["project_link"], "https://example.invalid/sql")
        self.assertNotIn("notes", payload)
        self.assertEqual(batch.results[0].source_ids, (self.owned.pk,))

    def test_detail_never_fetches_project_link(self):
        with patch("urllib.request.urlopen") as urlopen_mock:
            with patch("urllib.request.urlretrieve") as urlretrieve_mock:
                batch = execute_plan(_plan(_detail(self.owned.pk)), user=self.owner)
        self.assertTrue(batch.ok)
        urlopen_mock.assert_not_called()
        urlretrieve_mock.assert_not_called()

    def test_detail_missing_and_cross_user_same_object_unavailable(self):
        other_entry = SkillEntry.objects.create(
            user=self.other,
            skill_name="Hidden",
            category=SkillEntry.Category.OTHER,
            evidence_level=SkillEntry.EvidenceLevel.NO_EVIDENCE,
        )
        missing = execute_plan(_plan(_detail(9_999_999)), user=self.owner)
        cross = execute_plan(_plan(_detail(other_entry.pk)), user=self.owner)
        self.assertEqual(missing.ok, cross.ok)
        self.assertFalse(missing.ok)
        self.assertEqual(missing.code, cross.code)
        self.assertEqual(missing.code, ExecutorCode.OBJECT_UNAVAILABLE)
        self.assertEqual(missing.results, ())
        self.assertEqual(cross.results, ())

    def test_detail_rejects_bool_zero_negative_id(self):
        for bad_id in (True, 0, -3):
            with self.subTest(bad_id=bad_id):
                request = ToolCallRequest(
                    tool_name="get_skill_entry_detail",
                    arguments={"skill_entry_id": bad_id},
                )
                batch = execute_plan(_plan(request), user=self.owner)
                self.assertFalse(batch.ok)
                self.assertEqual(batch.code, ExecutorCode.INVALID_ARGUMENTS)
                self.assertEqual(batch.results, ())

    def test_detail_execution_time_relookup_handles_disappearing_row(self):
        owned_pk = self.owned.pk
        self.assertTrue(
            SkillEntry.objects.for_user(self.owner).filter(pk=owned_pk).exists()
        )
        call_log: list[str] = []
        real_detail = TOOL_HANDLERS["get_skill_entry_detail"]
        real_summary = TOOL_HANDLERS["get_skill_ledger_summary"]

        def wrap_detail(request, *, user, embedding_provider=None):
            call_log.append("detail")
            # Delete after validation succeeded, immediately before real lookup.
            SkillEntry.objects.filter(pk=owned_pk).delete()
            return real_detail(
                request,
                user=user,
                embedding_provider=embedding_provider,
            )

        def wrap_summary(request, *, user, embedding_provider=None):
            call_log.append("summary")
            return real_summary(
                request,
                user=user,
                embedding_provider=embedding_provider,
            )

        with patch(
            "apps.skill_ledger.assistant.executor.TOOL_HANDLERS",
            {
                "get_skill_entry_detail": wrap_detail,
                "get_skill_ledger_summary": wrap_summary,
                "search_skill_evidence": TOOL_HANDLERS["search_skill_evidence"],
            },
        ):
            batch = execute_plan(
                _plan(_detail(owned_pk), _summary()),
                user=self.owner,
            )

        self.assertFalse(batch.ok)
        self.assertEqual(batch.code, ExecutorCode.OBJECT_UNAVAILABLE)
        self.assertEqual(batch.tools_executed, 1)
        self.assertEqual(len(batch.results), 1)
        self.assertEqual(batch.results[0].tool_name, "get_skill_entry_detail")
        self.assertEqual(batch.results[0].status, ToolCallStatus.REJECTED)
        self.assertEqual(batch.results[0].rejection_code, "OBJECT_UNAVAILABLE")
        self.assertIsNone(batch.results[0].payload)
        self.assertEqual(batch.results[0].source_ids, ())
        self.assertEqual(call_log, ["detail"])
        self.assertFalse(
            SkillEntry.objects.for_user(self.owner).filter(pk=owned_pk).exists()
        )

    def test_unknown_and_write_looking_tools_same_not_allowed(self):
        unknown = execute_plan(
            _plan(
                ToolCallRequest(tool_name="totally_unknown_tool", arguments={})
            ),
            user=self.owner,
        )
        write_looking = execute_plan(
            _plan(
                ToolCallRequest(
                    tool_name="write_skill_entry",
                    arguments={"skill_name": "x"},
                )
            ),
            user=self.owner,
        )
        self.assertEqual(unknown.code, ExecutorCode.TOOL_NOT_ALLOWED)
        self.assertEqual(write_looking.code, ExecutorCode.TOOL_NOT_ALLOWED)
        self.assertEqual(unknown.results, ())
        self.assertEqual(write_looking.results, ())

    def test_unexpected_and_missing_arguments_rejected(self):
        unexpected = execute_plan(
            _plan(
                ToolCallRequest(
                    tool_name="get_skill_ledger_summary",
                    arguments={"filter": "x"},
                )
            ),
            user=self.owner,
        )
        missing = execute_plan(
            _plan(
                ToolCallRequest(
                    tool_name="search_skill_evidence",
                    arguments={"query": "sql"},
                )
            ),
            user=self.owner,
            embedding_provider=self.provider,
        )
        self.assertEqual(unexpected.code, ExecutorCode.INVALID_ARGUMENTS)
        self.assertEqual(missing.code, ExecutorCode.INVALID_ARGUMENTS)
        self.assertEqual(unexpected.results, ())
        self.assertEqual(missing.results, ())

    def test_user_user_id_cannot_be_supplied_and_auth_required(self):
        with self.assertRaises(Exception):
            ToolCallRequest(
                tool_name="get_skill_ledger_summary",
                arguments={"user_id": self.owner.pk},
            )
        with self.assertRaises(Exception):
            ToolCallRequest(
                tool_name="get_skill_ledger_summary",
                arguments={"user": "x"},
            )
        anon = execute_plan(_plan(_summary()), user=AnonymousUser())
        self.assertEqual(anon.code, ExecutorCode.AUTHENTICATION_REQUIRED)
        self.assertEqual(anon.results, ())

    def test_duplicate_same_tool_calls_rejected_before_execution(self):
        batch = execute_plan(
            _plan(_summary(), _summary()),
            user=self.owner,
        )
        self.assertEqual(batch.code, ExecutorCode.DUPLICATE_TOOL_CALL)
        self.assertEqual(batch.results, ())
        self.assertEqual(batch.tools_executed, 0)

    def test_valid_plus_invalid_mixed_plan_executes_zero(self):
        batch = execute_plan(
            _plan(_summary(), _search(top_k=0)),
            user=self.owner,
            embedding_provider=self.provider,
        )
        self.assertFalse(batch.ok)
        self.assertEqual(batch.code, ExecutorCode.INVALID_ARGUMENTS)
        self.assertEqual(batch.results, ())
        self.assertEqual(batch.tools_executed, 0)

    def test_owned_plus_cross_user_mixed_plan_executes_zero(self):
        other_entry = SkillEntry.objects.create(
            user=self.other,
            skill_name="Hidden",
            category=SkillEntry.Category.OTHER,
            evidence_level=SkillEntry.EvidenceLevel.NO_EVIDENCE,
        )
        batch = execute_plan(
            _plan(_summary(), _detail(other_entry.pk)),
            user=self.owner,
        )
        self.assertEqual(batch.code, ExecutorCode.OBJECT_UNAVAILABLE)
        self.assertEqual(batch.results, ())
        self.assertEqual(batch.tools_executed, 0)

    def test_two_independent_valid_tools_execute_in_declared_order(self):
        batch = execute_plan(
            _plan(_summary(), _search(top_k=1)),
            user=self.owner,
            embedding_provider=self.provider,
        )
        self.assertTrue(batch.ok)
        self.assertEqual(batch.tools_executed, 2)
        self.assertEqual(
            [item.tool_name for item in batch.results],
            ["get_skill_ledger_summary", "search_skill_evidence"],
        )

    def test_max_plan_calls_and_per_tool_metadata_enforced(self):
        from apps.skill_ledger.assistant.contracts import AssistantContractError

        with self.assertRaises(AssistantContractError):
            PlannerDecision(
                outcome=PlannerOutcome.TOOL_PLAN,
                calls=(_summary(), _search(top_k=1), _detail(self.owned.pk)),
            )
        for definition in TOOL_REGISTRY.values():
            self.assertEqual(definition.maximum_calls, 1)
            self.assertLessEqual(definition.maximum_calls, 1)

    def test_result_size_limit_enforced_generically(self):
        limit = TOOL_REGISTRY["get_skill_ledger_summary"].result_size_limit
        pad = "x" * (limit + 256)

        def oversized_summary(request, *, user, embedding_provider=None):
            return ToolCallResult(
                tool_name="get_skill_ledger_summary",
                status=ToolCallStatus.SUCCESS,
                rejection_code=None,
                payload={
                    "total_entries": 0,
                    "evidence_level_counts": {},
                    "category_counts": {},
                    "pad": pad,
                },
                source_ids=(),
            )

        with patch(
            "apps.skill_ledger.assistant.executor.TOOL_HANDLERS",
            {
                "get_skill_ledger_summary": oversized_summary,
                "search_skill_evidence": TOOL_HANDLERS["search_skill_evidence"],
                "get_skill_entry_detail": TOOL_HANDLERS["get_skill_entry_detail"],
            },
        ):
            batch = execute_plan(_plan(_summary()), user=self.owner)

        self.assertFalse(batch.ok)
        self.assertEqual(batch.code, ExecutorCode.RESULT_SIZE_LIMIT_EXCEEDED)
        self.assertEqual(batch.tools_executed, 1)
        self.assertEqual(batch.results[0].tool_name, "get_skill_ledger_summary")
        self.assertEqual(batch.results[0].status, ToolCallStatus.FAILED)
        self.assertIsNone(batch.results[0].payload)
        self.assertEqual(batch.results[0].source_ids, ())
        real = execute_plan(_plan(_summary()), user=self.owner)
        self.assertTrue(real.ok)
        self.assertLessEqual(
            measure_tool_call_result_size(real.results[0]),
            limit,
        )

    def test_first_success_second_failure_counts_two_attempts(self):
        owned_pk = self.owned.pk
        call_log: list[str] = []
        real_detail = TOOL_HANDLERS["get_skill_entry_detail"]
        real_summary = TOOL_HANDLERS["get_skill_ledger_summary"]

        def wrap_summary(request, *, user, embedding_provider=None):
            call_log.append("summary")
            return real_summary(
                request,
                user=user,
                embedding_provider=embedding_provider,
            )

        def wrap_detail(request, *, user, embedding_provider=None):
            call_log.append("detail")
            SkillEntry.objects.filter(pk=owned_pk).delete()
            return real_detail(
                request,
                user=user,
                embedding_provider=embedding_provider,
            )

        with patch(
            "apps.skill_ledger.assistant.executor.TOOL_HANDLERS",
            {
                "get_skill_ledger_summary": wrap_summary,
                "get_skill_entry_detail": wrap_detail,
                "search_skill_evidence": TOOL_HANDLERS["search_skill_evidence"],
            },
        ):
            batch = execute_plan(
                _plan(_summary(), _detail(owned_pk)),
                user=self.owner,
            )

        self.assertFalse(batch.ok)
        self.assertEqual(batch.code, ExecutorCode.OBJECT_UNAVAILABLE)
        self.assertEqual(batch.tools_executed, 2)
        self.assertEqual(call_log, ["summary", "detail"])
        self.assertTrue(batch.results[0].ok)
        self.assertFalse(batch.results[1].ok)

    def test_mismatched_result_tool_name_fails_closed(self):
        def mismatched(request, *, user, embedding_provider=None):
            return ToolCallResult(
                tool_name="search_skill_evidence",
                status=ToolCallStatus.SUCCESS,
                rejection_code=None,
                payload={
                    "total_entries": 1,
                    "evidence_level_counts": {},
                    "category_counts": {},
                },
                source_ids=(99,),
            )

        with patch(
            "apps.skill_ledger.assistant.executor.TOOL_HANDLERS",
            {
                "get_skill_ledger_summary": mismatched,
                "search_skill_evidence": TOOL_HANDLERS["search_skill_evidence"],
                "get_skill_entry_detail": TOOL_HANDLERS["get_skill_entry_detail"],
            },
        ):
            batch = execute_plan(_plan(_summary()), user=self.owner)

        self.assertFalse(batch.ok)
        self.assertEqual(batch.code, ExecutorCode.TOOL_EXECUTION_FAILED)
        self.assertEqual(batch.tools_executed, 1)
        self.assertEqual(batch.results[0].tool_name, "get_skill_ledger_summary")
        self.assertEqual(batch.results[0].status, ToolCallStatus.FAILED)
        self.assertEqual(
            batch.results[0].rejection_code,
            ExecutorCode.TOOL_EXECUTION_FAILED.value,
        )
        self.assertIsNone(batch.results[0].payload)
        self.assertEqual(batch.results[0].source_ids, ())

    def test_no_tool_executes_zero_handlers(self):
        batch = execute_plan(
            PlannerDecision(outcome=PlannerOutcome.NO_TOOL, calls=()),
            user=self.owner,
        )
        self.assertTrue(batch.ok)
        self.assertEqual(batch.code, ExecutorCode.NO_TOOL)
        self.assertEqual(batch.results, ())
        self.assertEqual(batch.tools_executed, 0)

    def test_executor_exception_fails_closed(self):
        def boom(*args, **kwargs):
            raise RuntimeError("boom")

        with patch(
            "apps.skill_ledger.assistant.executor.TOOL_HANDLERS",
            {
                "get_skill_ledger_summary": boom,
                "search_skill_evidence": TOOL_HANDLERS["search_skill_evidence"],
                "get_skill_entry_detail": TOOL_HANDLERS["get_skill_entry_detail"],
            },
        ):
            batch = execute_plan(_plan(_summary()), user=self.owner)
        self.assertFalse(batch.ok)
        self.assertEqual(batch.code, ExecutorCode.TOOL_EXECUTION_FAILED)
        self.assertEqual(batch.tools_executed, 1)
        self.assertEqual(batch.results[0].tool_name, "get_skill_ledger_summary")
        self.assertEqual(batch.results[0].status, ToolCallStatus.FAILED)
        self.assertIsNone(batch.results[0].payload)
        self.assertEqual(batch.results[0].source_ids, ())

    def test_search_does_not_regenerate_embeddings_or_mutate_entries(self):
        before = EvidenceEmbedding.objects.get(skill_entry=self.owned)
        before_vector = list(before.embedding_vector)
        before_hash = before.content_sha256
        notes_before = self.owned.notes
        with patch(
            "apps.skill_ledger.embedding_cache.regenerate_evidence_embedding",
            wraps=regenerate_evidence_embedding,
        ) as regen:
            batch = execute_plan(
                _plan(_search(top_k=1)),
                user=self.owner,
                embedding_provider=self.provider,
            )
            regen.assert_not_called()
        self.assertTrue(batch.ok)
        self.owned.refresh_from_db()
        after = EvidenceEmbedding.objects.get(skill_entry=self.owned)
        self.assertEqual(self.owned.notes, notes_before)
        self.assertEqual(list(after.embedding_vector), before_vector)
        self.assertEqual(after.content_sha256, before_hash)

    def test_rejected_results_cannot_become_successful_evidence(self):
        batch = execute_plan(_plan(_detail(9_999_999)), user=self.owner)
        self.assertFalse(batch.ok)
        self.assertEqual(batch.results, ())
        self.assertEqual(batch.tools_executed, 0)

        owned_pk = self.owned.pk
        real_detail = TOOL_HANDLERS["get_skill_entry_detail"]

        def wrap_detail(request, *, user, embedding_provider=None):
            SkillEntry.objects.filter(pk=owned_pk).delete()
            return real_detail(
                request,
                user=user,
                embedding_provider=embedding_provider,
            )

        with patch(
            "apps.skill_ledger.assistant.executor.TOOL_HANDLERS",
            {
                "get_skill_entry_detail": wrap_detail,
                "get_skill_ledger_summary": TOOL_HANDLERS["get_skill_ledger_summary"],
                "search_skill_evidence": TOOL_HANDLERS["search_skill_evidence"],
            },
        ):
            failed = execute_plan(_plan(_detail(owned_pk)), user=self.owner)

        self.assertEqual(failed.tools_executed, 1)
        self.assertFalse(failed.results[0].ok)
        self.assertEqual(failed.results[0].source_ids, ())
        self.assertIsNone(failed.results[0].payload)

    def test_public_validated_plan_symbols_are_not_exported(self):
        import apps.skill_ledger.assistant.executor as executor_mod

        self.assertFalse(hasattr(executor_mod, "ValidatedPlan"))
        self.assertFalse(hasattr(executor_mod, "ValidatedPlanCall"))
        self.assertFalse(hasattr(executor_mod, "execute_validated_plan"))
        self.assertFalse(hasattr(executor_mod, "validate_plan"))
        self.assertTrue(hasattr(executor_mod, "execute_plan"))
        self.assertTrue(callable(executor_mod.execute_plan))

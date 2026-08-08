"""Sprint 119 Phase 2: exact cosine EvidenceEmbedding retrieval tests."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.skill_ledger.embedding_cache import regenerate_evidence_embedding
from apps.skill_ledger.embedding_provider import (
    DeterministicOfflineEmbeddingProvider,
    EmbeddingProviderError,
    validate_embedding_vector,
)
from apps.skill_ledger.models import EvidenceEmbedding, SkillEntry
from apps.skill_ledger.rag_corpus import content_sha256_for_entry
from apps.skill_ledger.rag_retrieval import (
    TOP_K,
    EvidenceRetrievalError,
    RetrievedSkillEvidence,
    _validated_non_zero_vector,
    exact_cosine_similarity,
    retrieve_owned_skill_evidence,
)

User = get_user_model()


class _FixedVectorProvider:
    """Local test provider returning predetermined finite vectors."""

    def __init__(
        self,
        *,
        provider_name: str,
        model_name: str,
        dimensions: int,
        query_vector: list[float],
    ):
        self._provider_name = provider_name
        self._model_name = model_name
        self._dimensions = dimensions
        self._query_vector = list(query_vector)

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed_documents(self, texts):
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        if not isinstance(text, str):
            raise EmbeddingProviderError("text must be a string.")
        return validate_embedding_vector(
            self._query_vector,
            expected_dimensions=self._dimensions,
        )


class ExactCosineMathTests(TestCase):
    def test_identical_vector_cosine_is_one(self):
        vector = [1.0, 2.0, 3.0]
        self.assertAlmostEqual(exact_cosine_similarity(vector, vector), 1.0)

    def test_orthogonal_vector_cosine_is_zero(self):
        left = [1.0, 0.0]
        right = [0.0, 1.0]
        self.assertAlmostEqual(exact_cosine_similarity(left, right), 0.0)


class ExactCosineRetrievalRankingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ret_owner", password="pass")
        self.provider_name = "fixed_retrieval_test"
        self.model_name = "fixed_v1"
        self.dimensions = 2

    def _create_entry(self, *, skill_name: str, sprint_reference: str = "") -> SkillEntry:
        return SkillEntry.objects.create(
            user=self.user,
            skill_name=skill_name,
            category=SkillEntry.Category.PROGRAMMING,
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
            sprint_reference=sprint_reference,
        )

    def _store_vector(self, entry: SkillEntry, vector: list[float]) -> EvidenceEmbedding:
        return EvidenceEmbedding.objects.create(
            skill_entry=entry,
            embedding_provider=self.provider_name,
            embedding_model=self.model_name,
            content_sha256=content_sha256_for_entry(entry),
            embedding_dimensions=self.dimensions,
            embedding_vector=vector,
        )

    def _provider(self, query_vector: list[float]) -> _FixedVectorProvider:
        return _FixedVectorProvider(
            provider_name=self.provider_name,
            model_name=self.model_name,
            dimensions=self.dimensions,
            query_vector=query_vector,
        )

    def test_deterministic_descending_ranking(self):
        near = self._create_entry(skill_name="NearMatch")
        mid = self._create_entry(skill_name="MidMatch")
        far = self._create_entry(skill_name="FarMatch")
        self._store_vector(near, [1.0, 0.0])
        self._store_vector(mid, [0.7, 0.7])
        self._store_vector(far, [0.0, 1.0])
        results = retrieve_owned_skill_evidence(
            self.user,
            "rank-query",
            provider=self._provider([1.0, 0.0]),
        )
        self.assertEqual(
            [item.skill_name for item in results],
            ["NearMatch", "MidMatch", "FarMatch"],
        )
        scores = [item.similarity_score for item in results]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertAlmostEqual(results[0].similarity_score, 1.0)

    def test_exact_tie_uses_skill_entry_pk_ascending(self):
        first = self._create_entry(skill_name="TieA")
        second = self._create_entry(skill_name="TieB")
        self.assertLess(first.pk, second.pk)
        # Identical vectors => identical cosine against the same query.
        self._store_vector(first, [1.0, 0.0])
        self._store_vector(second, [1.0, 0.0])
        results = retrieve_owned_skill_evidence(
            self.user,
            "tie-query",
            provider=self._provider([1.0, 0.0]),
        )
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].skill_entry_id, first.pk)
        self.assertEqual(results[1].skill_entry_id, second.pk)
        self.assertAlmostEqual(
            results[0].similarity_score,
            results[1].similarity_score,
        )

    def test_top_k_returns_maximum_five(self):
        self.assertEqual(TOP_K, 5)
        for index in range(7):
            entry = self._create_entry(skill_name=f"Skill{index}")
            # Slightly different vectors keep ranking deterministic.
            self._store_vector(entry, [1.0, float(index) * 0.01 + 0.01])
        results = retrieve_owned_skill_evidence(
            self.user,
            "topk-query",
            provider=self._provider([1.0, 0.0]),
        )
        self.assertEqual(len(results), 5)

    def test_fewer_than_five_valid_records_returns_only_available(self):
        one = self._create_entry(skill_name="OnlyOne")
        two = self._create_entry(skill_name="OnlyTwo")
        self._store_vector(one, [1.0, 0.0])
        self._store_vector(two, [0.0, 1.0])
        results = retrieve_owned_skill_evidence(
            self.user,
            "few-query",
            provider=self._provider([1.0, 0.0]),
        )
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].skill_name, "OnlyOne")


class ExactCosineRetrievalExclusionTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="own_ret", password="pass")
        self.other = User.objects.create_user(username="oth_ret", password="pass")
        self.provider_name = "fixed_exclusion_test"
        self.model_name = "fixed_v1"
        self.dimensions = 2
        self.owner_entry = SkillEntry.objects.create(
            user=self.owner,
            skill_name="OwnerPython",
            category=SkillEntry.Category.PROGRAMMING,
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
            sprint_reference="Sprint 119",
            notes="private notes must not appear in results",
        )
        self.other_entry = SkillEntry.objects.create(
            user=self.other,
            skill_name="OtherSQL",
            category=SkillEntry.Category.PROGRAMMING,
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
            sprint_reference="Sprint 1",
        )

    def _provider(self, query_vector: list[float]) -> _FixedVectorProvider:
        return _FixedVectorProvider(
            provider_name=self.provider_name,
            model_name=self.model_name,
            dimensions=self.dimensions,
            query_vector=query_vector,
        )

    def _store(
        self,
        entry: SkillEntry,
        vector: list[float],
        *,
        provider_name: str | None = None,
        model_name: str | None = None,
        content_sha256: str | None = None,
        dimensions: int | None = None,
    ) -> EvidenceEmbedding:
        return EvidenceEmbedding.objects.create(
            skill_entry=entry,
            embedding_provider=provider_name or self.provider_name,
            embedding_model=model_name or self.model_name,
            content_sha256=content_sha256 or content_sha256_for_entry(entry),
            embedding_dimensions=dimensions if dimensions is not None else self.dimensions,
            embedding_vector=vector,
        )

    def test_other_users_evidence_is_excluded(self):
        self._store(self.owner_entry, [1.0, 0.0])
        self._store(self.other_entry, [1.0, 0.0])
        results = retrieve_owned_skill_evidence(
            self.owner,
            "ownership-query",
            provider=self._provider([1.0, 0.0]),
        )
        ids = {item.skill_entry_id for item in results}
        self.assertEqual(ids, {self.owner_entry.pk})
        self.assertNotIn(self.other_entry.pk, ids)
        for item in results:
            self.assertIsInstance(item, RetrievedSkillEvidence)
            self.assertFalse(hasattr(item, "notes"))
            payload = item.__dict__
            self.assertNotIn("notes", payload)
            self.assertNotIn("user", payload)
            self.assertNotIn("embedding_vector", payload)

    def test_stale_cache_row_is_excluded(self):
        self._store(self.owner_entry, [1.0, 0.0])
        self.owner_entry.skill_name = "OwnerPythonRenamed"
        self.owner_entry.save(update_fields=["skill_name"])
        results = retrieve_owned_skill_evidence(
            self.owner,
            "stale-query",
            provider=self._provider([1.0, 0.0]),
        )
        self.assertEqual(results, ())
        self.assertEqual(EvidenceEmbedding.objects.count(), 1)

    def test_malformed_non_finite_or_dimension_mismatched_vector_excluded(self):
        # Persistable JSON values that fail retrieval validation under SQLite.
        persistable_cases = (
            [True, False],
            [1.0, 0.0, 0.0],
            "not-a-list",
            [],
            {"x": 1.0},
        )
        for index, bad_vector in enumerate(persistable_cases):
            with self.subTest(index=index, bad_vector=bad_vector):
                EvidenceEmbedding.objects.filter(skill_entry=self.owner_entry).delete()
                EvidenceEmbedding.objects.create(
                    skill_entry=self.owner_entry,
                    embedding_provider=self.provider_name,
                    embedding_model=self.model_name,
                    content_sha256=content_sha256_for_entry(self.owner_entry),
                    embedding_dimensions=self.dimensions,
                    embedding_vector=bad_vector,
                )
                results = retrieve_owned_skill_evidence(
                    self.owner,
                    "bad-vector-query",
                    provider=self._provider([1.0, 0.0]),
                )
                self.assertEqual(results, ())

        # Non-finite floats are rejected by the retrieval validator even though
        # SQLite JSONField cannot persist NaN/Infinity.
        self.assertIsNone(
            _validated_non_zero_vector(
                [1.0, float("nan")],
                expected_dimensions=self.dimensions,
            )
        )
        self.assertIsNone(
            _validated_non_zero_vector(
                [1.0, float("inf")],
                expected_dimensions=self.dimensions,
            )
        )

    def test_zero_stored_vector_is_excluded(self):
        self._store(self.owner_entry, [0.0, 0.0])
        results = retrieve_owned_skill_evidence(
            self.owner,
            "zero-stored-query",
            provider=self._provider([1.0, 0.0]),
        )
        self.assertEqual(results, ())

    def test_provider_model_mismatch_is_excluded(self):
        self._store(
            self.owner_entry,
            [1.0, 0.0],
            provider_name="other_provider",
            model_name="other_model",
        )
        results = retrieve_owned_skill_evidence(
            self.owner,
            "mismatch-query",
            provider=self._provider([1.0, 0.0]),
        )
        self.assertEqual(results, ())

    def test_invalid_or_zero_query_embedding_fails_closed(self):
        self._store(self.owner_entry, [1.0, 0.0])
        with self.assertRaises(EvidenceRetrievalError):
            retrieve_owned_skill_evidence(
                self.owner,
                "zero-query",
                provider=self._provider([0.0, 0.0]),
            )
        with self.assertRaises(EvidenceRetrievalError):
            retrieve_owned_skill_evidence(
                self.owner,
                "   ",
                provider=self._provider([1.0, 0.0]),
            )
        with self.assertRaises(EvidenceRetrievalError):
            retrieve_owned_skill_evidence(
                self.owner,
                "",
                provider=self._provider([1.0, 0.0]),
            )


class _RaisingQueryEmbeddingProvider:
    """Local test provider whose embed_query raises EmbeddingProviderError."""

    @property
    def provider_name(self) -> str:
        return "raising_query_test"

    @property
    def model_name(self) -> str:
        return "raising_v1"

    @property
    def dimensions(self) -> int:
        return 2

    def embed_documents(self, texts):
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        raise EmbeddingProviderError("simulated provider rejection")


class _InvalidOutputQueryEmbeddingProvider:
    """Local test provider returning invalid query embedding output."""

    def __init__(self, raw_output):
        self._raw_output = raw_output

    @property
    def provider_name(self) -> str:
        return "invalid_output_query_test"

    @property
    def model_name(self) -> str:
        return "invalid_output_v1"

    @property
    def dimensions(self) -> int:
        return 2

    def embed_documents(self, texts):
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str):
        return self._raw_output


class ExactCosineQueryBoundaryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="bound_ret", password="pass")
        self.entry = SkillEntry.objects.create(
            user=self.user,
            skill_name="BoundarySkill",
            category=SkillEntry.Category.PROGRAMMING,
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
            sprint_reference="Sprint 119",
        )
        EvidenceEmbedding.objects.create(
            skill_entry=self.entry,
            embedding_provider="raising_query_test",
            embedding_model="raising_v1",
            content_sha256=content_sha256_for_entry(self.entry),
            embedding_dimensions=2,
            embedding_vector=[1.0, 0.0],
        )
        EvidenceEmbedding.objects.create(
            skill_entry=self.entry,
            embedding_provider="invalid_output_query_test",
            embedding_model="invalid_output_v1",
            content_sha256=content_sha256_for_entry(self.entry),
            embedding_dimensions=2,
            embedding_vector=[0.0, 1.0],
        )

    def test_embed_query_embedding_provider_error_becomes_retrieval_error(self):
        before = list(
            EvidenceEmbedding.objects.order_by("pk").values(
                "pk",
                "content_sha256",
                "embedding_vector",
                "updated_at",
            )
        )
        with self.assertRaises(EvidenceRetrievalError) as raised:
            retrieve_owned_skill_evidence(
                self.user,
                "provider-raise-query",
                provider=_RaisingQueryEmbeddingProvider(),
            )
        self.assertIsInstance(raised.exception.__cause__, EmbeddingProviderError)
        after = list(
            EvidenceEmbedding.objects.order_by("pk").values(
                "pk",
                "content_sha256",
                "embedding_vector",
                "updated_at",
            )
        )
        self.assertEqual(before, after)

    def test_invalid_provider_query_output_fails_closed_without_results(self):
        before_count = EvidenceEmbedding.objects.count()
        before = list(
            EvidenceEmbedding.objects.order_by("pk").values(
                "pk",
                "content_sha256",
                "embedding_vector",
                "updated_at",
            )
        )
        invalid_outputs = (
            [1.0, 0.0, 0.0],
            [True, False],
            [1.0, float("nan")],
            [1.0, float("inf")],
            "not-a-vector",
        )
        for raw in invalid_outputs:
            with self.subTest(raw=raw):
                with self.assertRaises(EvidenceRetrievalError):
                    retrieve_owned_skill_evidence(
                        self.user,
                        "invalid-output-query",
                        provider=_InvalidOutputQueryEmbeddingProvider(raw),
                    )
        after = list(
            EvidenceEmbedding.objects.order_by("pk").values(
                "pk",
                "content_sha256",
                "embedding_vector",
                "updated_at",
            )
        )
        self.assertEqual(EvidenceEmbedding.objects.count(), before_count)
        self.assertEqual(before, after)


class ExactCosineRetrievalIntegrationTests(TestCase):
    def test_phase1_offline_provider_path_does_not_regenerate_cache(self):
        user = User.objects.create_user(username="integ_ret", password="pass")
        entry = SkillEntry.objects.create(
            user=user,
            skill_name="SQL",
            category=SkillEntry.Category.PROGRAMMING,
            evidence_level=SkillEntry.EvidenceLevel.LEARNING_TARGET,
            sprint_reference="Sprint 119",
        )
        provider = DeterministicOfflineEmbeddingProvider()
        regenerate_evidence_embedding(entry, provider=provider)
        before = list(
            EvidenceEmbedding.objects.values(
                "pk",
                "content_sha256",
                "embedding_vector",
                "updated_at",
            )
        )
        results = retrieve_owned_skill_evidence(
            user,
            "SQL analytics",
            provider=provider,
        )
        after = list(
            EvidenceEmbedding.objects.values(
                "pk",
                "content_sha256",
                "embedding_vector",
                "updated_at",
            )
        )
        self.assertEqual(before, after)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].skill_entry_id, entry.pk)
        self.assertEqual(results[0].evidence_level, entry.evidence_level)
        self.assertEqual(results[0].content_sha256, content_sha256_for_entry(entry))
        self.assertIsInstance(results[0].similarity_score, float)
        self.assertGreater(results[0].similarity_score, -1.1)
        self.assertLessEqual(results[0].similarity_score, 1.0)

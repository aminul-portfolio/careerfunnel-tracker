"""Sprint 119 Phase 1: SkillEntry RAG corpus + offline embedding cache tests."""

from __future__ import annotations

import json
import socket
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import IntegrityError, transaction
from django.test import TestCase, TransactionTestCase

from apps.skill_ledger.embedding_cache import (
    CACHE_STATUS_CURRENT,
    CACHE_STATUS_STALE,
    evaluate_cache_currency,
    is_cache_current,
    regenerate_evidence_embedding,
)
from apps.skill_ledger.embedding_provider import (
    DeterministicOfflineEmbeddingProvider,
    EmbeddingProviderError,
    validate_embedding_vector,
)
from apps.skill_ledger.models import EvidenceEmbedding, SkillEntry
from apps.skill_ledger.rag_corpus import (
    APPROVED_CANONICAL_FIELDS,
    EXCLUDED_CANONICAL_FIELDS,
    build_canonical_source_representation,
    build_skill_evidence_corpus,
    canonical_json_bytes,
    content_sha256_for_entry,
    sha256_hex,
)

User = get_user_model()


class SkillEvidenceCorpusOwnershipTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="rag_owner", password="pass")
        self.other = User.objects.create_user(username="rag_other", password="pass")
        self.owner_entry = SkillEntry.objects.create(
            user=self.owner,
            skill_name="Python",
            category=SkillEntry.Category.PROGRAMMING,
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
            sprint_reference="Sprint 119",
            notes="owner private notes must stay out of corpus text",
            project_link="https://example.com/owner",
            visibility=SkillEntry.Visibility.PRIVATE,
        )
        self.other_entry = SkillEntry.objects.create(
            user=self.other,
            skill_name="HiddenSQL",
            category=SkillEntry.Category.PROGRAMMING,
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
            sprint_reference="Sprint 1",
            notes="other user notes",
            project_link="https://example.com/other",
            visibility=SkillEntry.Visibility.PUBLIC,
        )

    def test_authenticated_users_skill_entries_are_included(self):
        corpus = build_skill_evidence_corpus(self.owner)
        ids = {item.skill_entry_id for item in corpus}
        self.assertIn(self.owner_entry.pk, ids)
        self.assertEqual(len(corpus), 1)
        self.assertEqual(corpus[0].skill_name, "Python")

    def test_another_users_skill_entries_are_excluded(self):
        corpus = build_skill_evidence_corpus(self.owner)
        ids = {item.skill_entry_id for item in corpus}
        self.assertNotIn(self.other_entry.pk, ids)
        self.assertNotIn("HiddenSQL", {item.skill_name for item in corpus})

    def test_invalid_or_anonymous_user_cannot_construct_corpus(self):
        self.assertEqual(build_skill_evidence_corpus(None), ())
        self.assertEqual(build_skill_evidence_corpus(AnonymousUser()), ())
        unsaved = User(username="unsaved_rag_user")
        self.assertIsNone(unsaved.pk)
        self.assertEqual(build_skill_evidence_corpus(unsaved), ())


class CanonicalRepresentationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="canon_owner", password="pass")
        self.entry = SkillEntry.objects.create(
            user=self.user,
            skill_name="dbt",
            category=SkillEntry.Category.ANALYTICS_ENGINEERING,
            evidence_level=SkillEntry.EvidenceLevel.LEARNING_TARGET,
            sprint_reference="Sprint 84",
            notes="secret study notes",
            project_link="https://example.com/dbt",
            visibility=SkillEntry.Visibility.PRIVATE,
        )

    def test_canonical_representation_includes_approved_fields_only(self):
        canonical = build_canonical_source_representation(self.entry)
        self.assertEqual(set(canonical.keys()), set(APPROVED_CANONICAL_FIELDS))
        for field in APPROVED_CANONICAL_FIELDS:
            self.assertIn(field, canonical)
        for forbidden in EXCLUDED_CANONICAL_FIELDS:
            self.assertNotIn(forbidden, canonical)

    def test_notes_are_excluded_from_canonical_representation(self):
        canonical = build_canonical_source_representation(self.entry)
        serialised = json.dumps(canonical)
        self.assertNotIn("notes", canonical)
        self.assertNotIn("secret study notes", serialised)
        self.assertNotIn("project_link", canonical)
        self.assertNotIn("https://example.com/dbt", serialised)
        self.assertNotIn("visibility", canonical)

    def test_canonical_representation_is_deterministic(self):
        first = build_canonical_source_representation(self.entry)
        second = build_canonical_source_representation(self.entry)
        self.assertEqual(first, second)
        self.assertEqual(sha256_hex(first), sha256_hex(second))

    def test_content_sha256_is_deterministic(self):
        first = content_sha256_for_entry(self.entry)
        second = content_sha256_for_entry(self.entry)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)
        self.assertTrue(first.islower())
        self.assertTrue(all(ch in "0123456789abcdef" for ch in first))
        corpus_item = build_skill_evidence_corpus(self.user)[0]
        self.assertEqual(corpus_item.content_sha256, first)


class EvidenceEmbeddingModelTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="embed_owner", password="pass")
        self.entry = SkillEntry.objects.create(
            user=self.user,
            skill_name="SQL",
            category=SkillEntry.Category.PROGRAMMING,
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
            sprint_reference="Sprint 119",
        )

    def test_evidence_embedding_fk_cascade_deletes_cache_rows(self):
        regenerate_evidence_embedding(self.entry)
        self.assertEqual(EvidenceEmbedding.objects.count(), 1)
        entry_pk = self.entry.pk
        self.entry.delete()
        self.assertFalse(
            EvidenceEmbedding.objects.filter(skill_entry_id=entry_pk).exists()
        )
        self.assertEqual(EvidenceEmbedding.objects.count(), 0)

    def test_duplicate_skill_entry_provider_model_is_rejected(self):
        provider = DeterministicOfflineEmbeddingProvider()
        regenerate_evidence_embedding(self.entry, provider=provider)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                EvidenceEmbedding.objects.create(
                    skill_entry=self.entry,
                    embedding_provider=provider.PROVIDER_NAME,
                    embedding_model=provider.MODEL_NAME,
                    content_sha256="a" * 64,
                    embedding_dimensions=provider.DIMENSIONS,
                    embedding_vector=[0.0] * provider.DIMENSIONS,
                )

    def test_json_vector_round_trip_works_under_sqlite(self):
        provider = DeterministicOfflineEmbeddingProvider()
        vector = provider.embed_query("sqlite-round-trip")
        row = EvidenceEmbedding.objects.create(
            skill_entry=self.entry,
            embedding_provider=provider.PROVIDER_NAME,
            embedding_model=provider.MODEL_NAME,
            content_sha256="b" * 64,
            embedding_dimensions=len(vector),
            embedding_vector=vector,
        )
        reloaded = EvidenceEmbedding.objects.get(pk=row.pk)
        self.assertIsInstance(reloaded.embedding_vector, list)
        self.assertEqual(len(reloaded.embedding_vector), provider.DIMENSIONS)
        self.assertEqual(reloaded.embedding_vector, vector)
        for value in reloaded.embedding_vector:
            self.assertIsInstance(value, float)
            self.assertNotIsInstance(value, bool)


class EvidenceEmbeddingCacheCurrencyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cache_owner", password="pass")
        self.entry = SkillEntry.objects.create(
            user=self.user,
            skill_name="Snowflake",
            category=SkillEntry.Category.CLOUD,
            evidence_level=SkillEntry.EvidenceLevel.LEARNING_TARGET,
            sprint_reference="Sprint 100",
        )
        self.embedding = regenerate_evidence_embedding(self.entry)

    def test_matching_content_hash_reports_current(self):
        self.assertEqual(
            evaluate_cache_currency(self.embedding, self.entry),
            CACHE_STATUS_CURRENT,
        )
        self.assertTrue(is_cache_current(self.embedding, self.entry))

    def test_changed_approved_source_content_reports_stale(self):
        self.entry.skill_name = "Apache Snowflake Renamed"
        self.entry.save(update_fields=["skill_name"])
        self.entry.refresh_from_db()
        self.embedding.refresh_from_db()
        self.assertEqual(
            evaluate_cache_currency(self.embedding, self.entry),
            CACHE_STATUS_STALE,
        )
        self.assertFalse(is_cache_current(self.embedding, self.entry))
        # Stale row is retained until explicit regeneration.
        self.assertEqual(EvidenceEmbedding.objects.count(), 1)
        refreshed = regenerate_evidence_embedding(self.entry)
        self.assertEqual(EvidenceEmbedding.objects.count(), 1)
        self.assertEqual(refreshed.pk, self.embedding.pk)
        self.assertEqual(
            evaluate_cache_currency(refreshed, self.entry),
            CACHE_STATUS_CURRENT,
        )


class DeterministicOfflineEmbeddingProviderTests(TestCase):
    def setUp(self):
        self.provider = DeterministicOfflineEmbeddingProvider()

    def test_deterministic_provider_returns_valid_fixed_dimensional_vectors(self):
        first = self.provider.embed_query("Python")
        second = self.provider.embed_query("Python")
        other = self.provider.embed_query("SQL")
        self.assertEqual(first, second)
        self.assertNotEqual(first, other)
        self.assertEqual(len(first), self.provider.DIMENSIONS)
        validated = validate_embedding_vector(
            first,
            expected_dimensions=self.provider.DIMENSIONS,
        )
        self.assertEqual(validated, first)
        documents = self.provider.embed_documents(["Python", "SQL"])
        self.assertEqual(documents[0], first)
        self.assertEqual(documents[1], other)
        with self.assertRaises(EmbeddingProviderError):
            validate_embedding_vector(
                [True] * self.provider.DIMENSIONS,
                expected_dimensions=self.provider.DIMENSIONS,
            )
        with self.assertRaises(EmbeddingProviderError):
            validate_embedding_vector(
                [float("nan")] * self.provider.DIMENSIONS,
                expected_dimensions=self.provider.DIMENSIONS,
            )
        with self.assertRaises(EmbeddingProviderError):
            validate_embedding_vector(
                [float("inf")] * self.provider.DIMENSIONS,
                expected_dimensions=self.provider.DIMENSIONS,
            )
        with self.assertRaises(EmbeddingProviderError):
            validate_embedding_vector([0.0], expected_dimensions=self.provider.DIMENSIONS)

    def test_deterministic_provider_performs_no_network_activity(self):
        def _deny_network(*_args, **_kwargs):
            raise AssertionError("network access attempted during offline embedding")

        with patch.object(socket, "socket", side_effect=_deny_network), patch.object(
            socket, "create_connection", side_effect=_deny_network
        ):
            vector = self.provider.embed_query("offline-only")
            documents = self.provider.embed_documents(["a", "b"])
        self.assertEqual(len(vector), self.provider.DIMENSIONS)
        self.assertEqual(len(documents), 2)


class _AlternateLocalEmbeddingProvider:
    """Test-only second EmbeddingProvider implementation (no network)."""

    def __init__(self):
        self._dimensions = 8

    @property
    def provider_name(self) -> str:
        return "alternate_local_test"

    @property
    def model_name(self) -> str:
        return "unit_test_hash_v1"

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed_documents(self, texts):
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        if not isinstance(text, str):
            raise EmbeddingProviderError("text must be a string.")
        seed = sum(ord(ch) for ch in text) + 1
        vector = [
            float(((seed * (index + 3)) % 97) / 97.0)
            for index in range(self._dimensions)
        ]
        return validate_embedding_vector(
            vector,
            expected_dimensions=self._dimensions,
        )


class EmbeddingProviderProtocolCacheTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="proto_owner", password="pass")
        self.entry = SkillEntry.objects.create(
            user=self.user,
            skill_name="Pandas",
            category=SkillEntry.Category.PROGRAMMING,
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
            sprint_reference="Sprint 119",
        )

    def test_regenerate_accepts_alternate_embedding_provider_implementation(self):
        alternate = _AlternateLocalEmbeddingProvider()
        embedding = regenerate_evidence_embedding(self.entry, provider=alternate)
        canonical_text = canonical_json_bytes(
            build_canonical_source_representation(self.entry)
        ).decode("utf-8")
        expected_vector = alternate.embed_query(canonical_text)
        self.assertEqual(embedding.embedding_provider, "alternate_local_test")
        self.assertEqual(embedding.embedding_model, "unit_test_hash_v1")
        self.assertEqual(embedding.embedding_dimensions, alternate.dimensions)
        self.assertEqual(embedding.embedding_vector, expected_vector)
        self.assertEqual(len(embedding.embedding_vector), alternate.dimensions)
        self.assertNotEqual(
            embedding.embedding_provider,
            DeterministicOfflineEmbeddingProvider.PROVIDER_NAME,
        )
        self.assertNotEqual(
            embedding.embedding_model,
            DeterministicOfflineEmbeddingProvider.MODEL_NAME,
        )

"""Sprint 116 Phase 1 synthetic live-canary contract tests."""

from __future__ import annotations

import json
import re
from dataclasses import FrozenInstanceError, replace
from types import ModuleType
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.skill_gaps.live_evaluation import (
    CANARY_CONTRACT_SCHEMA_VERSION,
    CONTRACT_MANIFEST_SHA256,
    canonical_manifest_bytes,
    contract_manifest_sha256,
    get_authoritative_canary_case,
    get_canary_manifest,
    validate_canary_contract,
)
from apps.skill_gaps.live_evaluation import (
    evidence_alignment_explanation_canary_contract as contract_module,
)


class EvidenceAlignmentExplanationCanaryContractTests(SimpleTestCase):
    """Validate the immutable, offline contract for one synthetic case."""

    def test_authoritative_case_has_locked_identity(self):
        case = get_authoritative_canary_case()

        self.assertEqual(
            case.case_id,
            "sprint-116-evidence-alignment-explanation-canary-001",
        )
        self.assertEqual(
            case.surface,
            "evidence_alignment_advisory_explanation",
        )
        self.assertEqual(case.schema_version, CANARY_CONTRACT_SCHEMA_VERSION)

    def test_verified_skills_are_exactly_locked_values(self):
        case = get_authoritative_canary_case()

        self.assertEqual(case.verified_skills, ("Python", "Django", "SQL"))

    def test_snowflake_is_only_learning_target_skill(self):
        case = get_authoritative_canary_case()

        self.assertEqual(case.learning_target_skills, ("Snowflake",))
        self.assertNotIn("Snowflake", case.verified_skills)
        self.assertNotIn("Snowflake", case.unmatched_requirements)

    def test_graphql_is_only_unmatched_requirement(self):
        case = get_authoritative_canary_case()

        self.assertEqual(case.unmatched_requirements, ("GraphQL",))
        self.assertNotIn("GraphQL", case.verified_skills)
        self.assertNotIn("GraphQL", case.learning_target_skills)

    def test_expected_outcome_is_some_requirements_verified(self):
        case = get_authoritative_canary_case()

        self.assertEqual(
            case.expected_deterministic_outcome,
            "SOME_REQUIREMENTS_VERIFIED",
        )

    def test_manifest_contains_only_json_compatible_contract_values(self):
        manifest = get_canary_manifest()

        self.assertEqual(
            set(manifest),
            {
                "case_id",
                "expected_deterministic_outcome",
                "learning_target_skills",
                "schema_version",
                "surface",
                "unmatched_requirements",
                "verified_skills",
            },
        )
        self.assertIsInstance(json.dumps(manifest), str)

    def test_manifest_serialisation_is_deterministic(self):
        first = canonical_manifest_bytes()
        second = canonical_manifest_bytes()

        self.assertEqual(first, second)
        self.assertNotIn(b" ", first)
        self.assertNotIn(b"\r", first)

    def test_manifest_hash_is_stable_and_authoritative(self):
        first = contract_manifest_sha256()
        second = contract_manifest_sha256()

        self.assertEqual(first, second)
        self.assertEqual(first, CONTRACT_MANIFEST_SHA256)

    def test_manifest_hash_is_lowercase_sha256_hexadecimal(self):
        digest = contract_manifest_sha256()

        self.assertEqual(len(digest), 64)
        self.assertIsNotNone(re.fullmatch(r"[0-9a-f]{64}", digest))

    def test_equivalent_dictionary_order_has_same_canonical_bytes_and_hash(self):
        manifest = get_canary_manifest()
        reversed_manifest = dict(reversed(tuple(manifest.items())))

        self.assertEqual(
            canonical_manifest_bytes(manifest),
            canonical_manifest_bytes(reversed_manifest),
        )
        self.assertEqual(
            contract_manifest_sha256(manifest),
            contract_manifest_sha256(reversed_manifest),
        )

    def test_evidence_categories_do_not_overlap(self):
        case = get_authoritative_canary_case()

        self.assertFalse(
            set(case.verified_skills) & set(case.learning_target_skills)
        )
        self.assertFalse(
            set(case.verified_skills) & set(case.unmatched_requirements)
        )
        self.assertFalse(
            set(case.learning_target_skills) & set(case.unmatched_requirements)
        )
        overlapping = replace(case, learning_target_skills=("Python",))
        with self.assertRaisesMessage(
            ValueError,
            "evidence categories must not overlap.",
        ):
            validate_canary_contract(overlapping)

    def test_verified_and_unmatched_overlap_is_rejected(self):
        overlapping = replace(
            get_authoritative_canary_case(),
            unmatched_requirements=("Python",),
        )

        with self.assertRaisesMessage(
            ValueError,
            "evidence categories must not overlap.",
        ):
            validate_canary_contract(overlapping)

    def test_learning_target_and_unmatched_overlap_is_rejected(self):
        overlapping = replace(
            get_authoritative_canary_case(),
            unmatched_requirements=("Snowflake",),
        )

        with self.assertRaisesMessage(
            ValueError,
            "evidence categories must not overlap.",
        ):
            validate_canary_contract(overlapping)

    def test_duplicate_skill_values_are_rejected(self):
        duplicate = replace(
            get_authoritative_canary_case(),
            verified_skills=("Python", "Python", "SQL"),
        )

        with self.assertRaisesMessage(
            ValueError,
            "verified_skills must not contain duplicates.",
        ):
            validate_canary_contract(duplicate)

    def test_empty_skill_values_are_rejected(self):
        invalid = replace(
            get_authoritative_canary_case(),
            learning_target_skills=("",),
        )

        with self.assertRaisesMessage(
            ValueError,
            "learning_target_skills must contain non-empty strings.",
        ):
            validate_canary_contract(invalid)

    def test_unexpected_outcome_is_rejected(self):
        invalid = replace(
            get_authoritative_canary_case(),
            expected_deterministic_outcome="ALL_REQUIREMENTS_VERIFIED",
        )

        with self.assertRaisesMessage(
            ValueError,
            "unexpected deterministic outcome.",
        ):
            validate_canary_contract(invalid)

    def test_contract_is_immutable(self):
        case = get_authoritative_canary_case()

        with self.assertRaises(FrozenInstanceError):
            case.case_id = "changed"  # type: ignore[misc]

    def test_mutable_skill_collections_are_rejected(self):
        invalid = replace(
            get_authoritative_canary_case(),
            verified_skills=["Python", "Django", "SQL"],  # type: ignore[arg-type]
        )

        with self.assertRaisesMessage(
            ValueError,
            "verified_skills must be an immutable tuple.",
        ):
            validate_canary_contract(invalid)

    def test_locked_schema_case_and_surface_are_validated(self):
        case = get_authoritative_canary_case()
        invalid_values = (
            (
                replace(case, schema_version="unsupported"),
                "unsupported canary contract schema version.",
            ),
            (
                replace(case, case_id="unexpected"),
                "unexpected canary case ID.",
            ),
            (
                replace(case, surface="unexpected"),
                "unexpected canary surface.",
            ),
        )

        for invalid, message in invalid_values:
            with self.subTest(message=message):
                with self.assertRaisesMessage(ValueError, message):
                    validate_canary_contract(invalid)

    def test_contract_generation_performs_no_database_query(self):
        with patch("django.db.backends.utils.CursorWrapper.execute") as execute:
            get_authoritative_canary_case()
            get_canary_manifest()
            canonical_manifest_bytes()
            contract_manifest_sha256()

        execute.assert_not_called()

    def test_contract_imports_and_calls_no_network_or_provider_code(self):
        direct_modules = {
            value.__name__
            for value in vars(contract_module).values()
            if isinstance(value, ModuleType)
        }

        with patch("socket.create_connection") as create_connection:
            validate_canary_contract(get_authoritative_canary_case())
            contract_manifest_sha256()

        self.assertEqual(direct_modules, {"hashlib", "json"})
        create_connection.assert_not_called()

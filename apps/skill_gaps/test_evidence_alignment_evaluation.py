"""Sprint 111C Phase 1: golden domain evaluation for evidence alignment.

Deterministic, version-pinned golden tests over the closed Sprint 111B
classifier and aggregation contracts. No ORM, providers, network I/O or
production mutations.
"""

from __future__ import annotations

import socket
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.applications.models import JobApplication
from apps.skill_gaps.deterministic_evidence_alignment import (
    EvidenceAlignmentOutcome,
    summarise_evidence_alignment,
)
from apps.skill_gaps.deterministic_gap_classifier import (
    MatchBasis,
    RequirementClassification,
    RequirementMatchResult,
    SkillLedgerEvidence,
    classify_requirements,
    normalise_requirement,
)
from apps.skill_gaps.models import ApplicationSkillGap
from apps.skill_ledger.models import SkillEntry

# Locked literal; do not import RULE_VERSION from production for this assertion.
EXPECTED_RULE_VERSION = "evidence_alignment_v1"

# Stable curated alias already defined by SKILL_ALIAS_MAP: "powerbi" -> "power bi".
CURATED_ALIAS_INPUT = "PowerBI"
CURATED_ALIAS_LEDGER_NAME = "Power BI"

LOCKED_OUTCOME_ORDER = (
    "NO_ACCEPTED_REQUIREMENTS",
    "MANUAL_REVIEW_REQUIRED",
    "ALL_REQUIREMENTS_VERIFIED",
    "SOME_REQUIREMENTS_VERIFIED",
    "DEVELOPMENT_RECORDS_ONLY",
    "NO_VERIFIED_EVIDENCE",
)


class Sprint111CPhase1GoldenDomainEvaluationTests(SimpleTestCase):
    """Golden domain evaluation for Sprint 111B evidence-alignment contract."""

    def _evidence(self, entry_id, skill_name, evidence_level):
        return SkillLedgerEvidence(
            entry_id=entry_id,
            skill_name=skill_name,
            evidence_level=evidence_level,
        )

    def _requirements(self, *raw_texts):
        return tuple(
            normalise_requirement(index, text)
            for index, text in enumerate(raw_texts)
        )

    def _classify(self, raw_texts, evidence):
        return classify_requirements(self._requirements(*raw_texts), evidence)

    def _assert_summary_contract(
        self,
        summary,
        *,
        outcome,
        triggered_rule,
        total_requirements,
        verified_count,
        learning_target_count,
        studying_count,
        no_match_count,
        explicit_no_evidence_count,
        no_current_evidence_count,
        review_required_count,
        unresolved_requirement_indexes,
        classifications,
        match_bases,
        input_order,
        results,
    ):
        self.assertEqual(summary.rule_version, EXPECTED_RULE_VERSION)
        self.assertEqual(summary.outcome, outcome)
        self.assertEqual(summary.triggered_rule, triggered_rule)
        self.assertEqual(summary.total_requirements, total_requirements)
        self.assertEqual(summary.verified_count, verified_count)
        self.assertEqual(summary.learning_target_count, learning_target_count)
        self.assertEqual(summary.studying_count, studying_count)
        self.assertEqual(summary.no_match_count, no_match_count)
        self.assertEqual(summary.explicit_no_evidence_count, explicit_no_evidence_count)
        self.assertEqual(summary.no_current_evidence_count, no_current_evidence_count)
        self.assertEqual(summary.review_required_count, review_required_count)
        self.assertEqual(
            summary.unresolved_requirement_indexes,
            unresolved_requirement_indexes,
        )
        self.assertIs(summary.per_requirement_results, results)
        self.assertEqual(
            tuple(row.original_text for row in results),
            input_order,
        )
        self.assertEqual(
            tuple(row.classification for row in results),
            classifications,
        )
        self.assertEqual(
            tuple(row.match_basis for row in results),
            match_bases,
        )
        self.assertEqual(
            tuple(row.requirement_index for row in results),
            tuple(range(len(results))),
        )

    def test_all_verified_golden_case(self):
        evidence = (
            self._evidence(1, "Python", "VERIFIED"),
            self._evidence(2, CURATED_ALIAS_LEDGER_NAME, "VERIFIED"),
        )
        input_order = ("Python", CURATED_ALIAS_INPUT)
        results = self._classify(input_order, evidence)
        summary = summarise_evidence_alignment(results)

        self._assert_summary_contract(
            summary,
            outcome=EvidenceAlignmentOutcome.ALL_REQUIREMENTS_VERIFIED,
            triggered_rule="rule_3_all_requirements_verified",
            total_requirements=2,
            verified_count=2,
            learning_target_count=0,
            studying_count=0,
            no_match_count=0,
            explicit_no_evidence_count=0,
            no_current_evidence_count=0,
            review_required_count=0,
            unresolved_requirement_indexes=(),
            classifications=(
                RequirementClassification.VERIFIED_MATCH,
                RequirementClassification.VERIFIED_MATCH,
            ),
            match_bases=(
                MatchBasis.EXACT_NAME,
                MatchBasis.CURATED_ALIAS,
            ),
            input_order=input_order,
            results=results,
        )
        self.assertEqual(results[0].matched_skill_name, "Python")
        self.assertEqual(results[1].matched_skill_name, CURATED_ALIAS_LEDGER_NAME)

    def test_some_verified_golden_case(self):
        evidence = (self._evidence(1, "Python", "VERIFIED"),)
        input_order = ("Python", "GraphQL")
        results = self._classify(input_order, evidence)
        summary = summarise_evidence_alignment(results)

        self._assert_summary_contract(
            summary,
            outcome=EvidenceAlignmentOutcome.SOME_REQUIREMENTS_VERIFIED,
            triggered_rule="rule_4_some_requirements_verified",
            total_requirements=2,
            verified_count=1,
            learning_target_count=0,
            studying_count=0,
            no_match_count=1,
            explicit_no_evidence_count=0,
            no_current_evidence_count=1,
            review_required_count=0,
            unresolved_requirement_indexes=(),
            classifications=(
                RequirementClassification.VERIFIED_MATCH,
                RequirementClassification.NO_EVIDENCE_GAP,
            ),
            match_bases=(
                MatchBasis.EXACT_NAME,
                MatchBasis.NO_MATCH,
            ),
            input_order=input_order,
            results=results,
        )

    def test_development_records_only_learning_target_golden_case(self):
        evidence = (self._evidence(2, "Snowflake", "LEARNING_TARGET"),)
        input_order = ("Snowflake",)
        results = self._classify(input_order, evidence)
        summary = summarise_evidence_alignment(results)

        self._assert_summary_contract(
            summary,
            outcome=EvidenceAlignmentOutcome.DEVELOPMENT_RECORDS_ONLY,
            triggered_rule="rule_5_development_records_only",
            total_requirements=1,
            verified_count=0,
            learning_target_count=1,
            studying_count=0,
            no_match_count=0,
            explicit_no_evidence_count=0,
            no_current_evidence_count=0,
            review_required_count=0,
            unresolved_requirement_indexes=(),
            classifications=(RequirementClassification.LEARNING_TARGET_MATCH,),
            match_bases=(MatchBasis.EXACT_NAME,),
            input_order=input_order,
            results=results,
        )

    def test_development_records_only_studying_golden_case(self):
        evidence = (self._evidence(3, "Statistics", "STUDYING"),)
        input_order = ("Statistics",)
        results = self._classify(input_order, evidence)
        summary = summarise_evidence_alignment(results)

        self._assert_summary_contract(
            summary,
            outcome=EvidenceAlignmentOutcome.DEVELOPMENT_RECORDS_ONLY,
            triggered_rule="rule_5_development_records_only",
            total_requirements=1,
            verified_count=0,
            learning_target_count=0,
            studying_count=1,
            no_match_count=0,
            explicit_no_evidence_count=0,
            no_current_evidence_count=0,
            review_required_count=0,
            unresolved_requirement_indexes=(),
            classifications=(RequirementClassification.STUDYING_MATCH,),
            match_bases=(MatchBasis.EXACT_NAME,),
            input_order=input_order,
            results=results,
        )

    def test_no_verified_evidence_golden_case(self):
        evidence = (self._evidence(4, "Kafka", "NO_EVIDENCE"),)
        input_order = ("Kafka", "GraphQL")
        results = self._classify(input_order, evidence)
        summary = summarise_evidence_alignment(results)

        self._assert_summary_contract(
            summary,
            outcome=EvidenceAlignmentOutcome.NO_VERIFIED_EVIDENCE,
            triggered_rule="rule_6_no_verified_evidence",
            total_requirements=2,
            verified_count=0,
            learning_target_count=0,
            studying_count=0,
            no_match_count=1,
            explicit_no_evidence_count=1,
            no_current_evidence_count=2,
            review_required_count=0,
            unresolved_requirement_indexes=(),
            classifications=(
                RequirementClassification.NO_EVIDENCE_GAP,
                RequirementClassification.NO_EVIDENCE_GAP,
            ),
            match_bases=(
                MatchBasis.NO_EVIDENCE,
                MatchBasis.NO_MATCH,
            ),
            input_order=input_order,
            results=results,
        )
        self.assertEqual(
            summary.no_current_evidence_count,
            summary.no_match_count + summary.explicit_no_evidence_count,
        )

    def test_manual_review_golden_case(self):
        cases = (
            (
                "compound_requirement_review",
                MatchBasis.COMPOUND_REQUIREMENT_REVIEW,
                ("Python and SQL",),
                (
                    self._evidence(1, "Python", "VERIFIED"),
                    self._evidence(2, "SQL", "VERIFIED"),
                ),
            ),
            (
                "claim_scope_review",
                MatchBasis.CLAIM_SCOPE_REVIEW,
                ("Senior Python",),
                (self._evidence(1, "Python", "VERIFIED"),),
            ),
            (
                "duplicate_evidence",
                MatchBasis.DUPLICATE_EVIDENCE,
                ("Python",),
                (
                    self._evidence(1, "Python", "VERIFIED"),
                    self._evidence(2, "Python", "VERIFIED"),
                ),
            ),
            (
                "conflicting_evidence",
                MatchBasis.CONFLICTING_EVIDENCE,
                ("Python",),
                (
                    self._evidence(1, "Python", "VERIFIED"),
                    self._evidence(2, "Python", "LEARNING_TARGET"),
                ),
            ),
        )
        for label, expected_basis, input_order, evidence in cases:
            with self.subTest(case=label):
                results = self._classify(input_order, evidence)
                summary = summarise_evidence_alignment(results)
                self._assert_summary_contract(
                    summary,
                    outcome=EvidenceAlignmentOutcome.MANUAL_REVIEW_REQUIRED,
                    triggered_rule="rule_2_review_required_or_malformed_present",
                    total_requirements=1,
                    verified_count=0,
                    learning_target_count=0,
                    studying_count=0,
                    no_match_count=0,
                    explicit_no_evidence_count=0,
                    no_current_evidence_count=0,
                    review_required_count=1,
                    unresolved_requirement_indexes=(0,),
                    classifications=(RequirementClassification.REVIEW_REQUIRED,),
                    match_bases=(expected_basis,),
                    input_order=input_order,
                    results=results,
                )

    def test_no_accepted_requirements_domain_guard(self):
        results = ()
        summary = summarise_evidence_alignment(results)
        self._assert_summary_contract(
            summary,
            outcome=EvidenceAlignmentOutcome.NO_ACCEPTED_REQUIREMENTS,
            triggered_rule="rule_1_no_accepted_requirements",
            total_requirements=0,
            verified_count=0,
            learning_target_count=0,
            studying_count=0,
            no_match_count=0,
            explicit_no_evidence_count=0,
            no_current_evidence_count=0,
            review_required_count=0,
            unresolved_requirement_indexes=(),
            classifications=(),
            match_bases=(),
            input_order=(),
            results=results,
        )

    def test_malformed_classification_basis_pair_fails_closed(self):
        results = (
            RequirementMatchResult(
                requirement_index=0,
                original_text="Broken verified pair",
                normalised_text="broken verified pair",
                classification=RequirementClassification.VERIFIED_MATCH,
                match_basis=MatchBasis.NO_MATCH,
                matched_skill_name=None,
                matched_evidence_level=None,
                matched_skill_entry_id=None,
                reason_codes=(),
            ),
        )
        try:
            summary = summarise_evidence_alignment(results)
        except Exception as exc:  # pragma: no cover - fail if raised
            self.fail(f"malformed pair raised unexpectedly: {exc!r}")

        self._assert_summary_contract(
            summary,
            outcome=EvidenceAlignmentOutcome.MANUAL_REVIEW_REQUIRED,
            triggered_rule="rule_2_review_required_or_malformed_present",
            total_requirements=1,
            verified_count=0,
            learning_target_count=0,
            studying_count=0,
            no_match_count=0,
            explicit_no_evidence_count=0,
            no_current_evidence_count=0,
            review_required_count=1,
            unresolved_requirement_indexes=(0,),
            classifications=(RequirementClassification.VERIFIED_MATCH,),
            match_bases=(MatchBasis.NO_MATCH,),
            input_order=("Broken verified pair",),
            results=results,
        )

    def test_repeated_domain_evaluation_is_identical(self):
        evidence = (
            self._evidence(1, "Python", "VERIFIED"),
            self._evidence(2, "SQL", "LEARNING_TARGET"),
        )
        input_order = ("Kafka", "Python", "SQL")
        results = self._classify(input_order, evidence)

        first = summarise_evidence_alignment(results)
        second = summarise_evidence_alignment(results)

        expected_classifications = (
            RequirementClassification.NO_EVIDENCE_GAP,
            RequirementClassification.VERIFIED_MATCH,
            RequirementClassification.LEARNING_TARGET_MATCH,
        )
        expected_match_bases = (
            MatchBasis.NO_MATCH,
            MatchBasis.EXACT_NAME,
            MatchBasis.EXACT_NAME,
        )

        self._assert_summary_contract(
            first,
            outcome=EvidenceAlignmentOutcome.SOME_REQUIREMENTS_VERIFIED,
            triggered_rule="rule_4_some_requirements_verified",
            total_requirements=3,
            verified_count=1,
            learning_target_count=1,
            studying_count=0,
            no_match_count=1,
            explicit_no_evidence_count=0,
            no_current_evidence_count=1,
            review_required_count=0,
            unresolved_requirement_indexes=(),
            classifications=expected_classifications,
            match_bases=expected_match_bases,
            input_order=input_order,
            results=results,
        )

        self._assert_summary_contract(
            second,
            outcome=EvidenceAlignmentOutcome.SOME_REQUIREMENTS_VERIFIED,
            triggered_rule="rule_4_some_requirements_verified",
            total_requirements=3,
            verified_count=1,
            learning_target_count=1,
            studying_count=0,
            no_match_count=1,
            explicit_no_evidence_count=0,
            no_current_evidence_count=1,
            review_required_count=0,
            unresolved_requirement_indexes=(),
            classifications=expected_classifications,
            match_bases=expected_match_bases,
            input_order=input_order,
            results=results,
        )

        self.assertEqual(first, second)

    def test_outcome_taxonomy_is_closed_and_unchanged(self):
        members = tuple(EvidenceAlignmentOutcome)
        names = tuple(member.name for member in members)
        values = tuple(member.value for member in members)

        self.assertEqual(len(members), 6)
        self.assertEqual(names, LOCKED_OUTCOME_ORDER)
        self.assertEqual(values, LOCKED_OUTCOME_ORDER)
        self.assertEqual(len(set(names)), 6)
        self.assertEqual(len(set(values)), 6)

        for expected in LOCKED_OUTCOME_ORDER:
            member = EvidenceAlignmentOutcome[expected]
            self.assertEqual(member.name, expected)
            self.assertEqual(member.value, expected)


class Sprint111CPhase2GoldenRouteEvaluationTests(TestCase):
    """Golden route evaluation for Sprint 111B evidence-alignment workflow."""

    def setUp(self):
        self.owner = User.objects.create_user(
            username="p111c2_owner",
            password="pass",
        )
        self.other = User.objects.create_user(
            username="p111c2_other",
            password="pass",
        )
        self.url = reverse("skill_gaps:jd_gap_analysis")

    def _create_entry(self, user, skill_name, evidence_level):
        return SkillEntry.objects.create(
            user=user,
            skill_name=skill_name,
            category=SkillEntry.Category.PROGRAMMING,
            evidence_level=evidence_level,
            visibility=SkillEntry.Visibility.PRIVATE,
        )

    def _model_counts(self):
        return {
            "skill_entry": SkillEntry.objects.count(),
            "job_application": JobApplication.objects.count(),
            "application_skill_gap": ApplicationSkillGap.objects.count(),
        }

    def test_owned_skill_ledger_only_and_requirement_order_preserved(self):
        owner_python = self._create_entry(
            self.owner,
            "Python",
            SkillEntry.EvidenceLevel.VERIFIED,
        )
        owner_snowflake = self._create_entry(
            self.owner,
            "Snowflake",
            SkillEntry.EvidenceLevel.LEARNING_TARGET,
        )
        other_kafka = self._create_entry(
            self.other,
            "Kafka",
            SkillEntry.EvidenceLevel.VERIFIED,
        )

        # Non-alphabetical deliberate order: Snowflake, Python, Kafka.
        input_order = ("Snowflake", "Python", "Kafka")
        for_user_users = []
        values_calls = []
        original_for_user = SkillEntry.objects.for_user

        def for_user_spy(user):
            for_user_users.append(user)
            queryset = original_for_user(user)
            original_values = queryset.values

            def values_spy(*fields, **kwargs):
                values_calls.append(fields)
                return original_values(*fields, **kwargs)

            queryset.values = values_spy
            return queryset

        self.client.login(username="p111c2_owner", password="pass")
        with patch.object(SkillEntry.objects, "for_user", side_effect=for_user_spy):
            response = self.client.post(
                self.url,
                {"requirements": "Snowflake\nPython\nKafka"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["analysis_performed"])
        summary = response.context["summary"]
        results = response.context["results"]
        self.assertIsNotNone(summary)
        self.assertEqual(for_user_users, [self.owner])
        self.assertEqual(len(values_calls), 1)
        self.assertEqual(values_calls[0], ("id", "skill_name", "evidence_level"))

        self.assertEqual(
            tuple(row.original_text for row in results),
            input_order,
        )
        self.assertEqual(
            tuple(row.requirement_index for row in results),
            (0, 1, 2),
        )
        self.assertIs(summary.per_requirement_results, results)
        self.assertEqual(
            tuple(row.original_text for row in summary.per_requirement_results),
            input_order,
        )

        self.assertEqual(
            results[0].classification,
            RequirementClassification.LEARNING_TARGET_MATCH,
        )
        self.assertEqual(results[0].matched_skill_entry_id, owner_snowflake.pk)
        self.assertEqual(
            results[1].classification,
            RequirementClassification.VERIFIED_MATCH,
        )
        self.assertEqual(results[1].matched_skill_entry_id, owner_python.pk)
        self.assertEqual(
            results[2].classification,
            RequirementClassification.NO_EVIDENCE_GAP,
        )
        self.assertEqual(results[2].match_basis, MatchBasis.NO_MATCH)
        self.assertIsNone(results[2].matched_skill_entry_id)
        self.assertIsNone(results[2].matched_skill_name)

        matched_ids = {
            row.matched_skill_entry_id
            for row in results
            if row.matched_skill_entry_id is not None
        }
        self.assertNotIn(other_kafka.pk, matched_ids)
        self.assertEqual(matched_ids, {owner_python.pk, owner_snowflake.pk})

        self.assertEqual(summary.rule_version, EXPECTED_RULE_VERSION)
        self.assertEqual(
            summary.outcome,
            EvidenceAlignmentOutcome.SOME_REQUIREMENTS_VERIFIED,
        )
        self.assertEqual(summary.triggered_rule, "rule_4_some_requirements_verified")
        self.assertEqual(summary.total_requirements, 3)
        self.assertEqual(summary.verified_count, 1)
        self.assertEqual(summary.learning_target_count, 1)
        self.assertEqual(summary.studying_count, 0)
        self.assertEqual(summary.no_match_count, 1)
        self.assertEqual(summary.explicit_no_evidence_count, 0)
        self.assertEqual(summary.no_current_evidence_count, 1)
        self.assertEqual(summary.review_required_count, 0)
        self.assertEqual(summary.unresolved_requirement_indexes, ())

    def test_valid_post_is_transient_and_preserves_model_counts(self):
        entry = self._create_entry(
            self.owner,
            "Python",
            SkillEntry.EvidenceLevel.VERIFIED,
        )
        before_values = SkillEntry.objects.values(
            "id",
            "skill_name",
            "evidence_level",
            "notes",
            "visibility",
        ).get(pk=entry.pk)
        before_counts = self._model_counts()

        self.client.login(username="p111c2_owner", password="pass")
        response = self.client.post(
            self.url,
            {"requirements": "Python\nGraphQL"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["analysis_performed"])
        summary = response.context["summary"]
        self.assertIsNotNone(summary)
        self.assertEqual(
            summary.outcome,
            EvidenceAlignmentOutcome.SOME_REQUIREMENTS_VERIFIED,
        )
        self.assertEqual(summary.triggered_rule, "rule_4_some_requirements_verified")
        self.assertEqual(self._model_counts(), before_counts)
        self.assertEqual(
            SkillEntry.objects.values(
                "id",
                "skill_name",
                "evidence_level",
                "notes",
                "visibility",
            ).get(pk=entry.pk),
            before_values,
        )

        content = response.content.decode("utf-8")
        content_lower = content.lower()
        self.assertNotIn("pre-fill add application", content_lower)
        self.assertNotIn("save analysis", content_lower)
        self.assertNotIn("save to application", content_lower)
        page_start = content_lower.find('class="page-content"')
        self.assertNotEqual(page_start, -1)
        page_content = content_lower[page_start:]
        self.assertNotIn("/applications/add/", page_content)
        self.assertNotIn("pre-fill add application", page_content)

    def test_invalid_post_and_get_do_not_evaluate(self):
        self._create_entry(
            self.owner,
            "Python",
            SkillEntry.EvidenceLevel.VERIFIED,
        )
        self.client.login(username="p111c2_owner", password="pass")
        before_counts = self._model_counts()

        paths = (
            ("get", lambda: self.client.get(self.url)),
            (
                "invalid_post",
                lambda: self.client.post(self.url, {"requirements": "\n\n"}),
            ),
        )
        for label, request_callable in paths:
            with self.subTest(path=label):
                with (
                    patch(
                        "apps.skill_gaps.deterministic_gap_views.classify_requirements"
                    ) as mock_classify,
                    patch(
                        "apps.skill_gaps.deterministic_gap_views."
                        "summarise_evidence_alignment"
                    ) as mock_summarise,
                ):
                    response = request_callable()
                    mock_classify.assert_not_called()
                    mock_summarise.assert_not_called()

                self.assertEqual(response.status_code, 200)
                self.assertFalse(response.context["analysis_performed"])
                self.assertIsNone(response.context["summary"])
                self.assertEqual(response.context["results"], ())
                self.assertEqual(self._model_counts(), before_counts)
                if label == "invalid_post":
                    self.assertTrue(response.context["form"].errors)

    def test_route_succeeds_with_network_blocked(self):
        self._create_entry(
            self.owner,
            "Python",
            SkillEntry.EvidenceLevel.VERIFIED,
        )
        self.client.login(username="p111c2_owner", password="pass")
        before_counts = self._model_counts()

        with (
            patch.object(
                socket,
                "create_connection",
                side_effect=AssertionError(
                    "network create_connection must not be called"
                ),
            ) as mock_create_connection,
            patch.object(
                socket.socket,
                "connect",
                side_effect=AssertionError(
                    "network socket.connect must not be called"
                ),
            ) as mock_socket_connect,
        ):
            response = self.client.post(
                self.url,
                {"requirements": "Python\nGraphQL"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["analysis_performed"])
        summary = response.context["summary"]
        results = response.context["results"]
        self.assertIsNotNone(summary)
        self.assertEqual(
            summary.outcome,
            EvidenceAlignmentOutcome.SOME_REQUIREMENTS_VERIFIED,
        )
        self.assertEqual(summary.triggered_rule, "rule_4_some_requirements_verified")
        self.assertEqual(summary.rule_version, EXPECTED_RULE_VERSION)
        self.assertEqual(len(results), 2)
        self.assertEqual(
            tuple(row.original_text for row in results),
            ("Python", "GraphQL"),
        )
        mock_create_connection.assert_not_called()
        mock_socket_connect.assert_not_called()
        self.assertEqual(self._model_counts(), before_counts)
        content_lower = response.content.decode("utf-8").lower()
        self.assertNotIn("provider_factory", content_lower)
        self.assertNotIn("openai", content_lower)
        self.assertNotIn("anthropic", content_lower)

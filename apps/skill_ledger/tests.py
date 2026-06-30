from dataclasses import FrozenInstanceError, asdict, replace
from io import StringIO

from django.apps import apps
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.core.management import call_command
from django.test import TestCase
from django.urls import resolve, reverse
from django.utils import timezone

from .advisory import (
    ADVISORY_CLASSIFICATIONS,
    ADVISORY_ROW_FIELDS,
    REQUIRED_JD_SIGNAL_SAFETY_WORDING,
    REQUIRED_SKILL_ADVISORY_SAFETY_WORDING,
    SkillAdvisoryValidationError,
    advisory_row_to_template_dict,
    build_skill_advisory_row,
    build_skill_advisory_rows,
    collect_jd_candidate_terms,
    validate_advisory_classification,
    validate_skill_advisory_row_schema,
)
from .ai_explanation import (
    FORBIDDEN_EXPLANATION_PHRASES,
    REQUIRED_EXPLANATION_SAFETY_WARNING,
    SPRINT_87_PROVIDER_MODE_MOCKED,
    SkillAdvisoryExplanation,
    build_skill_advisory_explanation,
    build_skill_advisory_explanations,
    explanation_to_dict,
    validate_explanation,
)
from .management.commands.seed_skill_ledger import LEARNING_TARGET_NOTES, VERIFIED_DEFAULT_NOTES
from .mocked_ai_response_evaluator import (
    AUTO_ACTION_DETECTED,
    CERTIFICATION_GUARANTEE,
    EMPLOYER_OUTCOME_PREDICTION,
    EMPTY_RESPONSE,
    EVALUATION_FORBIDDEN_PHRASES,
    GENERATED_DOCUMENT_DETECTED,
    JD_SIGNAL_AS_PROFICIENCY,
    LEARNING_TARGET_INFLATION,
    LIVE_PROVIDER_IMPLICATION,
    MUTATION_CLAIM_DETECTED,
    EvaluationFinding,
    MockedAIResponseEvaluation,
    evaluate_mocked_ai_response,
)
from .models import SkillEntry


class SkillLedgerAdvisoryServiceTests(TestCase):
    def _entry(self, **overrides):
        entry = {
            "skill_name": "Python",
            "category": SkillEntry.Category.PROGRAMMING,
            "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
            "sprint_reference": "Sprint 84",
            "project_link": "https://example.com/python",
            "visibility": SkillEntry.Visibility.PRIVATE,
        }
        entry.update(overrides)
        return entry

    def _row(self, **overrides):
        return build_skill_advisory_row(self._entry(**overrides))

    def test_skill_advisory_row_schema_has_required_fields(self):
        row = self._row()
        row_dict = advisory_row_to_template_dict(row)

        self.assertEqual(tuple(row_dict.keys()), ADVISORY_ROW_FIELDS)
        self.assertEqual(
            tuple(row.__dataclass_fields__),
            ADVISORY_ROW_FIELDS,
        )

    def test_skill_advisory_row_rejects_extra_fields(self):
        row_dict = advisory_row_to_template_dict(self._row())
        row_dict["extra"] = "not allowed"

        with self.assertRaisesMessage(SkillAdvisoryValidationError, "extra_schema_keys"):
            validate_skill_advisory_row_schema(row_dict)

    def test_classification_set_is_complete_and_bounded(self):
        expected = {
            "VERIFIED_WITH_EVIDENCE": "Verified - sprint evidence present",
            "VERIFIED_NO_REFERENCE": "Verified - add sprint reference",
            "LEARNING_TARGET": "Learning target - do not claim as verified",
            "STUDYING": "Studying - personal study only",
            "NO_EVIDENCE": "Gap identified - do not claim",
            "PUBLIC_RISK": "Public visibility risk - review before publishing",
            "JD_SIGNAL_UNMATCHED": "Appears in JDs - not yet in ledger",
            "CLAIM_SAFE": "Safe to discuss - evidence confirmed",
        }

        self.assertEqual(ADVISORY_CLASSIFICATIONS, expected)
        for classification in ADVISORY_CLASSIFICATIONS:
            self.assertEqual(validate_advisory_classification(classification), classification)
        with self.assertRaisesMessage(
            SkillAdvisoryValidationError,
            "invalid_advisory_classification",
        ):
            validate_advisory_classification("OTHER")

    def test_advisory_classifies_verified_with_sprint_reference(self):
        row = self._row(project_link="")

        self.assertEqual(row.classification, "VERIFIED_WITH_EVIDENCE")
        self.assertFalse(row.claim_ready)
        self.assertTrue(row.manual_review_required)

    def test_advisory_classifies_verified_without_sprint_reference(self):
        row = self._row(sprint_reference="", project_link="https://example.com/python")

        self.assertEqual(row.classification, "VERIFIED_NO_REFERENCE")
        self.assertFalse(row.claim_ready)
        self.assertTrue(row.manual_review_required)

    def test_advisory_classifies_learning_target(self):
        row = self._row(evidence_level=SkillEntry.EvidenceLevel.LEARNING_TARGET)

        self.assertEqual(row.classification, "LEARNING_TARGET")
        self.assertFalse(row.claim_ready)

    def test_advisory_classifies_studying(self):
        row = self._row(evidence_level=SkillEntry.EvidenceLevel.STUDYING)

        self.assertEqual(row.classification, "STUDYING")
        self.assertFalse(row.claim_ready)

    def test_advisory_classifies_no_evidence(self):
        row = self._row(evidence_level=SkillEntry.EvidenceLevel.NO_EVIDENCE)

        self.assertEqual(row.classification, "NO_EVIDENCE")
        self.assertFalse(row.claim_ready)

    def test_advisory_classifies_public_visibility_risk(self):
        row = self._row(
            evidence_level=SkillEntry.EvidenceLevel.LEARNING_TARGET,
            visibility=SkillEntry.Visibility.PUBLIC,
        )

        self.assertEqual(row.classification, "PUBLIC_RISK")
        self.assertTrue(row.public_visibility_risk)
        self.assertFalse(row.claim_ready)
        self.assertTrue(row.manual_review_required)

    def test_advisory_classifies_jd_signal_unmatched(self):
        rows = build_skill_advisory_rows(
            (self._entry(skill_name="Python"),),
            jd_candidate_terms=("Airflow",),
        )

        unmatched = rows[-1]
        self.assertEqual(unmatched.skill_name, "Airflow")
        self.assertEqual(unmatched.classification, "JD_SIGNAL_UNMATCHED")
        self.assertTrue(unmatched.jd_candidate_match)
        self.assertFalse(unmatched.claim_ready)

    def test_advisory_classifies_claim_safe_when_all_evidence_present(self):
        row = self._row()

        self.assertEqual(row.classification, "CLAIM_SAFE")
        self.assertTrue(row.claim_ready)
        self.assertFalse(row.manual_review_required)

    def test_advisory_marks_learning_target_claim_ready_false(self):
        row = self._row(evidence_level=SkillEntry.EvidenceLevel.LEARNING_TARGET)

        self.assertFalse(row.claim_ready)
        self.assertTrue(row.manual_review_required)

    def test_advisory_marks_studying_claim_ready_false(self):
        row = self._row(evidence_level=SkillEntry.EvidenceLevel.STUDYING)

        self.assertFalse(row.claim_ready)
        self.assertTrue(row.manual_review_required)

    def test_advisory_marks_no_evidence_claim_ready_false(self):
        row = self._row(evidence_level=SkillEntry.EvidenceLevel.NO_EVIDENCE)

        self.assertFalse(row.claim_ready)
        self.assertTrue(row.manual_review_required)

    def test_advisory_marks_verified_no_reference_claim_ready_false(self):
        row = self._row(sprint_reference="")

        self.assertEqual(row.classification, "VERIFIED_NO_REFERENCE")
        self.assertFalse(row.claim_ready)
        self.assertTrue(row.manual_review_required)

    def test_advisory_never_sets_manual_review_false_for_gap(self):
        for evidence_level in (
            SkillEntry.EvidenceLevel.LEARNING_TARGET,
            SkillEntry.EvidenceLevel.STUDYING,
            SkillEntry.EvidenceLevel.NO_EVIDENCE,
        ):
            with self.subTest(evidence_level=evidence_level):
                self.assertTrue(self._row(evidence_level=evidence_level).manual_review_required)

    def test_advisory_service_does_not_write_to_skill_entry(self):
        entry = SkillEntry.objects.create(
            skill_name="Python",
            category=SkillEntry.Category.PROGRAMMING,
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
            sprint_reference="Sprint 84",
            project_link="https://example.com/python",
            visibility=SkillEntry.Visibility.PRIVATE,
            notes="Private note.",
        )
        before_values = SkillEntry.objects.values().get(pk=entry.pk)

        row = build_skill_advisory_row(entry)
        entry.refresh_from_db()

        self.assertEqual(row.classification, "CLAIM_SAFE")
        self.assertEqual(SkillEntry.objects.values().get(pk=entry.pk), before_values)

    def test_advisory_service_does_not_write_to_database(self):
        SkillEntry.objects.create(skill_name="Python")
        before_count = SkillEntry.objects.count()

        rows = build_skill_advisory_rows((), jd_candidate_terms=("Airflow",))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].classification, "JD_SIGNAL_UNMATCHED")
        self.assertEqual(SkillEntry.objects.count(), before_count)

    def test_advisory_service_accepts_empty_ledger_gracefully(self):
        self.assertEqual(build_skill_advisory_rows(()), ())

    def test_advisory_service_accepts_no_jd_candidates_gracefully(self):
        rows = build_skill_advisory_rows((self._entry(skill_name="Python"),))

        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0].jd_candidate_match)

    def test_advisory_safety_wording_is_preserved_exactly(self):
        expected = (
            "Skill Ledger advisory signals are planning aids only.",
            (
                "A skill is claim-ready only when supported by verified project evidence, "
                "tests, screenshots, or prior work experience."
            ),
            "Learning targets must not be presented as verified skills.",
            "JD requirement signals do not prove proficiency.",
            (
                "Review evidence manually before adding any skill to your CV, LinkedIn, "
                "or public profile."
            ),
            "This page does not update your Skill Ledger automatically.",
            (
                "Classifications are generated from your Skill Ledger fields using "
                "deterministic rules, not AI inference."
            ),
            (
                "Public visibility risk means a Skill Ledger entry is set to public but "
                "does not have confirmed evidence. Review before sharing."
            ),
        )

        self.assertEqual(REQUIRED_SKILL_ADVISORY_SAFETY_WORDING, expected)

    def test_advisory_generated_text_avoids_forbidden_phrases(self):
        rows = build_skill_advisory_rows(
            (
                self._entry(),
                self._entry(
                    skill_name="Snowflake",
                    evidence_level=SkillEntry.EvidenceLevel.LEARNING_TARGET,
                    visibility=SkillEntry.Visibility.PUBLIC,
                ),
            ),
            jd_candidate_terms=("Airflow",),
        )
        generated_text = " ".join(
            (
                *ADVISORY_CLASSIFICATIONS.values(),
                *REQUIRED_SKILL_ADVISORY_SAFETY_WORDING,
                *(row.advisory_note for row in rows),
                *(row.action_hint for row in rows),
            ),
        ).lower()

        for forbidden in (
            "employer ready",
            "job ready",
            "you meet the requirements",
            "verified by employer",
            "certified",
            "guaranteed",
            "you are qualified",
            "this proves proficiency",
            "ai verified",
            "automatically verified",
            "skill confirmed",
            "ready to apply",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, generated_text)


class SkillLedgerAIExplanationServiceTests(TestCase):
    def _entry(self, **overrides):
        entry = {
            "skill_name": "Python",
            "category": SkillEntry.Category.PROGRAMMING,
            "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
            "sprint_reference": "Sprint 84",
            "project_link": "https://example.com/python",
            "visibility": SkillEntry.Visibility.PRIVATE,
        }
        entry.update(overrides)
        return entry

    def _row(self, **overrides):
        return build_skill_advisory_row(self._entry(**overrides))

    def _golden_rows_by_classification(self):
        rows = {
            "VERIFIED_WITH_EVIDENCE": self._row(project_link=""),
            "VERIFIED_NO_REFERENCE": self._row(sprint_reference=""),
            "LEARNING_TARGET": self._row(
                evidence_level=SkillEntry.EvidenceLevel.LEARNING_TARGET,
            ),
            "STUDYING": self._row(evidence_level=SkillEntry.EvidenceLevel.STUDYING),
            "NO_EVIDENCE": self._row(evidence_level=SkillEntry.EvidenceLevel.NO_EVIDENCE),
            "PUBLIC_RISK": self._row(
                evidence_level=SkillEntry.EvidenceLevel.LEARNING_TARGET,
                visibility=SkillEntry.Visibility.PUBLIC,
            ),
            "CLAIM_SAFE": self._row(),
        }
        rows["JD_SIGNAL_UNMATCHED"] = build_skill_advisory_rows(
            (),
            jd_candidate_terms=("Airflow",),
        )[0]
        return rows

    def _valid_explanation(self):
        return build_skill_advisory_explanation(self._row())

    def test_skill_advisory_explanation_schema_is_frozen(self):
        explanation = self._valid_explanation()

        with self.assertRaises(FrozenInstanceError):
            explanation.skill_name = "Changed"

    def test_skill_advisory_explanation_rejects_none_fields(self):
        for field_name in SkillAdvisoryExplanation.__dataclass_fields__:
            with self.subTest(field_name=field_name):
                explanation = replace(self._valid_explanation(), **{field_name: None})

                with self.assertRaises(SkillAdvisoryValidationError):
                    validate_explanation(explanation)

    def test_skill_advisory_explanation_provider_mode_is_constant(self):
        self.assertEqual(SPRINT_87_PROVIDER_MODE_MOCKED, "mocked")

        explanation = self._valid_explanation()

        self.assertEqual(explanation.provider_mode, SPRINT_87_PROVIDER_MODE_MOCKED)

    def test_explanation_for_verified_with_evidence(self):
        explanation = build_skill_advisory_explanation(
            self._golden_rows_by_classification()["VERIFIED_WITH_EVIDENCE"],
        )

        self.assertEqual(explanation.classification, "VERIFIED_WITH_EVIDENCE")
        self.assertIn("Sprint evidence is present", explanation.evidence_basis)
        self.assertIn(REQUIRED_EXPLANATION_SAFETY_WARNING, explanation.claim_safety_warning)

    def test_explanation_for_verified_no_reference(self):
        explanation = build_skill_advisory_explanation(
            self._golden_rows_by_classification()["VERIFIED_NO_REFERENCE"],
        )

        self.assertEqual(explanation.classification, "VERIFIED_NO_REFERENCE")
        self.assertIn("Verified status needs a sprint reference", explanation.evidence_basis)

    def test_explanation_for_learning_target(self):
        explanation = build_skill_advisory_explanation(
            self._golden_rows_by_classification()["LEARNING_TARGET"],
        )

        self.assertEqual(explanation.classification, "LEARNING_TARGET")
        self.assertIn("learning target", explanation.evidence_basis.lower())

    def test_explanation_for_studying(self):
        explanation = build_skill_advisory_explanation(
            self._golden_rows_by_classification()["STUDYING"],
        )

        self.assertEqual(explanation.classification, "STUDYING")
        self.assertIn("personal study", explanation.evidence_basis)

    def test_explanation_for_no_evidence(self):
        explanation = build_skill_advisory_explanation(
            self._golden_rows_by_classification()["NO_EVIDENCE"],
        )

        self.assertEqual(explanation.classification, "NO_EVIDENCE")
        self.assertIn("No supporting evidence", explanation.evidence_basis)

    def test_explanation_for_public_risk(self):
        explanation = build_skill_advisory_explanation(
            self._golden_rows_by_classification()["PUBLIC_RISK"],
        )

        self.assertEqual(explanation.classification, "PUBLIC_RISK")
        self.assertIn("public entry", explanation.evidence_basis)

    def test_explanation_for_jd_signal_unmatched(self):
        explanation = build_skill_advisory_explanation(
            self._golden_rows_by_classification()["JD_SIGNAL_UNMATCHED"],
        )

        self.assertEqual(explanation.classification, "JD_SIGNAL_UNMATCHED")
        self.assertIn("JD signal context is present", explanation.jd_signal_context)

    def test_explanation_for_claim_safe(self):
        explanation = build_skill_advisory_explanation(
            self._golden_rows_by_classification()["CLAIM_SAFE"],
        )

        self.assertEqual(explanation.classification, "CLAIM_SAFE")
        self.assertIn("Verified project evidence", explanation.evidence_basis)

    def test_explanation_for_jd_signal_present_evidence_missing(self):
        row = build_skill_advisory_rows(
            (
                self._entry(
                    skill_name="Airflow",
                    evidence_level=SkillEntry.EvidenceLevel.NO_EVIDENCE,
                ),
            ),
            jd_candidate_terms=("Airflow",),
        )[0]

        explanation = build_skill_advisory_explanation(row)

        self.assertEqual(explanation.classification, "NO_EVIDENCE")
        self.assertIn("JD signal context is present", explanation.jd_signal_context)
        self.assertIn(REQUIRED_EXPLANATION_SAFETY_WARNING, explanation.claim_safety_warning)

    def test_explanation_for_jd_signal_present_verified_evidence(self):
        row = build_skill_advisory_rows(
            (self._entry(skill_name="Python"),),
            jd_candidate_terms=("Python",),
        )[0]

        explanation = build_skill_advisory_explanation(row)

        self.assertEqual(explanation.classification, "CLAIM_SAFE")
        self.assertIn("JD signal context is present", explanation.jd_signal_context)
        self.assertIn(REQUIRED_EXPLANATION_SAFETY_WARNING, explanation.claim_safety_warning)

    def test_explanation_claim_safety_warning_never_empty(self):
        for row in self._golden_rows_by_classification().values():
            with self.subTest(classification=row.classification):
                explanation = build_skill_advisory_explanation(row)

                self.assertTrue(explanation.claim_safety_warning)
                self.assertIn(
                    REQUIRED_EXPLANATION_SAFETY_WARNING,
                    explanation.claim_safety_warning,
                )

    def test_validator_rejects_explanation_with_empty_warning(self):
        explanation = replace(self._valid_explanation(), claim_safety_warning="")

        with self.assertRaisesMessage(
            SkillAdvisoryValidationError,
            "claim_safety_warning_required",
        ):
            validate_explanation(explanation)

    def test_forbidden_phrases_absent_from_all_golden_cases(self):
        explanations = tuple(
            build_skill_advisory_explanation(row)
            for row in self._golden_rows_by_classification().values()
        )
        generated_text = " ".join(
            " ".join(explanation_to_dict(explanation).values())
            for explanation in explanations
        ).lower()

        for forbidden in FORBIDDEN_EXPLANATION_PHRASES:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, generated_text)

    def test_explanation_service_does_not_write_to_skill_entry(self):
        entry = SkillEntry.objects.create(
            skill_name="Python",
            category=SkillEntry.Category.PROGRAMMING,
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
            sprint_reference="Sprint 84",
            project_link="https://example.com/python",
            visibility=SkillEntry.Visibility.PRIVATE,
            notes="Private note.",
        )
        row = build_skill_advisory_row(entry)
        before_values = SkillEntry.objects.values().get(pk=entry.pk)

        explanation = build_skill_advisory_explanation(row)
        entry.refresh_from_db()

        self.assertEqual(explanation.classification, "CLAIM_SAFE")
        self.assertEqual(SkillEntry.objects.values().get(pk=entry.pk), before_values)

    def test_explanation_service_does_not_write_to_database(self):
        row = self._row()
        before_count = SkillEntry.objects.count()

        with self.assertNumQueries(0):
            explanation = build_skill_advisory_explanation(row)

        self.assertEqual(explanation.classification, "CLAIM_SAFE")
        self.assertEqual(SkillEntry.objects.count(), before_count)

    def test_explanation_provider_mode_is_mocked_in_sprint_87(self):
        explanation = self._valid_explanation()

        self.assertEqual(explanation.provider_mode, "mocked")
        with self.assertRaisesMessage(SkillAdvisoryValidationError, "invalid_provider_mode"):
            validate_explanation(replace(explanation, provider_mode="live"))

    def test_explanation_service_accepts_empty_jd_signal_context(self):
        explanation = build_skill_advisory_explanation(self._row())

        self.assertEqual(explanation.jd_signal_context, "")
        self.assertEqual(validate_explanation(explanation), explanation)

    def test_sprint_85_classifications_unchanged_for_explanation_contract(self):
        self.assertEqual(
            tuple(ADVISORY_CLASSIFICATIONS),
            (
                "VERIFIED_WITH_EVIDENCE",
                "VERIFIED_NO_REFERENCE",
                "LEARNING_TARGET",
                "STUDYING",
                "NO_EVIDENCE",
                "PUBLIC_RISK",
                "JD_SIGNAL_UNMATCHED",
                "CLAIM_SAFE",
            ),
        )

    def test_explanation_builder_returns_tuple_without_mutating_rows(self):
        rows = tuple(self._golden_rows_by_classification().values())
        before_rows = tuple(asdict(row) for row in rows)

        explanations = build_skill_advisory_explanations(rows)

        self.assertIsInstance(explanations, tuple)
        self.assertEqual(len(explanations), len(rows))
        self.assertEqual(tuple(asdict(row) for row in rows), before_rows)

    def test_explanation_to_dict_returns_only_contract_fields(self):
        explanation = self._valid_explanation()

        explanation_dict = explanation_to_dict(explanation)

        self.assertEqual(
            tuple(explanation_dict),
            tuple(SkillAdvisoryExplanation.__dataclass_fields__),
        )
        self.assertNotIn("row", explanation_dict)
        self.assertNotIn("application", explanation_dict)

    def test_validator_rejects_non_explanation_input(self):
        with self.assertRaisesMessage(
            SkillAdvisoryValidationError,
            "invalid_explanation_type",
        ):
            validate_explanation({"skill_name": "Python"})

    def test_validator_rejects_non_string_field_values(self):
        explanation = replace(self._valid_explanation(), skill_name=123)

        with self.assertRaisesMessage(
            SkillAdvisoryValidationError,
            "skill_name_must_be_string",
        ):
            validate_explanation(explanation)

    def test_validator_rejects_forbidden_phrases_case_insensitively(self):
        explanation = replace(
            self._valid_explanation(),
            confidence_boundary="This proves proficiency.",
        )

        with self.assertRaisesMessage(
            SkillAdvisoryValidationError,
            "forbidden_explanation_phrase",
        ):
            validate_explanation(explanation)

    def test_explanation_service_does_not_require_application_imports(self):
        self.assertNotIn(
            "JobApplication",
            build_skill_advisory_explanation.__code__.co_names,
        )
        self.assertNotIn("applications", build_skill_advisory_explanation.__code__.co_names)


class SkillLedgerAdvisoryPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="advisoryuser", password="StrongPass12345")
        self.url = reverse("skill_ledger:advisory")

    def _login(self):
        self.client.login(username="advisoryuser", password="StrongPass12345")

    def _create_skill_entry(self, **overrides):
        defaults = {
            "skill_name": "Python",
            "category": SkillEntry.Category.PROGRAMMING,
            "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
            "sprint_reference": "Sprint 84",
            "project_link": "https://example.com/python",
            "notes": "Private note must not render.",
            "visibility": SkillEntry.Visibility.PRIVATE,
        }
        defaults.update(overrides)
        return SkillEntry.objects.create(**defaults)

    def test_skill_ledger_advisory_page_loads_for_authenticated_user(self):
        self._create_skill_entry()
        self._login()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Skill Ledger Advisory")
        self.assertContains(response, "Safe to discuss - evidence confirmed")

    def test_skill_ledger_advisory_page_redirects_anonymous_user(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response["Location"])

    def test_skill_ledger_advisory_page_is_get_only(self):
        self._login()

        response = self.client.post(self.url, {"skill_name": "Python"})

        self.assertEqual(response.status_code, 405)

    def test_skill_ledger_advisory_page_shows_advisory_wording(self):
        self._create_skill_entry()
        self._login()

        response = self.client.get(self.url)

        for wording in REQUIRED_SKILL_ADVISORY_SAFETY_WORDING:
            with self.subTest(wording=wording):
                self.assertContains(response, wording)
        self.assertContains(response, "Classifications are deterministic rules, not AI inference.")

    def test_skill_ledger_advisory_page_shows_claim_ready_false_for_gaps(self):
        self._create_skill_entry(
            skill_name="GraphQL",
            evidence_level=SkillEntry.EvidenceLevel.NO_EVIDENCE,
            sprint_reference="",
            project_link="",
        )
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, "GraphQL")
        self.assertContains(response, "Gap identified - do not claim")
        self.assertContains(response, "Claim ready: No")
        self.assertContains(response, "Manual review required: Yes")

    def test_skill_ledger_advisory_page_does_not_imply_employer_readiness(self):
        self._create_skill_entry()
        self._login()

        response = self.client.get(self.url)
        content = response.content.decode()

        for forbidden in (
            "Employer ready",
            "Job ready",
            "You meet the requirements",
            "Verified by employer",
            "Certified",
            "Guaranteed",
            "You are qualified",
            "This proves proficiency",
            "AI verified",
            "Automatically verified",
            "Skill confirmed",
            "Ready to apply",
            "provider output",
            "AI output",
            "raw provider output",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, content)

    def test_skill_ledger_advisory_page_does_not_save_output(self):
        entry = self._create_skill_entry()
        JobApplication = apps.get_model("applications", "JobApplication")
        application = JobApplication.objects.create(
            user=self.user,
            company_name="Private Employer",
            job_title="Private Analyst",
            date_applied=timezone.localdate(),
            job_description="Private JD text.",
        )
        before_entry_count = SkillEntry.objects.count()
        before_application_count = JobApplication.objects.count()
        before_entry_values = SkillEntry.objects.values().get(pk=entry.pk)
        before_application_values = JobApplication.objects.values().get(pk=application.pk)
        self._login()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(SkillEntry.objects.count(), before_entry_count)
        self.assertEqual(JobApplication.objects.count(), before_application_count)
        self.assertEqual(SkillEntry.objects.values().get(pk=entry.pk), before_entry_values)
        self.assertEqual(
            JobApplication.objects.values().get(pk=application.pk),
            before_application_values,
        )
        self.assertNotIn("skill_ledger_advisory_output", self.client.session.keys())
        self.assertNotIn("provider_response", self.client.session.keys())

    def test_skill_ledger_advisory_page_does_not_update_skill_entries(self):
        entry = self._create_skill_entry(
            evidence_level=SkillEntry.EvidenceLevel.LEARNING_TARGET,
            visibility=SkillEntry.Visibility.PUBLIC,
        )
        before_values = SkillEntry.objects.values().get(pk=entry.pk)
        self._login()

        response = self.client.get(self.url)
        entry.refresh_from_db()
        advisory_section = response.content.decode().split('<div class="cf85-page"', 1)[1]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(SkillEntry.objects.values().get(pk=entry.pk), before_values)
        self.assertEqual(entry.evidence_level, SkillEntry.EvidenceLevel.LEARNING_TARGET)
        self.assertEqual(entry.visibility, SkillEntry.Visibility.PUBLIC)
        self.assertNotIn("<form", advisory_section)
        self.assertNotIn("<button", advisory_section)
        self.assertNotIn("Save", advisory_section)

    def test_skill_ledger_advisory_page_shows_public_risk_warning(self):
        self._create_skill_entry(
            skill_name="Snowflake",
            evidence_level=SkillEntry.EvidenceLevel.LEARNING_TARGET,
            visibility=SkillEntry.Visibility.PUBLIC,
        )
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, "Snowflake")
        self.assertContains(response, "Public visibility risk - review before publishing")
        self.assertContains(response, "Public visibility risk: Yes")
        self.assertContains(response, "This public entry does not have confirmed evidence.")

    def test_skill_ledger_advisory_page_jd_match_shown_as_advisory_only(self):
        self._create_skill_entry()
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, "JD candidate match: No - advisory context only.")
        self.assertContains(
            response,
            "No JD signal candidate terms met the deterministic frequency threshold.",
        )
        self.assertContains(response, "JD requirement signals do not prove proficiency.")
        self.assertNotContains(response, "This proves proficiency")


class SkillLedgerAdvisoryClassificationKeyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="classificationkeyuser",
            password="StrongPass12345",
        )
        self.url = reverse("skill_ledger:advisory")

    def _login(self):
        self.client.login(username="classificationkeyuser", password="StrongPass12345")

    def _create_skill_entry(self, **overrides):
        defaults = {
            "skill_name": "Python",
            "category": SkillEntry.Category.PROGRAMMING,
            "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
            "sprint_reference": "Sprint 84",
            "project_link": "https://example.com/python",
            "visibility": SkillEntry.Visibility.PRIVATE,
        }
        defaults.update(overrides)
        return SkillEntry.objects.create(**defaults)

    def _get_advisory_page(self):
        self._create_skill_entry()
        self._login()
        return self.client.get(self.url)

    def test_advisory_page_classification_key_section_renders(self):
        response = self._get_advisory_page()

        self.assertContains(response, "Classification key")
        self.assertContains(
            response,
            (
                "Classifications are deterministic - derived from your Skill Ledger "
                "evidence_level and visibility fields. They are not AI-generated assessments."
            ),
        )

    def test_advisory_page_classification_key_shows_verified_label(self):
        response = self._get_advisory_page()

        self.assertContains(response, "VERIFIED WITH EVIDENCE")
        self.assertContains(response, "sprint evidence present, safe to discuss")
        self.assertContains(response, "VERIFIED NO REFERENCE")
        self.assertContains(response, "add a sprint reference to strengthen claim")

    def test_advisory_page_classification_key_shows_learning_target_label(self):
        response = self._get_advisory_page()

        self.assertContains(response, "LEARNING TARGET")
        self.assertContains(response, "do not claim as verified")

    def test_advisory_page_classification_key_shows_studying_label(self):
        response = self._get_advisory_page()

        self.assertContains(response, "STUDYING")
        self.assertContains(response, "personal study only, not claim-ready")

    def test_advisory_page_classification_key_shows_no_evidence_label(self):
        response = self._get_advisory_page()

        self.assertContains(response, "NO EVIDENCE")
        self.assertContains(response, "gap identified, do not claim")

    def test_advisory_page_classification_key_shows_public_risk_label(self):
        response = self._get_advisory_page()

        self.assertContains(response, "PUBLIC RISK")
        self.assertContains(response, "public visibility set but evidence incomplete")

    def test_advisory_page_classification_key_shows_claim_safe_label(self):
        response = self._get_advisory_page()

        self.assertContains(response, "CLAIM SAFE")
        self.assertContains(response, "evidence confirmed, safe to discuss")

    def test_advisory_page_classification_key_shows_jd_signal_unmatched_label(self):
        response = self._get_advisory_page()

        self.assertContains(response, "JD SIGNAL UNMATCHED")
        self.assertContains(response, "appears in JDs, not yet in your ledger")

    def test_advisory_page_existing_safety_wording_survives_sprint_94(self):
        response = self._get_advisory_page()

        for wording in (
            "Skill Ledger advisory signals are planning aids only.",
            (
                "A skill is claim-ready only when supported by verified project evidence, "
                "tests, screenshots, or prior work experience."
            ),
            "Learning targets must not be presented as verified skills.",
            "JD requirement signals do not prove proficiency.",
            (
                "Review evidence manually before adding any skill to your CV, LinkedIn, "
                "or public profile."
            ),
            "This page does not update your Skill Ledger automatically.",
            (
                "Classifications are generated from your Skill Ledger fields using "
                "deterministic rules, not AI inference."
            ),
        ):
            with self.subTest(wording=wording):
                self.assertContains(response, wording)

    def test_advisory_page_jd_signal_wording_survives_sprint_94(self):
        response = self._get_advisory_page()

        self.assertContains(response, "JD signal context is advisory only.")
        self.assertContains(response, "A JD signal does not prove proficiency.")

    def test_advisory_page_forbidden_phrases_still_absent_after_sprint_94(self):
        response = self._get_advisory_page()
        content = response.content.decode().lower()
        forbidden_phrases = (
            "employer confirmed",
            "you are qualified",
            "job ready",
            "employer ready",
            "this proves proficiency",
            "ai verified",
            "automatically verified",
            "skill confirmed",
            "ready to apply",
            "you meet the requirements",
            "this jd signal verifies",
            "proficiency confirmed",
            "ai confirmed",
            "ai has assessed your skill",
            "employer-ready",
            "profile updated",
            "cv updated",
            "application submitted",
            "auto-save",
            "auto-apply",
            "production ai",
            "live ai monitoring",
            "real-time ai metrics",
            "claim-ready skill",
            "verified by ai",
            "verified by jd",
            "automatically classified",
            "ai assessed",
        )

        for forbidden in forbidden_phrases:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, content)

    def test_advisory_page_classification_key_does_not_imply_verification(self):
        response = self._get_advisory_page()
        content = response.content.decode().lower()

        self.assertContains(
            response,
            "They are not AI-generated assessments.",
        )
        self.assertNotIn("verified by ai", content)
        self.assertNotIn("verified by jd", content)
        self.assertNotIn("ai assessed", content)
        self.assertNotIn("automatically classified", content)


class SkillLedgerAIExplanationPreviewPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="explanationuser",
            password="StrongPass12345",
        )
        self.url = reverse("skill_ledger:advisory_explanations")
        self.JobApplication = apps.get_model("applications", "JobApplication")

    def _login(self):
        self.client.login(username="explanationuser", password="StrongPass12345")

    def _jd_text(self, *terms, marker=""):
        intro = " ".join((*terms, marker)).strip()
        filler = " deterministic planning context" * 140
        return f"{intro} {filler}".strip()

    def _create_application(self, **overrides):
        defaults = {
            "user": self.user,
            "company_name": "Private Employer",
            "job_title": "Private Analyst",
            "date_applied": timezone.localdate(),
            "job_description": self._jd_text("python"),
            "job_url": "",
            "salary_range": "Private salary",
            "contact_name": "Private Contact",
            "contact_email": "private@example.com",
            "notes": "Private application note.",
        }
        defaults.update(overrides)
        return self.JobApplication.objects.create(**defaults)

    def _create_jd_ready_pair(self, term="python", marker=""):
        self._create_application(job_description=self._jd_text(term, marker=marker))
        self._create_application(
            company_name="Private Employer Two",
            job_description=self._jd_text(term, marker=marker),
        )

    def _create_skill_entry(self, **overrides):
        defaults = {
            "skill_name": "python",
            "category": SkillEntry.Category.PROGRAMMING,
            "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
            "sprint_reference": "Sprint 84",
            "project_link": "https://example.com/python",
            "notes": "Private note must not render.",
            "visibility": SkillEntry.Visibility.PRIVATE,
        }
        defaults.update(overrides)
        return SkillEntry.objects.create(**defaults)

    def test_explanation_preview_redirects_anonymous_user(self):
        response = self.client.get("/skill-ledger/advisory/explanations/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response["Location"])

    def test_explanation_preview_authenticated_user_receives_200(self):
        self._create_skill_entry()
        self._login()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_explanation_preview_route_name_resolves_correctly(self):
        self.assertEqual(self.url, "/skill-ledger/advisory/explanations/")

        match = resolve(self.url)

        self.assertEqual(match.view_name, "skill_ledger:advisory_explanations")

    def test_explanation_preview_renders_contract_heading(self):
        self._create_skill_entry()
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, "AI explanation contract preview")

    def test_explanation_preview_renders_provider_mode_mocked(self):
        self._create_skill_entry()
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, f"Provider mode: {SPRINT_87_PROVIDER_MODE_MOCKED}")

    def test_explanation_preview_renders_required_safety_warning(self):
        self._create_skill_entry()
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, REQUIRED_EXPLANATION_SAFETY_WARNING)

    def test_explanation_preview_renders_no_live_provider_output_wording(self):
        self._create_skill_entry()
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, "No live provider output is shown here.")

    def test_explanation_preview_renders_no_mutation_wording(self):
        self._create_skill_entry()
        self._login()

        response = self.client.get(self.url)

        self.assertContains(
            response,
            "This preview does not save, update, publish, or submit anything.",
        )

    def test_explanation_preview_renders_rows_for_existing_skill_entries(self):
        self._create_skill_entry(skill_name="python")
        self._create_skill_entry(
            skill_name="sql",
            evidence_level=SkillEntry.EvidenceLevel.NO_EVIDENCE,
            sprint_reference="",
            project_link="",
        )
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, "python")
        self.assertContains(response, "sql")
        self.assertContains(response, "Classification: CLAIM_SAFE")
        self.assertContains(response, "Classification: NO_EVIDENCE")
        self.assertContains(response, "Evidence basis:")
        self.assertContains(response, "Manual next action:")
        self.assertContains(response, "Source limitations:")
        self.assertContains(response, "Confidence boundary:")

    def test_explanation_preview_renders_jd_signal_context_safely(self):
        self._create_skill_entry(skill_name="python")
        self._create_jd_ready_pair("python")
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, "JD signal context:")
        self.assertContains(response, "Saved JD signal context is present")
        self.assertContains(response, "A JD signal does not prove proficiency.")

    def test_explanation_preview_does_not_render_raw_jd_text(self):
        self._create_skill_entry(skill_name="python")
        self._create_jd_ready_pair("python", marker="UNIQUE_PRIVATE_JD_SENTENCE")
        self._login()

        response = self.client.get(self.url)
        content = response.content.decode()

        self.assertContains(response, "JD signal context:")
        self.assertNotIn("UNIQUE_PRIVATE_JD_SENTENCE", content)
        self.assertNotIn("deterministic planning context", content)
        self.assertNotIn("Private Employer", content)
        self.assertNotIn("Private Analyst", content)

    def test_explanation_preview_post_is_not_allowed(self):
        self._login()

        response = self.client.post(self.url, {"skill_name": "python"})

        self.assertEqual(response.status_code, 405)

    def test_explanation_preview_does_not_mutate_skill_entries(self):
        entry = self._create_skill_entry(
            evidence_level=SkillEntry.EvidenceLevel.LEARNING_TARGET,
            visibility=SkillEntry.Visibility.PUBLIC,
        )
        before_count = SkillEntry.objects.count()
        before_values = SkillEntry.objects.values().get(pk=entry.pk)
        self._login()

        response = self.client.get(self.url)
        entry.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(SkillEntry.objects.count(), before_count)
        self.assertEqual(SkillEntry.objects.values().get(pk=entry.pk), before_values)
        self.assertEqual(entry.evidence_level, SkillEntry.EvidenceLevel.LEARNING_TARGET)
        self.assertEqual(entry.visibility, SkillEntry.Visibility.PUBLIC)

    def test_explanation_preview_forbidden_phrases_absent_from_rendered_page(self):
        self._create_skill_entry()
        self._login()

        response = self.client.get(self.url)
        content = response.content.decode().lower()
        forbidden_phrases = (
            *FORBIDDEN_EXPLANATION_PHRASES,
            "live provider output generated",
            "ai confirmed",
            "ai has assessed your skill",
            "ai says you are qualified",
            "employer-ready",
            "profile updated",
            "cv updated",
            "application submitted",
            "auto-save",
            "auto-apply",
        )

        for forbidden in forbidden_phrases:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, content)

    def test_explanation_preview_has_no_save_update_submit_or_publish_controls(self):
        self._create_skill_entry()
        self._login()

        response = self.client.get(self.url)
        content = response.content.decode().lower().split('<div class="cf88-page"', 1)[1]

        self.assertNotIn("<form", content)
        self.assertNotIn("<button", content)
        self.assertNotIn('type="submit"', content)
        self.assertNotIn('name="save"', content)
        self.assertNotIn('name="update"', content)
        self.assertNotIn('name="publish"', content)

    def test_explanation_preview_does_not_expose_provider_live_or_api_key_wording(self):
        self._create_skill_entry()
        self._login()

        response = self.client.get(self.url)
        content = response.content.decode().lower()

        for forbidden in (
            "openai",
            "anthropic",
            "api key",
            "secret key",
            "provider response",
            "raw provider output",
            "generated by a live provider",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, content)

    def test_existing_advisory_page_still_loads(self):
        self._create_skill_entry()
        self._login()

        response = self.client.get(reverse("skill_ledger:advisory"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Skill Ledger Advisory")

    def test_public_skill_ledger_remains_public_and_does_not_expose_explanations(self):
        self._create_skill_entry(visibility=SkillEntry.Visibility.PUBLIC)

        response = self.client.get(reverse("skill_ledger:public"))
        content = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "python")
        self.assertNotIn("AI explanation contract preview", content)
        self.assertNotIn("Claim safety warning:", content)
        self.assertNotIn(REQUIRED_EXPLANATION_SAFETY_WARNING, content)


class SkillLedgerAIExplanationEvidenceDashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="aievidenceuser",
            password="StrongPass12345",
        )
        self.url = reverse("skill_ledger:advisory_ai_evidence")
        self.JobApplication = apps.get_model("applications", "JobApplication")

    def _login(self):
        self.client.login(username="aievidenceuser", password="StrongPass12345")

    def _jd_text(self, *terms, marker=""):
        intro = " ".join((*terms, marker)).strip()
        filler = " deterministic planning context" * 140
        return f"{intro} {filler}".strip()

    def _create_application(self, **overrides):
        defaults = {
            "user": self.user,
            "company_name": "Private Employer",
            "job_title": "Private Analyst",
            "date_applied": timezone.localdate(),
            "job_description": self._jd_text("python"),
            "job_url": "",
            "salary_range": "Private salary",
            "contact_name": "Private Contact",
            "contact_email": "private@example.com",
            "notes": "Private application note.",
        }
        defaults.update(overrides)
        return self.JobApplication.objects.create(**defaults)

    def _create_jd_ready_pair(self, term="python", marker=""):
        self._create_application(job_description=self._jd_text(term, marker=marker))
        self._create_application(
            company_name="Private Employer Two",
            job_description=self._jd_text(term, marker=marker),
        )

    def _create_skill_entry(self, **overrides):
        defaults = {
            "skill_name": "python",
            "category": SkillEntry.Category.PROGRAMMING,
            "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
            "sprint_reference": "Sprint 84",
            "project_link": "https://example.com/python",
            "notes": "Private note must not render.",
            "visibility": SkillEntry.Visibility.PRIVATE,
        }
        defaults.update(overrides)
        return SkillEntry.objects.create(**defaults)

    def _dashboard_content(self):
        response = self.client.get(self.url)
        return response.content.decode()

    def test_ai_evidence_dashboard_loads_for_authenticated_user(self):
        self._create_skill_entry()
        self._login()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI explanation layer - safety controls and evidence")

    def test_ai_evidence_dashboard_redirects_anonymous_user(self):
        response = self.client.get("/skill-ledger/advisory/ai-evidence/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response["Location"])

    def test_ai_evidence_dashboard_is_get_only(self):
        self._login()

        response = self.client.post(self.url, {"provider_mode": "mocked"})

        self.assertEqual(response.status_code, 405)

    def test_ai_evidence_dashboard_shows_provider_mode_mocked(self):
        self._create_skill_entry()
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, f"Provider mode: {SPRINT_87_PROVIDER_MODE_MOCKED}")

    def test_ai_evidence_dashboard_shows_no_live_provider_configured(self):
        self._create_skill_entry()
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, "No live provider is configured for this sprint.")
        self.assertContains(response, "Live provider configured")
        self.assertContains(response, "API key configured")

    def test_ai_evidence_dashboard_shows_forbidden_phrase_count(self):
        self._create_skill_entry()
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, "Forbidden phrase count")
        self.assertContains(response, str(len(FORBIDDEN_EXPLANATION_PHRASES)))

    def test_ai_evidence_dashboard_shows_required_safety_warning_present(self):
        self._create_skill_entry()
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, "Required safety warning")
        self.assertContains(response, "Present")
        self.assertContains(response, REQUIRED_EXPLANATION_SAFETY_WARNING)

    def test_ai_evidence_dashboard_shows_skill_ledger_entry_count(self):
        self._create_skill_entry(skill_name="python")
        self._create_skill_entry(skill_name="sql")
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, "Skill Ledger entries")
        self.assertContains(response, "2")
        self.assertContains(response, "Advisory rows generated")
        self.assertContains(response, "Explanation rows available")

    def test_ai_evidence_dashboard_shows_no_mutation_boundary_status(self):
        self._create_skill_entry()
        self._login()

        response = self.client.get(self.url)

        self.assertContains(
            response,
            "This dashboard does not save, update, publish, submit, or mutate records.",
        )
        self.assertContains(response, "Mutation/save/update")
        self.assertContains(response, "Public exposure")
        self.assertContains(response, "CV/profile mutation")
        self.assertContains(response, "Background task")

    def test_ai_evidence_dashboard_does_not_render_raw_jd_text(self):
        self._create_skill_entry(skill_name="python")
        self._create_jd_ready_pair("python", marker="UNIQUE_PRIVATE_JD_SENTENCE")
        self._login()

        content = self._dashboard_content()

        self.assertIn("JD signal context terms", content)
        self.assertNotIn("UNIQUE_PRIVATE_JD_SENTENCE", content)
        self.assertNotIn("deterministic planning context", content)
        self.assertNotIn("Private Employer", content)
        self.assertNotIn("Private Analyst", content)

    def test_ai_evidence_dashboard_does_not_render_raw_provider_output(self):
        self._create_skill_entry()
        self._login()

        content = self._dashboard_content()

        self.assertIn("No raw provider output is stored or displayed.", content)
        self.assertNotIn("RAW_PROVIDER_PAYLOAD", content)
        self.assertNotIn("prompt text:", content.lower())
        self.assertNotIn("completion text:", content.lower())

    def test_ai_evidence_dashboard_does_not_imply_live_ai_monitoring(self):
        self._create_skill_entry()
        self._login()

        content = self._dashboard_content().lower()

        for forbidden in (
            "ai observability dashboard",
            "ai monitoring",
            "production ai telemetry",
            "real-time ai metrics",
            "live observability",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, content)

    def test_ai_evidence_dashboard_forbidden_phrases_absent(self):
        self._create_skill_entry()
        self._login()

        content = self._dashboard_content().lower()
        forbidden_phrases = (
            *FORBIDDEN_EXPLANATION_PHRASES,
            "ai confirmed",
            "ai has assessed your skill",
            "ai says you are qualified",
            "employer-ready",
            "profile updated",
            "cv updated",
            "application submitted",
            "auto-save",
        )

        for forbidden in forbidden_phrases:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, content)

    def test_sprint_88_explanations_page_unaffected(self):
        self._create_skill_entry()
        self._login()

        response = self.client.get(reverse("skill_ledger:advisory_explanations"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI explanation contract preview")
        self.assertContains(response, "Provider mode: mocked")


class SkillLedgerAIAdvisoryReviewHubTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="aireviewhubuser",
            password="StrongPass12345",
        )
        self.url = reverse("skill_ledger:advisory_ai_review_hub")
        self.JobApplication = apps.get_model("applications", "JobApplication")

    def _login(self):
        self.client.login(username="aireviewhubuser", password="StrongPass12345")

    def _jd_text(self, *terms, marker=""):
        intro = " ".join((*terms, marker)).strip()
        filler = " deterministic planning context" * 140
        return f"{intro} {filler}".strip()

    def _create_application(self, **overrides):
        defaults = {
            "user": self.user,
            "company_name": "Private Employer",
            "job_title": "Private Analyst",
            "date_applied": timezone.localdate(),
            "job_description": self._jd_text("python"),
            "job_url": "",
            "salary_range": "Private salary",
            "contact_name": "Private Contact",
            "contact_email": "private@example.com",
            "notes": "Private application note.",
        }
        defaults.update(overrides)
        return self.JobApplication.objects.create(**defaults)

    def _create_jd_ready_pair(self, term="python", marker=""):
        self._create_application(job_description=self._jd_text(term, marker=marker))
        self._create_application(
            company_name="Private Employer Two",
            job_description=self._jd_text(term, marker=marker),
        )

    def _create_skill_entry(self, **overrides):
        defaults = {
            "skill_name": "python",
            "category": SkillEntry.Category.PROGRAMMING,
            "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
            "sprint_reference": "Sprint 84",
            "project_link": "https://example.com/python",
            "notes": "Private note must not render.",
            "visibility": SkillEntry.Visibility.PRIVATE,
        }
        defaults.update(overrides)
        return SkillEntry.objects.create(**defaults)

    def _hub_content(self):
        response = self.client.get(self.url)
        return response.content.decode()

    def test_ai_review_hub_loads_for_authenticated_user(self):
        self._create_skill_entry()
        self._login()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI advisory review hub")

    def test_ai_review_hub_redirects_anonymous_user(self):
        response = self.client.get("/skill-ledger/advisory/ai-review-hub/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response["Location"])

    def test_ai_review_hub_post_returns_405(self):
        self._login()

        response = self.client.post(self.url, {"provider_mode": "mocked"})

        self.assertEqual(response.status_code, 405)

    def test_ai_review_hub_links_to_explanation_preview(self):
        self._create_skill_entry()
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, 'href="/skill-ledger/advisory/explanations/"')
        self.assertContains(response, "AI explanation preview")

    def test_ai_review_hub_links_to_safety_evidence_dashboard(self):
        self._create_skill_entry()
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, 'href="/skill-ledger/advisory/ai-evidence/"')
        self.assertContains(response, "AI safety controls and evidence dashboard")

    def test_ai_review_hub_renders_manual_review_workflow(self):
        self._create_skill_entry()
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, "Review the private AI explanation preview.")
        self.assertContains(response, "Check the safety controls and evidence dashboard.")
        self.assertContains(
            response,
            (
                "Manually verify evidence before using any skill in your CV, LinkedIn, "
                "or public profile."
            ),
        )

    def test_ai_review_hub_renders_no_save_no_submit_wording(self):
        self._create_skill_entry()
        self._login()

        response = self.client.get(self.url)
        hub_content = response.content.decode().lower().split('<div class="cf90-page"', 1)[1]

        self.assertContains(
            response,
            "This hub does not save, update, publish, submit, or mutate records.",
        )
        self.assertNotIn("<form", hub_content)
        self.assertNotIn("<button", hub_content)
        self.assertNotIn('type="submit"', hub_content)

    def test_ai_review_hub_renders_no_live_provider_wording(self):
        self._create_skill_entry()
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, "No live AI provider is called from this hub.")
        self.assertContains(
            response,
            (
                "No raw JD text, prompt text, provider response, or AI output is stored "
                "or displayed here."
            ),
        )
        self.assertContains(
            response,
            "This hub does not call any AI provider. All links lead to private advisory pages.",
        )

    def test_ai_review_hub_does_not_render_raw_jd_marker(self):
        self._create_skill_entry(skill_name="python")
        self._create_jd_ready_pair("python", marker="UNIQUE_PRIVATE_JD_SENTENCE")
        self._login()

        content = self._hub_content()

        self.assertNotIn("UNIQUE_PRIVATE_JD_SENTENCE", content)
        self.assertNotIn("deterministic planning context", content)
        self.assertNotIn("Private Employer", content)
        self.assertNotIn("Private Analyst", content)

    def test_ai_review_hub_does_not_render_explanation_row_content(self):
        self._create_skill_entry(skill_name="UNIQUE_SKILL_NAME")
        self._login()

        content = self._hub_content()

        self.assertNotIn("UNIQUE_SKILL_NAME", content)
        self.assertNotIn("Evidence basis:", content)
        self.assertNotIn("Manual next action:", content)
        self.assertNotIn("Confidence boundary:", content)
        self.assertNotIn("Classification: CLAIM_SAFE", content)

    def test_ai_review_hub_forbidden_phrases_absent(self):
        self._create_skill_entry()
        self._login()

        content = self._hub_content().lower()
        forbidden_phrases = (
            *FORBIDDEN_EXPLANATION_PHRASES,
            "ai confirmed",
            "ai has assessed your skill",
            "ai says you are qualified",
            "employer-ready",
            "profile updated",
            "cv updated",
            "application submitted",
            "auto-save",
            "auto-apply",
            "production ai",
            "live ai monitoring",
            "real-time ai metrics",
            "ai observability dashboard",
        )

        for forbidden in forbidden_phrases:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, content)

    def test_sprint_88_explanation_preview_unaffected(self):
        self._create_skill_entry()
        self._login()

        response = self.client.get(reverse("skill_ledger:advisory_explanations"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI explanation contract preview")
        self.assertContains(response, "Provider mode: mocked")

    def test_sprint_89_safety_dashboard_unaffected(self):
        self._create_skill_entry()
        self._login()

        response = self.client.get(reverse("skill_ledger:advisory_ai_evidence"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI explanation layer - safety controls and evidence")
        self.assertContains(response, "Provider mode: mocked")

    def test_ai_review_hub_renders_skill_ledger_entry_count(self):
        self._create_skill_entry(skill_name="python")
        self._create_skill_entry(skill_name="sql")
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, "Skill Ledger entries")
        self.assertContains(response, "Advisory rows")
        self.assertContains(response, "Explanation rows")
        self.assertContains(response, "Provider mode")
        self.assertContains(response, "2")
        self.assertContains(response, SPRINT_87_PROVIDER_MODE_MOCKED)


class SkillLedgerAIAdvisoryManualReviewChecklistTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="manualreviewuser",
            password="StrongPass12345",
        )
        self.url = reverse("skill_ledger:advisory_manual_review_checklist")
        self.JobApplication = apps.get_model("applications", "JobApplication")

    def _login(self):
        self.client.login(username="manualreviewuser", password="StrongPass12345")

    def _page_content(self):
        response = self.client.get(self.url)
        return response.content.decode()

    def _checklist_content(self):
        return self._page_content().split('<div class="cf91-page"', 1)[1]

    def _create_skill_entry(self, **overrides):
        defaults = {
            "skill_name": "UNIQUE_STATIC_ONLY_SKILL",
            "category": SkillEntry.Category.PROGRAMMING,
            "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
            "sprint_reference": "Sprint 84",
            "project_link": "https://example.com/python",
            "visibility": SkillEntry.Visibility.PRIVATE,
        }
        defaults.update(overrides)
        return SkillEntry.objects.create(**defaults)

    def _create_application_with_marker(self):
        return self.JobApplication.objects.create(
            user=self.user,
            company_name="Private Employer",
            job_title="Private Analyst",
            date_applied=timezone.localdate(),
            job_description="UNIQUE_PRIVATE_JD_MARKER deterministic planning context",
        )

    def test_manual_review_checklist_loads_for_authenticated_user(self):
        self._login()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI advisory manual review checklist")

    def test_manual_review_checklist_redirects_anonymous_user(self):
        response = self.client.get("/skill-ledger/advisory/manual-review-checklist/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response["Location"])

    def test_manual_review_checklist_post_returns_405(self):
        self._login()

        response = self.client.post(self.url, {"review": "done"})

        self.assertEqual(response.status_code, 405)

    def test_manual_review_checklist_links_to_explanation_preview(self):
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, 'href="/skill-ledger/advisory/explanations/"')
        self.assertContains(response, "AI explanation preview")

    def test_manual_review_checklist_links_to_safety_evidence_dashboard(self):
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, 'href="/skill-ledger/advisory/ai-evidence/"')
        self.assertContains(response, "AI safety controls and evidence dashboard")

    def test_manual_review_checklist_links_to_review_hub(self):
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, 'href="/skill-ledger/advisory/ai-review-hub/"')
        self.assertContains(response, "AI advisory review hub")

    def test_manual_review_checklist_renders_checklist_sections(self):
        self._login()

        response = self.client.get(self.url)

        for section in (
            "Evidence source review",
            "Sprint reference review",
            "Project link review",
            "Evidence level decision",
            "JD signal caution",
            "Public claim decision boundary",
            "CV, LinkedIn, portfolio, and public profile caution",
            "Manual-only review workflow",
        ):
            with self.subTest(section=section):
                self.assertContains(response, section)

    def test_manual_review_checklist_renders_verified_guidance(self):
        self._login()

        response = self.client.get(self.url)

        self.assertContains(
            response,
            (
                "Use VERIFIED skills in public claims only when the linked evidence, "
                "sprint reference, and project context have been manually reviewed."
            ),
        )
        self.assertContains(
            response,
            (
                "VERIFIED skills may be considered for public claims only after linked "
                "evidence, sprint reference, and project context have been manually reviewed."
            ),
        )

    def test_manual_review_checklist_renders_learning_target_caution(self):
        self._login()

        response = self.client.get(self.url)

        self.assertContains(
            response,
            (
                "Do not present LEARNING_TARGET, STUDYING, NO_EVIDENCE, or JD-only "
                "signals as verified proficiency."
            ),
        )
        self.assertContains(
            response,
            (
                "LEARNING_TARGET, STUDYING, NO_EVIDENCE, and JD-only signals must not "
                "be presented as verified proficiency."
            ),
        )

    def test_manual_review_checklist_renders_no_save_no_submit_wording(self):
        self._login()

        response = self.client.get(self.url)

        self.assertContains(
            response,
            "This checklist does not save, update, publish, submit, or mutate records.",
        )

    def test_manual_review_checklist_renders_no_live_provider_wording(self):
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, "No live AI provider is called from this checklist.")
        self.assertContains(
            response,
            (
                "No raw JD text, prompt text, provider response, or AI output is stored "
                "or displayed here."
            ),
        )
        self.assertContains(
            response,
            (
                "This checklist is static guidance. It does not query your Skill Ledger, "
                "call any provider, or generate personalised output. Apply it manually "
                "to your own evidence."
            ),
        )

    def test_manual_review_checklist_no_forms_or_inputs_present(self):
        self._login()

        content = self._checklist_content().lower()

        self.assertNotIn("<form", content)
        self.assertNotIn("<input", content)
        self.assertNotIn("<textarea", content)

    def test_manual_review_checklist_no_checkboxes_present(self):
        self._login()

        content = self._checklist_content().lower()

        self.assertNotIn('type="checkbox"', content)
        self.assertNotIn("checkbox", content)

    def test_manual_review_checklist_no_submit_buttons_present(self):
        self._login()

        content = self._checklist_content().lower()

        self.assertNotIn("<button", content)
        self.assertNotIn('type="submit"', content)
        self.assertNotIn('role="button"', content)

    def test_manual_review_checklist_no_raw_jd_marker_text(self):
        self._create_application_with_marker()
        self._login()

        content = self._page_content()

        self.assertNotIn("UNIQUE_PRIVATE_JD_MARKER", content)
        self.assertNotIn("deterministic planning context", content)
        self.assertNotIn("Private Employer", content)
        self.assertNotIn("Private Analyst", content)

    def test_manual_review_checklist_no_explanation_row_content(self):
        self._create_skill_entry()
        self._login()

        content = self._page_content()

        self.assertNotIn("UNIQUE_STATIC_ONLY_SKILL", content)
        self.assertNotIn("Evidence basis:", content)
        self.assertNotIn("Manual next action:", content)
        self.assertNotIn("Confidence boundary:", content)
        self.assertNotIn("Classification: CLAIM_SAFE", content)

    def test_manual_review_checklist_forbidden_phrases_absent(self):
        self._login()

        content = self._page_content().lower()
        forbidden_phrases = (
            "employer confirmed",
            "you are qualified",
            "job ready",
            "employer ready",
            "this proves proficiency",
            "ai verified",
            "automatically verified",
            "skill confirmed",
            "ready to apply",
            "you meet the requirements",
            "this jd signal verifies",
            "proficiency confirmed",
            "ai confirmed",
            "ai has assessed your skill",
            "ai says you are qualified",
            "employer-ready",
            "profile updated",
            "cv updated",
            "linkedin updated",
            "application submitted",
            "auto-save",
            "auto-apply",
            "production ai",
            "live ai monitoring",
            "real-time ai metrics",
            "ai observability dashboard",
            "claim-ready skill",
            "verified by ai",
            "verified by jd",
        )

        for forbidden in forbidden_phrases:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, content)

    def test_sprint_88_explanation_preview_unaffected(self):
        self._login()

        response = self.client.get(reverse("skill_ledger:advisory_explanations"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI explanation contract preview")

    def test_sprint_89_safety_dashboard_unaffected(self):
        self._login()

        response = self.client.get(reverse("skill_ledger:advisory_ai_evidence"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI explanation layer - safety controls and evidence")

    def test_sprint_90_review_hub_unaffected(self):
        self._login()

        response = self.client.get(reverse("skill_ledger:advisory_ai_review_hub"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI advisory review hub")

    def test_manual_review_checklist_renders_required_safety_wording(self):
        self._login()

        response = self.client.get(self.url)

        for wording in (
            "This checklist is private and advisory only.",
            (
                "This checklist does not verify proficiency, certify skills, "
                "or predict employer outcomes."
            ),
            (
                "Review evidence manually before using any skill in your CV, LinkedIn, "
                "portfolio, or public profile."
            ),
            "A JD signal does not prove proficiency.",
            "JD signal context is advisory only.",
            "A JD signal does not make a skill claim-ready.",
            "Skill gap signals are advisory only.",
            "Learning recommendations are planning aids.",
        ):
            with self.subTest(wording=wording):
                self.assertContains(response, wording)

    def test_manual_review_checklist_route_resolves_by_namespaced_reverse(self):
        self.assertEqual(
            reverse("skill_ledger:advisory_manual_review_checklist"),
            "/skill-ledger/advisory/manual-review-checklist/",
        )


class SkillLedgerAIAdvisoryReviewHubChecklistLinkTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="reviewhubchecklistuser",
            password="StrongPass12345",
        )
        self.hub_url = reverse("skill_ledger:advisory_ai_review_hub")
        self.checklist_url = reverse("skill_ledger:advisory_manual_review_checklist")

    def _login(self):
        self.client.login(username="reviewhubchecklistuser", password="StrongPass12345")

    def _hub_content(self):
        response = self.client.get(self.hub_url)
        return response.content.decode()

    def test_review_hub_renders_link_to_manual_review_checklist(self):
        self._login()

        response = self.client.get(self.hub_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Manual review checklist")

    def test_review_hub_checklist_link_uses_correct_url(self):
        self._login()

        response = self.client.get(self.hub_url)

        self.assertContains(
            response,
            'href="/skill-ledger/advisory/manual-review-checklist/"',
        )
        self.assertEqual(
            self.checklist_url,
            "/skill-ledger/advisory/manual-review-checklist/",
        )

    def test_review_hub_anonymous_access_still_redirected(self):
        response = self.client.get(self.hub_url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response["Location"])

    def test_sprint_91_checklist_loads_for_authenticated_user(self):
        self._login()

        response = self.client.get(self.checklist_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI advisory manual review checklist")

    def test_sprint_91_checklist_redirects_anonymous_user(self):
        response = self.client.get(self.checklist_url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response["Location"])

    def test_sprint_91_checklist_post_returns_405(self):
        self._login()

        response = self.client.post(self.checklist_url, {"review": "done"})

        self.assertEqual(response.status_code, 405)

    def test_review_hub_does_not_render_forbidden_phrases(self):
        self._login()

        content = self._hub_content().lower()
        forbidden_phrases = (
            *FORBIDDEN_EXPLANATION_PHRASES,
            "ai confirmed",
            "ai has assessed your skill",
            "ai says you are qualified",
            "employer-ready",
            "profile updated",
            "cv updated",
            "linkedin updated",
            "application submitted",
            "auto-save",
            "auto-apply",
            "production ai",
            "live ai monitoring",
            "real-time ai metrics",
            "ai observability dashboard",
            "claim-ready skill",
            "verified by ai",
            "verified by jd",
        )

        for forbidden in forbidden_phrases:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, content)

    def test_review_hub_no_forms_inputs_or_submit_controls(self):
        self._login()

        content = self._hub_content().lower().split('<div class="cf90-page"', 1)[1]

        self.assertNotIn("<form", content)
        self.assertNotIn("<input", content)
        self.assertNotIn("<textarea", content)
        self.assertNotIn("<button", content)
        self.assertNotIn('type="submit"', content)
        self.assertNotIn('role="button"', content)
        self.assertIn("AI advisory review hub", self._hub_content())
        self.assertIn("This hub is private and advisory only.", self._hub_content())
        self.assertIn("No live AI provider is called from this hub.", self._hub_content())


class SkillLedgerAIAdvisorySafetyWordingRegressionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="safetyregressionuser",
            password="StrongPass12345",
        )
        self.JobApplication = apps.get_model("applications", "JobApplication")
        self.forbidden_phrases = (
            "employer confirmed",
            "you are qualified",
            "job ready",
            "employer ready",
            "this proves proficiency",
            "ai verified",
            "automatically verified",
            "skill confirmed",
            "ready to apply",
            "you meet the requirements",
            "this jd signal verifies",
            "proficiency confirmed",
            "ai confirmed",
            "ai has assessed your skill",
            "employer-ready",
            "profile updated",
            "cv updated",
            "application submitted",
            "auto-save",
            "auto-apply",
            "production ai",
            "live ai monitoring",
            "real-time ai metrics",
            "claim-ready skill",
            "verified by ai",
            "verified by jd",
        )

    def _login(self):
        self.client.login(username="safetyregressionuser", password="StrongPass12345")

    def _authenticated_get(self, route_name, **kwargs):
        self._login()
        return self.client.get(reverse(route_name, kwargs=kwargs or None))

    def _create_skill_entry(self):
        return SkillEntry.objects.create(
            skill_name="Python",
            category=SkillEntry.Category.PROGRAMMING,
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
            sprint_reference="Sprint 84",
            project_link="https://example.com/python",
            visibility=SkillEntry.Visibility.PRIVATE,
        )

    def _create_application(self):
        return self.JobApplication.objects.create(
            user=self.user,
            company_name="Evidence Analytics Ltd",
            job_title="Data Analyst",
            date_applied=timezone.localdate(),
            job_description="Python SQL dashboard analytics evidence.",
        )

    def _assert_forbidden_absent(self, response):
        content = response.content.decode().lower()
        for phrase in self.forbidden_phrases:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, content)

    def test_explanations_page_preserves_advisory_only_wording(self):
        response = self._authenticated_get("skill_ledger:advisory_explanations")

        self.assertContains(response, "Explanations are advisory only.")

    def test_explanations_page_preserves_no_proficiency_claim_wording(self):
        response = self._authenticated_get("skill_ledger:advisory_explanations")

        self.assertContains(
            response,
            (
                "This explanation is advisory only and does not verify proficiency, "
                "certify skills, or predict employer outcomes."
            ),
        )

    def test_ai_evidence_dashboard_preserves_advisory_evidence_wording(self):
        response = self._authenticated_get("skill_ledger:advisory_ai_evidence")

        self.assertContains(response, "This dashboard is advisory evidence only.")

    def test_ai_evidence_dashboard_preserves_no_mutation_wording(self):
        response = self._authenticated_get("skill_ledger:advisory_ai_evidence")

        self.assertContains(
            response,
            "This dashboard does not save, update, publish, submit, or mutate records.",
        )

    def test_review_hub_preserves_no_live_provider_wording(self):
        response = self._authenticated_get("skill_ledger:advisory_ai_review_hub")

        self.assertContains(response, "No live AI provider is called from this hub.")

    def test_review_hub_preserves_no_raw_output_wording(self):
        response = self._authenticated_get("skill_ledger:advisory_ai_review_hub")

        self.assertContains(
            response,
            (
                "No raw JD text, prompt text, provider response, or AI output is stored "
                "or displayed here."
            ),
        )

    def test_manual_checklist_preserves_verified_evidence_guidance(self):
        response = self._authenticated_get(
            "skill_ledger:advisory_manual_review_checklist",
        )

        self.assertContains(
            response,
            (
                "Use VERIFIED skills in public claims only when the linked evidence, "
                "sprint reference, and project context have been manually reviewed."
            ),
        )

    def test_manual_checklist_preserves_learning_target_caution_wording(self):
        response = self._authenticated_get(
            "skill_ledger:advisory_manual_review_checklist",
        )

        self.assertContains(
            response,
            (
                "Do not present LEARNING_TARGET, STUDYING, NO_EVIDENCE, or JD-only "
                "signals as verified proficiency."
            ),
        )

    def test_explanations_page_forbidden_phrases_absent(self):
        response = self._authenticated_get("skill_ledger:advisory_explanations")

        self._assert_forbidden_absent(response)

    def test_ai_evidence_dashboard_forbidden_phrases_absent(self):
        response = self._authenticated_get("skill_ledger:advisory_ai_evidence")

        self._assert_forbidden_absent(response)

    def test_review_hub_forbidden_phrases_absent(self):
        response = self._authenticated_get("skill_ledger:advisory_ai_review_hub")

        self._assert_forbidden_absent(response)

    def test_manual_checklist_forbidden_phrases_absent(self):
        response = self._authenticated_get(
            "skill_ledger:advisory_manual_review_checklist",
        )

        self._assert_forbidden_absent(response)

    def test_advisory_page_forbidden_phrases_absent(self):
        self._create_skill_entry()

        response = self._authenticated_get("skill_ledger:advisory")

        self._assert_forbidden_absent(response)

    def test_skill_ledger_list_forbidden_phrases_absent(self):
        self._create_skill_entry()

        response = self._authenticated_get("skill_ledger:list")

        self._assert_forbidden_absent(response)

    def test_application_form_prefill_wording_survives(self):
        self._login()

        response = self.client.get(
            reverse("applications:application_create"),
            {"company_name": "FinSight", "job_title": "Junior Finance Data Analyst"},
        )

        self.assertContains(
            response,
            "Pre-filling this form does not save your application.",
        )

    def test_application_detail_tracking_only_wording_survives(self):
        self._login()

        response = self.client.get(
            reverse("applications:application_create"),
            {"company_name": "FinSight", "job_title": "Junior Finance Data Analyst"},
        )

        self.assertContains(response, "Saving creates a tracking record only.")

    def test_jd_gap_aggregation_advisory_wording_survives(self):
        response = self._authenticated_get("applications:jd_gap_aggregation")

        self.assertContains(response, "Skill gap signals are advisory only.")

    def test_advisory_page_jd_signal_wording_survives_sprint_93(self):
        self._create_skill_entry()

        response = self._authenticated_get("skill_ledger:advisory")

        self.assertContains(response, "A JD signal does not prove proficiency.")
        self.assertContains(
            response,
            (
                "Review evidence manually before adding any JD-signalled skill to your "
                "CV, LinkedIn, or public profile."
            ),
        )

    def test_advisory_page_claim_ready_wording_survives_sprint_93(self):
        self._create_skill_entry()

        response = self._authenticated_get("skill_ledger:advisory")

        self.assertContains(response, "A JD signal does not make a skill claim-ready.")

    def test_advisory_page_manual_review_wording_survives_sprint_93(self):
        self._create_skill_entry()

        response = self._authenticated_get("skill_ledger:advisory")

        self.assertContains(response, "Manual review required:")

    def test_skill_gap_private_planning_tool_wording_survives_sprint_93(self):
        response = self._authenticated_get("skill_gaps:ai_career_coach")

        self.assertContains(response, "This is a private planning tool.")

    def test_skill_gap_advisory_judgement_wording_survives_sprint_93(self):
        response = self._authenticated_get("skill_gaps:ai_career_coach")

        self.assertContains(response, "All output is advisory. Use your own judgement.")


class SkillLedgerJdSignalContextTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="jdcontext", password="StrongPass12345")
        self.url = reverse("skill_ledger:advisory")
        self.JobApplication = apps.get_model("applications", "JobApplication")

    def _login(self):
        self.client.login(username="jdcontext", password="StrongPass12345")

    def _jd_text(self, *terms, marker=""):
        intro = " ".join((*terms, marker)).strip()
        filler = " deterministic planning context" * 140
        return f"{intro} {filler}".strip()

    def _create_application(self, **overrides):
        defaults = {
            "user": self.user,
            "company_name": "Private Employer",
            "job_title": "Private Analyst",
            "date_applied": timezone.localdate(),
            "job_description": self._jd_text("python"),
            "job_url": "",
            "salary_range": "Private salary",
            "contact_name": "Private Contact",
            "contact_email": "private@example.com",
            "notes": "Private application note.",
        }
        defaults.update(overrides)
        return self.JobApplication.objects.create(**defaults)

    def _create_skill_entry(self, **overrides):
        defaults = {
            "skill_name": "python",
            "category": SkillEntry.Category.PROGRAMMING,
            "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
            "sprint_reference": "Sprint 84",
            "project_link": "https://example.com/python",
            "visibility": SkillEntry.Visibility.PRIVATE,
        }
        defaults.update(overrides)
        return SkillEntry.objects.create(**defaults)

    def _create_jd_ready_pair(self, term="python", marker=""):
        self._create_application(job_description=self._jd_text(term, marker=marker))
        self._create_application(
            company_name="Private Employer Two",
            job_description=self._jd_text(term, marker=marker),
        )

    def test_collect_jd_candidate_terms_returns_tuple_of_strings(self):
        self._create_jd_ready_pair("python")

        terms = collect_jd_candidate_terms(self.user)

        self.assertIsInstance(terms, tuple)
        self.assertIn("python", terms)
        self.assertTrue(all(isinstance(term, str) for term in terms))

    def test_collect_jd_candidate_terms_returns_empty_when_no_jd_ready_records(self):
        self.assertEqual(collect_jd_candidate_terms(self.user), ())

    def test_collect_jd_candidate_terms_applies_min_frequency_threshold(self):
        self._create_jd_ready_pair("python")

        self.assertEqual(collect_jd_candidate_terms(self.user, min_frequency=3), ())
        self.assertEqual(collect_jd_candidate_terms(self.user, min_frequency=2), ("python",))

    def test_collect_jd_candidate_terms_deduplicates_terms(self):
        self._create_application(job_description=self._jd_text("power bi"))
        self._create_application(
            company_name="Private Employer Two",
            job_description=self._jd_text("powerbi"),
        )

        terms = collect_jd_candidate_terms(self.user)

        self.assertEqual(terms.count("power bi"), 1)

    def test_collect_jd_candidate_terms_does_not_expose_raw_jd_text(self):
        self._create_jd_ready_pair("python", marker="UNIQUE_PRIVATE_JD_SENTENCE")

        terms = collect_jd_candidate_terms(self.user)
        rendered_terms = " ".join(terms)

        self.assertIn("python", terms)
        self.assertNotIn("UNIQUE_PRIVATE_JD_SENTENCE", rendered_terms)
        self.assertNotIn("deterministic planning context", rendered_terms)

    def test_collect_jd_candidate_terms_does_not_write_to_database(self):
        self._create_jd_ready_pair("python")
        before_skill_count = SkillEntry.objects.count()
        before_application_count = self.JobApplication.objects.count()
        before_application_values = tuple(self.JobApplication.objects.values())

        terms = collect_jd_candidate_terms(self.user)

        self.assertEqual(terms, ("python",))
        self.assertEqual(SkillEntry.objects.count(), before_skill_count)
        self.assertEqual(self.JobApplication.objects.count(), before_application_count)
        self.assertEqual(tuple(self.JobApplication.objects.values()), before_application_values)

    def test_advisory_rows_show_jd_match_true_when_term_in_candidate_terms(self):
        row = build_skill_advisory_rows(
            ({"skill_name": "Python", "evidence_level": "VERIFIED"},),
            jd_candidate_terms=("python",),
        )[0]

        self.assertTrue(row.jd_candidate_match)

    def test_advisory_rows_show_jd_match_false_when_term_absent(self):
        row = build_skill_advisory_rows(
            ({"skill_name": "Python", "evidence_level": "VERIFIED"},),
            jd_candidate_terms=("sql",),
        )[0]

        self.assertFalse(row.jd_candidate_match)

    def test_advisory_rows_handle_empty_jd_candidate_terms_gracefully(self):
        rows = build_skill_advisory_rows(
            ({"skill_name": "Python", "evidence_level": "VERIFIED"},),
            jd_candidate_terms=(),
        )

        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0].jd_candidate_match)

    def test_advisory_page_shows_jd_signal_context(self):
        self._create_skill_entry()
        self._create_jd_ready_pair("python")
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, "JD signal context is connected")
        self.assertContains(response, "JD candidate match: Yes - advisory context only.")

    def test_advisory_page_jd_signal_wording_present(self):
        self._create_skill_entry()
        self._create_jd_ready_pair("python")
        self._login()

        response = self.client.get(self.url)

        for wording in REQUIRED_JD_SIGNAL_SAFETY_WORDING:
            with self.subTest(wording=wording):
                self.assertContains(response, wording)
        for wording in REQUIRED_SKILL_ADVISORY_SAFETY_WORDING:
            with self.subTest(wording=wording):
                self.assertContains(response, wording)

    def test_advisory_page_does_not_render_raw_jd_text(self):
        self._create_skill_entry()
        self._create_jd_ready_pair("python", marker="UNIQUE_PRIVATE_JD_SENTENCE")
        self._login()

        response = self.client.get(self.url)
        content = response.content.decode()

        self.assertContains(response, "JD candidate match: Yes - advisory context only.")
        self.assertNotIn("UNIQUE_PRIVATE_JD_SENTENCE", content)
        self.assertNotIn("deterministic planning context", content)

    def test_advisory_page_does_not_expose_application_data(self):
        self._create_skill_entry()
        self._create_jd_ready_pair("python")
        self._login()

        response = self.client.get(self.url)
        content = response.content.decode()

        for forbidden in (
            "Private Employer",
            "Private Analyst",
            "Private salary",
            "Private Contact",
            "private@example.com",
            "Private application note.",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, content)

    def test_advisory_page_does_not_imply_employer_confirmation(self):
        self._create_skill_entry()
        self._create_jd_ready_pair("python")
        self._login()

        response = self.client.get(self.url)
        content = response.content.decode()

        for forbidden in (
            "Employer confirmed this skill",
            "You are qualified for roles requiring",
            "Automatically matched to employer demand",
            "AI confirmed",
            "Employer ready",
            "Verified by employer",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, content)

    def test_advisory_page_does_not_imply_proficiency_from_jd_signal(self):
        self._create_skill_entry()
        self._create_jd_ready_pair("python")
        self._login()

        response = self.client.get(self.url)
        content = response.content.decode()

        for forbidden in (
            "This JD signal verifies your proficiency",
            "You meet the requirements for this skill",
            "This proves proficiency",
            "AI verified",
            "Automatically verified",
            "Skill confirmed",
            "Ready to apply",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, content)
        self.assertContains(response, "A JD signal does not prove proficiency.")

    def test_advisory_page_still_loads_when_no_jd_ready_records(self):
        self._create_skill_entry()
        self._login()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "No JD signal candidate terms met the deterministic frequency threshold.",
        )

    def test_advisory_page_still_loads_for_authenticated_user(self):
        self._create_skill_entry()
        self._create_jd_ready_pair("python")
        self._login()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Skill Ledger Advisory")

    def test_sprint_85_advisory_classifications_unchanged(self):
        self.assertEqual(
            ADVISORY_CLASSIFICATIONS,
            {
                "VERIFIED_WITH_EVIDENCE": "Verified - sprint evidence present",
                "VERIFIED_NO_REFERENCE": "Verified - add sprint reference",
                "LEARNING_TARGET": "Learning target - do not claim as verified",
                "STUDYING": "Studying - personal study only",
                "NO_EVIDENCE": "Gap identified - do not claim",
                "PUBLIC_RISK": "Public visibility risk - review before publishing",
                "JD_SIGNAL_UNMATCHED": "Appears in JDs - not yet in ledger",
                "CLAIM_SAFE": "Safe to discuss - evidence confirmed",
            },
        )


class SkillEntryModelTests(TestCase):
    def test_skill_entry_visibility_defaults_to_private(self):
        entry = SkillEntry.objects.create(skill_name="SQL")

        self.assertEqual(entry.visibility, SkillEntry.Visibility.PRIVATE)

    def test_skill_entry_evidence_level_choices_valid(self):
        values = [choice.value for choice in SkillEntry.EvidenceLevel]

        self.assertIn(SkillEntry.EvidenceLevel.VERIFIED, values)
        self.assertIn(SkillEntry.EvidenceLevel.LEARNING_TARGET, values)
        self.assertIn(SkillEntry.EvidenceLevel.STUDYING, values)
        self.assertIn(SkillEntry.EvidenceLevel.NO_EVIDENCE, values)

    def test_skill_entry_str_representation(self):
        entry = SkillEntry.objects.create(
            skill_name="SQL",
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
        )

        self.assertEqual(str(entry), "SQL (Verified - portfolio evidence confirmed)")

    def test_skill_entry_date_fields_auto_populate(self):
        before_create = timezone.now()

        entry = SkillEntry.objects.create(skill_name="Python")

        self.assertIsNotNone(entry.date_added)
        self.assertIsNotNone(entry.last_updated)
        self.assertGreaterEqual(entry.date_added, before_create)
        self.assertGreaterEqual(entry.last_updated, before_create)


class SkillLedgerViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def _create_skill_entry(self, **overrides):
        defaults = {
            "skill_name": "Power BI",
            "category": SkillEntry.Category.BUSINESS_INTELLIGENCE,
            "evidence_level": SkillEntry.EvidenceLevel.STUDYING,
            "sprint_reference": "Sprint 70",
            "project_link": "https://example.com/project",
            "notes": "Existing private note.",
            "visibility": SkillEntry.Visibility.PRIVATE,
        }
        defaults.update(overrides)
        return SkillEntry.objects.create(**defaults)

    def _valid_edit_data(self, **overrides):
        data = {
            "skill_name": "Power BI",
            "category": SkillEntry.Category.BUSINESS_INTELLIGENCE,
            "evidence_level": SkillEntry.EvidenceLevel.STUDYING,
            "sprint_reference": "Sprint 70",
            "project_link": "https://example.com/project",
            "notes": "Existing private note.",
            "visibility": SkillEntry.Visibility.PRIVATE,
        }
        data.update(overrides)
        return data

    def _get_edit(self, entry):
        self.client.login(username="aminul", password="StrongPass12345")
        return self.client.get(reverse("skill_ledger:edit", kwargs={"pk": entry.pk}))

    def _post_edit(self, entry, **overrides):
        self.client.login(username="aminul", password="StrongPass12345")
        return self.client.post(
            reverse("skill_ledger:edit", kwargs={"pk": entry.pk}),
            self._valid_edit_data(**overrides),
        )

    def test_skill_ledger_list_view_requires_login(self):
        response = self.client.get(reverse("skill_ledger:list"))

        self.assertEqual(response.status_code, 302)

    def test_skill_ledger_list_view_loads_for_authenticated_user(self):
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(reverse("skill_ledger:list"))

        self.assertEqual(response.status_code, 200)

    def test_skill_entry_create_view_requires_login(self):
        response = self.client.get(reverse("skill_ledger:create"))

        self.assertEqual(response.status_code, 302)

    def test_skill_entry_create_view_loads_for_authenticated_user(self):
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(reverse("skill_ledger:create"))

        self.assertEqual(response.status_code, 200)

    def test_skill_entry_detail_view_loads_for_authenticated_user(self):
        entry = SkillEntry.objects.create(skill_name="Power BI")
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(reverse("skill_ledger:detail", kwargs={"pk": entry.pk}))

        self.assertEqual(response.status_code, 200)

    def test_skill_ledger_list_renders_safely_with_no_entries(self):
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(reverse("skill_ledger:list"))

        self.assertEqual(response.status_code, 200)

    def test_skill_entry_create_view_creates_entry(self):
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.post(
            reverse("skill_ledger:create"),
            {
                "skill_name": "dbt",
                "category": SkillEntry.Category.ANALYTICS_ENGINEERING,
                "evidence_level": SkillEntry.EvidenceLevel.LEARNING_TARGET,
                "sprint_reference": "Sprint 70",
                "project_link": "https://example.com/project",
                "notes": "Developing analytics engineering evidence.",
                "visibility": SkillEntry.Visibility.PRIVATE,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(SkillEntry.objects.filter(skill_name="dbt").exists())

    def test_skill_entry_edit_loads_for_authenticated_user(self):
        entry = self._create_skill_entry()

        response = self._get_edit(entry)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Edit Skill Entry")

    def test_skill_entry_edit_redirects_anonymous_user(self):
        entry = self._create_skill_entry()

        response = self.client.get(reverse("skill_ledger:edit", kwargs={"pk": entry.pk}))

        self.assertEqual(response.status_code, 302)

    def test_skill_entry_edit_returns_404_for_nonexistent_entry(self):
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(reverse("skill_ledger:edit", kwargs={"pk": 99999}))

        self.assertEqual(response.status_code, 404)

    def test_skill_entry_edit_prepopulates_existing_values(self):
        entry = self._create_skill_entry(
            skill_name="dbt",
            category=SkillEntry.Category.ANALYTICS_ENGINEERING,
            evidence_level=SkillEntry.EvidenceLevel.LEARNING_TARGET,
            sprint_reference="Sprint 71",
            project_link="https://example.com/dbt",
            notes="Existing analytics engineering note.",
            visibility=SkillEntry.Visibility.PUBLIC,
        )

        response = self._get_edit(entry)
        form = response.context["form"]

        self.assertEqual(form["skill_name"].value(), "dbt")
        self.assertEqual(form["category"].value(), SkillEntry.Category.ANALYTICS_ENGINEERING)
        self.assertEqual(form["evidence_level"].value(), SkillEntry.EvidenceLevel.LEARNING_TARGET)
        self.assertEqual(form["sprint_reference"].value(), "Sprint 71")
        self.assertEqual(form["project_link"].value(), "https://example.com/dbt")
        self.assertEqual(form["notes"].value(), "Existing analytics engineering note.")
        self.assertEqual(form["visibility"].value(), SkillEntry.Visibility.PUBLIC)

    def test_skill_entry_edit_valid_post_updates_skill_name(self):
        entry = self._create_skill_entry()

        response = self._post_edit(entry, skill_name="Advanced SQL")

        self.assertRedirects(response, reverse("skill_ledger:detail", kwargs={"pk": entry.pk}))
        entry.refresh_from_db()
        self.assertEqual(entry.skill_name, "Advanced SQL")

    def test_skill_entry_edit_valid_post_updates_evidence_level(self):
        entry = self._create_skill_entry(evidence_level=SkillEntry.EvidenceLevel.STUDYING)

        self._post_edit(entry, evidence_level=SkillEntry.EvidenceLevel.VERIFIED)

        entry.refresh_from_db()
        self.assertEqual(entry.evidence_level, SkillEntry.EvidenceLevel.VERIFIED)

    def test_skill_entry_edit_valid_post_updates_visibility(self):
        entry = self._create_skill_entry(visibility=SkillEntry.Visibility.PRIVATE)

        self._post_edit(entry, visibility=SkillEntry.Visibility.PUBLIC)

        entry.refresh_from_db()
        self.assertEqual(entry.visibility, SkillEntry.Visibility.PUBLIC)

    def test_skill_entry_edit_valid_post_updates_sprint_reference(self):
        entry = self._create_skill_entry(sprint_reference="Sprint 70")

        self._post_edit(entry, sprint_reference="Sprint 75")

        entry.refresh_from_db()
        self.assertEqual(entry.sprint_reference, "Sprint 75")

    def test_skill_entry_edit_form_does_not_include_date_added(self):
        entry = self._create_skill_entry()

        response = self._get_edit(entry)

        self.assertNotIn("date_added", response.context["form"].fields)
        self.assertNotContains(response, 'name="date_added"')

    def test_skill_entry_edit_form_does_not_include_last_updated(self):
        entry = self._create_skill_entry()

        response = self._get_edit(entry)

        self.assertNotIn("last_updated", response.context["form"].fields)
        self.assertNotContains(response, 'name="last_updated"')

    def test_skill_entry_edit_advisory_panel_present(self):
        entry = self._create_skill_entry()

        response = self._get_edit(entry)

        self.assertContains(
            response,
            (
                "Changing evidence level updates your private Skill Ledger record only. "
                "It does not verify a skill by itself."
            ),
        )
        self.assertContains(
            response,
            (
                "VERIFIED means portfolio evidence exists in a closed sprint, passing tests, "
                "or prior work experience - not external certification."
            ),
        )

    def test_skill_entry_edit_does_not_imply_automatic_verification(self):
        entry = self._create_skill_entry()

        response = self._get_edit(entry)

        for phrase in (
            "Skill " + "verified",
            "Automatically " + "verified",
            "Employer " + "confirmed",
            "Cert" + "ified",
            "Syn" + "ced",
            "Auto " + "verification",
            "Employer " + "validation",
            "Recruiter " + "confirmation",
        ):
            with self.subTest(phrase=phrase):
                self.assertNotContains(response, phrase)

    def test_skill_ledger_list_shows_edit_link_per_entry(self):
        entry = self._create_skill_entry()
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(reverse("skill_ledger:list"))

        self.assertContains(response, reverse("skill_ledger:edit", kwargs={"pk": entry.pk}))
        self.assertContains(response, ">Edit<")

    def test_skill_entry_edit_success_message_present(self):
        entry = self._create_skill_entry()

        response = self._post_edit(entry, skill_name="Updated Power BI")
        messages = [message.message for message in get_messages(response.wsgi_request)]

        self.assertIn(
            "Skill entry updated. Your private Skill Ledger record has been saved.",
            messages,
        )

    def test_skill_entry_admin_registered(self):
        self.assertIn(SkillEntry, admin.site._registry)

    def test_skill_ledger_shows_verified_entries(self):
        SkillEntry.objects.create(
            skill_name="Python",
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
        )
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(reverse("skill_ledger:list"))

        self.assertContains(response, "VERIFIED")
        self.assertContains(response, "Python")

    def test_skill_ledger_shows_learning_target_entries(self):
        SkillEntry.objects.create(
            skill_name="Snowflake",
            evidence_level=SkillEntry.EvidenceLevel.LEARNING_TARGET,
        )
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(reverse("skill_ledger:list"))

        self.assertContains(response, "LEARNING_TARGET")
        self.assertContains(response, "Snowflake")

    def test_skill_ledger_shows_studying_entries(self):
        SkillEntry.objects.create(
            skill_name="Statistics",
            evidence_level=SkillEntry.EvidenceLevel.STUDYING,
        )
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(reverse("skill_ledger:list"))

        self.assertContains(response, "STUDYING")
        self.assertContains(response, "Statistics")

    def test_skill_ledger_shows_no_evidence_entries(self):
        SkillEntry.objects.create(
            skill_name="GraphQL",
            evidence_level=SkillEntry.EvidenceLevel.NO_EVIDENCE,
        )
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(reverse("skill_ledger:list"))

        self.assertContains(response, "NO_EVIDENCE")
        self.assertContains(response, "GraphQL")

    def test_skill_ledger_kpi_strip_renders_counts(self):
        SkillEntry.objects.create(
            skill_name="Python",
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
        )
        SkillEntry.objects.create(
            skill_name="Snowflake",
            evidence_level=SkillEntry.EvidenceLevel.LEARNING_TARGET,
        )
        SkillEntry.objects.create(
            skill_name="Statistics",
            evidence_level=SkillEntry.EvidenceLevel.STUDYING,
        )
        SkillEntry.objects.create(
            skill_name="GraphQL",
            evidence_level=SkillEntry.EvidenceLevel.NO_EVIDENCE,
        )
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(reverse("skill_ledger:list"))

        self.assertContains(response, "Verified")
        self.assertContains(response, "Learning Target")
        self.assertContains(response, "Studying")
        self.assertContains(response, "No Evidence")
        self.assertEqual(response.context["kpi_counts"][SkillEntry.EvidenceLevel.VERIFIED], 1)
        self.assertEqual(
            response.context["kpi_counts"][SkillEntry.EvidenceLevel.LEARNING_TARGET],
            1,
        )
        self.assertEqual(response.context["kpi_counts"][SkillEntry.EvidenceLevel.STUDYING], 1)
        self.assertEqual(response.context["kpi_counts"][SkillEntry.EvidenceLevel.NO_EVIDENCE], 1)

    def test_skill_ledger_search_filters_by_skill_name(self):
        SkillEntry.objects.create(skill_name="dbt")
        SkillEntry.objects.create(skill_name="Snowflake")
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(reverse("skill_ledger:list"), {"q": "dbt"})

        self.assertContains(response, "dbt")
        self.assertNotContains(response, "Snowflake")
        self.assertEqual(response.context["search_query"], "dbt")

    def test_skill_ledger_kpi_counts_remain_global_when_search_is_applied(self):
        SkillEntry.objects.create(
            skill_name="dbt",
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
        )
        SkillEntry.objects.create(
            skill_name="Snowflake",
            evidence_level=SkillEntry.EvidenceLevel.LEARNING_TARGET,
        )
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(reverse("skill_ledger:list"), {"q": "dbt"})

        self.assertContains(response, "dbt")
        self.assertNotContains(response, "Snowflake")
        self.assertEqual(response.context["kpi_counts"][SkillEntry.EvidenceLevel.VERIFIED], 1)
        self.assertEqual(
            response.context["kpi_counts"][SkillEntry.EvidenceLevel.LEARNING_TARGET],
            1,
        )

    def test_skill_ledger_empty_state_renders_when_no_entries(self):
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(reverse("skill_ledger:list"))

        self.assertContains(response, "No skill entries yet")

    def test_skill_ledger_advisory_panel_present(self):
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(reverse("skill_ledger:list"))

        self.assertContains(
            response,
            (
                "This ledger is private and for your personal reference only. Entries are not "
                "visible to employers or recruiters until you enable the public view in a "
                "future update."
            ),
        )
        self.assertContains(
            response,
            (
                "VERIFIED means portfolio evidence exists in a closed sprint, passing tests, "
                "or prior work experience. It does not mean externally certified or "
                "employer-verified."
            ),
        )

    def test_skill_ledger_does_not_imply_employer_verification(self):
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(reverse("skill_ledger:list"))

        self.assertNotContains(response, "employer verified")
        self.assertNotContains(response, "recruiter verified")
        self.assertNotContains(response, "automatically verified")
        self.assertNotContains(response, "AI verified")

    def test_skill_ledger_does_not_claim_certified_status(self):
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(reverse("skill_ledger:list"))

        self.assertContains(response, "It does not mean externally certified or employer-verified.")
        self.assertNotContains(response, "is certified")
        self.assertNotContains(response, "public profile published")
        self.assertNotContains(response, "visible to employers now")


class SkillLedgerSeedCommandTests(TestCase):
    def test_seed_skill_ledger_command_creates_verified_entries(self):
        output = StringIO()

        call_command("seed_skill_ledger", stdout=output)

        self.assertTrue(
            SkillEntry.objects.filter(
                skill_name="Python",
                category=SkillEntry.Category.PROGRAMMING,
                evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
                visibility=SkillEntry.Visibility.PRIVATE,
                notes=VERIFIED_DEFAULT_NOTES,
            ).exists()
        )
        self.assertTrue(
            SkillEntry.objects.filter(
                skill_name="dbt",
                evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
                notes__contains="not dbt Cloud or production orchestration",
            ).exists()
        )
        self.assertIn("Created:", output.getvalue())

    def test_seed_skill_ledger_command_creates_learning_target_entries(self):
        call_command("seed_skill_ledger", stdout=StringIO())

        self.assertTrue(
            SkillEntry.objects.filter(
                skill_name="Snowflake",
                category=SkillEntry.Category.CLOUD,
                evidence_level=SkillEntry.EvidenceLevel.LEARNING_TARGET,
                visibility=SkillEntry.Visibility.PRIVATE,
                notes=LEARNING_TARGET_NOTES,
            ).exists()
        )
        self.assertTrue(
            SkillEntry.objects.filter(
                skill_name="Databricks",
                evidence_level=SkillEntry.EvidenceLevel.LEARNING_TARGET,
            ).exists()
        )

    def test_seed_skill_ledger_command_is_idempotent(self):
        call_command("seed_skill_ledger", stdout=StringIO())
        count_after_first_run = SkillEntry.objects.count()

        call_command("seed_skill_ledger", stdout=StringIO())

        self.assertEqual(SkillEntry.objects.count(), count_after_first_run)

    def test_seed_skill_ledger_does_not_overwrite_existing_entries(self):
        SkillEntry.objects.create(
            skill_name="Python",
            category=SkillEntry.Category.OTHER,
            evidence_level=SkillEntry.EvidenceLevel.STUDYING,
            notes="User-edited notes.",
        )

        call_command("seed_skill_ledger", stdout=StringIO())

        entry = SkillEntry.objects.get(skill_name="Python")
        self.assertEqual(entry.category, SkillEntry.Category.OTHER)
        self.assertEqual(entry.evidence_level, SkillEntry.EvidenceLevel.STUDYING)
        self.assertEqual(entry.notes, "User-edited notes.")


class PublicSkillLedgerViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def test_public_skill_ledger_accessible_without_login(self):
        response = self.client.get(reverse("skill_ledger:public"))

        self.assertEqual(response.status_code, 200)

    def test_public_skill_ledger_returns_200(self):
        response = self.client.get("/skill-ledger/public/")

        self.assertEqual(response.status_code, 200)

    def test_private_skill_ledger_still_requires_login(self):
        response = self.client.get(reverse("skill_ledger:list"))

        self.assertEqual(response.status_code, 302)

    def test_public_view_shows_verified_public_entries(self):
        SkillEntry.objects.create(
            skill_name="Python",
            visibility=SkillEntry.Visibility.PUBLIC,
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
        )

        response = self.client.get(reverse("skill_ledger:public"))

        self.assertContains(response, "Python")
        self.assertContains(response, "Verified - portfolio evidence confirmed")

    def test_public_view_shows_learning_target_public_entries(self):
        SkillEntry.objects.create(
            skill_name="Snowflake",
            visibility=SkillEntry.Visibility.PUBLIC,
            evidence_level=SkillEntry.EvidenceLevel.LEARNING_TARGET,
        )

        response = self.client.get(reverse("skill_ledger:public"))

        self.assertContains(response, "Snowflake")
        self.assertContains(response, "Developing - not yet portfolio-evidenced")

    def test_public_view_does_not_show_private_entries(self):
        SkillEntry.objects.create(
            skill_name="Private Python",
            visibility=SkillEntry.Visibility.PRIVATE,
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
        )
        SkillEntry.objects.create(
            skill_name="Private Snowflake",
            visibility=SkillEntry.Visibility.PRIVATE,
            evidence_level=SkillEntry.EvidenceLevel.LEARNING_TARGET,
        )

        response = self.client.get(reverse("skill_ledger:public"))

        self.assertNotContains(response, "Private Python")
        self.assertNotContains(response, "Private Snowflake")

    def test_public_view_does_not_show_studying_entries_even_if_public(self):
        SkillEntry.objects.create(
            skill_name="Statistics Study",
            visibility=SkillEntry.Visibility.PUBLIC,
            evidence_level=SkillEntry.EvidenceLevel.STUDYING,
        )

        response = self.client.get(reverse("skill_ledger:public"))

        self.assertNotContains(response, "Statistics Study")
        self.assertNotContains(response, "STUDYING")

    def test_public_view_does_not_show_no_evidence_entries_even_if_public(self):
        SkillEntry.objects.create(
            skill_name="GraphQL Gap",
            visibility=SkillEntry.Visibility.PUBLIC,
            evidence_level=SkillEntry.EvidenceLevel.NO_EVIDENCE,
        )

        response = self.client.get(reverse("skill_ledger:public"))

        self.assertNotContains(response, "GraphQL Gap")
        self.assertNotContains(response, "NO_EVIDENCE")

    def test_public_kpi_shows_verified_count_only(self):
        SkillEntry.objects.create(
            skill_name="Python",
            visibility=SkillEntry.Visibility.PUBLIC,
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
        )
        SkillEntry.objects.create(
            skill_name="Private SQL",
            visibility=SkillEntry.Visibility.PRIVATE,
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
        )

        response = self.client.get(reverse("skill_ledger:public"))

        self.assertEqual(response.context["kpi_counts"][SkillEntry.EvidenceLevel.VERIFIED], 1)

    def test_public_kpi_shows_learning_target_count_only(self):
        SkillEntry.objects.create(
            skill_name="Snowflake",
            visibility=SkillEntry.Visibility.PUBLIC,
            evidence_level=SkillEntry.EvidenceLevel.LEARNING_TARGET,
        )
        SkillEntry.objects.create(
            skill_name="Private Airflow",
            visibility=SkillEntry.Visibility.PRIVATE,
            evidence_level=SkillEntry.EvidenceLevel.LEARNING_TARGET,
        )

        response = self.client.get(reverse("skill_ledger:public"))

        self.assertEqual(
            response.context["kpi_counts"][SkillEntry.EvidenceLevel.LEARNING_TARGET],
            1,
        )

    def test_public_kpi_does_not_show_studying_count(self):
        SkillEntry.objects.create(
            skill_name="Statistics Study",
            visibility=SkillEntry.Visibility.PUBLIC,
            evidence_level=SkillEntry.EvidenceLevel.STUDYING,
        )

        response = self.client.get(reverse("skill_ledger:public"))

        self.assertNotIn(SkillEntry.EvidenceLevel.STUDYING, response.context["kpi_counts"])
        self.assertNotContains(response, "Studying")

    def test_public_kpi_does_not_show_no_evidence_count(self):
        SkillEntry.objects.create(
            skill_name="GraphQL Gap",
            visibility=SkillEntry.Visibility.PUBLIC,
            evidence_level=SkillEntry.EvidenceLevel.NO_EVIDENCE,
        )

        response = self.client.get(reverse("skill_ledger:public"))

        self.assertNotIn(SkillEntry.EvidenceLevel.NO_EVIDENCE, response.context["kpi_counts"])
        self.assertNotContains(response, "No Evidence")

    def test_public_search_filters_by_skill_name(self):
        SkillEntry.objects.create(
            skill_name="dbt",
            visibility=SkillEntry.Visibility.PUBLIC,
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
        )
        SkillEntry.objects.create(
            skill_name="Snowflake",
            visibility=SkillEntry.Visibility.PUBLIC,
            evidence_level=SkillEntry.EvidenceLevel.LEARNING_TARGET,
        )
        SkillEntry.objects.create(
            skill_name="Private dbt",
            visibility=SkillEntry.Visibility.PRIVATE,
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
        )
        SkillEntry.objects.create(
            skill_name="dbt Study",
            visibility=SkillEntry.Visibility.PUBLIC,
            evidence_level=SkillEntry.EvidenceLevel.STUDYING,
        )

        response = self.client.get(reverse("skill_ledger:public"), {"q": "dbt"})

        self.assertContains(response, "dbt")
        self.assertNotContains(response, "Snowflake")
        self.assertNotContains(response, "Private dbt")
        self.assertNotContains(response, "dbt Study")
        self.assertEqual(response.context["search_query"], "dbt")

    def test_public_view_verified_boundary_wording_present(self):
        response = self.client.get(reverse("skill_ledger:public"))

        self.assertContains(
            response,
            (
                "VERIFIED means portfolio evidence exists in a closed sprint, passing tests, "
                "or prior work experience. It does not mean externally certified or "
                "employer-verified."
            ),
        )

    def test_public_view_does_not_imply_employer_verification(self):
        response = self.client.get(reverse("skill_ledger:public"))

        self.assertNotContains(response, "employer verified")
        self.assertNotContains(response, "recruiter verified")
        self.assertNotContains(response, "automatically verified")
        self.assertNotContains(response, "AI verified")

    def test_public_view_does_not_imply_certification(self):
        response = self.client.get(reverse("skill_ledger:public"))

        self.assertContains(response, "It does not mean externally certified or employer-verified.")
        self.assertNotContains(response, "is certified")
        self.assertNotContains(response, "public endorsement")
        self.assertNotContains(response, "guaranteed proficiency")
        self.assertNotContains(response, "job-ready for every role")

    def test_public_view_does_not_expose_private_notes(self):
        SkillEntry.objects.create(
            skill_name="Python",
            visibility=SkillEntry.Visibility.PUBLIC,
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
            notes="Distinctive private implementation note should stay hidden.",
        )

        response = self.client.get(reverse("skill_ledger:public"))

        self.assertContains(response, "Python")
        self.assertNotContains(response, "Distinctive private implementation note")

    def test_public_view_noindex_meta_tag_present(self):
        response = self.client.get(reverse("skill_ledger:public"))

        self.assertContains(response, '<meta name="robots" content="noindex, nofollow">')

    def test_private_ledger_contains_view_public_ledger_link(self):
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(reverse("skill_ledger:list"))

        self.assertContains(response, "View public ledger")
        self.assertContains(response, reverse("skill_ledger:public"))

    def test_sprint_70_private_ledger_unchanged(self):
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(reverse("skill_ledger:list"))

        self.assertContains(response, "Verified")
        self.assertContains(response, "Learning Target")
        self.assertContains(response, "Studying")
        self.assertContains(response, "No Evidence")


class PrivateAIAdvisoryEvaluationCasebookTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="casebookuser",
            password="StrongPass12345",
        )
        self.url = reverse("skill_ledger:advisory_evaluation_casebook")
        self.hub_url = reverse("skill_ledger:advisory_ai_review_hub")

    def _login(self):
        self.client.login(username="casebookuser", password="StrongPass12345")

    def _get_casebook(self):
        self._login()
        return self.client.get(self.url)

    def test_evaluation_casebook_loads_for_authenticated_user(self):
        response = self._get_casebook()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.url, "/skill-ledger/advisory/evaluation-casebook/")
        self.assertEqual(
            resolve(self.url).view_name,
            "skill_ledger:advisory_evaluation_casebook",
        )
        self.assertContains(response, "Private AI Advisory Evaluation Casebook")
        self.assertContains(
            response,
            "Private planning reference - deterministic cases only",
        )

    def test_evaluation_casebook_redirects_anonymous_user(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response["Location"])

    def test_evaluation_casebook_post_returns_405(self):
        self._login()

        response = self.client.post(self.url, {"case": "review"})

        self.assertEqual(response.status_code, 405)

    def test_evaluation_casebook_renders_structural_case_markers(self):
        response = self._get_casebook()

        self.assertContains(response, 'data-testid="evaluation-case"', count=8)
        self.assertGreaterEqual(
            response.content.decode().count('data-testid="evaluation-case"'),
            8,
        )

    def test_evaluation_casebook_renders_evaluation_focus_labels(self):
        response = self._get_casebook()

        self.assertContains(response, "Evaluation focus", count=8)

    def test_evaluation_casebook_renders_safety_boundary_labels(self):
        response = self._get_casebook()

        self.assertContains(response, "Safety boundary", count=8)

    def test_evaluation_casebook_renders_expected_safe_behaviour(self):
        response = self._get_casebook()

        self.assertContains(response, "Expected safe behaviour", count=8)

    def test_evaluation_casebook_renders_fail_condition(self):
        response = self._get_casebook()

        self.assertContains(response, "Fail condition", count=8)

    def test_evaluation_casebook_advisory_wording_present(self):
        response = self._get_casebook()

        self.assertContains(
            response,
            "These cases are deterministic review examples, not live AI generations.",
        )
        self.assertContains(
            response,
            "Evaluation cases are planning and safety review aids only.",
        )
        self.assertContains(
            response,
            (
                "Passing an evaluation case does not verify skill proficiency or "
                "predict employer outcomes."
            ),
        )
        self.assertContains(response, "This page is private and advisory only.")

    def test_evaluation_casebook_no_live_provider_wording_present(self):
        response = self._get_casebook()

        self.assertContains(response, "No live AI model is used in this version.")
        self.assertContains(response, "No live AI model or provider integration is used.")

    def test_evaluation_casebook_no_mutation_wording_present(self):
        response = self._get_casebook()

        self.assertContains(
            response,
            (
                "These examples do not update CVs, public profiles, applications, "
                "or Skill Ledger evidence."
            ),
        )
        self.assertContains(
            response,
            "No CV, public profile, application, or Skill Ledger evidence is changed.",
        )

    def test_evaluation_casebook_forbidden_phrases_absent(self):
        response = self._get_casebook()

        for phrase in (
            "production AI evaluation framework",
            "live AI evaluation results",
            "automated AI grading",
            "model performance benchmark",
            "provider-powered evaluation",
            "OpenAI",
            "Anthropic",
            "Gemini",
            "LangChain",
            "auto-updates your CV",
            "auto-submits applications",
            "verifies proficiency",
            "predicts employer outcomes",
            "generated by AI",
            "production-ready AI system",
        ):
            with self.subTest(phrase=phrase):
                self.assertNotContains(response, phrase)

    def test_review_hub_links_to_evaluation_casebook(self):
        self._login()

        response = self.client.get(self.hub_url)
        content = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI Advisory Evaluation Casebook")
        self.assertContains(
            response,
            'href="/skill-ledger/advisory/evaluation-casebook/"',
        )
        self.assertEqual(
            content.count('href="/skill-ledger/advisory/evaluation-casebook/"'),
            1,
        )

    def test_sprint_88_explanations_page_unaffected(self):
        self._login()

        response = self.client.get(reverse("skill_ledger:advisory_explanations"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI explanation contract preview")
        self.assertContains(response, "No live provider output is shown here.")
        self.assertContains(response, "Explanations are advisory only.")

    def test_sprint_89_evidence_dashboard_unaffected(self):
        self._login()

        response = self.client.get(reverse("skill_ledger:advisory_ai_evidence"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI explanation layer - safety controls and evidence")
        self.assertContains(response, "No live provider is configured for this sprint.")
        self.assertContains(response, "This dashboard is advisory evidence only.")


class SkillLedgerAdvisoryClaimSafetyExamplesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="claimsafetyuser",
            password="StrongPass12345",
        )
        self.url = reverse("skill_ledger:advisory")

    def _login(self):
        self.client.login(username="claimsafetyuser", password="StrongPass12345")

    def _get_advisory(self):
        self._login()
        return self.client.get(self.url)

    def test_advisory_page_renders_claim_safety_examples_section(self):
        response = self._get_advisory()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Claim-safety examples")
        self.assertContains(response, "Claim-safety examples are advisory only.")

    def test_advisory_page_renders_at_least_four_claim_safety_example_blocks(self):
        response = self._get_advisory()

        self.assertContains(response, 'data-testid="claim-safety-example"', count=4)
        self.assertContains(response, "Learning-target skill claim inflation")
        self.assertContains(response, "Expert in Databricks with production pipeline ownership.")
        self.assertContains(
            response,
            "Databricks is a learning target; portfolio evidence is planned but not yet verified.",
        )
        self.assertNotContains(response, "Expert in dbt with production pipeline ownership.")
        self.assertNotContains(
            response,
            "dbt is a learning target; portfolio evidence is planned but not yet verified.",
        )
        self.assertContains(response, "JD signal mistaken as proof of proficiency")
        self.assertContains(
            response,
            "Verified skill without enough public evidence context",
        )
        self.assertContains(
            response,
            "Public CV, LinkedIn, or profile wording before manual review",
        )

    def test_advisory_page_renders_unsafe_claim_and_safer_alternative_labels(self):
        response = self._get_advisory()

        self.assertContains(response, "Unsafe inflated claim:")
        self.assertContains(response, "Safer evidence-grounded alternative:")
        self.assertContains(response, "Manual review note:")
        self.assertContains(response, "Unsafe examples show wording to avoid.")
        self.assertContains(response, "Safer examples still require manual evidence review.")

    def test_advisory_page_renders_manual_review_wording_before_public_use(self):
        response = self._get_advisory()

        self.assertContains(response, "Manual review is required before using any claim in a CV")
        self.assertContains(response, "cover letter, or interview answer.")
        self.assertContains(
            response,
            (
                "Review CV, LinkedIn, public profile, cover letter, and interview "
                "wording manually before publishing any claim."
            ),
        )

    def test_advisory_page_renders_no_live_ai_and_no_certification_wording(self):
        response = self._get_advisory()

        self.assertContains(response, "No live AI model is used in this advisory page.")
        self.assertContains(
            response,
            "These examples do not certify proficiency or predict employer outcomes.",
        )
        self.assertContains(
            response,
            "Do not use learning-target, studying, or no-evidence skills as verified claims.",
        )
        self.assertContains(response, "A JD signal does not prove proficiency.")

    def test_advisory_page_renders_no_mutation_wording(self):
        response = self._get_advisory()

        self.assertContains(
            response,
            "This page does not update CVs, LinkedIn, public profiles, applications, or Skill",
        )
        self.assertContains(response, "Ledger evidence.")

    def test_advisory_page_preserves_deterministic_classification_wording(self):
        response = self._get_advisory()

        self.assertContains(response, "Classifications are deterministic rules, not AI inference.")
        self.assertContains(response, "LEARNING TARGET</strong> - do not claim as verified")
        self.assertContains(response, "STUDYING</strong> - personal study only, not claim-ready")
        self.assertContains(response, "NO EVIDENCE</strong> - gap identified, do not claim")
        self.assertContains(
            response,
            (
                "Classifications are deterministic - derived from your Skill Ledger "
                "evidence_level and visibility fields. They are not AI-generated assessments."
            ),
        )

    def test_advisory_page_claim_safety_examples_require_login(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response["Location"])

    def test_advisory_page_post_remains_get_only(self):
        self._login()

        response = self.client.post(self.url, {"skill_name": "Python"})

        self.assertEqual(response.status_code, 405)

    def test_advisory_page_claim_safety_examples_render_without_advisory_rows(self):
        response = self._get_advisory()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No Skill Ledger entries available")
        self.assertContains(response, "Claim-safety examples")
        self.assertContains(response, 'data-testid="claim-safety-example"', count=4)


class MockedAIResponseEvaluatorTests(TestCase):
    def test_evaluator_detects_learning_target_inflation(self):
        response_text = (
            "Your learning target in Databricks is verified and claim-ready for interviews."
        )
        evaluation = evaluate_mocked_ai_response(response_text)

        self.assertEqual(evaluation.verdict, "blocked")
        codes = {finding.code for finding in evaluation.findings}
        self.assertIn(LEARNING_TARGET_INFLATION, codes)

    def test_evaluator_detects_jd_signal_as_proficiency(self):
        response_text = "The JD signal proves you are proficient in Airflow."
        evaluation = evaluate_mocked_ai_response(response_text)

        self.assertEqual(evaluation.verdict, "blocked")
        codes = {finding.code for finding in evaluation.findings}
        self.assertIn(JD_SIGNAL_AS_PROFICIENCY, codes)

    def test_evaluator_detects_mutation_claim(self):
        response_text = "We updated your CV with the new skills."
        evaluation = evaluate_mocked_ai_response(response_text)

        self.assertEqual(evaluation.verdict, "blocked")
        codes = {finding.code for finding in evaluation.findings}
        self.assertIn(MUTATION_CLAIM_DETECTED, codes)

    def test_evaluator_detects_document_generation_claim(self):
        response_text = "We generated your CV for this role."
        evaluation = evaluate_mocked_ai_response(response_text)

        self.assertEqual(evaluation.verdict, "blocked")
        codes = {finding.code for finding in evaluation.findings}
        self.assertIn(GENERATED_DOCUMENT_DETECTED, codes)

    def test_evaluator_detects_auto_action_claim(self):
        response_text = "CareerFunnel has saved the changes on your behalf."
        evaluation = evaluate_mocked_ai_response(response_text)

        self.assertEqual(evaluation.verdict, "blocked")
        codes = {finding.code for finding in evaluation.findings}
        self.assertIn(AUTO_ACTION_DETECTED, codes)

    def test_evaluator_detects_certification_guarantee_wording(self):
        response_text = "This analysis certifies your proficiency in Python."
        evaluation = evaluate_mocked_ai_response(response_text)

        self.assertEqual(evaluation.verdict, "blocked")
        codes = {finding.code for finding in evaluation.findings}
        self.assertIn(CERTIFICATION_GUARANTEE, codes)

    def test_evaluator_detects_employer_outcome_prediction(self):
        response_text = "This wording guarantees interviews with top employers."
        evaluation = evaluate_mocked_ai_response(response_text)

        self.assertEqual(evaluation.verdict, "blocked")
        codes = {finding.code for finding in evaluation.findings}
        self.assertIn(EMPLOYER_OUTCOME_PREDICTION, codes)

    def test_evaluator_detects_live_ai_provider_implication(self):
        response_text = "OpenAI confirmed your skill level for this role."
        evaluation = evaluate_mocked_ai_response(response_text)

        self.assertEqual(evaluation.verdict, "blocked")
        codes = {finding.code for finding in evaluation.findings}
        self.assertIn(LIVE_PROVIDER_IMPLICATION, codes)

    def test_evaluator_detects_empty_response(self):
        evaluation = evaluate_mocked_ai_response("   ")

        self.assertEqual(evaluation.verdict, "blocked")
        self.assertEqual(len(evaluation.findings), 1)
        self.assertEqual(evaluation.findings[0].code, EMPTY_RESPONSE)

    def test_evaluation_finding_is_frozen_dataclass(self):
        finding = EvaluationFinding(
            code=LEARNING_TARGET_INFLATION,
            excerpt="learning target verified",
            severity="block",
        )

        with self.assertRaises(FrozenInstanceError):
            finding.code = "changed"

    def test_mocked_ai_response_evaluation_is_frozen_dataclass(self):
        evaluation: MockedAIResponseEvaluation = evaluate_mocked_ai_response(
            "Advisory-only manual review note."
        )

        with self.assertRaises(FrozenInstanceError):
            evaluation.verdict = "blocked"

    def test_evaluator_returns_allowed_for_safe_advisory_text(self):
        response_text = (
            "This explanation is advisory only. Manual review is required before reuse. "
            "Databricks remains a learning target and should not be presented as verified "
            "without reviewed evidence."
        )
        evaluation = evaluate_mocked_ai_response(response_text)

        self.assertEqual(evaluation.verdict, "allowed")
        self.assertEqual(evaluation.findings, ())

    def test_evaluator_allows_response_with_all_required_safety_wording(self):
        response_text = (
            f"{REQUIRED_EXPLANATION_SAFETY_WARNING} "
            "Review evidence manually before adding any skill to your CV or LinkedIn."
        )
        evaluation = evaluate_mocked_ai_response(response_text)

        self.assertEqual(evaluation.verdict, "allowed")
        self.assertEqual(evaluation.findings, ())

    def test_evaluator_inherits_sprint_87_forbidden_phrases(self):
        response_text = "Based on this row, you are qualified for the role."
        evaluation = evaluate_mocked_ai_response(response_text)

        self.assertEqual(evaluation.verdict, "blocked")
        self.assertTrue(
            any(
                finding.excerpt.lower() == "you are qualified"
                for finding in evaluation.findings
            )
        )
        self.assertIn(
            "you are qualified",
            FORBIDDEN_EXPLANATION_PHRASES,
        )
        self.assertIn(
            "you are qualified",
            EVALUATION_FORBIDDEN_PHRASES,
        )

    def test_findings_include_non_empty_excerpts(self):
        response_text = "We generated your CV and OpenAI confirmed the result."
        evaluation = evaluate_mocked_ai_response(response_text)

        self.assertGreater(len(evaluation.findings), 0)
        for finding in evaluation.findings:
            self.assertTrue(finding.excerpt.strip())

    def test_input_length_is_preserved(self):
        response_text = "  Advisory-only note with leading spaces.  "
        evaluation = evaluate_mocked_ai_response(response_text)

        self.assertEqual(evaluation.input_length, len(response_text))

    def test_evaluated_at_sprint_is_sprint_101(self):
        evaluation = evaluate_mocked_ai_response("Manual review remains required.")

        self.assertEqual(evaluation.evaluated_at_sprint, "sprint_101")

    def test_evaluator_does_not_require_database_records(self):
        evaluation = evaluate_mocked_ai_response("Deterministic advisory output only.")

        self.assertEqual(evaluation.verdict, "allowed")
        self.assertEqual(SkillEntry.objects.count(), 0)

    def test_evaluator_uses_specific_codes_for_multiple_findings(self):
        response_text = (
            "We generated your CV. OpenAI confirmed proficiency. "
            "This guarantees interviews."
        )
        evaluation = evaluate_mocked_ai_response(response_text)

        self.assertEqual(evaluation.verdict, "blocked")
        codes = {finding.code for finding in evaluation.findings}
        self.assertIn(GENERATED_DOCUMENT_DETECTED, codes)
        self.assertIn(LIVE_PROVIDER_IMPLICATION, codes)
        self.assertIn(EMPLOYER_OUTCOME_PREDICTION, codes)

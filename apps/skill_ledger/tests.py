from io import StringIO

from django.apps import apps
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
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
from .management.commands.seed_skill_ledger import LEARNING_TARGET_NOTES, VERIFIED_DEFAULT_NOTES
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

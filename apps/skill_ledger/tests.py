from io import StringIO

from django.contrib import admin
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .management.commands.seed_skill_ledger import LEARNING_TARGET_NOTES, VERIFIED_DEFAULT_NOTES
from .models import SkillEntry


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

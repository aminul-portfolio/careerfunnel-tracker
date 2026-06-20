from django.contrib import admin
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

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

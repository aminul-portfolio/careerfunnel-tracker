from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.skill_ledger.models import SkillEntry
from apps.skill_ledger.selectors import get_skill_ledger_evidence_summary


class SkillLedgerOwnershipIsolationSkillsViewTests(TestCase):
    """Sprint 110A Phase 3A: skills evidence-summary page ownership isolation."""

    def setUp(self):
        self.owner = User.objects.create_user(username="skills_owner", password="pass")
        self.other = User.objects.create_user(username="skills_other", password="pass")
        self.url = reverse("skills:final_career_intelligence_workflow")

    def _create_entry(self, *, user, skill_name, evidence_level):
        return SkillEntry.objects.create(
            user=user,
            skill_name=skill_name,
            category=SkillEntry.Category.PROGRAMMING,
            evidence_level=evidence_level,
            visibility=SkillEntry.Visibility.PRIVATE,
        )

    def test_skills_evidence_summary_page_uses_only_request_user_entries(self):
        self._create_entry(
            user=self.owner,
            skill_name="OwnerPython",
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
        )
        self._create_entry(
            user=self.other,
            skill_name="OtherPython",
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
        )
        self.client.login(username="skills_owner", password="pass")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        summary = response.context["skill_ledger_summary"]
        self.assertEqual(summary["total_entries"], 1)
        self.assertEqual(summary["counts"][SkillEntry.EvidenceLevel.VERIFIED], 1)
        verified_names = [entry.skill_name for entry in summary["verified_entries"]]
        self.assertEqual(verified_names, ["OwnerPython"])
        self.assertNotIn("OtherPython", verified_names)

    def test_another_users_entries_do_not_alter_counts_or_displayed_evidence(self):
        self._create_entry(
            user=self.owner,
            skill_name="OwnerStudying",
            evidence_level=SkillEntry.EvidenceLevel.STUDYING,
        )
        for index in range(3):
            self._create_entry(
                user=self.other,
                skill_name=f"OtherVerified{index}",
                evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
            )
        self.client.login(username="skills_owner", password="pass")
        response = self.client.get(self.url)
        summary = response.context["skill_ledger_summary"]
        self.assertEqual(summary["total_entries"], 1)
        self.assertEqual(summary["counts"][SkillEntry.EvidenceLevel.VERIFIED], 0)
        self.assertEqual(summary["counts"][SkillEntry.EvidenceLevel.STUDYING], 1)
        self.assertEqual(summary["verified_entries"], [])
        expected = get_skill_ledger_evidence_summary(self.owner)
        self.assertEqual(summary["counts"], expected["counts"])
        self.assertEqual(summary["total_entries"], expected["total_entries"])

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.skills.services.job_ai_capability_matching import (
    match_job_description_to_ai_capabilities,
)
from apps.skills.views import DEMO_JOB_DESCRIPTION

FORBIDDEN_PAGE_PHRASES = (
    "auto-apply",
    "auto-send",
    "web scraping",
    "scrapes jobs",
    "billing",
    "gmail integration",
    "calendar integration",
    "live saas users",
    "customers",
    "production deployment",
    "openai",
    "claude",
    "external provider call",
)


class JobAICapabilityMatchReportViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")
        self.url = reverse("skills:job_ai_capability_match_report")
        self.expected = match_job_description_to_ai_capabilities(DEMO_JOB_DESCRIPTION)

    def _login(self):
        self.client.login(username="aminul", password="StrongPass12345")

    def _get(self):
        self._login()
        return self.client.get(self.url)

    def test_page_requires_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_page_loads_for_logged_in_user(self):
        response = self._get()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Job AI Capability Match")

    def test_skill_gap_page_loads_without_error(self):
        response = self._get()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Missing / weak capabilities")

    def test_skill_gap_page_shows_advisory_only_message(self):
        response = self._get()
        self.assertContains(
            response,
            (
                "Skill gap signals are advisory only. They indicate learning priorities, "
                "not current proficiency."
            ),
        )

    def test_skill_gap_page_shows_portfolio_evidence_required_message(self):
        response = self._get()
        self.assertContains(
            response,
            (
                "Before adding a skill to your CV or public profile, ensure it is supported "
                "by project evidence, tests, screenshots, or prior work experience."
            ),
        )

    def test_skill_gap_wording_does_not_claim_skill_as_proven(self):
        response = self._get()
        content = response.content.decode()
        self.assertNotIn("proven proficiency", content)
        self.assertNotIn("verified skill", content)
        self.assertNotIn("is ready to claim", content)
        self.assertNotIn("skills are ready to claim", content)
        self.assertNotIn("recommendation proves", content)
        self.assertNotIn("proves proficiency", content)

    def test_skill_intelligence_wording_does_not_mention_auto_apply_or_auto_sync(self):
        response = self._get()
        content = response.content.decode()
        for phrase in (
            "auto-apply",
            "auto apply",
            "auto-sync",
            "auto sync",
            "automatically updated",
            "Gmail",
            "OAuth",
            "Calendar",
            "Submit Application",
            "Apply Now",
        ):
            self.assertNotIn(phrase, content)

    def test_skill_gap_page_does_not_invent_learning_target_boundary(self):
        response = self._get()
        content = response.content.decode()
        self.assertNotIn("LEARNING_TARGET", content)

    def test_match_score_appears(self):
        response = self._get()
        self.assertContains(response, str(self.expected.match_score))
        self.assertContains(response, "Match Score")

    def test_match_label_appears(self):
        response = self._get()
        self.assertContains(response, self.expected.match_label)
        self.assertContains(response, "Match Label")

    def test_detected_terms_appear(self):
        response = self._get()
        self.assertContains(response, "Detected terms")
        for term in self.expected.detected_terms:
            self.assertContains(response, term)

    def test_matched_capability_titles_appear(self):
        response = self._get()
        self.assertContains(response, "Matched capabilities")
        for capability in self.expected.matched_capabilities:
            self.assertContains(response, capability.title)

    def test_claim_safety_wording_appears(self):
        response = self._get()
        content = response.content.decode().lower()
        self.assertIn("rule-based keyword matching report", content)
        self.assertIn("not predictive hiring ai", content)
        self.assertIn("does not use external ai apis", content)
        self.assertIn("does not scrape jobs", content)
        self.assertIn("demo sample job description", content)

    def test_page_does_not_contain_forbidden_claim_phrases(self):
        response = self._get()
        content = response.content.decode().lower()
        for phrase in FORBIDDEN_PAGE_PHRASES:
            self.assertNotIn(phrase, content, msg=f"Page contains forbidden phrase: {phrase}")

    def test_view_uses_service_output_safely(self):
        response = self._get()
        self.assertIn("match_result", response.context)
        self.assertIn("demo_job_description", response.context)
        self.assertEqual(response.context["demo_job_description"], DEMO_JOB_DESCRIPTION)
        self.assertEqual(response.context["match_result"], self.expected)

    def test_demo_sample_job_description_appears(self):
        response = self._get()
        self.assertContains(response, DEMO_JOB_DESCRIPTION)
        self.assertContains(response, "not a real application")

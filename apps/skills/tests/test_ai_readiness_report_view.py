from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.skills.services.ai_readiness_scoring import (
    build_portfolio_baseline_ai_readiness_score,
)

FORBIDDEN_PAGE_PHRASES = (
    "auto-apply",
    "auto-send",
    "scraping",
    "billing",
    "gmail integration",
    "calendar integration",
    "live saas users",
    "customers",
    "production deployment",
)


class AIReadinessReportViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")
        self.url = reverse("skills:ai_readiness_report")
        self.expected = build_portfolio_baseline_ai_readiness_score()

    def _login(self):
        self.client.login(username="aminul", password="StrongPass12345")

    def _get(self):
        self._login()
        return self.client.get(self.url)

    def test_readiness_report_page_loads_successfully(self):
        response = self._get()
        self.assertEqual(response.status_code, 200)

    def test_readiness_score_appears(self):
        response = self._get()
        self.assertContains(response, str(self.expected.readiness_score))
        self.assertContains(response, "AI Readiness Score")

    def test_readiness_label_appears(self):
        response = self._get()
        self.assertContains(response, self.expected.readiness_label)
        self.assertContains(response, "Readiness Label")

    def test_claim_safety_wording_appears(self):
        response = self._get()
        content = response.content.decode().lower()
        self.assertIn("rule-based advisory readiness report", content)
        self.assertIn("not predictive hiring ai", content)
        self.assertIn("does not use external ai apis", content)
        self.assertIn("manual review", content)

    def test_page_does_not_contain_forbidden_claim_phrases(self):
        response = self._get()
        content = response.content.decode().lower()
        for phrase in FORBIDDEN_PAGE_PHRASES:
            self.assertNotIn(phrase, content, msg=f"Page contains forbidden phrase: {phrase}")

    def test_page_requires_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_service_output_safely(self):
        response = self._get()
        self.assertIn("readiness", response.context)
        self.assertEqual(response.context["readiness"], self.expected)

    def test_capability_coverage_counts_appear(self):
        response = self._get()
        self.assertContains(
            response,
            f"{self.expected.capabilities_with_evidence}/{self.expected.capabilities_total}",
        )
        self.assertContains(response, "Explanation points")
        self.assertContains(response, self.expected.capability_lines[0].title)

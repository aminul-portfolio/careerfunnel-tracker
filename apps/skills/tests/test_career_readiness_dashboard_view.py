from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.skills.services.career_readiness_dashboard import build_career_readiness_dashboard

FORBIDDEN_PAGE_PHRASES = (
    "auto-apply",
    "auto-send",
    "web scraping",
    "scrapes jobs",
    "gmail integration",
    "calendar integration",
    "billing",
    "live saas users",
    "customers",
    "production deployment",
    "openai",
    "claude",
    "external provider call",
)


class CareerReadinessDashboardViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")
        self.url = reverse("skills:career_readiness_dashboard")
        self.expected = build_career_readiness_dashboard()

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
        self.assertContains(response, "Career Readiness Dashboard")

    def test_readiness_score_appears(self):
        response = self._get()
        self.assertContains(response, "AI Readiness Score")
        self.assertContains(response, str(self.expected.readiness_score))
        self.assertContains(response, self.expected.readiness_label)

    def test_job_match_score_appears(self):
        response = self._get()
        self.assertContains(response, "Job AI Match Score")
        self.assertContains(response, str(self.expected.job_match_score))
        self.assertContains(response, self.expected.job_match_label)

    def test_overall_priority_appears(self):
        response = self._get()
        self.assertContains(response, "Overall Priority")
        self.assertContains(response, self.expected.overall_priority)

    def test_next_best_action_appears(self):
        response = self._get()
        self.assertContains(response, "Next best action")
        self.assertContains(response, self.expected.next_best_action)

    def test_kpi_cards_appear(self):
        response = self._get()
        for card in self.expected.kpi_cards:
            self.assertContains(response, card.label)
            self.assertContains(response, card.value)
            self.assertContains(response, card.status)

    def test_summary_points_appear(self):
        response = self._get()
        self.assertContains(response, "Summary points")
        for point in self.expected.summary_points:
            self.assertContains(response, point)

    def test_dashboard_sections_appear(self):
        response = self._get()
        self.assertContains(response, "Dashboard sections")
        for section in self.expected.dashboard_sections:
            self.assertContains(response, section.title)
            self.assertContains(response, section.summary)

    def test_claim_safety_wording_appears(self):
        response = self._get()
        content = response.content.decode().lower()
        self.assertIn("rule-based career readiness dashboard for manual review", content)
        self.assertIn("not predictive hiring ai", content)
        self.assertIn("does not use external ai apis", content)
        self.assertIn("does not automate applications", content)
        self.assertIn("does not replace human judgement", content)
        self.assertIn("manual review", content)

    def test_view_uses_service_output_safely(self):
        response = self._get()
        self.assertIn("dashboard", response.context)
        self.assertEqual(response.context["dashboard"], self.expected)

    def test_page_does_not_contain_forbidden_claim_phrases(self):
        response = self._get()
        content = response.content.decode().lower()
        for phrase in FORBIDDEN_PAGE_PHRASES:
            self.assertNotIn(phrase, content, msg=f"Page contains forbidden phrase: {phrase}")

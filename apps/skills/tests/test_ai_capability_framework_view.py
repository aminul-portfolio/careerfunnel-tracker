from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.skills.services.ai_capability_framework import get_ai_capability_framework

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


class AICapabilityFrameworkViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")
        self.url = reverse("skills:ai_capability_framework")
        self.sample_capability = get_ai_capability_framework()[0]

    def _login(self):
        self.client.login(username="aminul", password="StrongPass12345")

    def _get(self):
        self._login()
        return self.client.get(self.url)

    def test_page_returns_http_200(self):
        response = self._get()
        self.assertEqual(response.status_code, 200)

    def test_page_contains_framework_title(self):
        response = self._get()
        self.assertContains(response, "AI Capability Framework")

    def test_page_includes_capability_title_from_service(self):
        response = self._get()
        self.assertContains(response, self.sample_capability.title)

    def test_page_includes_manual_and_advisory_wording(self):
        response = self._get()
        content = response.content.decode().lower()
        self.assertIn("manual and advisory", content)

    def test_page_includes_example_tools_only_wording(self):
        response = self._get()
        content = response.content.decode().lower()
        self.assertIn("example tools only", content)

    def test_page_does_not_contain_forbidden_claim_phrases(self):
        response = self._get()
        content = response.content.decode().lower()
        for phrase in FORBIDDEN_PAGE_PHRASES:
            self.assertNotIn(phrase, content, msg=f"Page contains forbidden phrase: {phrase}")

    def test_page_requires_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_page_context_uses_service_capabilities(self):
        response = self._get()
        self.assertIn("capabilities", response.context)
        self.assertEqual(
            tuple(response.context["capabilities"]),
            get_ai_capability_framework(),
        )

from pathlib import Path

from django.apps import apps
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from apps.ai_agents.views import (
    LOCKED_DISCLOSURE,
    LOCKED_MANUAL_REVIEW_WARNING,
    LOCKED_PRIVACY_WARNING,
    LOCKED_SCREENSHOT_WARNING,
)


class ClaimSafetyReviewRouteTests(TestCase):
    def setUp(self):
        self.url = reverse("ai_agents:claim_safety_review")
        self.staff_user = User.objects.create_user(
            username="staff-user",
            email="staff@example.com",
            password="password123",
            is_staff=True,
        )
        self.non_staff_user = User.objects.create_user(
            username="nonstaff-user",
            email="nonstaff@example.com",
            password="password123",
            is_staff=False,
        )

    def _full_model_count(self) -> int:
        total = 0
        for model in apps.get_models():
            total += model.objects.count()
        return total

    def _assert_locked_strings(self, content: str) -> None:
        self.assertIn(LOCKED_DISCLOSURE, content)
        self.assertIn(LOCKED_PRIVACY_WARNING, content)
        self.assertIn(LOCKED_SCREENSHOT_WARNING, content)
        self.assertIn(LOCKED_MANUAL_REVIEW_WARNING, content)

    def test_anonymous_get_redirects_or_forbidden(self):
        response = self.client.get(self.url)
        self.assertIn(response.status_code, (302, 403))

    def test_anonymous_post_redirects_or_forbidden(self):
        response = self.client.post(
            self.url,
            {"claim_text": "Portfolio project", "channel": "general"},
        )
        self.assertIn(response.status_code, (302, 403))

    def test_non_staff_get_redirects_or_forbidden(self):
        self.client.force_login(self.non_staff_user)
        response = self.client.get(self.url)
        self.assertIn(response.status_code, (302, 403))

    def test_staff_get_renders_form_and_locked_disclosure(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self._assert_locked_strings(content)
        self.assertContains(response, "name=\"claim_text\"")
        self.assertContains(response, "name=\"evidence_context\"")
        self.assertContains(response, "name=\"channel\"")

    def test_staff_post_returns_review_and_locked_disclosure(self):
        self.client.force_login(self.staff_user)
        response = self.client.post(
            self.url,
            {
                "claim_text": "CareerFunnel Tracker is a local portfolio project.",
                "evidence_context": "README what the platform does",
                "channel": "general",
            },
        )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self._assert_locked_strings(content)
        self.assertIn("overall_verdict:", content)
        self.assertIn("risk_level:", content)

    def test_post_without_csrf_is_forbidden(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.staff_user)
        response = csrf_client.post(
            self.url,
            {"claim_text": "Local project", "channel": "general"},
        )
        self.assertEqual(response.status_code, 403)

    def test_input_length_cap_rejects_oversized_claim_text(self):
        self.client.force_login(self.staff_user)
        response = self.client.post(
            self.url,
            {
                "claim_text": "x" * 1201,
                "evidence_context": "",
                "channel": "general",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ensure this value has at most 1200 characters")

    def test_input_length_cap_rejects_oversized_evidence_context(self):
        self.client.force_login(self.staff_user)
        response = self.client.post(
            self.url,
            {
                "claim_text": "Local project",
                "evidence_context": "x" * 2001,
                "channel": "general",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ensure this value has at most 2000 characters")

    def test_script_payload_is_escaped(self):
        self.client.force_login(self.staff_user)
        payload = "<script>alert(\"x\")</script>"
        response = self.client.post(
            self.url,
            {
                "claim_text": payload,
                "evidence_context": "",
                "channel": "general",
            },
        )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertNotIn("<script>", content)
        self.assertIn("&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;", content)

    def test_template_does_not_use_safe_mark_safe_or_autoescape_off(self):
        template_path = (
            Path(__file__).resolve().parents[2]
            / "templates"
            / "claim_safety"
            / "review.html"
        )
        content = template_path.read_text(encoding="utf-8").lower()
        self.assertNotIn("|safe", content)
        self.assertNotIn("mark_safe", content)
        self.assertNotIn("autoescape off", content)

    def test_view_form_template_do_not_import_provider_or_network_symbols(self):
        repo_root = Path(__file__).resolve().parents[2]
        paths = [
            repo_root / "apps" / "ai_agents" / "forms.py",
            repo_root / "apps" / "ai_agents" / "views.py",
            repo_root / "apps" / "ai_agents" / "test_claim_safety_review_route.py",
            repo_root / "templates" / "claim_safety" / "review.html",
        ]
        forbidden_modules = (
            "openai",
            "anthropic",
            "gemini",
            "langchain",
            "requests",
            "httpx",
            "socket",
            "urllib",
        )
        for path in paths:
            content = path.read_text(encoding="utf-8").lower()
            for module_name in forbidden_modules:
                self.assertNotIn(f"import {module_name}", content)
                self.assertNotIn(f"from {module_name}", content)

    def test_post_is_stateless_and_does_not_create_rows(self):
        self.client.force_login(self.staff_user)
        before_count = self._full_model_count()
        first = self.client.post(
            self.url,
            {
                "claim_text": "Local project with documented tests.",
                "evidence_context": "README and phase4a log",
                "channel": "portfolio",
            },
        )
        second = self.client.post(
            self.url,
            {
                "claim_text": "Local project with documented tests.",
                "evidence_context": "README and phase4a log",
                "channel": "portfolio",
            },
        )
        after_count = self._full_model_count()
        self.assertEqual(before_count, after_count)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertContains(first, "overall_verdict:")
        self.assertContains(second, "overall_verdict:")

    def test_new_route_view_and_template_names_are_neutral(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("claim-safety/review/", self.url)
        self.assertTemplateUsed(response, "claim_safety/review.html")

    def test_empty_claim_returns_unknown_without_saving(self):
        self.client.force_login(self.staff_user)
        before_count = self._full_model_count()
        response = self.client.post(
            self.url,
            {
                "claim_text": "   ",
                "evidence_context": "",
                "channel": "general",
            },
        )
        after_count = self._full_model_count()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(before_count, after_count)
        self.assertContains(response, "overall_verdict:")
        self.assertContains(response, "unknown")

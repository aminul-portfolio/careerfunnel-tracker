from pathlib import Path

from django.conf import settings
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

    def test_sprint_69h_premium_shell_classes_render(self):
        response = self._get()
        content = response.content.decode()

        expected_classes = [
            "cf69h-page",
            "cf69h-hero",
            "cf69h-safety-note",
            "cf69h-summary-grid",
            "cf69h-summary-card",
            "cf69h-section",
            "cf69h-evidence-grid",
            "cf69h-evidence-card",
        ]
        for class_name in expected_classes:
            with self.subTest(class_name=class_name):
                self.assertIn(class_name, content)

    def test_sprint_69h_preserves_advisory_planning_framing(self):
        response = self._get()

        self.assertContains(response, "manual and advisory")
        self.assertContains(response, "read-only page")
        self.assertContains(response, "portfolio planning")
        self.assertContains(response, "Planning framework")
        self.assertContains(response, "Evidence-informed review before public claims")
        self.assertContains(response, "capability planning")

    def test_sprint_69h_existing_capability_dimensions_still_render(self):
        response = self._get()
        capabilities = get_ai_capability_framework()

        self.assertContains(response, capabilities[0].title)
        self.assertContains(response, capabilities[0].description)
        self.assertContains(response, capabilities[0].evidence_examples[0])
        self.assertContains(response, capabilities[0].career_relevance)
        self.assertContains(response, "Evidence examples")
        self.assertContains(response, "Career relevance")
        self.assertContains(response, "Tool examples")
        self.assertContains(response, "Claim-safety note")

    def test_sprint_69h_summary_uses_existing_capabilities(self):
        response = self._get()

        self.assertContains(response, "Capability categories")
        self.assertContains(response, f"<strong>{len(get_ai_capability_framework())}</strong>")
        self.assertContains(response, "Manual")
        self.assertContains(response, "Planning")
        self.assertContains(response, "Examples")

    def test_sprint_69h_learning_targets_are_not_framed_as_proven_current_skills(self):
        response = self._get()
        content = response.content.decode().lower()

        for skill_name in ("dbt", "airflow", "snowflake", "bigquery", "power bi"):
            with self.subTest(skill_name=skill_name):
                self.assertIn(skill_name, content)
        self.assertContains(response, "Evidence review required before public claims")
        forbidden_phrases = [
            "verified mastery",
            "guaranteed readiness",
            "proven current skills",
            "employer verification",
            "external verification",
            "hiring prediction",
            "automatic career decisioning",
        ]
        for phrase in forbidden_phrases:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, content)

    def test_sprint_69h_does_not_imply_automatic_cv_or_profile_changes(self):
        response = self._get()
        content = response.content.decode().lower()

        self.assertIn("not automatic cv changes", content)
        forbidden_phrases = [
            "updates your cv automatically",
            "automatic profile updates",
            "updates your profile automatically",
            "rewrites your cv automatically",
        ]
        for phrase in forbidden_phrases:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, content)

    def test_sprint_69h_get_request_does_not_create_update_or_delete_records(self):
        before_user_count = User.objects.count()
        before_capabilities = get_ai_capability_framework()

        response = self._get()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), before_user_count)
        self.assertEqual(get_ai_capability_framework(), before_capabilities)

    def test_sprint_69h_styles_remain_page_scoped(self):
        template_path = (
            Path(settings.BASE_DIR) / "templates" / "skills" / "ai_capability_framework.html"
        )
        template_source = template_path.read_text(encoding="utf-8")

        self.assertIn("cf69h-", template_source)
        self.assertIn("<style>", template_source)
        self.assertNotIn("static/css", template_source)
        self.assertNotIn("static/js", template_source)

    def test_sprint_69h_phase_a_styles_are_scoped_to_capability_template(self):
        template_path = (
            Path(settings.BASE_DIR) / "templates" / "skills" / "ai_capability_framework.html"
        )
        template_source = template_path.read_text(encoding="utf-8")

        self.assertIn("cf69h-", template_source)
        self.assertIn("cf-ai-capability-framework", template_source)
        self.assertIn("<style>", template_source)
        self.assertNotIn("static/css", template_source)
        self.assertNotIn("static/js", template_source)

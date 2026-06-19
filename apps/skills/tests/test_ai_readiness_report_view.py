from pathlib import Path

from django.conf import settings
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

    def test_sprint_69h_b_premium_shell_classes_render(self):
        response = self._get()
        content = response.content.decode()

        expected_classes = [
            "cf69h-page",
            "cf69h-hero",
            "cf69h-safety-note",
            "cf69h-kpi-grid",
            "cf69h-kpi-card",
            "cf69h-section",
            "cf69h-section-list",
            "cf69h-table-wrap",
        ]
        for class_name in expected_classes:
            with self.subTest(class_name=class_name):
                self.assertIn(class_name, content)

    def test_sprint_69j_b_shared_premium_classes_render(self):
        response = self._get()
        content = response.content.decode()

        expected_classes = [
            "cf-premium-page",
            "cf-premium-hero",
            "cf-premium-hero-title",
            "cf-premium-hero-copy",
            "cf-premium-advisory",
            "cf-premium-advisory-manual",
            "cf-premium-trust-list",
            "cf-premium-trust-list-item",
            "cf-premium-pill-list",
            "cf-premium-pill",
            "cf-premium-section",
        ]
        for class_name in expected_classes:
            with self.subTest(class_name=class_name):
                self.assertIn(class_name, content)

    def test_sprint_69h_b_preserves_advisory_planning_framing(self):
        response = self._get()

        self.assertContains(response, "rule-based advisory readiness report")
        self.assertContains(response, "manual review")
        self.assertContains(response, "Planning report")
        self.assertContains(response, "Evidence-informed review before public claims")
        self.assertContains(response, "readiness planning")
        self.assertContains(response, "portfolio evidence review")

    def test_sprint_69h_b_existing_readiness_content_still_renders(self):
        response = self._get()

        self.assertContains(response, "AI Readiness Score")
        self.assertContains(response, str(self.expected.readiness_score))
        self.assertContains(response, self.expected.readiness_label)
        self.assertContains(response, f"Readiness score {self.expected.readiness_score}/100")
        self.assertContains(response, "using weighted capability coverage")
        self.assertContains(response, self.expected.claim_safety_notes[0])
        self.assertContains(response, self.expected.capability_lines[0].title)
        self.assertContains(response, self.expected.capability_lines[0].explanation)

    def test_sprint_69h_b_preserves_manual_capability_framework_link(self):
        response = self._get()

        self.assertContains(response, "Open AI Capability Framework")
        self.assertContains(response, reverse("skills:ai_capability_framework"))

    def test_sprint_69h_b_learning_targets_are_not_framed_as_proven_current_skills(self):
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

    def test_sprint_69h_b_does_not_imply_automatic_cv_or_profile_changes(self):
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

    def test_sprint_69h_b_get_request_does_not_create_update_or_delete_records(self):
        before_user_count = User.objects.count()
        before_readiness = build_portfolio_baseline_ai_readiness_score()

        response = self._get()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), before_user_count)
        self.assertEqual(build_portfolio_baseline_ai_readiness_score(), before_readiness)

    def test_sprint_69h_b_styles_remain_page_scoped(self):
        template_path = (
            Path(settings.BASE_DIR) / "templates" / "skills" / "ai_readiness_report.html"
        )
        template_source = template_path.read_text(encoding="utf-8")

        self.assertIn("cf69h-", template_source)
        self.assertIn("cf-premium-", template_source)
        self.assertIn("<style>", template_source)
        self.assertIn("cf69h-kpi-grid", template_source)
        self.assertIn("cf69h-table-wrap", template_source)
        self.assertNotIn("static/css", template_source)
        self.assertNotIn("static/js", template_source)

    def test_sprint_69h_b_phase_a_and_c_files_are_not_modified_by_this_test_contract(self):
        untouched_paths = [
            Path(settings.BASE_DIR) / "templates" / "skills" / "ai_capability_framework.html",
            Path(settings.BASE_DIR)
            / "templates"
            / "skills"
            / "job_ai_capability_match_report.html",
            Path(settings.BASE_DIR)
            / "apps"
            / "skills"
            / "tests"
            / "test_ai_capability_framework_view.py",
            Path(settings.BASE_DIR)
            / "apps"
            / "skills"
            / "tests"
            / "test_job_ai_capability_match_report_view.py",
        ]

        for path in untouched_paths:
            with self.subTest(path=path):
                content = path.read_text(encoding="utf-8")
                self.assertNotIn("cf-ai-readiness-report", content)
                self.assertNotIn("AI Readiness Score", content)

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.skills.services.learning_recommendations import (
    build_portfolio_baseline_learning_recommendations,
)

FORBIDDEN_PAGE_PHRASES = (
    "auto-apply",
    "auto-send",
    "ai automation",
    "automated career decision",
    "web scraping",
    "scrapes jobs",
    "employer verified",
    "employer verification",
    "guaranteed readiness",
    "gmail integration",
    "calendar integration",
    "billing",
    "live job market",
    "live saas users",
    "customers",
    "production deployment",
    "openai",
    "claude",
    "external provider call",
)


class LearningRecommendationsReportViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")
        self.url = reverse("skills:learning_recommendations_report")
        self.expected = build_portfolio_baseline_learning_recommendations()

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
        self.assertContains(response, "Learning Recommendations")

    def test_learning_recommendations_report_page_loads_without_error(self):
        response = self._get()
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "skills/learning_recommendations_report.html")

    def test_learning_recommendations_report_advisory_only_label_present(self):
        response = self._get()
        self.assertContains(
            response,
            "Rule-based advisory recommendation report for manual review.",
        )
        self.assertContains(response, "Advisory only. Verify before acting on any item.")

    def test_learning_recommendations_report_step_indicator_present(self):
        response = self._get()
        self.assertContains(response, "Step 4 of 7")

    def test_learning_recommendations_report_get_does_not_create_or_modify_records(self):
        self._login()
        before_user_count = User.objects.count()
        before_user_state = User.objects.values(
            "username",
            "email",
            "is_active",
            "is_staff",
            "is_superuser",
            "last_login",
        ).get(pk=self.user.pk)

        response = self.client.get(self.url)

        after_user_state = User.objects.values(
            "username",
            "email",
            "is_active",
            "is_staff",
            "is_superuser",
            "last_login",
        ).get(pk=self.user.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), before_user_count)
        self.assertEqual(after_user_state, before_user_state)
        self.assertEqual(response.context["recommendations"], self.expected)

    def test_learning_recommendations_page_shows_planning_aid_only_message(self):
        response = self._get()
        self.assertContains(
            response,
            (
                "Learning recommendations are planning aids. A recommendation does not "
                "mean the skill is portfolio-evidenced or ready to claim."
            ),
        )

    def test_learning_recommendations_wording_does_not_claim_proven_proficiency(self):
        response = self._get()
        content = response.content.decode()
        self.assertNotIn("proven proficiency", content)
        self.assertNotIn("verified skill", content)
        self.assertNotIn("is ready to claim", content)
        self.assertNotIn("skills are ready to claim", content)
        self.assertNotIn("recommendation proves", content)
        self.assertNotIn("proves proficiency", content)

    def test_learning_recommendations_page_shows_portfolio_evidence_required_message(self):
        response = self._get()
        self.assertContains(
            response,
            (
                "Before adding a skill to your CV or public profile, ensure it is supported "
                "by project evidence, tests, screenshots, or prior work experience."
            ),
        )

    def test_learning_recommendations_page_does_not_invent_learning_target_boundary(self):
        response = self._get()
        content = response.content.decode()
        self.assertNotIn("LEARNING_TARGET", content)

    def test_overall_priority_appears(self):
        response = self._get()
        self.assertContains(response, "Overall Priority")
        self.assertContains(response, self.expected.overall_priority)

    def test_next_best_action_appears(self):
        response = self._get()
        self.assertContains(response, "Next best action")
        self.assertContains(response, self.expected.next_best_action)

    def test_readiness_summary_appears(self):
        response = self._get()
        self.assertContains(response, "Readiness summary")
        self.assertContains(response, str(self.expected.readiness_summary.readiness_score))
        self.assertContains(response, self.expected.readiness_summary.readiness_label)

    def test_job_match_summary_appears(self):
        response = self._get()
        self.assertContains(response, "Job-match summary")
        self.assertContains(response, str(self.expected.job_match_summary.match_score))
        self.assertContains(response, self.expected.job_match_summary.match_label)

    def test_recommendations_appear(self):
        response = self._get()
        self.assertContains(response, "Recommendations")
        for item in self.expected.recommendations:
            self.assertContains(response, item.title)
            self.assertContains(response, item.category)
            self.assertContains(response, item.priority)

    def test_claim_safety_wording_appears(self):
        response = self._get()
        content = response.content.decode().lower()
        self.assertIn("rule-based advisory recommendation report", content)
        self.assertIn("advisory only", content)
        self.assertIn("not predictive hiring ai", content)
        self.assertIn("does not use external ai apis", content)
        self.assertIn("does not replace human judgement", content)
        self.assertIn("manual review", content)

    def test_view_uses_service_output_safely(self):
        response = self._get()
        self.assertIn("recommendations", response.context)
        self.assertEqual(response.context["recommendations"], self.expected)

    def test_page_does_not_contain_forbidden_claim_phrases(self):
        response = self._get()
        content = response.content.decode().lower()
        for phrase in FORBIDDEN_PAGE_PHRASES:
            self.assertNotIn(phrase, content, msg=f"Page contains forbidden phrase: {phrase}")


class Sprint105EPhase1LearningRecommendationsWorkflowCardPolishTests(TestCase):
    UNSAFE_CLAIM_PHRASES = (
        "is predictive hiring ai",
        "external ai apis are used",
        "applications are automated",
        "auto-apply",
        "employer submission",
        "documents are generated here",
        "guaranteed job outcome",
    )

    MANUAL_ACTION_LABELS = (
        "Open AI Readiness Report",
        "Open Job AI Capability Match",
        "Open AI Capability Framework",
    )

    def setUp(self):
        self.user = User.objects.create_user(
            username="cf105e-learning-user",
            password="StrongPass12345",
        )
        self.url = reverse("skills:learning_recommendations_report")
        self.expected = build_portfolio_baseline_learning_recommendations()

    def _get(self):
        self.client.login(username="cf105e-learning-user", password="StrongPass12345")
        return self.client.get(self.url)

    def test_page_renders_successfully(self):
        response = self._get()
        self.assertEqual(response.status_code, 200)

    def test_page_local_root_and_workflow_markers_present(self):
        response = self._get()
        content = response.content.decode()
        self.assertIn("cf69i-route4-page", content)
        self.assertIn("cf69i-route4-hero", content)
        self.assertIn("cf69i-route4-actions", content)
        self.assertIn("cf-report-manual-actions", content)

    def test_step_indicator_and_advisory_wording_preserved(self):
        response = self._get()
        self.assertContains(response, "Step 4 of 7")
        self.assertContains(
            response,
            "Rule-based advisory recommendation report for manual review.",
        )
        self.assertContains(response, "It is not predictive hiring AI.")
        self.assertContains(response, "It does not use external AI APIs.")
        self.assertContains(response, "It does not automate applications.")
        self.assertContains(response, "It does not replace human judgement.")
        self.assertContains(
            response,
            (
                "Learning recommendations are planning aids. A recommendation does not "
                "mean the skill is portfolio-evidenced or ready to claim."
            ),
        )
        self.assertContains(
            response,
            (
                "Before adding a skill to your CV or public profile, ensure it is supported "
                "by project evidence, tests, screenshots, or prior work experience."
            ),
        )
        self.assertContains(response, "Advisory only. Verify before acting on any item.")

    def test_manual_action_link_labels_preserved(self):
        response = self._get()
        for label in self.MANUAL_ACTION_LABELS:
            with self.subTest(label=label):
                self.assertContains(response, label)

    def test_service_derived_kpi_content_preserved(self):
        response = self._get()
        self.assertContains(response, "Overall Priority")
        self.assertContains(response, self.expected.overall_priority)
        self.assertContains(response, "Next best action")
        self.assertContains(response, self.expected.next_best_action)

    def test_unsafe_claim_phrases_absent(self):
        response = self._get()
        content = response.content.decode().lower()
        for phrase in self.UNSAFE_CLAIM_PHRASES:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, content)

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.skills.services.career_readiness_dashboard import build_career_readiness_dashboard

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

    def test_career_readiness_dashboard_page_loads_without_error(self):
        response = self._get()
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "skills/career_readiness_dashboard.html")

    def test_career_readiness_dashboard_advisory_only_label_present(self):
        response = self._get()
        self.assertContains(
            response,
            "Rule-based career readiness dashboard for manual review.",
        )
        self.assertContains(response, "This is a rule-based career readiness dashboard")

    def test_career_readiness_dashboard_step_indicator_present(self):
        response = self._get()
        self.assertContains(response, "Step 5 of 7")

    def test_career_readiness_dashboard_get_does_not_create_or_modify_records(self):
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
        self.assertEqual(response.context["dashboard"], self.expected)

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
        self.assertIn("rule-based aggregation", content)
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


class Sprint105EPhase1CareerReadinessDashboardWorkflowCardPolishTests(TestCase):
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
        "Open Learning Recommendations",
        "Open AI Capability Framework",
    )

    def setUp(self):
        self.user = User.objects.create_user(
            username="cf105e-readiness-user",
            password="StrongPass12345",
        )
        self.url = reverse("skills:career_readiness_dashboard")
        self.expected = build_career_readiness_dashboard()

    def _get(self):
        self.client.login(username="cf105e-readiness-user", password="StrongPass12345")
        return self.client.get(self.url)

    def test_page_renders_successfully(self):
        response = self._get()
        self.assertEqual(response.status_code, 200)

    def test_page_local_root_and_workflow_markers_present(self):
        response = self._get()
        content = response.content.decode()
        self.assertIn("cf69i-route5-page", content)
        self.assertIn("cf69i-route5-hero", content)
        self.assertIn("cf69i-route5-actions", content)
        self.assertIn("cf-report-manual-actions", content)

    def test_step_indicator_and_advisory_wording_preserved(self):
        response = self._get()
        self.assertContains(response, "Step 5 of 7")
        self.assertContains(
            response,
            "Rule-based career readiness dashboard for manual review.",
        )
        self.assertContains(
            response,
            "This is a rule-based career readiness dashboard for manual review.",
        )
        self.assertContains(response, "It is not predictive hiring AI.")
        self.assertContains(response, "It does not use external AI APIs.")
        self.assertContains(response, "It does not automate applications.")
        self.assertContains(response, "It does not replace human judgement.")
        self.assertContains(
            response,
            "Verify every KPI and summary point manually before portfolio or interview use.",
        )

    def test_manual_action_link_labels_preserved(self):
        response = self._get()
        for label in self.MANUAL_ACTION_LABELS:
            with self.subTest(label=label):
                self.assertContains(response, label)

    def test_service_derived_kpi_content_preserved(self):
        response = self._get()
        for card in self.expected.kpi_cards:
            with self.subTest(label=card.label):
                self.assertContains(response, card.label)
                self.assertContains(response, card.value)
        self.assertContains(response, "Next best action")
        self.assertContains(response, self.expected.next_best_action)

    def test_unsafe_claim_phrases_absent(self):
        response = self._get()
        content = response.content.decode().lower()
        for phrase in self.UNSAFE_CLAIM_PHRASES:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, content)

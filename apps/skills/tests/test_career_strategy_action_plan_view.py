from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.skills.services.career_strategy_action_plan import build_career_strategy_action_plan

FORBIDDEN_PAGE_PHRASES = (
    "auto-apply",
    "auto-send",
    "ai automation",
    "automated career decision",
    "career plan is complete",
    "completed career plan",
    "completion guarantee",
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


class CareerStrategyActionPlanViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")
        self.url = reverse("skills:career_strategy_action_plan")
        self.expected = build_career_strategy_action_plan()

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
        self.assertContains(response, "Career Strategy Action Plan")

    def test_career_strategy_action_plan_page_loads_without_error(self):
        response = self._get()
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "skills/career_strategy_action_plan.html")

    def test_career_strategy_action_plan_advisory_only_label_present(self):
        response = self._get()
        self.assertContains(
            response,
            "Rule-based career strategy action plan for manual review.",
        )
        self.assertContains(response, "Advisory only. Verify before acting on any item.")

    def test_career_strategy_action_plan_step_indicator_present(self):
        response = self._get()
        self.assertContains(response, "Step 6 of 7")

    def test_career_strategy_action_plan_get_does_not_create_or_modify_records(self):
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
        self.assertEqual(response.context["action_plan"], self.expected)

    def test_strategy_label_appears(self):
        response = self._get()
        self.assertContains(response, "Strategy Label")
        self.assertContains(response, self.expected.strategy_label)

    def test_overall_status_appears(self):
        response = self._get()
        self.assertContains(response, "Overall Status")
        self.assertContains(response, self.expected.overall_status)

    def test_next_best_action_appears(self):
        response = self._get()
        self.assertContains(response, "Next best action")
        self.assertContains(response, self.expected.next_best_action)

    def test_action_items_appear(self):
        response = self._get()
        self.assertContains(response, "Action items")
        for item in self.expected.action_items:
            self.assertContains(response, item.title)
            self.assertContains(response, item.category)
            self.assertContains(response, item.priority)
            self.assertContains(response, item.status)
            self.assertContains(response, item.reason)
            self.assertContains(response, item.suggested_next_step)
            self.assertContains(response, item.evidence_target)
            self.assertContains(response, item.linked_dashboard_section)

    def test_progress_indicators_appear(self):
        response = self._get()
        self.assertContains(response, "Progress indicators")
        for indicator in self.expected.progress_indicators:
            self.assertContains(response, indicator.label)
            self.assertContains(response, indicator.current_value)
            self.assertContains(response, indicator.target_value)
            self.assertContains(response, indicator.status)
            self.assertContains(response, indicator.supporting_text)

    def test_evidence_targets_appear(self):
        response = self._get()
        self.assertContains(response, "Evidence targets")
        for target in self.expected.evidence_targets:
            self.assertContains(response, target)

    def test_summary_points_appear(self):
        response = self._get()
        self.assertContains(response, "Summary points")
        for point in self.expected.summary_points:
            self.assertContains(response, point)

    def test_claim_safety_wording_appears(self):
        response = self._get()
        content = response.content.decode().lower()
        self.assertIn("rule-based career strategy action plan for manual review", content)
        self.assertIn("advisory only", content)
        self.assertIn("not predictive hiring ai", content)
        self.assertIn("does not use external ai apis", content)
        self.assertIn("does not automate applications", content)
        self.assertIn("does not replace human judgement", content)
        self.assertIn("advisory snapshots, not persisted tracking records", content)
        self.assertIn("manual review", content)

    def test_view_uses_service_output_safely(self):
        response = self._get()
        self.assertIn("action_plan", response.context)
        self.assertEqual(response.context["action_plan"], self.expected)

    def test_page_does_not_contain_forbidden_claim_phrases(self):
        response = self._get()
        content = response.content.decode().lower()
        for phrase in FORBIDDEN_PAGE_PHRASES:
            self.assertNotIn(phrase, content, msg=f"Page contains forbidden phrase: {phrase}")


class Sprint105EPhase1CareerStrategyActionPlanWorkflowCardPolishTests(TestCase):
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
        "Open Career Readiness Dashboard",
        "Open Learning Recommendations",
        "Open AI Readiness Report",
        "Open Job AI Capability Match",
    )

    def setUp(self):
        self.user = User.objects.create_user(
            username="cf105e-strategy-user",
            password="StrongPass12345",
        )
        self.url = reverse("skills:career_strategy_action_plan")
        self.expected = build_career_strategy_action_plan()

    def _get(self):
        self.client.login(username="cf105e-strategy-user", password="StrongPass12345")
        return self.client.get(self.url)

    def test_page_renders_successfully(self):
        response = self._get()
        self.assertEqual(response.status_code, 200)

    def test_page_local_root_and_workflow_markers_present(self):
        response = self._get()
        content = response.content.decode()
        self.assertIn("cf69i-route6-page", content)
        self.assertIn("cf69i-route6-hero", content)
        self.assertIn("cf69i-route6-actions", content)
        self.assertIn("cf-report-manual-actions", content)

    def test_step_indicator_and_advisory_wording_preserved(self):
        response = self._get()
        self.assertContains(response, "Step 6 of 7")
        self.assertContains(
            response,
            "Rule-based career strategy action plan for manual review.",
        )
        self.assertContains(
            response,
            "This is a rule-based career strategy action plan for manual review.",
        )
        self.assertContains(response, "It is not predictive hiring AI.")
        self.assertContains(response, "It does not use external AI APIs.")
        self.assertContains(response, "It does not automate applications.")
        self.assertContains(response, "It does not replace human judgement.")
        self.assertContains(
            response,
            "Progress indicators are advisory snapshots, not persisted tracking records.",
        )
        self.assertContains(
            response,
            "Verify every action item and progress indicator manually before acting.",
        )
        self.assertContains(response, "Advisory only. Verify before acting on any item.")

    def test_manual_action_link_labels_preserved(self):
        response = self._get()
        for label in self.MANUAL_ACTION_LABELS:
            with self.subTest(label=label):
                self.assertContains(response, label)

    def test_service_derived_kpi_content_preserved(self):
        response = self._get()
        self.assertContains(response, "Strategy Label")
        self.assertContains(response, self.expected.strategy_label)
        self.assertContains(response, "Overall Status")
        self.assertContains(response, self.expected.overall_status)
        self.assertContains(response, "Next best action")
        self.assertContains(response, self.expected.next_best_action)

    def test_unsafe_claim_phrases_absent(self):
        response = self._get()
        content = response.content.decode().lower()
        for phrase in self.UNSAFE_CLAIM_PHRASES:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, content)

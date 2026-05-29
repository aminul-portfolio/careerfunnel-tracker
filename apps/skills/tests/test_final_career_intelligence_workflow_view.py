from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.skills.services.final_career_intelligence_workflow import (
    build_final_career_intelligence_workflow,
)

FORBIDDEN_PAGE_PHRASES = (
    "auto-apply",
    "auto-send",
    "scraping",
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


class FinalCareerIntelligenceWorkflowViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")
        self.url = reverse("skills:final_career_intelligence_workflow")
        self.expected = build_final_career_intelligence_workflow()

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
        self.assertContains(response, "Final Career Intelligence Workflow")

    def test_workflow_label_appears(self):
        response = self._get()
        self.assertContains(response, "Workflow Label")
        self.assertContains(response, self.expected.workflow_label)

    def test_overall_status_appears(self):
        response = self._get()
        self.assertContains(response, "Overall Status")
        self.assertContains(response, self.expected.overall_status)

    def test_readiness_score_appears(self):
        response = self._get()
        self.assertContains(response, "AI Readiness Score")
        self.assertContains(response, str(self.expected.readiness_score))

    def test_job_match_score_appears(self):
        response = self._get()
        self.assertContains(response, "Job AI Match Score")
        self.assertContains(response, str(self.expected.job_match_score))

    def test_strategy_status_appears(self):
        response = self._get()
        self.assertContains(response, "Strategy Status")
        self.assertContains(response, self.expected.strategy_status)

    def test_next_best_action_appears(self):
        response = self._get()
        self.assertContains(response, "Next best action")
        self.assertContains(response, self.expected.next_best_action)

    def test_workflow_stages_appear(self):
        response = self._get()
        self.assertContains(response, "Workflow stages")
        for stage in self.expected.workflow_stages:
            self.assertContains(response, str(stage.stage_number))
            self.assertContains(response, stage.title)
            self.assertContains(response, stage.source)
            self.assertContains(response, stage.status)
            self.assertContains(response, stage.summary)
            self.assertContains(response, stage.output_reference)

    def test_action_sequence_appears(self):
        response = self._get()
        self.assertContains(response, "Action sequence")
        for item in self.expected.action_sequence:
            self.assertContains(response, str(item.step_number))
            self.assertContains(response, item.title)
            self.assertContains(response, item.priority)
            self.assertContains(response, item.status)
            self.assertContains(response, item.reason)
            self.assertContains(response, item.manual_next_step)
            self.assertContains(response, item.source_stage)
            self.assertContains(response, item.evidence_target)

    def test_integration_summary_appears(self):
        response = self._get()
        self.assertContains(response, "Integration summary")
        for point in self.expected.integration_summary:
            self.assertContains(response, point)

    def test_evidence_targets_appear(self):
        response = self._get()
        self.assertContains(response, "Evidence targets")
        for target in self.expected.evidence_targets:
            self.assertContains(response, target)

    def test_claim_safety_wording_appears(self):
        response = self._get()
        content = response.content.decode().lower()
        self.assertIn(
            "rule-based final career intelligence workflow for manual review",
            content,
        )
        self.assertIn("not predictive hiring ai", content)
        self.assertIn("does not use external ai apis", content)
        self.assertIn("does not automate applications", content)
        self.assertIn("does not replace human judgement", content)
        self.assertIn("all workflow outputs require manual verification", content)
        self.assertIn("before portfolio, application, or interview use", content)
        self.assertIn("manual review", content)

    def test_view_uses_service_output_safely(self):
        response = self._get()
        self.assertIn("workflow", response.context)
        self.assertEqual(response.context["workflow"], self.expected)

    def test_page_does_not_contain_forbidden_claim_phrases(self):
        response = self._get()
        content = response.content.decode().lower()
        for phrase in FORBIDDEN_PAGE_PHRASES:
            self.assertNotIn(phrase, content, msg=f"Page contains forbidden phrase: {phrase}")

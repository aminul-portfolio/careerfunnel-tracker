import inspect

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.skills import views as skill_views

MANDATORY_NON_PERSONALISED_WORDING = (
    "These are general workflow principles, not personalised recommendations based on "
    "your current data. They apply to the manual application and evidence-review "
    "process generally."
)

STATIC_GUIDANCE_PRINCIPLES = (
    "Review evidence before claiming a learning-target skill",
    "Prioritise evidence-backed skills when tailoring a manual application",
    "Check whether a manual follow-up is appropriate before drafting",
    "Do not claim tools that are only learning targets",
    "Improve evidence for repeated JD signals",
    "Review weak-fit applications before investing tailoring time",
    "Add portfolio evidence for high-value skills",
    "Continue the manual save and manual submit workflow",
)

FORBIDDEN_POSITIVE_AUTOMATION_CLAIMS = (
    "I analysed your current applications",
    "I analysed your Skill Ledger",
    "This is a personalised recommendation",
    "based on your saved records",
    "This recommendation is based on your current data",
    "AI decided",
    "automatically applied",
    "application submitted",
    "application saved",
    "email sent",
    "CV updated",
    "public profile updated",
    "Skill Ledger evidence updated",
    "skill verified",
    "employer outcome predicted",
    "guaranteed fit",
    "auto-send",
    "auto-save",
    "live AI recommendation",
    "production AI provider",
)


class CareerWorkflowDecisionAssistantStaticTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="workflowassistantuser",
            password="StrongPass12345",
        )
        self.url = reverse("skills:career_workflow_decision_assistant")
        self.hub_url = reverse("skills:final_career_intelligence_workflow")
        self.readiness_url = reverse("skills:career_readiness_dashboard")
        self.strategy_url = reverse("skills:career_strategy_action_plan")

    def _login(self):
        self.client.login(username="workflowassistantuser", password="StrongPass12345")

    def _get_assistant(self):
        self._login()
        return self.client.get(self.url)

    def test_career_workflow_decision_assistant_loads_for_authenticated_user(self):
        response = self._get_assistant()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.url, "/skills/career-workflow-decision-assistant/")
        self.assertContains(response, "Career Workflow Decision Assistant")
        self.assertTemplateUsed(
            response,
            "skills/career_workflow_decision_assistant.html",
        )

    def test_career_workflow_decision_assistant_redirects_anonymous_user(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response["Location"])

    def test_career_workflow_decision_assistant_post_returns_405(self):
        self._login()

        response = self.client.post(self.url, {"action": "review"})

        self.assertEqual(response.status_code, 405)

    def test_career_workflow_decision_assistant_renders_mandatory_non_personalised_wording(self):
        response = self._get_assistant()

        self.assertContains(response, MANDATORY_NON_PERSONALISED_WORDING)

    def test_career_workflow_decision_assistant_advisory_wording_present(self):
        response = self._get_assistant()

        self.assertContains(response, "Workflow recommendations are advisory only.")

    def test_career_workflow_decision_assistant_no_application_submit_wording_present(self):
        response = self._get_assistant()

        self.assertContains(response, "This assistant does not submit applications.")

    def test_career_workflow_decision_assistant_no_application_save_wording_present(self):
        response = self._get_assistant()

        self.assertContains(response, "This assistant does not save application records.")

    def test_career_workflow_decision_assistant_no_email_send_wording_present(self):
        response = self._get_assistant()

        self.assertContains(response, "This assistant does not send emails.")

    def test_career_workflow_decision_assistant_no_mutation_wording_present(self):
        response = self._get_assistant()

        self.assertContains(
            response,
            (
                "This assistant does not update CVs, public profiles, or Skill Ledger "
                "evidence."
            ),
        )
        self.assertContains(response, "Review all recommendations manually before acting.")

    def test_career_workflow_decision_assistant_no_live_ai_wording_present(self):
        response = self._get_assistant()

        self.assertContains(response, "No live AI model is used in this version.")

    def test_career_workflow_decision_assistant_no_current_record_read_wording_present(self):
        response = self._get_assistant()

        self.assertContains(
            response,
            (
                "No current application or Skill Ledger records are read for this static "
                "version."
            ),
        )

    def test_career_workflow_decision_assistant_renders_all_eight_static_guidance_principles(self):
        response = self._get_assistant()

        self.assertContains(response, 'data-testid="workflow-principle"', count=8)
        for principle in STATIC_GUIDANCE_PRINCIPLES:
            with self.subTest(principle=principle):
                self.assertContains(response, principle)

    def test_career_workflow_decision_assistant_forbidden_positive_automation_claims_absent(self):
        response = self._get_assistant()
        content = response.content.decode()

        for phrase in FORBIDDEN_POSITIVE_AUTOMATION_CLAIMS:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, content)

    def test_final_career_intelligence_workflow_links_to_assistant_once(self):
        self._login()

        response = self.client.get(self.hub_url)
        content = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Open Career Workflow Decision Assistant")
        self.assertContains(
            response,
            'href="/skills/career-workflow-decision-assistant/"',
        )
        self.assertEqual(
            content.count('href="/skills/career-workflow-decision-assistant/"'),
            1,
        )

    def test_final_career_intelligence_workflow_still_loads(self):
        self._login()

        response = self.client.get(self.hub_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Final Career Intelligence Workflow")

    def test_career_readiness_dashboard_route_unaffected(self):
        self._login()

        response = self.client.get(self.readiness_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Career Readiness Dashboard")

    def test_career_strategy_action_plan_route_unaffected(self):
        self._login()

        response = self.client.get(self.strategy_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Career Strategy Action Plan")

    def test_career_workflow_decision_assistant_view_has_no_cross_app_queries(self):
        view_source = inspect.getsource(skill_views.career_workflow_decision_assistant)

        self.assertNotIn("apps.applications", view_source)
        self.assertNotIn("apps.skill_ledger", view_source)
        self.assertNotIn("apps.skill_gaps", view_source)
        self.assertNotIn(".objects", view_source)

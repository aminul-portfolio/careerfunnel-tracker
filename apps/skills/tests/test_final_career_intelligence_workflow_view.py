import inspect

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.skill_ledger.models import SkillEntry
from apps.skills import views as skill_views
from apps.skills.services.final_career_intelligence_workflow import (
    build_final_career_intelligence_workflow,
)

FORBIDDEN_PAGE_PHRASES = (
    "auto-apply",
    "auto-send",
    "ai automation",
    "automated career decision",
    "career plan is complete",
    "completed career plan",
    "completion guarantee",
    "employer verified",
    "employer verification",
    "guaranteed readiness",
    "live job market",
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

    def _create_skill_entry(self, **overrides):
        defaults = {
            "skill_name": "Python",
            "category": SkillEntry.Category.PROGRAMMING,
            "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
            "sprint_reference": "Sprint 75",
            "project_link": "https://example.com/project",
            "notes": "Private evidence note.",
            "visibility": SkillEntry.Visibility.PRIVATE,
        }
        defaults.update(overrides)
        return SkillEntry.objects.create(**defaults)

    def test_page_requires_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_page_loads_for_logged_in_user(self):
        response = self._get()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Final Career Intelligence Workflow")

    def test_final_career_intelligence_workflow_page_loads_without_error(self):
        response = self._get()
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "skills/final_career_intelligence_workflow.html",
        )

    def test_final_career_intelligence_workflow_advisory_only_label_present(self):
        response = self._get()
        self.assertContains(
            response,
            "Rule-based final career intelligence workflow for manual review.",
        )
        self.assertContains(response, "Advisory only. Verify each stage output manually.")

    def test_final_career_intelligence_workflow_step_indicator_present(self):
        response = self._get()
        self.assertContains(response, "Step 7 of 7")

    def test_final_career_intelligence_workflow_get_does_not_create_or_modify_records(
        self,
    ):
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
        self.assertEqual(response.context["workflow"], self.expected)

    def test_final_career_intelligence_workflow_does_not_imply_completion_guarantee(
        self,
    ):
        response = self._get()
        content = response.content.decode().lower()
        self.assertNotIn("career plan is complete", content)
        self.assertNotIn("completed career plan", content)
        self.assertNotIn("completion guarantee", content)
        self.assertNotIn("you are ready", content)
        self.assertNotIn("guaranteed readiness", content)

    def test_final_career_intelligence_workflow_advisory_framing_present(self):
        response = self._get()
        content = response.content.decode().lower()
        self.assertIn("rule-based final career intelligence workflow", content)
        self.assertIn("advisory only", content)
        self.assertIn("manual verification", content)
        self.assertIn("manual review", content)

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

    def test_final_workflow_context_includes_skill_ledger_summary(self):
        self._create_skill_entry()

        response = self._get()

        self.assertIn("skill_ledger_summary", response.context)
        self.assertEqual(response.context["skill_ledger_summary"]["total_entries"], 1)

    def test_final_workflow_renders_skill_ledger_evidence_summary_section(self):
        response = self._get()

        self.assertContains(response, "Skill Ledger evidence summary")
        self.assertContains(response, "Private Skill Ledger evidence snapshot")

    def test_final_workflow_renders_skill_ledger_verified_count(self):
        self._create_skill_entry(evidence_level=SkillEntry.EvidenceLevel.VERIFIED)

        response = self._get()

        self.assertContains(response, "VERIFIED")
        self.assertContains(response, "Python")
        self.assertContains(response, "Sprint: Sprint 75")

    def test_final_workflow_renders_skill_ledger_learning_target_count(self):
        self._create_skill_entry(
            skill_name="Snowflake",
            evidence_level=SkillEntry.EvidenceLevel.LEARNING_TARGET,
        )

        response = self._get()

        self.assertContains(response, "LEARNING_TARGET")
        self.assertContains(response, "No VERIFIED Skill Ledger entries recorded yet.")
        self.assertEqual(
            response.context["skill_ledger_summary"]["counts"][
                SkillEntry.EvidenceLevel.LEARNING_TARGET
            ],
            1,
        )

    def test_final_workflow_renders_private_skill_ledger_link(self):
        response = self._get()

        self.assertContains(response, reverse("skill_ledger:list"))
        self.assertContains(response, "Open private Skill Ledger")

    def test_final_workflow_skill_ledger_advisory_wording_present(self):
        response = self._get()

        self.assertContains(
            response,
            (
                "Skill Ledger evidence is manually maintained and supports portfolio planning. "
                "It does not verify a skill by itself."
            ),
        )

    def test_final_workflow_verified_boundary_wording_present(self):
        response = self._get()

        self.assertContains(
            response,
            (
                "VERIFIED means portfolio evidence exists in a closed sprint, passing tests, "
                "or prior work experience - not external certification."
            ),
        )

    def test_final_workflow_read_only_note_present(self):
        response = self._get()

        self.assertContains(
            response,
            "This summary is read-only. To update your Skill Ledger, use the private Skill Ledger.",
        )

    def test_final_workflow_does_not_imply_automatic_verification(self):
        response = self._get()
        content = response.content.decode().lower()

        for phrase in (
            "automatic " + "verification",
            "auto-sync",
            "auto update",
            "auto apply",
        ):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, content)

    def test_final_workflow_does_not_imply_employer_confirmation(self):
        response = self._get()
        content = response.content.decode().lower()

        for phrase in (
            "employer " + "verified",
            "employer " + "confirmation",
            "cert" + "ified",
        ):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, content)

    def test_final_workflow_does_not_import_or_display_jd_gap_data(self):
        response = self._get()
        content = response.content.decode().lower()
        workflow_content = content.split("cf-final-career-intelligence-workflow", 1)[1]
        view_source = inspect.getsource(skill_views)

        self.assertNotIn("apps.applications", view_source)
        self.assertNotIn("jd gap", workflow_content)
        self.assertNotIn("job description gap", workflow_content)

    def test_final_workflow_get_does_not_mutate_skill_ledger_entries(self):
        entry = self._create_skill_entry(
            skill_name="Power BI",
            evidence_level=SkillEntry.EvidenceLevel.STUDYING,
        )
        before = SkillEntry.objects.values(
            "skill_name",
            "category",
            "evidence_level",
            "sprint_reference",
            "project_link",
            "notes",
            "visibility",
        ).get(pk=entry.pk)

        response = self._get()

        after = SkillEntry.objects.values(
            "skill_name",
            "category",
            "evidence_level",
            "sprint_reference",
            "project_link",
            "notes",
            "visibility",
        ).get(pk=entry.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(after, before)


class Sprint105EPhase1BFinalCareerIntelligenceWorkflowCardPolishTests(TestCase):
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
        "Open Career Strategy Action Plan",
        "Open Career Readiness Dashboard",
        "Open Learning Recommendations",
        "Open AI Readiness Report",
        "Open Job AI Capability Match",
        "Open AI Capability Framework",
        "Open Career Workflow Decision Assistant",
    )

    def setUp(self):
        self.user = User.objects.create_user(
            username="cf105e-final-workflow-user",
            password="StrongPass12345",
        )
        self.url = reverse("skills:final_career_intelligence_workflow")

    def _get(self):
        self.client.login(username="cf105e-final-workflow-user", password="StrongPass12345")
        return self.client.get(self.url)

    def test_page_renders_successfully(self):
        response = self._get()
        self.assertEqual(response.status_code, 200)

    def test_step_indicator_and_page_local_markers_present(self):
        response = self._get()
        content = response.content.decode()
        self.assertContains(response, "Step 7 of 7")
        self.assertIn("cf69i-route7-page", content)
        self.assertIn("cf69i-route7-hero", content)
        self.assertIn("cf69i-route7-actions", content)
        self.assertIn("cf-report-manual-actions", content)

    def test_manual_action_link_labels_preserved(self):
        response = self._get()
        for label in self.MANUAL_ACTION_LABELS:
            with self.subTest(label=label):
                self.assertContains(response, label)

    def test_advisory_wording_preserved(self):
        response = self._get()
        self.assertContains(
            response,
            "Rule-based final career intelligence workflow for manual review.",
        )
        self.assertContains(response, "It is not predictive hiring AI.")
        self.assertContains(response, "It does not use external AI APIs.")
        self.assertContains(response, "It does not automate applications.")
        self.assertContains(response, "It does not replace human judgement.")
        self.assertContains(response, "Advisory only. Verify each stage output manually.")

    def test_unsafe_claim_phrases_absent(self):
        response = self._get()
        content = response.content.decode().lower()
        for phrase in self.UNSAFE_CLAIM_PHRASES:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, content)

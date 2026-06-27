from django.test import SimpleTestCase, TestCase

from apps.skill_ledger.models import SkillEntry
from apps.skill_ledger.selectors import get_skill_ledger_evidence_summary
from apps.skills.services.ai_readiness_scoring import (
    build_empty_ai_readiness_score,
    build_portfolio_baseline_ai_readiness_score,
)
from apps.skills.services.career_readiness_dashboard import (
    build_career_readiness_dashboard,
)
from apps.skills.services.career_strategy_action_plan import (
    build_career_strategy_action_plan,
)
from apps.skills.services.final_career_intelligence_workflow import (
    APPROVED_ACTION_SEQUENCE_PRIORITIES,
    APPROVED_ACTION_SEQUENCE_STATUSES,
    APPROVED_OVERALL_WORKFLOW_STATUSES,
    APPROVED_WORKFLOW_STAGE_STATUSES,
    EXPECTED_WORKFLOW_STAGE_TITLES,
    WORKFLOW_CLAIM_SAFETY_NOTES,
    build_final_career_intelligence_workflow,
)
from apps.skills.services.job_ai_capability_matching import (
    match_job_description_to_ai_capabilities,
)
from apps.skills.services.learning_recommendations import (
    DEFAULT_SAMPLE_JOB_DESCRIPTION,
    build_learning_recommendations,
)

FORBIDDEN_WORKFLOW_PHRASES = (
    "auto-apply",
    "auto-send",
    "scraping",
    "billing",
    "gmail",
    "calendar integration",
    "live saas users",
    "customers",
    "production deployment",
    "openai",
    "anthropic",
    "claude",
)

REQUIRED_RESULT_FIELDS = (
    "workflow_label",
    "overall_status",
    "readiness_score",
    "job_match_score",
    "strategy_status",
    "next_best_action",
    "workflow_stages",
    "action_sequence",
    "integration_summary",
    "evidence_targets",
    "claim_safety_notes",
)


class FinalCareerIntelligenceWorkflowTests(SimpleTestCase):
    def setUp(self):
        self.workflow = build_final_career_intelligence_workflow()

    def _combined_text(self, result) -> str:
        parts = [
            result.workflow_label,
            result.overall_status,
            result.strategy_status,
            result.next_best_action,
            *result.integration_summary,
            *result.claim_safety_notes,
            *result.evidence_targets,
            *(stage.title for stage in result.workflow_stages),
            *(stage.summary for stage in result.workflow_stages),
            *(item.title for item in result.action_sequence),
            *(item.reason for item in result.action_sequence),
            *(item.manual_next_step for item in result.action_sequence),
        ]
        return " ".join(parts).lower()

    def test_final_workflow_result_has_required_structure(self):
        for field_name in REQUIRED_RESULT_FIELDS:
            self.assertTrue(hasattr(self.workflow, field_name), msg=field_name)
            self.assertIsNotNone(getattr(self.workflow, field_name))
        self.assertEqual(len(self.workflow.workflow_stages), 7)
        self.assertGreater(len(self.workflow.action_sequence), 0)

    def test_all_expected_workflow_stages_exist(self):
        stage_titles = [stage.title for stage in self.workflow.workflow_stages]
        self.assertEqual(stage_titles, list(EXPECTED_WORKFLOW_STAGE_TITLES))
        for stage in self.workflow.workflow_stages:
            self.assertTrue(stage.source.strip())
            self.assertTrue(stage.summary.strip())
            self.assertTrue(stage.output_reference.strip())
            self.assertIn(stage.status, APPROVED_WORKFLOW_STAGE_STATUSES)

    def test_action_sequence_is_generated(self):
        action_plan = build_career_strategy_action_plan()
        self.assertEqual(
            len(self.workflow.action_sequence),
            len(action_plan.action_items),
        )
        for item in self.workflow.action_sequence:
            self.assertTrue(item.title.strip())
            self.assertTrue(item.manual_next_step.strip())
            self.assertTrue(item.source_stage.strip())
            self.assertTrue(item.evidence_target.strip())

    def test_next_best_action_is_included(self):
        action_plan = build_career_strategy_action_plan()
        self.assertEqual(self.workflow.next_best_action, action_plan.next_best_action)
        combined = self._combined_text(self.workflow)
        self.assertIn(action_plan.next_best_action.lower(), combined)

    def test_readiness_score_and_job_match_score_are_included(self):
        readiness = build_portfolio_baseline_ai_readiness_score()
        job_match = match_job_description_to_ai_capabilities(DEFAULT_SAMPLE_JOB_DESCRIPTION)
        self.assertEqual(self.workflow.readiness_score, readiness.readiness_score)
        self.assertEqual(self.workflow.job_match_score, job_match.match_score)

    def test_evidence_targets_are_collected(self):
        self.assertGreater(len(self.workflow.evidence_targets), 0)
        sequence_targets = {item.evidence_target for item in self.workflow.action_sequence}
        for target in self.workflow.evidence_targets:
            self.assertIn(target, sequence_targets)

    def test_manual_review_gate_always_exists(self):
        manual_stages = [
            stage
            for stage in self.workflow.workflow_stages
            if stage.title == "Manual Review Gate"
        ]
        self.assertEqual(len(manual_stages), 1)
        self.assertEqual(manual_stages[0].status, "Manual check")
        manual_steps = [
            item
            for item in self.workflow.action_sequence
            if item.source_stage == "Manual Review Gate"
            or item.status == "Manual check"
        ]
        self.assertGreaterEqual(len(manual_steps), 1)

    def test_priority_and_status_labels_are_approved(self):
        self.assertIn(self.workflow.overall_status, APPROVED_OVERALL_WORKFLOW_STATUSES)
        for stage in self.workflow.workflow_stages:
            self.assertIn(stage.status, APPROVED_WORKFLOW_STAGE_STATUSES)
        for item in self.workflow.action_sequence:
            self.assertIn(item.priority, APPROVED_ACTION_SEQUENCE_PRIORITIES)
            self.assertIn(item.status, APPROVED_ACTION_SEQUENCE_STATUSES)

    def test_high_priority_action_plan_includes_high_priority_sequence_item(self):
        readiness = build_empty_ai_readiness_score()
        job_match = match_job_description_to_ai_capabilities(DEFAULT_SAMPLE_JOB_DESCRIPTION)
        dashboard = build_career_readiness_dashboard(
            readiness,
            job_match,
            build_learning_recommendations(readiness, job_match),
        )
        action_plan = build_career_strategy_action_plan(dashboard)
        workflow = build_final_career_intelligence_workflow(
            readiness=readiness,
            job_match=job_match,
            recommendations=build_learning_recommendations(readiness, job_match),
            dashboard=dashboard,
            action_plan=action_plan,
        )
        high_priority_items = [
            item for item in workflow.action_sequence if item.priority == "High"
        ]
        self.assertGreater(len(high_priority_items), 0)
        self.assertEqual(workflow.overall_status, "Needs evidence strengthening")

    def test_integrated_status_when_readiness_and_job_match_strong(self):
        readiness = build_portfolio_baseline_ai_readiness_score()
        job_match = match_job_description_to_ai_capabilities(DEFAULT_SAMPLE_JOB_DESCRIPTION)
        dashboard = build_career_readiness_dashboard(readiness, job_match)
        action_plan = build_career_strategy_action_plan(dashboard)
        workflow = build_final_career_intelligence_workflow(
            readiness=readiness,
            job_match=job_match,
            dashboard=dashboard,
            action_plan=action_plan,
        )
        if (
            readiness.readiness_score >= 70
            and job_match.match_score >= 50
            and action_plan.overall_status == "Ready for targeted applications"
        ):
            self.assertEqual(
                workflow.overall_status,
                "Integrated workflow ready for manual use",
            )

    def test_output_is_deterministic(self):
        first = build_final_career_intelligence_workflow()
        second = build_final_career_intelligence_workflow()
        self.assertEqual(first, second)

    def test_claim_safety_notes_are_present(self):
        self.assertEqual(self.workflow.claim_safety_notes, WORKFLOW_CLAIM_SAFETY_NOTES)
        combined = self._combined_text(self.workflow)
        self.assertIn("manual", combined)
        self.assertIn("external ai provider", combined)

    def test_forbidden_claim_phrases_not_in_output(self):
        combined = self._combined_text(self.workflow)
        for phrase in FORBIDDEN_WORKFLOW_PHRASES:
            self.assertNotIn(phrase, combined, msg=f"Output contains forbidden phrase: {phrase}")

    def test_no_external_api_behaviour_is_pure_local_aggregation(self):
        combined = self._combined_text(self.workflow)
        self.assertNotIn("api call", combined)
        self.assertNotIn("api key", combined)


class SkillLedgerEvidenceSummarySelectorTests(TestCase):
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

    def test_skill_ledger_evidence_summary_handles_empty_ledger(self):
        summary = get_skill_ledger_evidence_summary()

        self.assertEqual(summary["total_entries"], 0)
        self.assertEqual(summary["verified_entries"], [])
        self.assertEqual(
            summary["counts"],
            {
                SkillEntry.EvidenceLevel.VERIFIED: 0,
                SkillEntry.EvidenceLevel.LEARNING_TARGET: 0,
                SkillEntry.EvidenceLevel.STUDYING: 0,
                SkillEntry.EvidenceLevel.NO_EVIDENCE: 0,
            },
        )

    def test_skill_ledger_evidence_summary_returns_verified_count(self):
        self._create_skill_entry(evidence_level=SkillEntry.EvidenceLevel.VERIFIED)

        summary = get_skill_ledger_evidence_summary()

        self.assertEqual(summary["counts"][SkillEntry.EvidenceLevel.VERIFIED], 1)

    def test_skill_ledger_evidence_summary_returns_learning_target_count(self):
        self._create_skill_entry(evidence_level=SkillEntry.EvidenceLevel.LEARNING_TARGET)

        summary = get_skill_ledger_evidence_summary()

        self.assertEqual(summary["counts"][SkillEntry.EvidenceLevel.LEARNING_TARGET], 1)

    def test_skill_ledger_evidence_summary_returns_studying_count(self):
        self._create_skill_entry(evidence_level=SkillEntry.EvidenceLevel.STUDYING)

        summary = get_skill_ledger_evidence_summary()

        self.assertEqual(summary["counts"][SkillEntry.EvidenceLevel.STUDYING], 1)

    def test_skill_ledger_evidence_summary_returns_no_evidence_count(self):
        self._create_skill_entry(evidence_level=SkillEntry.EvidenceLevel.NO_EVIDENCE)

        summary = get_skill_ledger_evidence_summary()

        self.assertEqual(summary["counts"][SkillEntry.EvidenceLevel.NO_EVIDENCE], 1)

    def test_skill_ledger_evidence_summary_returns_verified_entries_only(self):
        verified = self._create_skill_entry(
            skill_name="Python",
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
        )
        self._create_skill_entry(
            skill_name="Snowflake",
            evidence_level=SkillEntry.EvidenceLevel.LEARNING_TARGET,
        )

        summary = get_skill_ledger_evidence_summary()

        self.assertEqual(summary["verified_entries"], [verified])

    def test_skill_ledger_evidence_summary_verified_entries_capped_at_five(self):
        for index in range(6):
            self._create_skill_entry(
                skill_name=f"Verified skill {index}",
                evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
            )

        summary = get_skill_ledger_evidence_summary()

        self.assertEqual(len(summary["verified_entries"]), 5)
        self.assertEqual(summary["counts"][SkillEntry.EvidenceLevel.VERIFIED], 6)

    def test_skill_ledger_evidence_summary_does_not_mutate_entries(self):
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

        get_skill_ledger_evidence_summary()

        after = SkillEntry.objects.values(
            "skill_name",
            "category",
            "evidence_level",
            "sprint_reference",
            "project_link",
            "notes",
            "visibility",
        ).get(pk=entry.pk)
        self.assertEqual(after, before)

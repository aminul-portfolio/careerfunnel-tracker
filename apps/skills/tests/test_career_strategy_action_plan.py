from django.test import SimpleTestCase

from apps.skills.services.ai_readiness_scoring import (
    build_empty_ai_readiness_score,
    build_portfolio_baseline_ai_readiness_score,
)
from apps.skills.services.career_readiness_dashboard import (
    build_career_readiness_dashboard,
)
from apps.skills.services.career_strategy_action_plan import (
    ACTION_PLAN_CLAIM_SAFETY_NOTES,
    APPROVED_ACTION_CATEGORIES,
    APPROVED_ACTION_PRIORITIES,
    APPROVED_ACTION_STATUSES,
    APPROVED_OVERALL_STATUSES,
    build_career_strategy_action_plan,
)
from apps.skills.services.job_ai_capability_matching import (
    match_job_description_to_ai_capabilities,
)
from apps.skills.services.learning_recommendations import (
    DEFAULT_SAMPLE_JOB_DESCRIPTION,
    build_learning_recommendations,
)

FORBIDDEN_ACTION_PLAN_PHRASES = (
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
    "strategy_label",
    "overall_status",
    "next_best_action",
    "action_items",
    "progress_indicators",
    "evidence_targets",
    "summary_points",
    "claim_safety_notes",
)

HIGH_JOB_MATCH_DESCRIPTION = (
    "generative AI prompt engineering workflow automation responsible AI governance "
    "stakeholder reporting AI-assisted presentation decks building operating AI agents "
    "RAG retrieval augmented generation data analysis"
)


class CareerStrategyActionPlanTests(SimpleTestCase):
    def setUp(self):
        self.plan = build_career_strategy_action_plan()

    def _combined_text(self, result) -> str:
        parts = [
            result.strategy_label,
            result.overall_status,
            result.next_best_action,
            *result.summary_points,
            *result.claim_safety_notes,
            *result.evidence_targets,
            *(item.title for item in result.action_items),
            *(item.reason for item in result.action_items),
            *(item.suggested_next_step for item in result.action_items),
            *(indicator.label for indicator in result.progress_indicators),
            *(indicator.supporting_text for indicator in result.progress_indicators),
        ]
        return " ".join(parts).lower()

    def test_action_plan_result_has_required_structure(self):
        for field_name in REQUIRED_RESULT_FIELDS:
            self.assertTrue(hasattr(self.plan, field_name), msg=field_name)
            self.assertIsNotNone(getattr(self.plan, field_name))
        self.assertGreater(len(self.plan.action_items), 0)
        self.assertEqual(len(self.plan.progress_indicators), 4)

    def test_action_items_are_generated(self):
        self.assertGreater(len(self.plan.action_items), 0)
        for item in self.plan.action_items:
            self.assertTrue(item.title.strip())
            self.assertTrue(item.suggested_next_step.strip())
            self.assertTrue(item.linked_dashboard_section.strip())

    def test_high_priority_dashboard_creates_high_priority_action(self):
        readiness = build_empty_ai_readiness_score()
        job_match = match_job_description_to_ai_capabilities(DEFAULT_SAMPLE_JOB_DESCRIPTION)
        dashboard = build_career_readiness_dashboard(
            readiness,
            job_match,
            build_learning_recommendations(readiness, job_match),
        )
        plan = build_career_strategy_action_plan(dashboard)
        self.assertEqual(dashboard.overall_priority, "High")
        high_priority_items = [
            item for item in plan.action_items if item.priority == "High"
        ]
        self.assertGreater(len(high_priority_items), 0)
        self.assertEqual(plan.next_best_action, dashboard.next_best_action)
        self.assertTrue(
            any(
                dashboard.next_best_action in item.suggested_next_step
                for item in high_priority_items
            )
        )

    def test_manual_review_action_always_exists(self):
        manual_items = [
            item
            for item in self.plan.action_items
            if item.category == "Manual review"
        ]
        self.assertGreaterEqual(len(manual_items), 1)
        self.assertTrue(
            any("confirm action plan manually" in item.title.lower() for item in manual_items)
        )

    def test_progress_indicators_are_generated(self):
        labels = {indicator.label for indicator in self.plan.progress_indicators}
        self.assertIn("AI Readiness Score", labels)
        self.assertIn("Job AI Match Score", labels)
        self.assertIn("High-Priority Recommendations", labels)
        self.assertIn("Capability Evidence Coverage", labels)
        for indicator in self.plan.progress_indicators:
            self.assertTrue(indicator.current_value)
            self.assertTrue(indicator.target_value)
            self.assertTrue(indicator.supporting_text)

    def test_evidence_targets_are_generated(self):
        self.assertGreater(len(self.plan.evidence_targets), 0)
        action_targets = {item.evidence_target for item in self.plan.action_items}
        for target in self.plan.evidence_targets:
            self.assertIn(target, action_targets)

    def test_next_best_action_is_included(self):
        dashboard = build_career_readiness_dashboard()
        self.assertEqual(self.plan.next_best_action, dashboard.next_best_action)
        combined = self._combined_text(self.plan)
        self.assertIn(dashboard.next_best_action.lower(), combined)

    def test_priority_and_status_labels_are_approved(self):
        for item in self.plan.action_items:
            self.assertIn(item.category, APPROVED_ACTION_CATEGORIES)
            self.assertIn(item.priority, APPROVED_ACTION_PRIORITIES)
            self.assertIn(item.status, APPROVED_ACTION_STATUSES)
        self.assertIn(self.plan.overall_status, APPROVED_OVERALL_STATUSES)

    def test_capability_gap_review_action_when_job_match_high_and_missing_gaps(self):
        readiness = build_portfolio_baseline_ai_readiness_score()
        job_match = match_job_description_to_ai_capabilities(HIGH_JOB_MATCH_DESCRIPTION)
        dashboard = build_career_readiness_dashboard(readiness, job_match)
        plan = build_career_strategy_action_plan(dashboard)
        self.assertGreaterEqual(dashboard.job_match_score, 50)
        self.assertGreater(dashboard.missing_capability_count, 0)
        gap_items = [
            item
            for item in plan.action_items
            if "capability gaps" in item.title.lower()
        ]
        self.assertEqual(len(gap_items), 1)
        self.assertEqual(gap_items[0].category, "Learning")

    def test_foundation_learning_action_when_readiness_below_50(self):
        readiness = build_empty_ai_readiness_score()
        job_match = match_job_description_to_ai_capabilities("")
        dashboard = build_career_readiness_dashboard(
            readiness,
            job_match,
            build_learning_recommendations(readiness, job_match),
        )
        plan = build_career_strategy_action_plan(dashboard)
        learning_items = [
            item
            for item in plan.action_items
            if item.category == "Learning" and item.priority == "High"
        ]
        self.assertGreater(len(learning_items), 0)
        self.assertEqual(plan.overall_status, "Needs focused improvement")

    def test_output_is_deterministic(self):
        first = build_career_strategy_action_plan()
        second = build_career_strategy_action_plan()
        self.assertEqual(first, second)

    def test_claim_safety_notes_are_present(self):
        self.assertEqual(self.plan.claim_safety_notes, ACTION_PLAN_CLAIM_SAFETY_NOTES)
        combined = self._combined_text(self.plan)
        self.assertIn("manual", combined)
        self.assertIn("external ai provider", combined)

    def test_forbidden_claim_phrases_not_in_output(self):
        combined = self._combined_text(self.plan)
        for phrase in FORBIDDEN_ACTION_PLAN_PHRASES:
            self.assertNotIn(phrase, combined, msg=f"Output contains forbidden phrase: {phrase}")

    def test_no_external_api_behaviour_is_pure_local_aggregation(self):
        combined = self._combined_text(self.plan)
        self.assertNotIn("api call", combined)
        self.assertNotIn("api key", combined)

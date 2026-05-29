from django.test import SimpleTestCase

from apps.skills.services.ai_readiness_scoring import (
    build_empty_ai_readiness_score,
    build_portfolio_baseline_ai_readiness_score,
)
from apps.skills.services.career_readiness_dashboard import (
    APPROVED_KPI_STATUSES,
    DASHBOARD_CLAIM_SAFETY_NOTES,
    build_career_readiness_dashboard,
)
from apps.skills.services.job_ai_capability_matching import (
    match_job_description_to_ai_capabilities,
)
from apps.skills.services.learning_recommendations import (
    DEFAULT_SAMPLE_JOB_DESCRIPTION,
    build_learning_recommendations,
)

FORBIDDEN_DASHBOARD_PHRASES = (
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
    "readiness_score",
    "readiness_label",
    "job_match_score",
    "job_match_label",
    "overall_priority",
    "next_best_action",
    "capability_count",
    "matched_capability_count",
    "missing_capability_count",
    "recommendation_count",
    "high_priority_recommendation_count",
    "kpi_cards",
    "summary_points",
    "dashboard_sections",
    "claim_safety_notes",
)


class CareerReadinessDashboardTests(SimpleTestCase):
    def setUp(self):
        self.dashboard = build_career_readiness_dashboard()

    def _combined_text(self, result) -> str:
        parts = [
            result.next_best_action,
            *result.summary_points,
            *result.claim_safety_notes,
            *(card.label for card in result.kpi_cards),
            *(card.supporting_text for card in result.kpi_cards),
            *(section.summary for section in result.dashboard_sections),
        ]
        return " ".join(parts).lower()

    def test_dashboard_result_has_required_structure(self):
        for field_name in REQUIRED_RESULT_FIELDS:
            self.assertTrue(hasattr(self.dashboard, field_name), msg=field_name)
            self.assertIsNotNone(getattr(self.dashboard, field_name))
        self.assertEqual(len(self.dashboard.kpi_cards), 4)
        self.assertEqual(len(self.dashboard.dashboard_sections), 4)

    def test_readiness_kpi_included(self):
        readiness = build_portfolio_baseline_ai_readiness_score()
        self.assertEqual(self.dashboard.readiness_score, readiness.readiness_score)
        self.assertEqual(self.dashboard.readiness_label, readiness.readiness_label)
        readiness_kpi = self.dashboard.kpi_cards[0]
        self.assertEqual(readiness_kpi.label, "AI Readiness Score")
        self.assertEqual(readiness_kpi.value, str(readiness.readiness_score))

    def test_job_match_kpi_included(self):
        job_match = match_job_description_to_ai_capabilities(DEFAULT_SAMPLE_JOB_DESCRIPTION)
        self.assertEqual(self.dashboard.job_match_score, job_match.match_score)
        self.assertEqual(self.dashboard.job_match_label, job_match.match_label)
        match_kpi = self.dashboard.kpi_cards[1]
        self.assertEqual(match_kpi.label, "Job AI Match Score")
        self.assertEqual(match_kpi.value, str(job_match.match_score))

    def test_recommendation_kpi_included(self):
        self.assertGreater(self.dashboard.recommendation_count, 0)
        priority_kpi = self.dashboard.kpi_cards[2]
        self.assertEqual(priority_kpi.label, "Overall Priority")
        self.assertEqual(priority_kpi.value, self.dashboard.overall_priority)

    def test_next_best_action_included(self):
        self.assertTrue(self.dashboard.next_best_action.strip())
        combined = self._combined_text(self.dashboard)
        self.assertIn(self.dashboard.next_best_action.lower(), combined)

    def test_summary_points_included(self):
        self.assertGreater(len(self.dashboard.summary_points), 0)
        combined = " ".join(self.dashboard.summary_points).lower()
        self.assertIn("career readiness dashboard", combined)

    def test_high_priority_recommendation_count(self):
        self.assertGreaterEqual(self.dashboard.high_priority_recommendation_count, 0)
        self.assertLessEqual(
            self.dashboard.high_priority_recommendation_count,
            self.dashboard.recommendation_count,
        )

    def test_kpi_status_labels_are_approved(self):
        for card in self.dashboard.kpi_cards:
            self.assertIn(card.status, APPROVED_KPI_STATUSES)

    def test_dashboard_section_titles(self):
        titles = {section.title for section in self.dashboard.dashboard_sections}
        self.assertEqual(
            titles,
            {
                "AI Readiness",
                "Job AI Capability Match",
                "Learning Recommendations",
                "Manual Review",
            },
        )

    def test_output_is_deterministic(self):
        first = build_career_readiness_dashboard()
        second = build_career_readiness_dashboard()
        self.assertEqual(first, second)

    def test_low_readiness_highlights_foundation_in_summary(self):
        readiness = build_empty_ai_readiness_score()
        job_match = match_job_description_to_ai_capabilities("")
        recommendations = build_learning_recommendations(readiness, job_match)
        result = build_career_readiness_dashboard(readiness, job_match, recommendations)
        combined = " ".join(result.summary_points).lower()
        self.assertIn("foundation improvement", combined)

    def test_claim_safety_notes_are_present(self):
        self.assertEqual(self.dashboard.claim_safety_notes, DASHBOARD_CLAIM_SAFETY_NOTES)
        combined = self._combined_text(self.dashboard)
        self.assertIn("manual", combined)
        self.assertIn("external ai provider", combined)

    def test_forbidden_claim_phrases_not_in_output(self):
        combined = self._combined_text(self.dashboard)
        for phrase in FORBIDDEN_DASHBOARD_PHRASES:
            self.assertNotIn(phrase, combined, msg=f"Output contains forbidden phrase: {phrase}")

    def test_no_external_api_behaviour_is_pure_local_aggregation(self):
        combined = self._combined_text(self.dashboard)
        self.assertNotIn("api call", combined)
        self.assertNotIn("api key", combined)

    def test_capability_counts_align_with_services(self):
        readiness = build_portfolio_baseline_ai_readiness_score()
        job_match = match_job_description_to_ai_capabilities(DEFAULT_SAMPLE_JOB_DESCRIPTION)
        result = build_career_readiness_dashboard(readiness, job_match)
        self.assertEqual(result.capability_count, readiness.capabilities_total)
        self.assertEqual(result.matched_capability_count, len(job_match.matched_capabilities))
        self.assertEqual(result.missing_capability_count, len(job_match.missing_capabilities))

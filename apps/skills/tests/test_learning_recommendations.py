from django.test import SimpleTestCase

from apps.skills.services.ai_readiness_scoring import (
    build_empty_ai_readiness_score,
    build_portfolio_baseline_ai_readiness_score,
    calculate_ai_readiness_score,
)
from apps.skills.services.job_ai_capability_matching import (
    match_job_description_to_ai_capabilities,
)
from apps.skills.services.learning_recommendations import (
    APPROVED_RECOMMENDATION_CATEGORIES,
    APPROVED_RECOMMENDATION_PRIORITIES,
    LEARNING_RECOMMENDATION_CLAIM_SAFETY_NOTES,
    build_learning_recommendations,
    build_portfolio_baseline_learning_recommendations,
)

FORBIDDEN_RECOMMENDATION_PHRASES = (
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

SAMPLE_JOB_WITH_AI_SIGNAL = (
    "Business analyst role using generative AI, prompt engineering, workflow automation, "
    "responsible AI governance, stakeholder reporting, and AI-assisted presentation decks."
)


class LearningRecommendationsTests(SimpleTestCase):
    def _combined_text(self, result) -> str:
        parts = [
            result.overall_priority,
            result.next_best_action,
            *result.claim_safety_notes,
            *(rec.title for rec in result.recommendations),
            *(rec.reason for rec in result.recommendations),
            *(rec.suggested_action for rec in result.recommendations),
        ]
        return " ".join(parts).lower()

    def test_low_readiness_scenario_includes_foundation_learning(self):
        readiness = build_empty_ai_readiness_score()
        job_match = match_job_description_to_ai_capabilities("")
        result = build_learning_recommendations(readiness, job_match)
        self.assertEqual(result.readiness_summary.readiness_score, 0)
        self.assertEqual(result.overall_priority, "High")
        categories = {rec.category for rec in result.recommendations}
        self.assertIn("Learning", categories)
        self.assertTrue(
            any("foundation" in rec.title.lower() for rec in result.recommendations)
        )

    def test_strong_readiness_with_high_job_match_includes_interview_prep(self):
        empty = build_empty_ai_readiness_score()
        evidence = {line.slug: "strong" for line in empty.capability_lines}
        readiness = calculate_ai_readiness_score(evidence)
        job_text = (
            SAMPLE_JOB_WITH_AI_SIGNAL
            + " AI agent orchestration, collaboration workshops, design mockups,"
            + " and video generation."
        )
        job_match = match_job_description_to_ai_capabilities(job_text)
        result = build_learning_recommendations(readiness, job_match)
        self.assertEqual(readiness.readiness_score, 100)
        self.assertGreaterEqual(job_match.match_score, 50)
        categories = {rec.category for rec in result.recommendations}
        self.assertIn("Interview preparation", categories)

    def test_missing_capability_recommendations_are_generated(self):
        readiness = build_portfolio_baseline_ai_readiness_score()
        job_match = match_job_description_to_ai_capabilities("ChatGPT prompt drafting only.")
        result = build_learning_recommendations(readiness, job_match)
        self.assertGreater(len(job_match.missing_capabilities), 0)
        missing_titles = {cap.title for cap in job_match.missing_capabilities}
        rec_titles = " ".join(rec.title for rec in result.recommendations)
        self.assertTrue(any(title in rec_titles for title in missing_titles))

    def test_matched_job_capability_with_weak_evidence_gets_gap_recommendation(self):
        from apps.skills.services.ai_readiness_scoring import (
            build_careerfunnel_portfolio_evidence_baseline,
        )

        baseline = dict(build_careerfunnel_portfolio_evidence_baseline())
        baseline["prompt-engineering-ai-tool-proficiency"] = "none"
        readiness = calculate_ai_readiness_score(baseline)
        job_match = match_job_description_to_ai_capabilities(
            "ChatGPT prompt engineering and generative AI drafting role."
        )
        result = build_learning_recommendations(readiness, job_match)
        gap_recs = [
            rec
            for rec in result.recommendations
            if rec.category in {"Project improvement", "CV evidence"}
            and rec.linked_capability_slug
        ]
        self.assertGreater(len(gap_recs), 0)

    def test_recommendation_priorities_use_approved_labels(self):
        result = build_portfolio_baseline_learning_recommendations()
        for recommendation in result.recommendations:
            self.assertIn(recommendation.priority, APPROVED_RECOMMENDATION_PRIORITIES)
            self.assertIn(recommendation.category, APPROVED_RECOMMENDATION_CATEGORIES)

    def test_output_is_deterministic(self):
        first = build_portfolio_baseline_learning_recommendations()
        second = build_portfolio_baseline_learning_recommendations()
        self.assertEqual(first, second)

    def test_next_best_action_is_non_empty(self):
        result = build_portfolio_baseline_learning_recommendations()
        self.assertTrue(result.next_best_action.strip())
        self.assertIn(
            result.next_best_action,
            {rec.suggested_action for rec in result.recommendations},
        )

    def test_claim_safety_notes_are_present(self):
        result = build_portfolio_baseline_learning_recommendations()
        self.assertEqual(result.claim_safety_notes, LEARNING_RECOMMENDATION_CLAIM_SAFETY_NOTES)
        combined = self._combined_text(result)
        self.assertIn("manual", combined)
        self.assertIn("external ai provider", combined)

    def test_forbidden_claim_phrases_not_in_output(self):
        result = build_portfolio_baseline_learning_recommendations()
        combined = self._combined_text(result)
        for phrase in FORBIDDEN_RECOMMENDATION_PHRASES:
            self.assertNotIn(phrase, combined, msg=f"Output contains forbidden phrase: {phrase}")

    def test_manual_review_recommendation_always_included(self):
        result = build_portfolio_baseline_learning_recommendations()
        manual = [rec for rec in result.recommendations if rec.category == "Manual review"]
        self.assertEqual(len(manual), 1)
        self.assertEqual(manual[0].priority, "Low")

    def test_summaries_reflect_input_services(self):
        readiness = build_portfolio_baseline_ai_readiness_score()
        job_match = match_job_description_to_ai_capabilities(SAMPLE_JOB_WITH_AI_SIGNAL)
        result = build_learning_recommendations(readiness, job_match)
        self.assertEqual(result.readiness_summary.readiness_score, readiness.readiness_score)
        self.assertEqual(result.readiness_summary.readiness_label, readiness.readiness_label)
        self.assertEqual(result.job_match_summary.match_score, job_match.match_score)
        self.assertEqual(result.job_match_summary.match_label, job_match.match_label)

    def test_no_external_api_behaviour_is_pure_local_logic(self):
        result = build_portfolio_baseline_learning_recommendations()
        combined = self._combined_text(result)
        self.assertNotIn("api call", combined)
        self.assertNotIn("api key", combined)

from django.test import SimpleTestCase

from apps.skills.services.ai_capability_framework import get_ai_capability_framework
from apps.skills.services.job_ai_capability_matching import (
    MATCHING_CLAIM_SAFETY_NOTES,
    assign_match_label,
    match_job_description_to_ai_capabilities,
)

FORBIDDEN_MATCHING_PHRASES = (
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


class JobAICapabilityMatchingTests(SimpleTestCase):
    def setUp(self):
        self.framework = get_ai_capability_framework()
        self.all_slugs = {capability.slug for capability in self.framework}

    def _combined_text(self, result) -> str:
        parts = [
            result.match_label,
            *result.explanation_points,
            *result.claim_safety_notes,
            *(cap.title for cap in result.matched_capabilities),
            *(cap.signal_note for cap in result.missing_capabilities),
        ]
        return " ".join(parts).lower()

    def test_empty_job_description_returns_limited_signal(self):
        result = match_job_description_to_ai_capabilities("")
        self.assertEqual(result.match_score, 0)
        self.assertEqual(result.match_label, "Limited AI signal")
        self.assertEqual(result.matched_capabilities, ())
        self.assertEqual(len(result.missing_capabilities), len(self.framework))
        self.assertEqual(result.detected_terms, ())

    def test_no_ai_signal_job_description(self):
        job_text = (
            "Junior Data Analyst required. SQL, Excel, KPI dashboards, and variance analysis. "
            "Finance team support role."
        )
        result = match_job_description_to_ai_capabilities(job_text)
        self.assertEqual(result.match_score, 0)
        self.assertEqual(result.match_label, "Limited AI signal")
        self.assertEqual(result.matched_capabilities, ())

    def test_prompt_and_tool_signal_matches_prompt_engineering_capability(self):
        job_text = "Use ChatGPT and Copilot for prompt engineering and generative AI drafting."
        result = match_job_description_to_ai_capabilities(job_text)
        slugs = {cap.slug for cap in result.matched_capabilities}
        self.assertIn("prompt-engineering-ai-tool-proficiency", slugs)
        self.assertIn("chatgpt", result.detected_terms)
        self.assertGreater(result.match_score, 0)

    def test_workflow_automation_signal_matches_workflow_capability(self):
        job_text = "Improve workflow automation and operations using productivity tools."
        result = match_job_description_to_ai_capabilities(job_text)
        slugs = {cap.slug for cap in result.matched_capabilities}
        self.assertIn("workflow-project-management-ai-tools", slugs)
        self.assertIn("automation", result.detected_terms)

    def test_governance_ethics_signal_matches_ethical_ai_capability(self):
        job_text = "Responsible AI, bias review, governance, and compliance are required."
        result = match_job_description_to_ai_capabilities(job_text)
        slugs = {cap.slug for cap in result.matched_capabilities}
        self.assertIn("ethical-ai-decision-making", slugs)
        self.assertIn("governance", result.detected_terms)

    def test_multiple_capability_matches_increase_score(self):
        job_text = (
            "Prompt engineering with ChatGPT, AI agent orchestration, workshop ideation on Miro, "
            "and stakeholder report decks."
        )
        result = match_job_description_to_ai_capabilities(job_text)
        self.assertGreaterEqual(len(result.matched_capabilities), 3)
        self.assertGreater(result.match_score, 25)
        matched_slugs = {cap.slug for cap in result.matched_capabilities}
        self.assertTrue(matched_slugs.issubset(self.all_slugs))

    def test_match_label_bands_at_boundaries(self):
        self.assertEqual(assign_match_label(0), "Limited AI signal")
        self.assertEqual(assign_match_label(24), "Limited AI signal")
        self.assertEqual(assign_match_label(25), "Moderate AI signal")
        self.assertEqual(assign_match_label(49), "Moderate AI signal")
        self.assertEqual(assign_match_label(50), "Strong AI signal")
        self.assertEqual(assign_match_label(74), "Strong AI signal")
        self.assertEqual(assign_match_label(75), "High AI-workflow alignment")
        self.assertEqual(assign_match_label(100), "High AI-workflow alignment")

    def test_matching_is_deterministic(self):
        job_text = "Generative AI prompt tooling and responsible AI governance."
        first = match_job_description_to_ai_capabilities(job_text)
        second = match_job_description_to_ai_capabilities(job_text)
        self.assertEqual(first, second)

    def test_forbidden_claim_safety_phrases_not_in_output(self):
        job_text = "Prompt engineering and workflow automation."
        result = match_job_description_to_ai_capabilities(job_text)
        combined = self._combined_text(result)
        for phrase in FORBIDDEN_MATCHING_PHRASES:
            self.assertNotIn(phrase, combined, msg=f"Output contains forbidden phrase: {phrase}")

    def test_result_includes_claim_safety_notes_and_explanations(self):
        result = match_job_description_to_ai_capabilities("ChatGPT prompt drafting.")
        self.assertEqual(result.claim_safety_notes, MATCHING_CLAIM_SAFETY_NOTES)
        self.assertGreater(len(result.explanation_points), 0)
        combined = self._combined_text(result)
        self.assertIn("manual review", combined)
        self.assertIn("external ai provider", combined)

    def test_missing_capabilities_cover_unmatched_framework_slugs(self):
        job_text = "ChatGPT prompt drafting only."
        result = match_job_description_to_ai_capabilities(job_text)
        matched_slugs = {cap.slug for cap in result.matched_capabilities}
        missing_slugs = {cap.slug for cap in result.missing_capabilities}
        self.assertEqual(matched_slugs & missing_slugs, set())
        self.assertEqual(matched_slugs | missing_slugs, self.all_slugs)

    def test_no_external_api_behaviour_is_pure_local_matching(self):
        job_text = "AI agent orchestration with LLM prompt tooling."
        result = match_job_description_to_ai_capabilities(job_text)
        self.assertGreater(len(result.matched_capabilities), 0)
        self.assertNotIn("api call", self._combined_text(result))
        self.assertNotIn("api key", self._combined_text(result))

from django.test import SimpleTestCase

from apps.skills.services.ai_capability_framework import get_ai_capability_framework
from apps.skills.services.ai_readiness_scoring import (
    APPROVED_EVIDENCE_STRENGTHS,
    EVIDENCE_STRENGTH_POINTS,
    LEVEL_WEIGHTS,
    READINESS_SCORING_CLAIM_SAFETY_NOTES,
    assign_readiness_label,
    build_careerfunnel_portfolio_evidence_baseline,
    build_empty_ai_readiness_score,
    build_portfolio_baseline_ai_readiness_score,
    calculate_ai_readiness_score,
    evidence_strength_from_tier,
)

FORBIDDEN_SCORING_PHRASES = (
    "auto-apply",
    "auto-send",
    "scraping",
    "billing",
    "gmail",
    "calendar integration",
    "live saas users",
    "customers",
    "production deployment",
)


class AIReadinessScoringTests(SimpleTestCase):
    def setUp(self):
        self.framework = get_ai_capability_framework()
        self.all_slugs = {capability.slug for capability in self.framework}

    def test_empty_evidence_returns_zero_score_and_foundation_needed_label(self):
        result = build_empty_ai_readiness_score()
        self.assertEqual(result.readiness_score, 0)
        self.assertEqual(result.readiness_label, "Foundation needed")
        self.assertEqual(result.capabilities_with_evidence, 0)
        self.assertEqual(len(result.capability_lines), len(self.framework))

    def test_all_strong_evidence_returns_maximum_score(self):
        evidence = {capability.slug: "strong" for capability in self.framework}
        result = calculate_ai_readiness_score(evidence)
        self.assertEqual(result.readiness_score, 100)
        self.assertEqual(result.readiness_label, "Agent / portfolio-ready")
        self.assertEqual(result.capabilities_with_evidence, len(self.framework))

    def test_scoring_is_deterministic_for_same_inputs(self):
        evidence = build_careerfunnel_portfolio_evidence_baseline()
        first = calculate_ai_readiness_score(evidence)
        second = calculate_ai_readiness_score(evidence)
        self.assertEqual(first, second)

    def test_unknown_capability_slug_raises_value_error(self):
        with self.assertRaises(ValueError) as error:
            calculate_ai_readiness_score({"not-a-real-slug": "strong"})
        self.assertIn("Unknown capability slugs", str(error.exception))

    def test_invalid_evidence_strength_raises_value_error(self):
        slug = self.framework[0].slug
        with self.assertRaises(ValueError) as error:
            calculate_ai_readiness_score({slug: "invalid"})
        self.assertIn("Unsupported evidence strength", str(error.exception))

    def test_every_capability_line_has_explanation_and_points(self):
        result = build_portfolio_baseline_ai_readiness_score()
        for line in result.capability_lines:
            self.assertIn(line.slug, self.all_slugs)
            self.assertTrue(line.title.strip())
            self.assertIn(line.evidence_strength, APPROVED_EVIDENCE_STRENGTHS)
            self.assertGreaterEqual(line.points_earned, 0)
            expected_possible = (
                EVIDENCE_STRENGTH_POINTS["strong"] * LEVEL_WEIGHTS[line.framework_level]
            )
            self.assertEqual(line.points_possible, expected_possible)
            self.assertTrue(line.explanation.strip())

    def test_readiness_label_bands_at_boundaries(self):
        self.assertEqual(assign_readiness_label(0), "Foundation needed")
        self.assertEqual(assign_readiness_label(24), "Foundation needed")
        self.assertEqual(assign_readiness_label(25), "Foundation in progress")
        self.assertEqual(assign_readiness_label(49), "Foundation in progress")
        self.assertEqual(assign_readiness_label(50), "Applied readiness")
        self.assertEqual(assign_readiness_label(69), "Applied readiness")
        self.assertEqual(assign_readiness_label(70), "Strong applied readiness")
        self.assertEqual(assign_readiness_label(84), "Strong applied readiness")
        self.assertEqual(assign_readiness_label(85), "Agent / portfolio-ready")
        self.assertEqual(assign_readiness_label(100), "Agent / portfolio-ready")

    def test_evidence_strength_from_tier_maps_evidence_bank_tiers(self):
        self.assertEqual(evidence_strength_from_tier(None), "none")
        self.assertEqual(evidence_strength_from_tier("strong"), "strong")
        self.assertEqual(evidence_strength_from_tier("partial"), "partial")
        self.assertEqual(evidence_strength_from_tier("gap_learning"), "gap_learning")

    def test_portfolio_baseline_is_claim_safe_and_non_empty(self):
        baseline = build_careerfunnel_portfolio_evidence_baseline()
        self.assertEqual(set(baseline), self.all_slugs)
        for strength in baseline.values():
            self.assertIn(strength, APPROVED_EVIDENCE_STRENGTHS)
        result = build_portfolio_baseline_ai_readiness_score()
        self.assertGreater(result.readiness_score, 0)
        self.assertLess(result.readiness_score, 100)

    def test_result_includes_claim_safety_and_explanation_points(self):
        result = build_portfolio_baseline_ai_readiness_score()
        self.assertEqual(result.claim_safety_notes, READINESS_SCORING_CLAIM_SAFETY_NOTES)
        self.assertGreater(len(result.explanation_points), 0)
        combined = " ".join(
            [
                result.readiness_label,
                *result.explanation_points,
                *result.claim_safety_notes,
                *(line.explanation for line in result.capability_lines),
            ]
        ).lower()
        self.assertIn("manual", combined)
        self.assertIn("advisory", combined)
        for phrase in FORBIDDEN_SCORING_PHRASES:
            self.assertNotIn(phrase, combined, msg=f"Scoring text contains: {phrase}")

    def test_stronger_evidence_never_lowers_score_for_same_capability(self):
        slug = self.framework[0].slug
        partial = calculate_ai_readiness_score({slug: "partial"})
        strong = calculate_ai_readiness_score({slug: "strong"})
        self.assertGreater(strong.readiness_score, partial.readiness_score)

    def test_gap_learning_counts_as_evidence_but_scores_below_partial(self):
        slug = self.framework[0].slug
        gap = calculate_ai_readiness_score({slug: "gap_learning"})
        partial = calculate_ai_readiness_score({slug: "partial"})
        self.assertEqual(gap.capabilities_with_evidence, 1)
        self.assertLess(gap.readiness_score, partial.readiness_score)

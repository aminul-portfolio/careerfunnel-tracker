from django.test import SimpleTestCase

from apps.skills.services.ai_capability_framework import (
    AI_CAPABILITY_FRAMEWORK,
    APPROVED_CAPABILITY_LEVELS,
    FRAMEWORK_CLAIM_SAFETY_NOTE,
    TOOL_EXAMPLES_DISCLAIMER,
    AICapabilityCategory,
    get_ai_capability_framework,
)

REQUIRED_FIELDS = (
    "slug",
    "title",
    "description",
    "level",
    "evidence_examples",
    "career_relevance",
    "tool_examples",
    "claim_safety_note",
)

FORBIDDEN_CAPABILITY_PHRASES = (
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


class AICapabilityFrameworkTests(SimpleTestCase):
    def setUp(self):
        self.framework = get_ai_capability_framework()

    def test_framework_returns_non_empty_list(self):
        self.assertIsInstance(self.framework, tuple)
        self.assertGreater(len(self.framework), 0)
        self.assertEqual(self.framework, AI_CAPABILITY_FRAMEWORK)

    def test_every_capability_has_required_fields(self):
        for capability in self.framework:
            self.assertIsInstance(capability, AICapabilityCategory)
            for field_name in REQUIRED_FIELDS:
                self.assertTrue(hasattr(capability, field_name), msg=field_name)
                value = getattr(capability, field_name)
                self.assertIsNotNone(value)
                if field_name in {"evidence_examples", "tool_examples"}:
                    self.assertIsInstance(value, tuple)
                    self.assertGreater(len(value), 0, msg=capability.slug)
                else:
                    self.assertIsInstance(value, str)
                    self.assertTrue(value.strip(), msg=field_name)

    def test_slugs_are_unique(self):
        slugs = [capability.slug for capability in self.framework]
        self.assertEqual(len(slugs), len(set(slugs)))

    def test_levels_are_limited_to_approved_values(self):
        for capability in self.framework:
            self.assertIn(capability.level, APPROVED_CAPABILITY_LEVELS)

    def test_tool_examples_are_labelled_as_examples_only(self):
        disclaimer_lower = TOOL_EXAMPLES_DISCLAIMER.lower()
        for capability in self.framework:
            joined_tools = " ".join(capability.tool_examples).lower()
            self.assertIn("example", joined_tools)
            self.assertIn("not integrated", joined_tools)
            self.assertIn(disclaimer_lower, joined_tools)

    def test_claim_safety_notes_are_advisory_and_manual(self):
        for capability in self.framework:
            note = capability.claim_safety_note.lower()
            self.assertIn("advisory", note)
            self.assertIn("manual", note)
            self.assertIn("external ai", note)

    def test_capability_text_avoids_forbidden_claims(self):
        for capability in self.framework:
            combined_text = " ".join(
                [
                    capability.title,
                    capability.description,
                    capability.career_relevance,
                    capability.claim_safety_note,
                    *capability.evidence_examples,
                    *capability.tool_examples,
                ]
            ).lower()
            for phrase in FORBIDDEN_CAPABILITY_PHRASES:
                self.assertNotIn(
                    phrase,
                    combined_text,
                    msg=f"{capability.slug} contains forbidden phrase: {phrase}",
                )

    def test_framework_level_claim_safety_note_is_consistent(self):
        for capability in self.framework:
            self.assertEqual(capability.claim_safety_note, FRAMEWORK_CLAIM_SAFETY_NOTE)

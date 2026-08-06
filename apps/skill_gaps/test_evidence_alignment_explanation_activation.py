"""Sprint 117 Phase 2: controlled availability for advisory explanation CTA."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.applications.models import JobApplication
from apps.skill_gaps.deterministic_evidence_alignment import (
    EvidenceAlignmentOutcome,
    EvidenceAlignmentSummary,
)
from apps.skill_gaps.models import ApplicationSkillGap
from apps.skill_ledger.models import SkillEntry

User = get_user_model()

EXPECTED_RULE_VERSION = "evidence_alignment_v1"
COMPOSE_PATH = (
    "apps.skill_gaps.deterministic_gap_views."
    "compose_evidence_alignment_explanation_provider"
)
BUILD_PAYLOAD_PATH = (
    "apps.skill_gaps.deterministic_gap_views."
    "build_evidence_alignment_explanation_payload"
)
CTA_LABEL = "Generate advisory explanation"
FALLBACK_STATEMENT = (
    "The advisory explanation could not be generated. Your deterministic "
    "evidence-alignment result remains available below."
)
ADVISORY_WORDING = (
    "AI-generated explanations are advisory and may be incomplete or contain "
    "errors. The deterministic evidence-alignment result above remains "
    "authoritative; this explanation does not add, change or verify any evidence."
)
NOT_SAVED_WORDING = (
    "This explanation is generated only when you request it and is not saved."
)


def _valid_provider_output(payload: dict) -> dict:
    verified: list[dict] = []
    development: list[dict] = []
    missing: list[dict] = []
    for req in payload["requirements"]:
        index = req["requirement_index"]
        skill = req.get("matched_skill_name")
        classification = req["classification"]
        if classification == "VERIFIED_MATCH":
            verified.append(
                {
                    "requirement_index": index,
                    "skill_names": [skill],
                    "explanation": (
                        f"{skill} matches verified Skill Ledger evidence."
                    ),
                }
            )
        elif classification in {"LEARNING_TARGET_MATCH", "STUDYING_MATCH"}:
            development.append(
                {
                    "requirement_index": index,
                    "skill_names": [skill],
                    "evidence_level": req["matched_evidence_level"],
                    "explanation": (
                        f"{skill} is present as a development Skill Ledger record."
                    ),
                }
            )
        elif classification == "NO_EVIDENCE_GAP":
            missing.append(
                {
                    "requirement_index": index,
                    "explanation": (
                        "No current Skill Ledger evidence for this requirement."
                    ),
                }
            )
    return {
        "summary": (
            "Deterministic evidence alignment explained from supplied "
            "Skill Ledger records only."
        ),
        "verified_evidence": verified,
        "development_evidence": development,
        "missing_evidence": missing,
    }


class EvidenceAlignmentExplanationActivationTests(TestCase):
    """Fail-closed page-level activation for the JD Gap Analysis CTA."""

    def setUp(self):
        self.owner = User.objects.create_user(
            username="s117p2_owner",
            password="pass",
        )
        self.url = reverse("skill_gaps:jd_gap_analysis")

    def _login(self):
        self.client.login(username="s117p2_owner", password="pass")

    def _create_entry(self, skill_name, evidence_level):
        return SkillEntry.objects.create(
            user=self.owner,
            skill_name=skill_name,
            category=SkillEntry.Category.PROGRAMMING,
            evidence_level=evidence_level,
            visibility=SkillEntry.Visibility.PRIVATE,
        )

    def _permitted_requirements(self):
        self._create_entry("Python", SkillEntry.EvidenceLevel.VERIFIED)
        self._create_entry(
            "Snowflake",
            SkillEntry.EvidenceLevel.LEARNING_TARGET,
        )
        return "Python\nSnowflake\nGraphQL"

    def _model_counts(self):
        return (
            SkillEntry.objects.count(),
            JobApplication.objects.count(),
            ApplicationSkillGap.objects.count(),
        )

    def test_anonymous_get_is_denied_or_redirected(self):
        response = self.client.get(self.url)
        self.assertIn(response.status_code, {301, 302})
        self.assertIn("/accounts/login/", response.url)

    def test_anonymous_post_is_denied_or_redirected(self):
        response = self.client.post(self.url, {"requirements": "Python"})
        self.assertIn(response.status_code, {301, 302})
        self.assertIn("/accounts/login/", response.url)

    @override_settings(AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=False)
    def test_authenticated_get_with_feature_disabled_hides_cta_and_skips_provider(self):
        self._login()
        self._create_entry("Python", SkillEntry.EvidenceLevel.VERIFIED)
        with (
            patch(COMPOSE_PATH) as compose,
            patch(BUILD_PAYLOAD_PATH) as build_payload,
        ):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["explanation_feature_enabled"])
        self.assertNotContains(response, CTA_LABEL)
        compose.assert_not_called()
        build_payload.assert_not_called()

    @override_settings(AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=False)
    def test_authenticated_deterministic_post_with_feature_disabled_hides_cta(self):
        self._login()
        requirements = self._permitted_requirements()
        with patch(COMPOSE_PATH) as compose:
            response = self.client.post(
                self.url,
                {"requirements": requirements},
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["analysis_performed"])
        self.assertIsNotNone(response.context["summary"])
        self.assertTrue(response.context["explanation_allowed"])
        self.assertFalse(response.context["explanation_feature_enabled"])
        self.assertContains(response, "Evidence alignment summary")
        self.assertNotContains(response, CTA_LABEL)
        compose.assert_not_called()

    @override_settings(AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=False)
    def test_forged_explanation_post_while_disabled_blocks_before_composition(self):
        self._login()
        requirements = self._permitted_requirements()
        provider = MagicMock(return_value={"summary": "should-not-run"})
        with (
            patch(COMPOSE_PATH, return_value=provider) as compose,
            patch(BUILD_PAYLOAD_PATH) as build_payload,
        ):
            response = self.client.post(
                self.url,
                {
                    "requirements": requirements,
                    "generate_explanation": "1",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["analysis_performed"])
        self.assertIsNotNone(response.context["summary"])
        self.assertTrue(response.context["explanation_requested"])
        self.assertFalse(response.context["explanation_feature_enabled"])
        self.assertIsNone(response.context["advisory_explanation"])
        self.assertFalse(response.context["advisory_explanation_failed"])
        self.assertContains(response, "Evidence alignment summary")
        self.assertNotContains(response, FALLBACK_STATEMENT)
        self.assertNotContains(response, CTA_LABEL)
        compose.assert_not_called()
        build_payload.assert_not_called()
        provider.assert_not_called()

    def test_missing_feature_setting_fails_closed(self):
        self._login()
        requirements = self._permitted_requirements()

        class _SettingsWithoutFlag:
            pass

        with (
            patch(
                "apps.skill_gaps.deterministic_gap_views.settings",
                _SettingsWithoutFlag(),
            ),
            patch(COMPOSE_PATH) as compose,
        ):
            response = self.client.post(
                self.url,
                {
                    "requirements": requirements,
                    "generate_explanation": "1",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["explanation_feature_enabled"])
        self.assertNotContains(response, CTA_LABEL)
        self.assertNotContains(response, FALLBACK_STATEMENT)
        compose.assert_not_called()

    def test_false_like_string_setting_cannot_activate_feature(self):
        self._login()
        requirements = self._permitted_requirements()
        with (
            override_settings(AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED="False"),
            patch(COMPOSE_PATH) as compose,
        ):
            response = self.client.post(
                self.url,
                {
                    "requirements": requirements,
                    "generate_explanation": "1",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["explanation_feature_enabled"])
        self.assertNotContains(response, CTA_LABEL)
        self.assertNotContains(response, FALLBACK_STATEMENT)
        compose.assert_not_called()

    @override_settings(AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True)
    def test_feature_enabled_with_permitted_outcome_shows_cta(self):
        self._login()
        requirements = self._permitted_requirements()
        with patch(COMPOSE_PATH) as compose:
            response = self.client.post(
                self.url,
                {"requirements": requirements},
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["explanation_feature_enabled"])
        self.assertTrue(response.context["explanation_allowed"])
        self.assertContains(response, CTA_LABEL)
        compose.assert_not_called()

    @override_settings(AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True)
    def test_feature_enabled_with_manual_review_hides_cta(self):
        self._login()
        self._create_entry("Python", SkillEntry.EvidenceLevel.VERIFIED)
        with patch(COMPOSE_PATH) as compose:
            response = self.client.post(
                self.url,
                {"requirements": "Senior Python"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["summary"].outcome,
            EvidenceAlignmentOutcome.MANUAL_REVIEW_REQUIRED,
        )
        self.assertFalse(response.context["explanation_allowed"])
        self.assertNotContains(response, CTA_LABEL)
        compose.assert_not_called()

    @override_settings(AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True)
    def test_feature_enabled_with_no_accepted_requirements_hides_cta(self):
        self._login()
        blocked_summary = EvidenceAlignmentSummary(
            rule_version=EXPECTED_RULE_VERSION,
            outcome=EvidenceAlignmentOutcome.NO_ACCEPTED_REQUIREMENTS,
            triggered_rule="NO_ACCEPTED_REQUIREMENTS",
            total_requirements=0,
            verified_count=0,
            learning_target_count=0,
            studying_count=0,
            no_match_count=0,
            explicit_no_evidence_count=0,
            no_current_evidence_count=0,
            review_required_count=0,
            unresolved_requirement_indexes=(),
            per_requirement_results=(),
        )
        with (
            patch(
                "apps.skill_gaps.deterministic_gap_views."
                "summarise_evidence_alignment",
                return_value=blocked_summary,
            ),
            patch(COMPOSE_PATH) as compose,
        ):
            response = self.client.post(
                self.url,
                {"requirements": "Python"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["explanation_allowed"])
        self.assertNotContains(response, CTA_LABEL)
        compose.assert_not_called()

    @override_settings(AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True)
    def test_explicit_valid_explanation_post_uses_non_telemetry_composer_once(self):
        self._login()
        requirements = self._permitted_requirements()
        provider = MagicMock(side_effect=_valid_provider_output)
        with patch(COMPOSE_PATH, return_value=provider) as compose:
            response = self.client.post(
                self.url,
                {
                    "requirements": requirements,
                    "generate_explanation": "1",
                },
            )
        self.assertEqual(response.status_code, 200)
        compose.assert_called_once()
        provider.assert_called_once()
        self.assertIsNotNone(response.context["advisory_explanation"])
        self.assertFalse(response.context["advisory_explanation_failed"])

    @override_settings(AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True)
    def test_accepted_provider_output_renders_locked_schema_sections(self):
        self._login()
        requirements = self._permitted_requirements()
        provider = MagicMock(side_effect=_valid_provider_output)
        with patch(COMPOSE_PATH, return_value=provider):
            response = self.client.post(
                self.url,
                {
                    "requirements": requirements,
                    "generate_explanation": "1",
                },
            )
        advisory = response.context["advisory_explanation"]
        self.assertEqual(
            set(advisory.keys()),
            {
                "summary",
                "verified_evidence",
                "development_evidence",
                "missing_evidence",
            },
        )
        self.assertContains(response, advisory["summary"])
        self.assertContains(response, "Verified evidence")
        self.assertContains(response, "Development evidence")
        self.assertContains(response, "Missing evidence")
        self.assertNotContains(response, CTA_LABEL)

    @override_settings(AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True)
    def test_invalid_provider_output_keeps_deterministic_result_and_safe_fallback(self):
        self._login()
        requirements = self._permitted_requirements()
        provider = MagicMock(
            return_value={
                "summary": "bad",
                "verified_evidence": [],
                "development_evidence": [],
                "missing_evidence": [],
                "extra_field": "rejected",
            }
        )
        with patch(COMPOSE_PATH, return_value=provider):
            response = self.client.post(
                self.url,
                {
                    "requirements": requirements,
                    "generate_explanation": "1",
                },
            )
        content = response.content.decode("utf-8")
        self.assertIsNone(response.context["advisory_explanation"])
        self.assertTrue(response.context["advisory_explanation_failed"])
        self.assertContains(response, "Evidence alignment summary")
        self.assertContains(response, FALLBACK_STATEMENT)
        self.assertNotIn("extra_field", content)
        self.assertNotContains(response, CTA_LABEL)
        provider.assert_called_once()

    @override_settings(AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True)
    def test_provider_exception_hides_details_and_keeps_deterministic_result(self):
        self._login()
        requirements = self._permitted_requirements()
        provider = MagicMock(side_effect=RuntimeError("secret-provider-boom"))
        with patch(COMPOSE_PATH, return_value=provider):
            response = self.client.post(
                self.url,
                {
                    "requirements": requirements,
                    "generate_explanation": "1",
                },
            )
        content = response.content.decode("utf-8")
        self.assertTrue(response.context["advisory_explanation_failed"])
        self.assertContains(response, "Evidence alignment summary")
        self.assertContains(response, FALLBACK_STATEMENT)
        self.assertNotIn("secret-provider-boom", content)
        self.assertNotIn("RuntimeError", content)
        self.assertNotIn("Traceback", content)
        provider.assert_called_once()

    @override_settings(AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True)
    def test_explanation_post_does_not_change_persistence_row_counts(self):
        self._login()
        requirements = self._permitted_requirements()
        before = self._model_counts()
        provider = MagicMock(side_effect=_valid_provider_output)
        with patch(COMPOSE_PATH, return_value=provider):
            response = self.client.post(
                self.url,
                {
                    "requirements": requirements,
                    "generate_explanation": "1",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._model_counts(), before)

    @override_settings(AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True)
    def test_template_contains_exact_cta_label_only_when_enabled(self):
        self._login()
        requirements = self._permitted_requirements()
        enabled = self.client.post(self.url, {"requirements": requirements})
        self.assertContains(enabled, CTA_LABEL)
        self.assertEqual(enabled.content.decode("utf-8").count(CTA_LABEL), 1)

        with override_settings(AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=False):
            disabled = self.client.post(
                self.url,
                {"requirements": requirements},
            )
        self.assertNotContains(disabled, CTA_LABEL)

    @override_settings(AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True)
    def test_existing_advisory_and_non_save_wording_remains_present(self):
        self._login()
        requirements = self._permitted_requirements()
        response = self.client.post(self.url, {"requirements": requirements})
        self.assertContains(response, ADVISORY_WORDING)
        self.assertContains(response, NOT_SAVED_WORDING)
        self.assertContains(
            response,
            "Skill gap signals are advisory only.",
        )

    @override_settings(AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True)
    def test_get_never_triggers_payload_construction_or_provider_composition(self):
        self._login()
        self._create_entry("Python", SkillEntry.EvidenceLevel.VERIFIED)
        with (
            patch(COMPOSE_PATH) as compose,
            patch(BUILD_PAYLOAD_PATH) as build_payload,
        ):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["explanation_feature_enabled"])
        compose.assert_not_called()
        build_payload.assert_not_called()

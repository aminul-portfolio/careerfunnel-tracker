"""Sprint 117: controlled activation and safety hardening for advisory explanation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.applications.models import JobApplication
from apps.skill_gaps.deterministic_evidence_alignment import (
    EvidenceAlignmentOutcome,
    EvidenceAlignmentSummary,
)
from apps.skill_gaps.explanation_request_governance import (
    REASON_COUNT_LIMIT_REACHED,
    REASON_GOVERNANCE_CONFIGURATION_INVALID,
    REASON_GOVERNANCE_STORAGE_UNAVAILABLE,
    ExplanationRequestReservationDecision,
    reserve_explanation_request,
)
from apps.skill_gaps.models import ApplicationSkillGap, ExplanationRequestCounter
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
VALIDATE_PATH = (
    "apps.skill_gaps.deterministic_gap_views."
    "validate_evidence_alignment_explanation_output"
)
CTA_LABEL = "Generate advisory explanation"
FALLBACK_STATEMENT = (
    "The advisory explanation could not be generated. Your deterministic "
    "evidence-alignment result remains available below."
)
GOVERNANCE_COUNT_LIMIT_WORDING = (
    "The advisory explanation is unavailable because the current request "
    "limit has been reached. Your deterministic evidence-alignment result "
    "remains available and has not been changed."
)
GOVERNANCE_GENERIC_UNAVAILABLE_WORDING = (
    "The advisory explanation is unavailable. Your deterministic "
    "evidence-alignment result remains available and has not been changed."
)
RESERVE_PATH = (
    "apps.skill_gaps.deterministic_gap_views.reserve_explanation_request"
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

    @override_settings(
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=100,
)
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

    @override_settings(
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=100,
)
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

    @override_settings(
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=100,
)
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

    @override_settings(
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=100,
)
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

    @override_settings(
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=100,
)
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

    @override_settings(
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=100,
)
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

    @override_settings(
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=100,
)
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

    @override_settings(
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=100,
)
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

    @override_settings(
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=100,
)
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

    @override_settings(
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=100,
)
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

    @override_settings(
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=100,
)
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


class EvidenceAlignmentExplanationActivationSafetyTests(TestCase):
    """Sprint 117 Phase 3: adversarial fail-closed activation boundary tests."""

    def setUp(self):
        self.owner = User.objects.create_user(
            username="s117p3_owner",
            password="pass",
        )
        self.url = reverse("skill_gaps:jd_gap_analysis")

    def _login(self):
        self.client.login(username="s117p3_owner", password="pass")

    def _create_entry(self, skill_name, evidence_level, user=None):
        return SkillEntry.objects.create(
            user=user or self.owner,
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

    def _context_text(self, response) -> str:
        parts: list[str] = []
        for layer in response.context:
            dicts = getattr(layer, "dicts", None)
            if dicts is not None:
                for mapping in dicts:
                    for key, value in mapping.items():
                        parts.append(f"{key}={value!r}")
            elif hasattr(layer, "items"):
                for key, value in layer.items():
                    parts.append(f"{key}={value!r}")
            else:
                parts.append(repr(layer))
        return "\n".join(parts)

    def test_integer_setting_fails_closed(self):
        self._login()
        requirements = self._permitted_requirements()
        with (
            override_settings(AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=1),
            patch(COMPOSE_PATH) as compose,
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
        self.assertFalse(response.context["explanation_feature_enabled"])
        self.assertNotContains(response, CTA_LABEL)
        compose.assert_not_called()
        build_payload.assert_not_called()

    def test_true_like_string_setting_fails_closed(self):
        self._login()
        requirements = self._permitted_requirements()
        with (
            override_settings(AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED="true"),
            patch(COMPOSE_PATH) as compose,
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
        self.assertFalse(response.context["explanation_feature_enabled"])
        self.assertNotContains(response, CTA_LABEL)
        compose.assert_not_called()
        build_payload.assert_not_called()

    @override_settings(AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=False)
    def test_disabled_feature_hides_complete_advisory_surface(self):
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
        self.assertContains(response, "Evidence alignment summary")
        self.assertContains(response, "Analysis results")
        self.assertNotContains(response, CTA_LABEL)
        self.assertNotContains(response, 'aria-label="Advisory explanation"')
        self.assertNotContains(response, FALLBACK_STATEMENT)
        self.assertNotContains(response, "<h2>Advisory explanation</h2>")
        self.assertNotContains(response, "<h3>Verified evidence</h3>")
        self.assertNotContains(response, "<h3>Development evidence</h3>")
        self.assertNotContains(response, "<h3>Missing evidence</h3>")
        compose.assert_not_called()

    @override_settings(
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=100,
)
    def test_enabled_standard_analysis_post_remains_provider_free(self):
        self._login()
        requirements = self._permitted_requirements()
        with (
            patch(COMPOSE_PATH) as compose,
            patch(BUILD_PAYLOAD_PATH) as build_payload,
            patch(VALIDATE_PATH) as validate_output,
        ):
            response = self.client.post(
                self.url,
                {"requirements": requirements},
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["explanation_allowed"])
        self.assertContains(response, CTA_LABEL)
        compose.assert_not_called()
        build_payload.assert_not_called()
        validate_output.assert_not_called()

    @override_settings(
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=100,
)
    def test_invalid_explanation_post_remains_provider_free(self):
        self._login()
        with (
            patch(COMPOSE_PATH) as compose,
            patch(BUILD_PAYLOAD_PATH) as build_payload,
            patch(VALIDATE_PATH) as validate_output,
        ):
            response = self.client.post(
                self.url,
                {
                    "requirements": "",
                    "generate_explanation": "1",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].is_valid())
        self.assertTrue(response.context["form"].errors)
        self.assertFalse(response.context["analysis_performed"])
        self.assertIsNone(response.context["summary"])
        self.assertIsNone(response.context["advisory_explanation"])
        self.assertFalse(response.context["advisory_explanation_failed"])
        self.assertNotContains(response, FALLBACK_STATEMENT)
        compose.assert_not_called()
        build_payload.assert_not_called()
        validate_output.assert_not_called()

    @override_settings(
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=100,
)
    def test_manual_review_forged_post_skips_complete_pipeline(self):
        self._login()
        self._create_entry("Python", SkillEntry.EvidenceLevel.VERIFIED)
        provider = MagicMock(return_value={"summary": "should-not-run"})
        with (
            patch(COMPOSE_PATH, return_value=provider) as compose,
            patch(BUILD_PAYLOAD_PATH) as build_payload,
            patch(VALIDATE_PATH) as validate_output,
        ):
            response = self.client.post(
                self.url,
                {
                    "requirements": "Senior Python",
                    "generate_explanation": "1",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["summary"].outcome,
            EvidenceAlignmentOutcome.MANUAL_REVIEW_REQUIRED,
        )
        self.assertFalse(response.context["explanation_allowed"])
        self.assertIsNone(response.context["advisory_explanation"])
        self.assertFalse(response.context["advisory_explanation_failed"])
        self.assertContains(response, "Evidence alignment summary")
        self.assertNotContains(response, FALLBACK_STATEMENT)
        compose.assert_not_called()
        build_payload.assert_not_called()
        provider.assert_not_called()
        validate_output.assert_not_called()

    @override_settings(
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=100,
)
    def test_no_accepted_requirements_forged_post_skips_pipeline(self):
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
        provider = MagicMock(return_value={"summary": "should-not-run"})
        with (
            patch(
                "apps.skill_gaps.deterministic_gap_views."
                "summarise_evidence_alignment",
                return_value=blocked_summary,
            ),
            patch(COMPOSE_PATH, return_value=provider) as compose,
            patch(BUILD_PAYLOAD_PATH) as build_payload,
            patch(VALIDATE_PATH) as validate_output,
        ):
            response = self.client.post(
                self.url,
                {
                    "requirements": "Python",
                    "generate_explanation": "1",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["summary"].outcome,
            EvidenceAlignmentOutcome.NO_ACCEPTED_REQUIREMENTS,
        )
        self.assertFalse(response.context["explanation_allowed"])
        self.assertIsNone(response.context["advisory_explanation"])
        self.assertFalse(response.context["advisory_explanation_failed"])
        self.assertContains(response, "Evidence alignment summary")
        compose.assert_not_called()
        build_payload.assert_not_called()
        provider.assert_not_called()
        validate_output.assert_not_called()

    @override_settings(
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=100,
)
    def test_composer_none_path_is_one_shot_and_safe(self):
        self._login()
        requirements = self._permitted_requirements()
        with (
            patch(COMPOSE_PATH, return_value=None) as compose,
            patch(BUILD_PAYLOAD_PATH) as build_payload,
            patch(VALIDATE_PATH) as validate_output,
        ):
            response = self.client.post(
                self.url,
                {
                    "requirements": requirements,
                    "generate_explanation": "1",
                },
            )
        content = response.content.decode("utf-8")
        self.assertEqual(response.status_code, 200)
        compose.assert_called_once()
        build_payload.assert_not_called()
        validate_output.assert_not_called()
        self.assertIsNone(response.context["advisory_explanation"])
        self.assertTrue(response.context["advisory_explanation_failed"])
        self.assertEqual(content.count(FALLBACK_STATEMENT), 1)
        self.assertNotContains(response, CTA_LABEL)
        self.assertContains(response, "Evidence alignment summary")

    @override_settings(
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=100,
)
    def test_provider_exception_has_no_retry(self):
        self._login()
        requirements = self._permitted_requirements()
        marker = "SENSITIVE_PROVIDER_MARKER_S117P3_9"
        provider = MagicMock(side_effect=RuntimeError(marker))
        with (
            patch(COMPOSE_PATH, return_value=provider) as compose,
            patch(BUILD_PAYLOAD_PATH) as build_payload,
            patch(VALIDATE_PATH) as validate_output,
        ):
            response = self.client.post(
                self.url,
                {
                    "requirements": requirements,
                    "generate_explanation": "1",
                },
            )
        content = response.content.decode("utf-8")
        self.assertEqual(response.status_code, 200)
        compose.assert_called_once()
        provider.assert_called_once()
        build_payload.assert_called_once()
        validate_output.assert_not_called()
        self.assertEqual(content.count(FALLBACK_STATEMENT), 1)
        self.assertNotIn(marker, content)
        self.assertNotIn("RuntimeError", content)
        self.assertContains(response, "Evidence alignment summary")

    @override_settings(
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=100,
)
    def test_validator_exception_has_no_retry(self):
        self._login()
        requirements = self._permitted_requirements()
        provider = MagicMock(side_effect=_valid_provider_output)
        with (
            patch(COMPOSE_PATH, return_value=provider) as compose,
            patch(
                VALIDATE_PATH,
                side_effect=ValueError("validator-boom-s117p3"),
            ) as validate_output,
        ):
            response = self.client.post(
                self.url,
                {
                    "requirements": requirements,
                    "generate_explanation": "1",
                },
            )
        content = response.content.decode("utf-8")
        self.assertEqual(response.status_code, 200)
        compose.assert_called_once()
        provider.assert_called_once()
        validate_output.assert_called_once()
        self.assertEqual(provider.call_count, 1)
        self.assertEqual(content.count(FALLBACK_STATEMENT), 1)
        self.assertIsNone(response.context["advisory_explanation"])
        self.assertTrue(response.context["advisory_explanation_failed"])
        self.assertNotIn("validator-boom-s117p3", content)
        self.assertNotIn("ValueError", content)

    @override_settings(
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=100,
)
    def test_non_dictionary_outputs_fail_closed(self):
        self._login()
        requirements = self._permitted_requirements()
        cases = {
            "none": None,
            "string": "not-a-dict",
            "list": [{"summary": "bad"}],
        }
        for label, raw in cases.items():
            with self.subTest(case=label):
                provider = MagicMock(return_value=raw)
                with patch(COMPOSE_PATH, return_value=provider):
                    response = self.client.post(
                        self.url,
                        {
                            "requirements": requirements,
                            "generate_explanation": "1",
                        },
                    )
                content = response.content.decode("utf-8")
                self.assertEqual(response.status_code, 200)
                provider.assert_called_once()
                self.assertEqual(provider.call_count, 1)
                self.assertIsNone(response.context["advisory_explanation"])
                self.assertTrue(response.context["advisory_explanation_failed"])
                self.assertEqual(content.count(FALLBACK_STATEMENT), 1)
                self.assertContains(response, "Evidence alignment summary")
                if isinstance(raw, str):
                    self.assertNotIn(raw, content)

    @override_settings(
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=100,
)
    def test_extra_top_level_schema_field_is_rejected(self):
        self._login()
        requirements = self._permitted_requirements()
        unauthorised_name = "unauthorised_fifth_field"
        unauthorised_value = "unauthorised-value-s117p3"

        def bad_output(payload):
            raw = _valid_provider_output(payload)
            raw[unauthorised_name] = unauthorised_value
            return raw

        provider = MagicMock(side_effect=bad_output)
        with patch(COMPOSE_PATH, return_value=provider):
            response = self.client.post(
                self.url,
                {
                    "requirements": requirements,
                    "generate_explanation": "1",
                },
            )
        content = response.content.decode("utf-8")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["advisory_explanation"])
        self.assertTrue(response.context["advisory_explanation_failed"])
        self.assertEqual(content.count(FALLBACK_STATEMENT), 1)
        self.assertNotIn(unauthorised_name, content)
        self.assertNotIn(unauthorised_value, content)
        provider.assert_called_once()

    @override_settings(
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=100,
)
    def test_learning_target_cannot_become_verified(self):
        self._login()
        requirements = self._permitted_requirements()
        claimed_verified = "Snowflake is verified Skill Ledger evidence."

        def misclassified(payload):
            raw = _valid_provider_output(payload)
            development = raw["development_evidence"]
            self.assertTrue(development)
            promoted = development.pop(0)
            raw["verified_evidence"].append(
                {
                    "requirement_index": promoted["requirement_index"],
                    "skill_names": list(promoted["skill_names"]),
                    "explanation": claimed_verified,
                }
            )
            return raw

        provider = MagicMock(side_effect=misclassified)
        with patch(COMPOSE_PATH, return_value=provider):
            response = self.client.post(
                self.url,
                {
                    "requirements": requirements,
                    "generate_explanation": "1",
                },
            )
        content = response.content.decode("utf-8")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["advisory_explanation"])
        self.assertTrue(response.context["advisory_explanation_failed"])
        self.assertEqual(content.count(FALLBACK_STATEMENT), 1)
        self.assertNotIn(claimed_verified, content)
        self.assertContains(response, "LEARNING_TARGET_MATCH")
        self.assertContains(response, "LEARNING_TARGET")
        self.assertContains(response, "Evidence alignment summary")
        provider.assert_called_once()

    @override_settings(
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=100,
)
    def test_invented_skill_or_credential_is_rejected(self):
        self._login()
        requirements = self._permitted_requirements()
        invented = "InventedCredentialCertXZ117"

        def invented_output(payload):
            raw = _valid_provider_output(payload)
            raw["verified_evidence"] = [
                {
                    "requirement_index": 0,
                    "skill_names": [invented],
                    "explanation": f"{invented} proves readiness.",
                }
            ]
            return raw

        provider = MagicMock(side_effect=invented_output)
        with patch(COMPOSE_PATH, return_value=provider):
            response = self.client.post(
                self.url,
                {
                    "requirements": requirements,
                    "generate_explanation": "1",
                },
            )
        content = response.content.decode("utf-8")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["advisory_explanation"])
        self.assertTrue(response.context["advisory_explanation_failed"])
        self.assertEqual(content.count(FALLBACK_STATEMENT), 1)
        self.assertNotIn(invented, content)
        self.assertContains(response, "Evidence alignment summary")
        self.assertContains(response, "Analysis results")
        provider.assert_called_once()

    @override_settings(
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=100,
)
    def test_provider_error_leakage_denial(self):
        self._login()
        requirements = self._permitted_requirements()
        markers = (
            "sk-ant-api03-LEAKTESTKEY117PHASE3XYZ",
            r"G:\final_polish\careerfunnel-tracker\secret.py",
            "/var/lib/careerfunnel/secret_prompt.bin",
            "req_id_s117p3_leak_9f3a2c",
            "SYSTEM_PROMPT_BEGIN_S117P3_DO_NOT_RENDER",
        )
        provider = MagicMock(
            side_effect=RuntimeError(" | ".join(markers)),
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
        context_text = self._context_text(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(content.count(FALLBACK_STATEMENT), 1)
        self.assertIsNone(response.context["advisory_explanation"])
        for marker in markers:
            self.assertNotIn(marker, content)
            self.assertNotIn(marker, context_text)
            self.assertNotIn(marker, FALLBACK_STATEMENT)
        provider.assert_called_once()

    @override_settings(
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=100,
)
    def test_repeated_valid_posts_remain_request_bounded(self):
        self._login()
        requirements = self._permitted_requirements()
        before = self._model_counts()
        provider = MagicMock(side_effect=_valid_provider_output)
        with patch(COMPOSE_PATH, return_value=provider) as compose:
            first = self.client.post(
                self.url,
                {
                    "requirements": requirements,
                    "generate_explanation": "1",
                },
            )
            second = self.client.post(
                self.url,
                {
                    "requirements": requirements,
                    "generate_explanation": "1",
                },
            )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertIsNotNone(first.context["advisory_explanation"])
        self.assertIsNotNone(second.context["advisory_explanation"])
        self.assertEqual(compose.call_count, 2)
        self.assertEqual(provider.call_count, 2)
        self.assertEqual(self._model_counts(), before)
        self.assertNotIn("advisory_explanation", self.client.session)
        self.assertNotIn("evidence_alignment_summary", self.client.session)

    @override_settings(
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=100,
)
    def test_current_user_evidence_isolation(self):
        self._login()
        requirements = self._permitted_requirements()
        other = User.objects.create_user(
            username="s117p3_other",
            password="pass",
        )
        other_entry = self._create_entry(
            "OtherUserPrivateSkillXZ117",
            SkillEntry.EvidenceLevel.NO_EVIDENCE,
            user=other,
        )
        self.assertEqual(
            other_entry.evidence_level,
            SkillEntry.EvidenceLevel.NO_EVIDENCE,
        )
        captured: dict = {}

        def capturing_provider(payload):
            captured["payload"] = payload
            return _valid_provider_output(payload)

        provider = MagicMock(side_effect=capturing_provider)
        with patch(COMPOSE_PATH, return_value=provider):
            response = self.client.post(
                self.url,
                {
                    "requirements": requirements,
                    "generate_explanation": "1",
                },
            )
        self.assertEqual(response.status_code, 200)
        provider.assert_called_once()
        payload = captured["payload"]
        payload_text = repr(payload)
        self.assertNotIn(other_entry.skill_name, payload_text)
        self.assertNotIn(str(other_entry.id), payload_text)
        payload_evidence_levels = {
            requirement.get("matched_evidence_level")
            for requirement in payload["requirements"]
            if requirement.get("matched_evidence_level") is not None
        }
        self.assertNotIn(
            SkillEntry.EvidenceLevel.NO_EVIDENCE,
            payload_evidence_levels,
        )
        content = response.content.decode("utf-8")
        self.assertNotIn(other_entry.skill_name, content)
        other_edit_url = reverse("skill_ledger:edit", args=[other_entry.id])
        self.assertNotIn(other_edit_url, content)
        for req in payload["requirements"]:
            self.assertNotEqual(req.get("matched_skill_name"), other_entry.skill_name)
            self.assertNotEqual(
                req.get("matched_skill_entry_id"),
                other_entry.id,
            )

    @override_settings(
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
    AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=100,
)
    def test_csrf_enforcement(self):
        requirements = self._permitted_requirements()
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.login(username="s117p3_owner", password="pass")
        provider = MagicMock(side_effect=_valid_provider_output)
        with (
            patch(COMPOSE_PATH, return_value=provider) as compose,
            patch(BUILD_PAYLOAD_PATH) as build_payload,
        ):
            denied = csrf_client.post(
                self.url,
                {
                    "requirements": requirements,
                    "generate_explanation": "1",
                },
            )
        self.assertEqual(denied.status_code, 403)
        compose.assert_not_called()
        build_payload.assert_not_called()
        provider.assert_not_called()

        get_response = csrf_client.get(self.url)
        self.assertEqual(get_response.status_code, 200)
        csrf_token = csrf_client.cookies["csrftoken"].value
        with patch(COMPOSE_PATH, return_value=provider) as compose_ok:
            allowed = csrf_client.post(
                self.url,
                {
                    "csrfmiddlewaretoken": csrf_token,
                    "requirements": requirements,
                    "generate_explanation": "1",
                },
            )
        self.assertEqual(allowed.status_code, 200)
        self.assertTrue(allowed.context["form"].is_valid())
        self.assertTrue(allowed.context["analysis_performed"])
        compose_ok.assert_called_once()
        provider.assert_called_once()
        self.assertIsNotNone(allowed.context["advisory_explanation"])


class EvidenceAlignmentExplanationRequestGovernanceRouteTests(TestCase):
    """Sprint 118 Phase 2B: route-level request governance before composition."""

    def setUp(self):
        self.owner = User.objects.create_user(
            username="s118p2b_owner",
            password="pass",
        )
        self.url = reverse("skill_gaps:jd_gap_analysis")

    def _login(self, username="s118p2b_owner"):
        self.client.login(username=username, password="pass")

    def _create_entry(self, skill_name, evidence_level, user=None):
        return SkillEntry.objects.create(
            user=user or self.owner,
            skill_name=skill_name,
            category=SkillEntry.Category.PROGRAMMING,
            evidence_level=evidence_level,
            visibility=SkillEntry.Visibility.PRIVATE,
        )

    def _permitted_requirements(self, user=None):
        owner = user or self.owner
        SkillEntry.objects.create(
            user=owner,
            skill_name="Python",
            category=SkillEntry.Category.PROGRAMMING,
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
            visibility=SkillEntry.Visibility.PRIVATE,
        )
        SkillEntry.objects.create(
            user=owner,
            skill_name="Snowflake",
            category=SkillEntry.Category.PROGRAMMING,
            evidence_level=SkillEntry.EvidenceLevel.LEARNING_TARGET,
            visibility=SkillEntry.Visibility.PRIVATE,
        )
        return "Python\nSnowflake\nGraphQL"

    def test_get_never_reserves_governance(self):
        self._login()
        self._create_entry("Python", SkillEntry.EvidenceLevel.VERIFIED)
        with patch(RESERVE_PATH) as reserve:
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        reserve.assert_not_called()
        self.assertFalse(response.context["explanation_governance_blocked"])

    @override_settings(
        AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
        AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=100,
    )
    def test_standard_analysis_post_never_reserves_governance(self):
        self._login()
        requirements = self._permitted_requirements()
        with patch(RESERVE_PATH) as reserve:
            response = self.client.post(self.url, {"requirements": requirements})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["analysis_performed"])
        reserve.assert_not_called()
        self.assertFalse(response.context["explanation_governance_blocked"])

    @override_settings(
        AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
        AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=100,
    )
    def test_invalid_form_post_never_reserves_governance(self):
        self._login()
        with patch(RESERVE_PATH) as reserve:
            response = self.client.post(
                self.url,
                {"requirements": "", "generate_explanation": "1"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["analysis_performed"])
        reserve.assert_not_called()

    @override_settings(
        AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
        AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=100,
    )
    def test_non_permitted_outcome_never_reserves_governance(self):
        self._login()
        self._create_entry("Python", SkillEntry.EvidenceLevel.VERIFIED)
        with patch(RESERVE_PATH) as reserve:
            response = self.client.post(
                self.url,
                {
                    "requirements": "Senior Python",
                    "generate_explanation": "1",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["explanation_allowed"])
        reserve.assert_not_called()

    @override_settings(AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=False)
    def test_feature_disabled_forged_explanation_post_never_reserves_governance(self):
        self._login()
        requirements = self._permitted_requirements()
        with patch(RESERVE_PATH) as reserve:
            response = self.client.post(
                self.url,
                {
                    "requirements": requirements,
                    "generate_explanation": "1",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["explanation_feature_enabled"])
        reserve.assert_not_called()
        self.assertFalse(response.context["explanation_governance_blocked"])

    @override_settings(
        AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
        AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=100,
    )
    def test_valid_explicit_request_reserves_once_and_uses_non_telemetry_path(self):
        self._login()
        requirements = self._permitted_requirements()
        provider = MagicMock(side_effect=_valid_provider_output)
        with (
            patch(RESERVE_PATH, wraps=reserve_explanation_request) as reserve,
            patch(COMPOSE_PATH, return_value=provider) as compose,
        ):
            response = self.client.post(
                self.url,
                {
                    "requirements": requirements,
                    "generate_explanation": "1",
                },
            )
        self.assertEqual(response.status_code, 200)
        reserve.assert_called_once_with(self.owner)
        compose.assert_called_once()
        provider.assert_called_once()
        self.assertIsNotNone(response.context["advisory_explanation"])
        self.assertFalse(response.context["advisory_explanation_failed"])
        self.assertFalse(response.context["explanation_governance_blocked"])
        self.assertEqual(
            ExplanationRequestCounter.objects.get(user=self.owner).request_count,
            1,
        )

    @override_settings(
        AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
        AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=1,
    )
    def test_daily_limit_one_allows_first_and_blocks_second_before_composition(self):
        self._login()
        requirements = self._permitted_requirements()
        provider = MagicMock(side_effect=_valid_provider_output)
        with patch(COMPOSE_PATH, return_value=provider) as compose:
            first = self.client.post(
                self.url,
                {
                    "requirements": requirements,
                    "generate_explanation": "1",
                },
            )
            second = self.client.post(
                self.url,
                {
                    "requirements": requirements,
                    "generate_explanation": "1",
                },
            )
        self.assertEqual(first.status_code, 200)
        self.assertIsNotNone(first.context["advisory_explanation"])
        self.assertFalse(first.context["explanation_governance_blocked"])
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.context["explanation_governance_blocked"])
        self.assertIsNone(second.context["advisory_explanation"])
        self.assertFalse(second.context["advisory_explanation_failed"])
        self.assertEqual(compose.call_count, 1)
        self.assertEqual(
            ExplanationRequestCounter.objects.get(user=self.owner).request_count,
            1,
        )

    @override_settings(
        AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
        AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=1,
    )
    def test_governance_blocked_request_skips_payload_provider_and_validator(self):
        self._login()
        requirements = self._permitted_requirements()
        first_provider = MagicMock(side_effect=_valid_provider_output)
        with patch(COMPOSE_PATH, return_value=first_provider):
            self.client.post(
                self.url,
                {
                    "requirements": requirements,
                    "generate_explanation": "1",
                },
            )
        blocked_provider = MagicMock(side_effect=_valid_provider_output)
        with (
            patch(COMPOSE_PATH, return_value=blocked_provider) as compose,
            patch(BUILD_PAYLOAD_PATH) as build_payload,
            patch(VALIDATE_PATH) as validate_output,
        ):
            blocked = self.client.post(
                self.url,
                {
                    "requirements": requirements,
                    "generate_explanation": "1",
                },
            )
        self.assertTrue(blocked.context["explanation_governance_blocked"])
        compose.assert_not_called()
        build_payload.assert_not_called()
        validate_output.assert_not_called()
        blocked_provider.assert_not_called()

    @override_settings(
        AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
        AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=1,
    )
    def test_count_limit_denial_renders_exact_locked_wording_once(self):
        self._login()
        requirements = self._permitted_requirements()
        provider = MagicMock(side_effect=_valid_provider_output)
        with patch(COMPOSE_PATH, return_value=provider):
            self.client.post(
                self.url,
                {
                    "requirements": requirements,
                    "generate_explanation": "1",
                },
            )
            blocked = self.client.post(
                self.url,
                {
                    "requirements": requirements,
                    "generate_explanation": "1",
                },
            )
        content = blocked.content.decode("utf-8")
        self.assertEqual(content.count(GOVERNANCE_COUNT_LIMIT_WORDING), 1)
        self.assertNotContains(blocked, FALLBACK_STATEMENT)
        self.assertContains(blocked, "Evidence alignment summary")
        self.assertTrue(blocked.context["analysis_performed"])

    @override_settings(
        AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
        AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=0,
    )
    def test_invalid_governance_configuration_renders_generic_wording_provider_free(
        self,
    ):
        self._login()
        requirements = self._permitted_requirements()
        provider = MagicMock(side_effect=_valid_provider_output)
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
        self.assertTrue(response.context["explanation_governance_blocked"])
        self.assertEqual(
            response.context["explanation_governance_message"],
            GOVERNANCE_GENERIC_UNAVAILABLE_WORDING,
        )
        self.assertEqual(
            response.content.decode("utf-8").count(
                GOVERNANCE_GENERIC_UNAVAILABLE_WORDING
            ),
            1,
        )
        self.assertIsNone(response.context["advisory_explanation"])
        self.assertFalse(response.context["advisory_explanation_failed"])
        compose.assert_not_called()
        build_payload.assert_not_called()
        provider.assert_not_called()
        self.assertEqual(ExplanationRequestCounter.objects.count(), 0)

    @override_settings(
        AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
        AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=100,
    )
    def test_storage_unavailable_renders_generic_wording_provider_free(self):
        self._login()
        requirements = self._permitted_requirements()
        provider = MagicMock(side_effect=_valid_provider_output)
        decision = ExplanationRequestReservationDecision(
            allowed=False,
            reason_code=REASON_GOVERNANCE_STORAGE_UNAVAILABLE,
        )
        with (
            patch(RESERVE_PATH, return_value=decision) as reserve,
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
        reserve.assert_called_once()
        self.assertTrue(response.context["explanation_governance_blocked"])
        self.assertEqual(
            response.context["explanation_governance_message"],
            GOVERNANCE_GENERIC_UNAVAILABLE_WORDING,
        )
        self.assertNotContains(response, FALLBACK_STATEMENT)
        compose.assert_not_called()
        build_payload.assert_not_called()
        provider.assert_not_called()

    @override_settings(
        AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
        AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=1,
    )
    def test_internal_reason_codes_and_quota_details_are_not_rendered(self):
        self._login()
        requirements = self._permitted_requirements()
        provider = MagicMock(side_effect=_valid_provider_output)
        with patch(COMPOSE_PATH, return_value=provider):
            self.client.post(
                self.url,
                {
                    "requirements": requirements,
                    "generate_explanation": "1",
                },
            )
            blocked = self.client.post(
                self.url,
                {
                    "requirements": requirements,
                    "generate_explanation": "1",
                },
            )
        content = blocked.content.decode("utf-8")
        for marker in (
            REASON_COUNT_LIMIT_REACHED,
            REASON_GOVERNANCE_CONFIGURATION_INVALID,
            REASON_GOVERNANCE_STORAGE_UNAVAILABLE,
            "request_count",
            "DAILY_REQUEST_LIMIT",
            "window_date",
            "reset",
            "remaining",
        ):
            self.assertNotIn(marker, content)
        self.assertNotIn("1", blocked.context["explanation_governance_message"])

    @override_settings(
        AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
        AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=5,
    )
    def test_provider_failure_after_reservation_consumes_quota_and_uses_fallback(self):
        self._login()
        requirements = self._permitted_requirements()
        provider = MagicMock(side_effect=RuntimeError("provider-boom-s118p2b"))
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
        self.assertFalse(response.context["explanation_governance_blocked"])
        self.assertTrue(response.context["advisory_explanation_failed"])
        self.assertIsNone(response.context["advisory_explanation"])
        self.assertContains(response, FALLBACK_STATEMENT)
        self.assertNotContains(response, GOVERNANCE_COUNT_LIMIT_WORDING)
        self.assertNotContains(response, GOVERNANCE_GENERIC_UNAVAILABLE_WORDING)
        self.assertEqual(
            ExplanationRequestCounter.objects.get(user=self.owner).request_count,
            1,
        )
        self.assertNotIn("provider-boom-s118p2b", response.content.decode("utf-8"))

    @override_settings(
        AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED=True,
        AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=1,
    )
    def test_route_level_quota_is_isolated_between_authenticated_users(self):
        other = User.objects.create_user(
            username="s118p2b_other",
            password="pass",
        )
        owner_requirements = self._permitted_requirements(user=self.owner)
        other_requirements = self._permitted_requirements(user=other)
        provider = MagicMock(side_effect=_valid_provider_output)

        self._login("s118p2b_owner")
        with patch(COMPOSE_PATH, return_value=provider):
            owner_first = self.client.post(
                self.url,
                {
                    "requirements": owner_requirements,
                    "generate_explanation": "1",
                },
            )
            owner_second = self.client.post(
                self.url,
                {
                    "requirements": owner_requirements,
                    "generate_explanation": "1",
                },
            )
        self.assertIsNotNone(owner_first.context["advisory_explanation"])
        self.assertTrue(owner_second.context["explanation_governance_blocked"])

        self.client.logout()
        self._login("s118p2b_other")
        with patch(COMPOSE_PATH, return_value=provider):
            other_first = self.client.post(
                self.url,
                {
                    "requirements": other_requirements,
                    "generate_explanation": "1",
                },
            )
        self.assertIsNotNone(other_first.context["advisory_explanation"])
        self.assertFalse(other_first.context["explanation_governance_blocked"])
        self.assertEqual(
            ExplanationRequestCounter.objects.get(user=self.owner).request_count,
            1,
        )
        self.assertEqual(
            ExplanationRequestCounter.objects.get(user=other).request_count,
            1,
        )

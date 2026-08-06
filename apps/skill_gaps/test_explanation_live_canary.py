"""Sprint 116 synthetic live-canary contract and runner tests."""

from __future__ import annotations

import hashlib
import inspect
import json
import re
from dataclasses import FrozenInstanceError, replace
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from apps.ai_agents import claude_provider as claude_provider_module
from apps.ai_agents import provider_factory as provider_factory_module
from apps.ai_agents.claude_provider import (
    CLAUDE_EVIDENCE_ALIGNMENT_MAX_TOKENS,
    CLAUDE_MODEL,
    ClaudeTelemetryResult,
    build_evidence_alignment_messages_create_kwargs,
    hash_request_payload,
    make_claude_cv_tailoring_telemetry_provider,
    make_claude_evidence_alignment_explanation_provider,
    make_claude_evidence_alignment_explanation_telemetry_provider,
    make_claude_fit_telemetry_provider,
)
from apps.ai_agents.provider_factory import (
    compose_evidence_alignment_explanation_telemetry_provider,
)
from apps.skill_gaps.explanation_output_validator import (
    validate_evidence_alignment_explanation_output,
)
from apps.skill_gaps.live_evaluation import (
    CANARY_CONTRACT_SCHEMA_VERSION,
    CONTRACT_MANIFEST_SHA256,
    canonical_manifest_bytes,
    contract_manifest_sha256,
    get_authoritative_canary_case,
    get_canary_manifest,
    validate_canary_contract,
)
from apps.skill_gaps.live_evaluation import (
    evidence_alignment_explanation_canary_contract as contract_module,
)
from apps.skill_gaps.live_evaluation import (
    evidence_alignment_explanation_canary_runner as runner_module,
)
from apps.skill_gaps.live_evaluation.evidence_alignment_explanation_canary_runner import (
    EvidenceAlignmentCanaryOutcome,
    EvidenceAlignmentCanaryRunResult,
    run_evidence_alignment_explanation_canary,
)


class EvidenceAlignmentExplanationCanaryContractTests(SimpleTestCase):
    """Validate the immutable, offline contract for one synthetic case."""

    def test_authoritative_case_has_locked_identity(self):
        case = get_authoritative_canary_case()

        self.assertEqual(
            case.case_id,
            "sprint-116-evidence-alignment-explanation-canary-001",
        )
        self.assertEqual(
            case.surface,
            "evidence_alignment_advisory_explanation",
        )
        self.assertEqual(case.schema_version, CANARY_CONTRACT_SCHEMA_VERSION)

    def test_verified_skills_are_exactly_locked_values(self):
        case = get_authoritative_canary_case()

        self.assertEqual(case.verified_skills, ("Python", "Django", "SQL"))

    def test_snowflake_is_only_learning_target_skill(self):
        case = get_authoritative_canary_case()

        self.assertEqual(case.learning_target_skills, ("Snowflake",))
        self.assertNotIn("Snowflake", case.verified_skills)
        self.assertNotIn("Snowflake", case.unmatched_requirements)

    def test_graphql_is_only_unmatched_requirement(self):
        case = get_authoritative_canary_case()

        self.assertEqual(case.unmatched_requirements, ("GraphQL",))
        self.assertNotIn("GraphQL", case.verified_skills)
        self.assertNotIn("GraphQL", case.learning_target_skills)

    def test_expected_outcome_is_some_requirements_verified(self):
        case = get_authoritative_canary_case()

        self.assertEqual(
            case.expected_deterministic_outcome,
            "SOME_REQUIREMENTS_VERIFIED",
        )

    def test_manifest_contains_only_json_compatible_contract_values(self):
        manifest = get_canary_manifest()

        self.assertEqual(
            set(manifest),
            {
                "case_id",
                "expected_deterministic_outcome",
                "learning_target_skills",
                "schema_version",
                "surface",
                "unmatched_requirements",
                "verified_skills",
            },
        )
        self.assertIsInstance(json.dumps(manifest), str)

    def test_manifest_serialisation_is_deterministic(self):
        first = canonical_manifest_bytes()
        second = canonical_manifest_bytes()

        self.assertEqual(first, second)
        self.assertNotIn(b" ", first)
        self.assertNotIn(b"\r", first)

    def test_manifest_hash_is_stable_and_authoritative(self):
        first = contract_manifest_sha256()
        second = contract_manifest_sha256()

        self.assertEqual(first, second)
        self.assertEqual(first, CONTRACT_MANIFEST_SHA256)

    def test_manifest_hash_is_lowercase_sha256_hexadecimal(self):
        digest = contract_manifest_sha256()

        self.assertEqual(len(digest), 64)
        self.assertIsNotNone(re.fullmatch(r"[0-9a-f]{64}", digest))

    def test_equivalent_dictionary_order_has_same_canonical_bytes_and_hash(self):
        manifest = get_canary_manifest()
        reversed_manifest = dict(reversed(tuple(manifest.items())))

        self.assertEqual(
            canonical_manifest_bytes(manifest),
            canonical_manifest_bytes(reversed_manifest),
        )
        self.assertEqual(
            contract_manifest_sha256(manifest),
            contract_manifest_sha256(reversed_manifest),
        )

    def test_evidence_categories_do_not_overlap(self):
        case = get_authoritative_canary_case()

        self.assertFalse(
            set(case.verified_skills) & set(case.learning_target_skills)
        )
        self.assertFalse(
            set(case.verified_skills) & set(case.unmatched_requirements)
        )
        self.assertFalse(
            set(case.learning_target_skills) & set(case.unmatched_requirements)
        )
        overlapping = replace(case, learning_target_skills=("Python",))
        with self.assertRaisesMessage(
            ValueError,
            "evidence categories must not overlap.",
        ):
            validate_canary_contract(overlapping)

    def test_verified_and_unmatched_overlap_is_rejected(self):
        overlapping = replace(
            get_authoritative_canary_case(),
            unmatched_requirements=("Python",),
        )

        with self.assertRaisesMessage(
            ValueError,
            "evidence categories must not overlap.",
        ):
            validate_canary_contract(overlapping)

    def test_learning_target_and_unmatched_overlap_is_rejected(self):
        overlapping = replace(
            get_authoritative_canary_case(),
            unmatched_requirements=("Snowflake",),
        )

        with self.assertRaisesMessage(
            ValueError,
            "evidence categories must not overlap.",
        ):
            validate_canary_contract(overlapping)

    def test_duplicate_skill_values_are_rejected(self):
        duplicate = replace(
            get_authoritative_canary_case(),
            verified_skills=("Python", "Python", "SQL"),
        )

        with self.assertRaisesMessage(
            ValueError,
            "verified_skills must not contain duplicates.",
        ):
            validate_canary_contract(duplicate)

    def test_empty_skill_values_are_rejected(self):
        invalid = replace(
            get_authoritative_canary_case(),
            learning_target_skills=("",),
        )

        with self.assertRaisesMessage(
            ValueError,
            "learning_target_skills must contain non-empty strings.",
        ):
            validate_canary_contract(invalid)

    def test_unexpected_outcome_is_rejected(self):
        invalid = replace(
            get_authoritative_canary_case(),
            expected_deterministic_outcome="ALL_REQUIREMENTS_VERIFIED",
        )

        with self.assertRaisesMessage(
            ValueError,
            "unexpected deterministic outcome.",
        ):
            validate_canary_contract(invalid)

    def test_contract_is_immutable(self):
        case = get_authoritative_canary_case()

        with self.assertRaises(FrozenInstanceError):
            case.case_id = "changed"  # type: ignore[misc]

    def test_mutable_skill_collections_are_rejected(self):
        invalid = replace(
            get_authoritative_canary_case(),
            verified_skills=["Python", "Django", "SQL"],  # type: ignore[arg-type]
        )

        with self.assertRaisesMessage(
            ValueError,
            "verified_skills must be an immutable tuple.",
        ):
            validate_canary_contract(invalid)

    def test_locked_schema_case_and_surface_are_validated(self):
        case = get_authoritative_canary_case()
        invalid_values = (
            (
                replace(case, schema_version="unsupported"),
                "unsupported canary contract schema version.",
            ),
            (
                replace(case, case_id="unexpected"),
                "unexpected canary case ID.",
            ),
            (
                replace(case, surface="unexpected"),
                "unexpected canary surface.",
            ),
        )

        for invalid, message in invalid_values:
            with self.subTest(message=message):
                with self.assertRaisesMessage(ValueError, message):
                    validate_canary_contract(invalid)

    def test_contract_generation_performs_no_database_query(self):
        with patch("django.db.backends.utils.CursorWrapper.execute") as execute:
            get_authoritative_canary_case()
            get_canary_manifest()
            canonical_manifest_bytes()
            contract_manifest_sha256()

        execute.assert_not_called()

    def test_contract_imports_and_calls_no_network_or_provider_code(self):
        direct_modules = {
            value.__name__
            for value in vars(contract_module).values()
            if isinstance(value, ModuleType)
        }

        with patch("socket.create_connection") as create_connection:
            validate_canary_contract(get_authoritative_canary_case())
            contract_manifest_sha256()

        self.assertEqual(direct_modules, {"hashlib", "json"})
        create_connection.assert_not_called()


_DEFAULT_PARSED = object()


def _valid_canary_output(payload: dict) -> dict:
    verified = []
    development = []
    missing = []
    for requirement in payload["requirements"]:
        index = requirement["requirement_index"]
        skill = requirement["matched_skill_name"]
        classification = requirement["classification"]
        if classification == "VERIFIED_MATCH":
            verified.append(
                {
                    "requirement_index": index,
                    "skill_names": [skill],
                    "explanation": f"{skill} matches verified evidence.",
                }
            )
        elif classification == "LEARNING_TARGET_MATCH":
            development.append(
                {
                    "requirement_index": index,
                    "skill_names": [skill],
                    "evidence_level": "LEARNING_TARGET",
                    "explanation": f"{skill} is recorded as a learning target.",
                }
            )
        else:
            missing.append(
                {
                    "requirement_index": index,
                    "explanation": "No current evidence supports this requirement.",
                }
            )
    return {
        "summary": "Synthetic evidence alignment uses supplied records only.",
        "verified_evidence": verified,
        "development_evidence": development,
        "missing_evidence": missing,
    }


_DEFAULT_RAW_RESPONSE_HASH = object()


def _canary_telemetry(
    payload: dict,
    *,
    parsed_payload: object = _DEFAULT_PARSED,
    returned_model: object = CLAUDE_MODEL,
    stop_reason: object = "end_turn",
    input_tokens: object = 120,
    output_tokens: object = 48,
    latency_ms: object = 9,
    request_payload_hash: str | None = None,
    serialised_raw_response: object = '{"synthetic":"response"}',
    raw_response_hash: object = _DEFAULT_RAW_RESPONSE_HASH,
    parse_error_category: str | None = None,
) -> ClaudeTelemetryResult:
    request_kwargs = build_evidence_alignment_messages_create_kwargs(payload)
    parsed = (
        _valid_canary_output(payload)
        if parsed_payload is _DEFAULT_PARSED
        else parsed_payload
    )
    if raw_response_hash is _DEFAULT_RAW_RESPONSE_HASH:
        if isinstance(serialised_raw_response, str) and serialised_raw_response:
            resolved_raw_hash = hashlib.sha256(
                serialised_raw_response.encode("utf-8")
            ).hexdigest()
        else:
            resolved_raw_hash = ""
    else:
        resolved_raw_hash = raw_response_hash
    return ClaudeTelemetryResult(
        parsed_payload=parsed,  # type: ignore[arg-type]
        returned_model=returned_model,  # type: ignore[arg-type]
        stop_reason=stop_reason,  # type: ignore[arg-type]
        input_tokens=input_tokens,  # type: ignore[arg-type]
        output_tokens=output_tokens,  # type: ignore[arg-type]
        raw_request_id="req_synthetic",
        latency_ms=latency_ms,  # type: ignore[arg-type]
        request_payload_hash=(
            request_payload_hash
            if request_payload_hash is not None
            else hash_request_payload(request_kwargs)
        ),
        serialised_raw_response=serialised_raw_response,  # type: ignore[arg-type]
        raw_response_hash=resolved_raw_hash,  # type: ignore[arg-type]
        parse_error_category=parse_error_category,
    )


class EvidenceAlignmentExplanationCanaryRunnerTests(SimpleTestCase):
    """Offline tests for the one-call canary runner and telemetry seam."""

    def setUp(self):
        payload, request_kwargs, _outcome = (
            runner_module._build_authoritative_payload_and_request()
        )
        self.payload = payload
        self.expected_contract_hash = CONTRACT_MANIFEST_SHA256
        self.expected_request_hash = hash_request_payload(request_kwargs)

    def _run(self, provider) -> EvidenceAlignmentCanaryRunResult:
        return run_evidence_alignment_explanation_canary(
            telemetry_provider=provider,
            expected_contract_manifest_sha256=self.expected_contract_hash,
            expected_request_payload_sha256=self.expected_request_hash,
        )

    def test_accepted_mocked_provider_path(self):
        result = self._run(lambda payload: _canary_telemetry(payload))

        self.assertEqual(
            result.outcome,
            EvidenceAlignmentCanaryOutcome.INTEGRATION_SUCCESS_OUTPUT_ACCEPTED,
        )
        self.assertEqual(result.parser_status, "accepted")
        self.assertEqual(result.validator_status, "accepted")
        self.assertIsNotNone(result.accepted_explanation_summary)

    def test_safely_rejected_mocked_provider_path(self):
        invalid = _valid_canary_output(self.payload)
        invalid.pop("missing_evidence")
        result = self._run(
            lambda payload: _canary_telemetry(payload, parsed_payload=invalid)
        )

        self.assertEqual(result.validator_status, "rejected")
        self.assertEqual(result.validator_rejection_code, "SCHEMA_MISMATCH")
        self.assertIsNone(result.accepted_explanation_summary)

    def test_safe_rejection_uses_control_pass_outcome(self):
        invalid = _valid_canary_output(self.payload)
        invalid["unexpected"] = "field"

        result = self._run(
            lambda payload: _canary_telemetry(payload, parsed_payload=invalid)
        )

        self.assertEqual(
            result.outcome,
            EvidenceAlignmentCanaryOutcome.CONTROL_PASS_OUTPUT_SAFELY_REJECTED,
        )

    def test_provider_exception_produces_provider_failure(self):
        provider = MagicMock(side_effect=RuntimeError("synthetic provider failure"))

        result = self._run(provider)

        self.assertEqual(
            result.outcome,
            EvidenceAlignmentCanaryOutcome.PROVIDER_FAILURE,
        )
        self.assertEqual(result.safe_error_category, "provider_boundary_failure")

    def test_provider_called_exactly_once_on_accepted_path(self):
        provider = MagicMock(side_effect=_canary_telemetry)

        result = self._run(provider)

        provider.assert_called_once()
        self.assertEqual(result.attempted_call_count, 1)
        self.assertEqual(result.completed_call_count, 1)

    def test_provider_called_exactly_once_on_rejected_path(self):
        invalid = _valid_canary_output(self.payload)
        invalid.pop("summary")
        provider = MagicMock(
            side_effect=lambda payload: _canary_telemetry(
                payload,
                parsed_payload=invalid,
            )
        )

        result = self._run(provider)

        provider.assert_called_once()
        self.assertEqual(result.attempted_call_count, 1)
        self.assertEqual(result.completed_call_count, 1)

    def test_provider_called_exactly_once_on_provider_exception(self):
        provider = MagicMock(side_effect=TimeoutError("synthetic timeout"))

        result = self._run(provider)

        provider.assert_called_once()
        self.assertEqual(result.attempted_call_count, 1)
        self.assertEqual(result.completed_call_count, 0)

    def test_no_retry_after_parser_failure(self):
        provider = MagicMock(
            side_effect=lambda payload: _canary_telemetry(
                payload,
                parsed_payload=None,
                parse_error_category="parser_rejection",
            )
        )

        result = self._run(provider)

        provider.assert_called_once()
        self.assertEqual(result.outcome, EvidenceAlignmentCanaryOutcome.INTEGRITY_FAILURE)
        self.assertEqual(result.parser_status, "rejected")

    def test_no_retry_after_validator_rejection(self):
        invalid = _valid_canary_output(self.payload)
        invalid.pop("missing_evidence")
        provider = MagicMock(
            side_effect=lambda payload: _canary_telemetry(
                payload,
                parsed_payload=invalid,
            )
        )

        result = self._run(provider)

        provider.assert_called_once()
        self.assertEqual(
            result.outcome,
            EvidenceAlignmentCanaryOutcome.CONTROL_PASS_OUTPUT_SAFELY_REJECTED,
        )

    def test_contract_manifest_mismatch_blocks_provider(self):
        provider = MagicMock()

        result = run_evidence_alignment_explanation_canary(
            telemetry_provider=provider,
            expected_contract_manifest_sha256="0" * 64,
            expected_request_payload_sha256=self.expected_request_hash,
        )

        provider.assert_not_called()
        self.assertFalse(result.contract_manifest_hash_match)
        self.assertEqual(result.attempted_call_count, 0)

    def test_request_payload_mismatch_blocks_provider(self):
        provider = MagicMock()

        result = run_evidence_alignment_explanation_canary(
            telemetry_provider=provider,
            expected_contract_manifest_sha256=self.expected_contract_hash,
            expected_request_payload_sha256="0" * 64,
        )

        provider.assert_not_called()
        self.assertFalse(result.request_payload_hash_match)
        self.assertEqual(result.attempted_call_count, 0)

    def test_manifest_and_request_hashes_are_independently_calculated(self):
        result = self._run(lambda payload: _canary_telemetry(payload))

        self.assertEqual(
            result.contract_manifest_sha256,
            contract_manifest_sha256(),
        )
        self.assertEqual(result.request_payload_sha256, self.expected_request_hash)

    def test_manifest_and_request_hashes_are_distinct(self):
        result = self._run(lambda payload: _canary_telemetry(payload))

        self.assertTrue(result.hashes_are_distinct)
        self.assertNotEqual(
            result.contract_manifest_sha256,
            result.request_payload_sha256,
        )

    def test_production_payload_builder_is_invoked(self):
        real_builder = runner_module.build_evidence_alignment_explanation_payload
        with patch.object(
            runner_module,
            "build_evidence_alignment_explanation_payload",
            wraps=real_builder,
        ) as builder:
            result = self._run(lambda payload: _canary_telemetry(payload))

        builder.assert_called_once()
        self.assertEqual(
            result.outcome,
            EvidenceAlignmentCanaryOutcome.INTEGRATION_SUCCESS_OUTPUT_ACCEPTED,
        )

    def test_production_request_builder_is_invoked(self):
        real_builder = runner_module.build_evidence_alignment_messages_create_kwargs
        with patch.object(
            runner_module,
            "build_evidence_alignment_messages_create_kwargs",
            wraps=real_builder,
        ) as builder:
            self._run(lambda payload: _canary_telemetry(payload))

        builder.assert_called_once()

    def test_production_validator_is_invoked(self):
        with patch.object(
            runner_module,
            "validate_evidence_alignment_explanation_output",
            wraps=validate_evidence_alignment_explanation_output,
        ) as validator:
            result = self._run(lambda payload: _canary_telemetry(payload))

        validator.assert_called_once()
        self.assertEqual(result.validator_status, "accepted")

    def test_locked_model_is_enforced_before_call(self):
        real_builder = runner_module.build_evidence_alignment_messages_create_kwargs

        def wrong_model(payload):
            kwargs = real_builder(payload)
            kwargs["model"] = "unexpected-model"
            return kwargs

        provider = MagicMock()
        with patch.object(
            runner_module,
            "build_evidence_alignment_messages_create_kwargs",
            side_effect=wrong_model,
        ):
            result = self._run(provider)

        provider.assert_not_called()
        self.assertEqual(result.outcome, EvidenceAlignmentCanaryOutcome.HARNESS_DEFECT)
        self.assertEqual(result.safe_error_category, "request_model_mismatch")

    def test_512_token_cap_is_enforced_from_production_request(self):
        result = self._run(lambda payload: _canary_telemetry(payload))

        self.assertEqual(CLAUDE_EVIDENCE_ALIGNMENT_MAX_TOKENS, 512)
        self.assertEqual(result.output_token_cap, 512)

    def test_competing_token_cap_blocks_before_provider_call(self):
        real_builder = runner_module.build_evidence_alignment_messages_create_kwargs

        def wrong_cap(payload):
            kwargs = real_builder(payload)
            kwargs["max_tokens"] = 513
            return kwargs

        provider = MagicMock()
        with patch.object(
            runner_module,
            "build_evidence_alignment_messages_create_kwargs",
            side_effect=wrong_cap,
        ):
            result = self._run(provider)

        provider.assert_not_called()
        self.assertEqual(result.outcome, EvidenceAlignmentCanaryOutcome.HARNESS_DEFECT)
        self.assertEqual(result.safe_error_category, "request_token_cap_mismatch")

    def test_returned_model_mismatch_produces_integrity_failure(self):
        result = self._run(
            lambda payload: _canary_telemetry(
                payload,
                returned_model="unexpected-model",
            )
        )

        self.assertEqual(result.outcome, EvidenceAlignmentCanaryOutcome.INTEGRITY_FAILURE)
        self.assertEqual(result.safe_error_category, "returned_model_mismatch")

    def test_missing_token_usage_produces_integrity_failure(self):
        result = self._run(
            lambda payload: _canary_telemetry(payload, input_tokens=None)
        )

        self.assertEqual(result.outcome, EvidenceAlignmentCanaryOutcome.INTEGRITY_FAILURE)
        self.assertEqual(result.safe_error_category, "input_tokens_invalid")

    def test_negative_token_count_produces_integrity_failure(self):
        result = self._run(
            lambda payload: _canary_telemetry(payload, output_tokens=-1)
        )

        self.assertEqual(result.outcome, EvidenceAlignmentCanaryOutcome.INTEGRITY_FAILURE)
        self.assertEqual(result.safe_error_category, "output_tokens_invalid")

    def test_missing_stop_reason_produces_integrity_failure(self):
        result = self._run(
            lambda payload: _canary_telemetry(payload, stop_reason=None)
        )

        self.assertEqual(result.outcome, EvidenceAlignmentCanaryOutcome.INTEGRITY_FAILURE)
        self.assertEqual(result.safe_error_category, "stop_reason_invalid")

    def test_malformed_latency_produces_integrity_failure(self):
        result = self._run(
            lambda payload: _canary_telemetry(payload, latency_ms="9")
        )

        self.assertEqual(result.outcome, EvidenceAlignmentCanaryOutcome.INTEGRITY_FAILURE)
        self.assertEqual(result.safe_error_category, "latency_invalid")

    def test_malformed_request_hash_produces_integrity_failure(self):
        result = self._run(
            lambda payload: _canary_telemetry(
                payload,
                request_payload_hash="not-a-hash",
            )
        )

        self.assertEqual(result.outcome, EvidenceAlignmentCanaryOutcome.INTEGRITY_FAILURE)
        self.assertEqual(
            result.safe_error_category,
            "telemetry_request_hash_invalid",
        )

    def test_raw_response_is_not_present_in_safe_result(self):
        serialised = '{"synthetic":"known-raw-body"}'
        expected_digest = hashlib.sha256(serialised.encode("utf-8")).hexdigest()
        result = self._run(
            lambda payload: _canary_telemetry(
                payload,
                serialised_raw_response=serialised,
            )
        )

        self.assertEqual(
            result.outcome,
            EvidenceAlignmentCanaryOutcome.INTEGRATION_SUCCESS_OUTPUT_ACCEPTED,
        )
        self.assertFalse(hasattr(result, "serialised_raw_response"))
        self.assertFalse(hasattr(result, "raw_response_hash"))
        self.assertFalse(hasattr(result, "raw_request_id"))
        self.assertNotIn(serialised, repr(result))
        self.assertNotIn("req_synthetic", repr(result))
        self.assertEqual(result.raw_response_sha256, expected_digest)
        self.assertNotIn(
            "serialised_raw_response",
            EvidenceAlignmentCanaryRunResult.__dataclass_fields__,
        )
        self.assertNotIn(
            "raw_request_id",
            EvidenceAlignmentCanaryRunResult.__dataclass_fields__,
        )
        self.assertNotIn(
            "raw_response_hash",
            EvidenceAlignmentCanaryRunResult.__dataclass_fields__,
        )

    def test_raw_response_hash_is_independently_verified_and_exposed(self):
        serialised = '{"synthetic":"independent-digest-fixture"}'
        expected_digest = hashlib.sha256(serialised.encode("utf-8")).hexdigest()
        result = self._run(
            lambda payload: _canary_telemetry(
                payload,
                serialised_raw_response=serialised,
                raw_response_hash=expected_digest,
            )
        )

        self.assertEqual(
            result.outcome,
            EvidenceAlignmentCanaryOutcome.INTEGRATION_SUCCESS_OUTPUT_ACCEPTED,
        )
        self.assertEqual(result.raw_response_sha256, expected_digest)
        self.assertNotIn(serialised, repr(result))
        self.assertFalse(hasattr(result, "serialised_raw_response"))
        self.assertFalse(hasattr(result, "raw_request_id"))
        self.assertNotIn("req_synthetic", repr(result))

    def test_raw_response_hash_mismatch_produces_integrity_failure(self):
        calls = {"count": 0}
        serialised = '{"synthetic":"mismatch-fixture"}'
        mismatched = "a" * 64

        def provider(payload):
            calls["count"] += 1
            return _canary_telemetry(
                payload,
                serialised_raw_response=serialised,
                raw_response_hash=mismatched,
            )

        result = self._run(provider)

        self.assertEqual(result.outcome, EvidenceAlignmentCanaryOutcome.INTEGRITY_FAILURE)
        self.assertEqual(result.safe_error_category, "raw_response_hash_mismatch")
        self.assertEqual(calls["count"], 1)
        self.assertEqual(result.attempted_call_count, 1)
        self.assertEqual(result.completed_call_count, 1)
        self.assertEqual(
            result.raw_response_sha256,
            hashlib.sha256(serialised.encode("utf-8")).hexdigest(),
        )
        self.assertNotIn(serialised, repr(result))
        self.assertNotEqual(result.raw_response_sha256, mismatched)
    def test_no_database_query_or_write_occurs(self):
        with patch("django.db.backends.utils.CursorWrapper.execute") as execute:
            result = self._run(lambda payload: _canary_telemetry(payload))

        execute.assert_not_called()
        self.assertEqual(result.persistence_count, 0)

    def test_no_settings_or_environment_read_occurs_in_runner(self):
        source = inspect.getsource(runner_module)

        self.assertNotIn("django.conf", source)
        self.assertNotIn("settings.", source)
        self.assertNotIn("os.environ", source)
        self.assertNotIn("os.getenv", source)

    def test_existing_dict_provider_behavior_remains_unchanged(self):
        expected = _valid_canary_output(self.payload)
        client = SimpleNamespace()
        with (
            patch.object(claude_provider_module, "_new_client", return_value=client),
            patch.object(
                claude_provider_module,
                "_execute_messages_create",
                return_value=(SimpleNamespace(), 3),
            ),
            patch.object(
                claude_provider_module,
                "_parse_claude_response",
                return_value=expected,
            ),
        ):
            provider = make_claude_evidence_alignment_explanation_provider("key")
            result = provider(self.payload)

        self.assertEqual(result, expected)
        self.assertIsInstance(result, dict)

    def test_fit_scoring_telemetry_provider_remains_shared(self):
        client = SimpleNamespace()
        telemetry = _canary_telemetry(self.payload)
        with (
            patch.object(claude_provider_module, "_new_client", return_value=client),
            patch.object(
                claude_provider_module,
                "_execute_messages_create",
                return_value=(SimpleNamespace(), 4),
            ),
            patch.object(
                claude_provider_module,
                "_build_telemetry_result",
                return_value=telemetry,
            ) as result_builder,
        ):
            provider = make_claude_fit_telemetry_provider("key")
            self.assertIs(provider({"job": "synthetic"}), telemetry)

        result_builder.assert_called_once()

    def test_cv_tailoring_telemetry_provider_remains_shared(self):
        client = SimpleNamespace()
        telemetry = _canary_telemetry(self.payload)
        with (
            patch.object(claude_provider_module, "_new_client", return_value=client),
            patch.object(
                claude_provider_module,
                "_execute_messages_create",
                return_value=(SimpleNamespace(), 4),
            ),
            patch.object(
                claude_provider_module,
                "_build_telemetry_result",
                return_value=telemetry,
            ) as result_builder,
        ):
            provider = make_claude_cv_tailoring_telemetry_provider("key")
            self.assertIs(provider({"cv_evidence": []}), telemetry)

        result_builder.assert_called_once()

    @override_settings(
        AI_EXPLANATION_PROVIDER="live",
        ANTHROPIC_API_KEY="synthetic-key",
    )
    def test_provider_factory_remains_sole_api_key_boundary(self):
        sentinel = MagicMock()
        with patch.object(
            provider_factory_module,
            "make_claude_evidence_alignment_explanation_telemetry_provider",
            return_value=sentinel,
        ) as factory:
            composed = compose_evidence_alignment_explanation_telemetry_provider()

        self.assertIs(composed, sentinel)
        factory.assert_called_once_with("synthetic-key")
        self.assertNotIn("_api_key", inspect.getsource(runner_module))

    @override_settings(
        AI_EXPLANATION_PROVIDER="mock",
        ANTHROPIC_API_KEY="synthetic-key",
    )
    def test_provider_factory_returns_none_when_live_mode_is_absent(self):
        with patch.object(
            provider_factory_module,
            "make_claude_evidence_alignment_explanation_telemetry_provider",
        ) as factory:
            composed = compose_evidence_alignment_explanation_telemetry_provider()

        self.assertIsNone(composed)
        factory.assert_not_called()

    def test_direct_claude_client_construction_remains_confined(self):
        self.assertIn(
            "anthropic.Anthropic(",
            inspect.getsource(claude_provider_module),
        )
        self.assertNotIn("anthropic.Anthropic(", inspect.getsource(runner_module))
        self.assertNotIn(
            "anthropic.Anthropic(",
            inspect.getsource(provider_factory_module),
        )

    def test_evidence_alignment_telemetry_seam_reuses_shared_helpers(self):
        client = SimpleNamespace()
        response = SimpleNamespace()
        telemetry = _canary_telemetry(self.payload)
        request_kwargs = build_evidence_alignment_messages_create_kwargs(self.payload)
        with (
            patch.object(claude_provider_module, "_new_client", return_value=client),
            patch.object(
                claude_provider_module,
                "build_evidence_alignment_messages_create_kwargs",
                return_value=request_kwargs,
            ) as request_builder,
            patch.object(
                claude_provider_module,
                "_execute_messages_create",
                return_value=(response, 7),
            ) as execute,
            patch.object(
                claude_provider_module,
                "_build_telemetry_result",
                return_value=telemetry,
            ) as result_builder,
        ):
            provider = (
                make_claude_evidence_alignment_explanation_telemetry_provider("key")
            )
            result = provider(self.payload)

        self.assertIs(result, telemetry)
        request_builder.assert_called_once_with(self.payload)
        execute.assert_called_once_with(client, request_kwargs)
        result_builder.assert_called_once_with(
            response,
            request_kwargs=request_kwargs,
            latency_ms=7,
        )

    def test_generation_configuration_is_recorded_without_invented_values(self):
        request_kwargs = build_evidence_alignment_messages_create_kwargs(self.payload)
        for key in ("temperature", "top_p", "top_k", "thinking"):
            self.assertNotIn(key, request_kwargs)

        result = self._run(lambda payload: _canary_telemetry(payload))

        self.assertEqual(
            result.outcome,
            EvidenceAlignmentCanaryOutcome.INTEGRATION_SUCCESS_OUTPUT_ACCEPTED,
        )
        self.assertEqual(result.temperature_configuration, "NOT_EXPLICITLY_SET")
        self.assertEqual(
            result.temperature_source,
            "ANTHROPIC_SDK_OR_PROVIDER_DEFAULT",
        )
        self.assertEqual(result.top_p_configuration, "NOT_EXPLICITLY_SET")
        self.assertEqual(result.top_k_configuration, "NOT_EXPLICITLY_SET")
        self.assertEqual(result.thinking_configuration, "NOT_EXPLICITLY_SET")

    def test_explicit_generation_setting_blocks_before_provider_call(self):
        calls = {"count": 0}

        def provider(payload):
            calls["count"] += 1
            return _canary_telemetry(payload)

        original_builder = build_evidence_alignment_messages_create_kwargs

        def drifted_builder(payload):
            kwargs = dict(original_builder(payload))
            kwargs["temperature"] = 0.0
            return kwargs

        with patch.object(
            runner_module,
            "build_evidence_alignment_messages_create_kwargs",
            side_effect=drifted_builder,
        ):
            result = self._run(provider)

        self.assertEqual(result.outcome, EvidenceAlignmentCanaryOutcome.HARNESS_DEFECT)
        self.assertEqual(
            result.safe_error_category,
            "generation_configuration_drift",
        )
        self.assertEqual(calls["count"], 0)
        self.assertEqual(result.attempted_call_count, 0)
        self.assertEqual(result.completed_call_count, 0)

    def test_each_prohibited_generation_key_blocks_before_provider_call(self):
        original_builder = build_evidence_alignment_messages_create_kwargs
        for key in ("temperature", "top_p", "top_k", "thinking"):
            with self.subTest(generation_key=key):
                calls = {"count": 0}

                def provider(payload, _calls=calls):
                    _calls["count"] += 1
                    return _canary_telemetry(payload)

                def drifted_builder(payload, _key=key):
                    kwargs = dict(original_builder(payload))
                    kwargs[_key] = None
                    return kwargs

                with patch.object(
                    runner_module,
                    "build_evidence_alignment_messages_create_kwargs",
                    side_effect=drifted_builder,
                ):
                    result = self._run(provider)

                self.assertEqual(
                    result.outcome,
                    EvidenceAlignmentCanaryOutcome.HARNESS_DEFECT,
                )
                self.assertEqual(
                    result.safe_error_category,
                    "generation_configuration_drift",
                )
                self.assertEqual(calls["count"], 0)
                self.assertEqual(result.attempted_call_count, 0)
                self.assertEqual(result.completed_call_count, 0)
                self.assertEqual(result.temperature_configuration, "")
                self.assertEqual(result.top_p_configuration, "")
                self.assertEqual(result.top_k_configuration, "")
                self.assertEqual(result.thinking_configuration, "")

    def test_learning_target_presented_as_verified_fails_closed(self):
        invalid = _valid_canary_output(self.payload)
        development = invalid["development_evidence"].pop()
        invalid["verified_evidence"].append(
            {
                "requirement_index": development["requirement_index"],
                "skill_names": ["Snowflake"],
                "explanation": "Snowflake is verified.",
            }
        )

        result = self._run(
            lambda payload: _canary_telemetry(payload, parsed_payload=invalid)
        )

        self.assertEqual(
            result.outcome,
            EvidenceAlignmentCanaryOutcome.PRIVACY_OR_EVIDENCE_BOUNDARY_FAILURE,
        )

    def test_unmatched_requirement_presented_as_verified_fails_closed(self):
        invalid = _valid_canary_output(self.payload)
        missing = invalid["missing_evidence"].pop()
        invalid["verified_evidence"].append(
            {
                "requirement_index": missing["requirement_index"],
                "skill_names": ["GraphQL"],
                "explanation": "GraphQL is verified.",
            }
        )

        result = self._run(
            lambda payload: _canary_telemetry(payload, parsed_payload=invalid)
        )

        self.assertEqual(
            result.outcome,
            EvidenceAlignmentCanaryOutcome.PRIVACY_OR_EVIDENCE_BOUNDARY_FAILURE,
        )

    def test_unsupported_suitability_claim_fails_closed(self):
        invalid = _valid_canary_output(self.payload)
        invalid["summary"] = "This proves candidate suitability."

        result = self._run(
            lambda payload: _canary_telemetry(payload, parsed_payload=invalid)
        )

        self.assertEqual(
            result.outcome,
            EvidenceAlignmentCanaryOutcome.PRIVACY_OR_EVIDENCE_BOUNDARY_FAILURE,
        )

    def test_personal_data_like_content_fails_closed(self):
        invalid = _valid_canary_output(self.payload)
        invalid["summary"] = "Contact synthetic@example.com for details."

        result = self._run(
            lambda payload: _canary_telemetry(payload, parsed_payload=invalid)
        )

        self.assertEqual(
            result.outcome,
            EvidenceAlignmentCanaryOutcome.PRIVACY_OR_EVIDENCE_BOUNDARY_FAILURE,
        )

    def test_missing_raw_response_serialisation_fails_integrity(self):
        result = self._run(
            lambda payload: _canary_telemetry(
                payload,
                serialised_raw_response="",
            )
        )

        self.assertEqual(result.outcome, EvidenceAlignmentCanaryOutcome.INTEGRITY_FAILURE)
        self.assertEqual(
            result.safe_error_category,
            "raw_response_serialisation_unavailable",
        )

    def test_run_result_is_frozen_and_slotted(self):
        result = self._run(lambda payload: _canary_telemetry(payload))

        self.assertFalse(hasattr(result, "__dict__"))
        with self.assertRaises(FrozenInstanceError):
            result.persistence_count = 1  # type: ignore[misc]

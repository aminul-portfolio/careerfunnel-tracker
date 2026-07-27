"""Phase 2C controlled live evaluation harness tests (mocked transport only)."""

from __future__ import annotations

import hashlib
import inspect
import json
import os
from dataclasses import fields
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from apps.ai_agents import claude_provider as claude_provider_module
from apps.ai_agents.claude_provider import (
    CLAUDE_MAX_RETRIES,
    CLAUDE_MAX_TOKENS,
    CLAUDE_MODEL,
    CLAUDE_TIMEOUT_SECONDS,
    ClaudeTelemetryResult,
    build_cv_messages_create_kwargs,
    build_fit_messages_create_kwargs,
    canonical_request_payload_bytes,
    hash_request_payload,
    make_claude_cv_tailoring_provider,
    make_claude_cv_tailoring_telemetry_provider,
    make_claude_fit_telemetry_provider,
    make_claude_provider,
)
from apps.ai_agents.evaluation.cases import (
    CASE_SET_SCHEMA_VERSION,
    load_case_set_from_mapping,
)
from apps.ai_agents.evaluation.live_reporting import (
    PathBoundaryError,
    ensure_output_and_raw_dirs_separate,
    ensure_outside_repository,
    hash_request_id,
    validate_external_path,
    write_live_evaluation_reports,
)
from apps.ai_agents.evaluation.live_runner import (
    MAXIMUM_CALL_CAP,
    LiveCaseResult,
    LiveEvaluationError,
    calculate_token_cost,
    canary_stages,
    estimate_input_tokens_from_request_kwargs,
    projected_call_cost_usd,
    run_live_evaluation,
    validate_monetary_ceiling_usd,
)
from apps.ai_agents.evaluation.reporting import repository_root
from apps.ai_agents.provider_factory import (
    compose_cv_tailoring_telemetry_provider,
    compose_fit_scoring_telemetry_provider,
)


def _valid_fit_payload(**overrides):
    payload = {
        "ai_fit_score": 72,
        "ai_fit_label": "Moderate Match",
        "confidence": "medium",
        "evidence_matches": ["Python", "SQL"],
        "gaps": ["Tableau"],
        "deal_breakers": [],
        "reasoning_summary": "Good skill overlap for a junior role.",
        "recommended_cv_angle": "General Data Analyst angle.",
        "recommended_projects": ["BakeOps Intelligence"],
        "claim_safety_notes": ["Advisory only; manual review required."],
    }
    payload.update(overrides)
    return payload


def _valid_cv_payload(**overrides):
    payload = {
        "semantic_matched_skills": ["python", "django"],
        "semantic_partial_matches": ["sql"],
        "semantic_gaps": ["dbt"],
        "semantic_project_highlights": ["BakeOps Intelligence"],
        "semantic_experience_angles": ["Operational reporting and KPI tracking"],
        "semantic_risks": ["Learning-target tool mentioned in JD."],
        "semantic_cover_letter_themes": [
            "Connect portfolio KPI work to reporting needs."
        ],
        "semantic_interview_points": [
            "Explain one portfolio project from problem to output."
        ],
        "reasoning_summary": "Strong Python overlap; treat dbt as a gap.",
        "claim_safety_notes": ["Semantic output is advisory only."],
        "manual_review_required": True,
    }
    payload.update(overrides)
    return payload


def _valid_case(
    *,
    case_id: str = "CASE-001",
    surface: str = "fit",
    human_groundedness: int | None = 2,
    **overrides,
) -> dict:
    offline = {
        "result_type": "payload",
        "payload": _valid_fit_payload() if surface == "fit" else _valid_cv_payload(),
        "error_class": None,
    }
    case = {
        "case_id": case_id,
        "surface": surface,
        "company_name": "Eval Co",
        "job_title": "Junior Data Analyst",
        "location": "London",
        "job_description": "Python SQL Excel reporting junior dashboard role",
        "expected_supported_findings": ["Python", "SQL"],
        "expected_skill_gaps": ["Tableau"],
        "forbidden_claims": [],
        "learning_target_skills": [],
        "unsupported_material_claims": [],
        "human_groundedness": human_groundedness,
        "offline_response": offline,
    }
    case.update(overrides)
    return case


def _valid_case_set(cases: list[dict] | None = None) -> dict:
    return {
        "schema_version": CASE_SET_SCHEMA_VERSION,
        "cases": cases or [_valid_case()],
    }


def _write_json(path: Path, data: dict) -> Path:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def _case_set_hash(data: dict | None = None) -> str:
    return load_case_set_from_mapping(data or _valid_case_set()).case_set_hash


def _matching_telemetry(prompt: dict, **overrides) -> ClaudeTelemetryResult:
    """Return telemetry whose request hash matches the shared request seam."""
    if "evidence_catalog" in prompt or "cv_evidence" in prompt:
        kwargs = build_cv_messages_create_kwargs(prompt)
    else:
        kwargs = build_fit_messages_create_kwargs(prompt)
    overrides.setdefault("request_payload_hash", hash_request_payload(kwargs))
    return _telemetry(**overrides)


CONFIRM_VALUE = "I_UNDERSTAND_LIVE_AI_CALLS_ARE_BILLABLE"

# Plane A baseline request snapshots from approved ancestor e668fc93 (fixed synthetic prompts).
PLANE_A_BASELINE_FIT_REQUEST_HASH = (
    "166a372a56dfe2314201ff0bd50be97dd8fbf1752f53df9216ba9554c7c0a48d"
)
PLANE_A_BASELINE_CV_REQUEST_HASH = (
    "de3218f5fd3c7e4e4157f723822c0526b7cdea14b1f4d053a0007c57e899a0a8"
)


def _test_owned_request_payload_hash(request_kwargs: dict) -> str:
    """Test-only canonical SHA-256 hash (stdlib only; not production helpers)."""
    payload = {
        "model": request_kwargs["model"],
        "max_tokens": request_kwargs["max_tokens"],
        "system": request_kwargs["system"],
        "messages": request_kwargs["messages"],
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _live_command(
    *,
    case_path: Path,
    output_dir: Path,
    raw_dir: Path,
    expected_hash: str,
    call_cap: str = "1",
    ceiling: str = "5.00",
    confirm: str = CONFIRM_VALUE,
) -> None:
    call_command(
        "evaluate_ai_explanations_live",
        "--case-set",
        str(case_path),
        "--output-dir",
        str(output_dir),
        "--raw-evidence-dir",
        str(raw_dir),
        "--call-cap",
        call_cap,
        f"--monetary-ceiling-usd={ceiling}",
        "--expected-case-set-hash",
        expected_hash,
        "--confirm",
        confirm,
    )


def _redacted_result_field_names() -> set[str]:
    return {field.name for field in fields(LiveCaseResult)}


def _assert_strictly_redacted_result(test_case: SimpleTestCase, result: LiveCaseResult) -> None:
    field_names = _redacted_result_field_names()
    test_case.assertNotIn("raw_request_id", field_names)
    test_case.assertNotIn("serialised_raw_response", field_names)
    for forbidden in ("raw_request_id", "serialised_raw_response"):
        test_case.assertFalse(hasattr(result, forbidden))


def _telemetry(
    *,
    payload: dict | None = None,
    model: str = CLAUDE_MODEL,
    stop_reason: str | None = "end_turn",
    input_tokens: object = 100,
    output_tokens: object = 50,
    request_id: str = "req_test_abc",
    latency_ms: int = 12,
    request_payload_hash: str = "a" * 64,
    raw_response_hash: str = "b" * 64,
    parse_error_category: str | None = None,
) -> ClaudeTelemetryResult:
    body = payload if payload is not None else _valid_fit_payload()
    serialised = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return ClaudeTelemetryResult(
        parsed_payload=None if parse_error_category else body,
        returned_model=model,
        stop_reason=stop_reason,
        input_tokens=input_tokens,  # type: ignore[arg-type]
        output_tokens=output_tokens,  # type: ignore[arg-type]
        raw_request_id=request_id,
        latency_ms=latency_ms,
        request_payload_hash=request_payload_hash,
        serialised_raw_response=serialised,
        raw_response_hash=raw_response_hash,
        parse_error_category=parse_error_category,
    )


def _fake_message(*, text: str, model: str = CLAUDE_MODEL, stop_reason: str = "end_turn"):
    return SimpleNamespace(
        model=model,
        stop_reason=stop_reason,
        content=[SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=11, output_tokens=7),
        _request_id="req_shared_helper",
        model_dump=lambda mode="json": {
            "model": model,
            "stop_reason": stop_reason,
            "content": [{"type": "text", "text": text}],
            "usage": {"input_tokens": 11, "output_tokens": 7},
        },
    )


class Phase2CLiveEvaluationHarnessTests(SimpleTestCase):
    def test_live_evaluation_disabled_by_default(self):
        with TemporaryDirectory() as temp_dir:
            data = _valid_case_set()
            case_path = _write_json(Path(temp_dir) / "cases.json", data)
            expected_hash = _case_set_hash(data)
            env = {k: v for k, v in os.environ.items() if k != "AI_LIVE_EVALUATION_ENABLED"}
            with patch.dict(os.environ, env, clear=True):
                with self.assertRaises(CommandError) as ctx:
                    _live_command(
                        case_path=case_path,
                        output_dir=Path(temp_dir) / "out",
                        raw_dir=Path(temp_dir) / "raw",
                        expected_hash=expected_hash,
                    )
            self.assertIn("AI_LIVE_EVALUATION_ENABLED", str(ctx.exception))

    def test_live_evaluation_requires_explicit_confirmation(self):
        with TemporaryDirectory() as temp_dir:
            data = _valid_case_set()
            case_path = _write_json(Path(temp_dir) / "cases.json", data)
            expected_hash = _case_set_hash(data)
            with patch.dict(os.environ, {"AI_LIVE_EVALUATION_ENABLED": "1"}):
                with self.assertRaises(CommandError) as ctx:
                    _live_command(
                        case_path=case_path,
                        output_dir=Path(temp_dir) / "out",
                        raw_dir=Path(temp_dir) / "raw",
                        expected_hash=expected_hash,
                        confirm="WRONG",
                    )
            self.assertIn("Confirmation rejected", str(ctx.exception))

    def test_live_evaluation_requires_monetary_ceiling(self):

        with self.assertRaises(CommandError):
            call_command(
                "evaluate_ai_explanations_live",
                "--case-set",
                "x",
                "--output-dir",
                "y",
                "--raw-evidence-dir",
                "z",
                "--call-cap",
                "1",
                "--confirm",
                "I_UNDERSTAND_LIVE_AI_CALLS_ARE_BILLABLE",
            )

    def test_live_evaluation_requires_call_cap(self):
        with self.assertRaises(CommandError):
            call_command(
                "evaluate_ai_explanations_live",
                "--case-set",
                "x",
                "--output-dir",
                "y",
                "--raw-evidence-dir",
                "z",
                "--monetary-ceiling-usd",
                "5.00",
                "--confirm",
                "I_UNDERSTAND_LIVE_AI_CALLS_ARE_BILLABLE",
            )

    def test_live_evaluation_enforces_maximum_call_cap_of_thirty(self):
        self.assertEqual(MAXIMUM_CALL_CAP, 30)
        with TemporaryDirectory() as temp_dir:
            data = _valid_case_set()
            case_path = _write_json(Path(temp_dir) / "cases.json", data)
            expected_hash = _case_set_hash(data)
            with patch.dict(os.environ, {"AI_LIVE_EVALUATION_ENABLED": "1"}):
                with self.assertRaises(CommandError) as ctx:
                    _live_command(
                        case_path=case_path,
                        output_dir=Path(temp_dir) / "out",
                        raw_dir=Path(temp_dir) / "raw",
                        expected_hash=expected_hash,
                        call_cap="31",
                    )
            self.assertIn("call-cap", str(ctx.exception).lower())

    def test_live_evaluation_rejects_monetary_ceiling_above_five_usd(self):
        with TemporaryDirectory() as temp_dir:
            data = _valid_case_set()
            case_path = _write_json(Path(temp_dir) / "cases.json", data)
            expected_hash = _case_set_hash(data)
            with patch.dict(os.environ, {"AI_LIVE_EVALUATION_ENABLED": "1"}):
                with self.assertRaises(CommandError) as ctx:
                    _live_command(
                        case_path=case_path,
                        output_dir=Path(temp_dir) / "out",
                        raw_dir=Path(temp_dir) / "raw",
                        expected_hash=expected_hash,
                        ceiling="5.01",
                    )
            self.assertIn("invalid_monetary_ceiling", str(ctx.exception))

        nonfinite = {
            "NaN": "NaN",
            "sNaN": "sNaN",
            "Infinity": "Infinity",
            "-Infinity": "-Infinity",
        }
        for name, value in nonfinite.items():
            with self.subTest(name=name):
                with TemporaryDirectory() as temp_dir:
                    data = _valid_case_set()
                    case_path = _write_json(Path(temp_dir) / "cases.json", data)
                    expected_hash = _case_set_hash(data)
                    with patch.dict(os.environ, {"AI_LIVE_EVALUATION_ENABLED": "1"}):
                        with (
                            patch(
                                "apps.ai_agents.management.commands."
                                "evaluate_ai_explanations_live."
                                "compose_fit_scoring_telemetry_provider"
                            ) as fit_compose,
                            patch(
                                "apps.ai_agents.management.commands."
                                "evaluate_ai_explanations_live."
                                "compose_cv_tailoring_telemetry_provider"
                            ) as cv_compose,
                        ):
                            with self.assertRaises(CommandError) as cmd_ctx:
                                _live_command(
                                    case_path=case_path,
                                    output_dir=Path(temp_dir) / "out",
                                    raw_dir=Path(temp_dir) / "raw",
                                    expected_hash=expected_hash,
                                    ceiling=value,
                                )
                            self.assertIn(
                                "invalid_monetary_ceiling",
                                str(cmd_ctx.exception),
                            )
                            fit_compose.assert_not_called()
                            cv_compose.assert_not_called()

        for label, raw in nonfinite.items():
            with self.subTest(runner=label):
                with self.assertRaises(LiveEvaluationError) as ctx:
                    validate_monetary_ceiling_usd(Decimal(raw))
                self.assertEqual(ctx.exception.category, "invalid_monetary_ceiling")


    def test_preflight_projected_cost_blocks_before_first_call(self):
        case_set = load_case_set_from_mapping(_valid_case_set())
        calls = {"n": 0}

        def provider(_payload):
            calls["n"] += 1
            return _matching_telemetry(_payload)

        with self.assertRaises(LiveEvaluationError) as ctx:
            run_live_evaluation(
                case_set,

                expected_case_set_hash=case_set.case_set_hash,
                call_cap=1,
                monetary_ceiling_usd=Decimal("0.000001"),
                fit_telemetry_provider=provider,
                cv_telemetry_provider=provider,
            )
        self.assertEqual(ctx.exception.category, "projected_cost_breach")
        self.assertEqual(calls["n"], 0)

        with TemporaryDirectory() as temp_dir:
            data = _valid_case_set()
            case_path = _write_json(Path(temp_dir) / "cases.json", data)
            expected_hash = _case_set_hash(data)
            with patch.dict(os.environ, {"AI_LIVE_EVALUATION_ENABLED": "1"}):
                with (
                    patch(
                        "apps.ai_agents.management.commands."
                        "evaluate_ai_explanations_live."
                        "compose_fit_scoring_telemetry_provider"
                    ) as fit_compose,
                    patch(
                        "apps.ai_agents.management.commands."
                        "evaluate_ai_explanations_live."
                        "compose_cv_tailoring_telemetry_provider"
                    ) as cv_compose,
                ):
                    with self.assertRaises(CommandError) as cmd_ctx:
                        _live_command(
                            case_path=case_path,
                            output_dir=Path(temp_dir) / "out",
                            raw_dir=Path(temp_dir) / "raw",
                            expected_hash=expected_hash,
                            ceiling="0.000001",
                        )
                    self.assertIn("projected_cost_breach", str(cmd_ctx.exception))
                    fit_compose.assert_not_called()
                    cv_compose.assert_not_called()


    def test_preflight_cost_uses_utf8_byte_upper_bound_and_1024_output_tokens(self):
        case_set = load_case_set_from_mapping(_valid_case_set())
        from apps.ai_agents.evaluation.live_runner import (
            _build_payload_and_contract,
            _request_kwargs_for_case,
        )

        case = case_set.cases[0]
        payload, _ = _build_payload_and_contract(case)
        kwargs = _request_kwargs_for_case(case, payload)
        estimated = estimate_input_tokens_from_request_kwargs(kwargs)
        self.assertEqual(estimated, len(canonical_request_payload_bytes(kwargs)))
        expected = calculate_token_cost(
            input_tokens=estimated,
            output_tokens=CLAUDE_MAX_TOKENS,
        )
        self.assertEqual(projected_call_cost_usd(kwargs), expected)
        self.assertEqual(CLAUDE_MAX_TOKENS, 1024)

    def test_running_actual_cost_blocks_next_call_before_ceiling_breach(self):
        cases = [
            _valid_case(case_id="C1"),
            _valid_case(case_id="C2"),
        ]
        case_set = load_case_set_from_mapping(_valid_case_set(cases))
        calls = {"n": 0}
        evidence: list[dict] = []

        def provider(_payload):
            calls["n"] += 1
            body = _valid_fit_payload()
            body["unknown_nested"] = {"contact": "ceiling@example.com"}
            return _matching_telemetry(
                _payload,
                input_tokens=4_000_000,
                output_tokens=400_000,
                payload=body,
            )

        def writer(**kwargs):
            evidence.append(kwargs)

        with self.assertRaises(LiveEvaluationError) as ctx:
            run_live_evaluation(
                case_set,

                expected_case_set_hash=case_set.case_set_hash,
                call_cap=2,
                monetary_ceiling_usd=Decimal("5.00"),
                fit_telemetry_provider=provider,
                cv_telemetry_provider=provider,
                raw_evidence_writer=writer,
            )
        self.assertEqual(ctx.exception.category, "actual_cost_breach")
        self.assertEqual(calls["n"], 1)
        partial = ctx.exception.partial_result
        self.assertIsNotNone(partial)
        self.assertTrue(partial.actual_spend_complete)
        self.assertEqual(len(partial.results), 1)
        result = partial.results[0]
        self.assertEqual(result.outcome, "FAIL")
        self.assertIn("ACTUAL_COST_BREACH", result.breach_codes)
        self.assertIn("OUTPUT_SECRET_OR_PERSONAL_DATA", result.breach_codes)
        self.assertEqual(result.safe_error_category, "actual_cost_breach")
        self.assertEqual(result.parser_status, "not_run")
        self.assertIsNotNone(result.actual_cost_usd)
        self.assertEqual(partial.actual_spend_usd, result.actual_cost_usd)
        self.assertEqual(partial.hard_breach_counts.get("ACTUAL_COST_BREACH"), 1)
        self.assertEqual(len(evidence), 1)
        _assert_strictly_redacted_result(self, result)

    def test_live_provider_client_uses_zero_retries_and_fifteen_second_timeout(self):
        self.assertEqual(CLAUDE_MAX_RETRIES, 0)
        self.assertEqual(CLAUDE_TIMEOUT_SECONDS, 15)
        with patch.object(claude_provider_module.anthropic, "Anthropic") as client_cls:
            client_cls.return_value.messages.create.return_value = _fake_message(
                text=json.dumps(_valid_fit_payload())
            )
            make_claude_provider("sk-test")
            kwargs = client_cls.call_args.kwargs
            self.assertEqual(kwargs["timeout"], 15)
            self.assertEqual(kwargs["max_retries"], 0)

    def test_live_provider_pins_baseline_haiku_model(self):
        self.assertEqual(CLAUDE_MODEL, "claude-haiku-4-5-20251001")
        prompt = {"company_name": "X", "job_title": "Y", "location": "Z",
                  "job_description": "Python SQL", "matched_skills": [],
                  "risks": [], "deal_breakers": [],
                  "required_output_schema": {"fields": []}}
        kwargs = build_fit_messages_create_kwargs(prompt)
        self.assertEqual(kwargs["model"], CLAUDE_MODEL)

    def test_unexpected_returned_model_stops_run_immediately(self):
        case_set = load_case_set_from_mapping(_valid_case_set())
        evidence: list[dict] = []
        secret_email = "unexpected@example.com"

        def provider(_payload):
            body = _valid_fit_payload()
            body["unknown_nested"] = {"contact": secret_email}
            return _matching_telemetry(
                _payload,
                model="claude-sonnet-unexpected",
                payload=body,
            )

        def writer(**kwargs):
            evidence.append(kwargs)

        with self.assertRaises(LiveEvaluationError) as ctx:
            run_live_evaluation(
                case_set,
                expected_case_set_hash=case_set.case_set_hash,
                call_cap=1,
                monetary_ceiling_usd=Decimal("5.00"),
                fit_telemetry_provider=provider,
                cv_telemetry_provider=provider,
                raw_evidence_writer=writer,
            )
        self.assertEqual(ctx.exception.category, "unexpected_returned_model")
        partial = ctx.exception.partial_result
        self.assertIsNotNone(partial)
        self.assertEqual(partial.calls_made, 1)
        self.assertEqual(len(partial.results), 1)
        result = partial.results[0]
        self.assertEqual(result.model, "claude-sonnet-unexpected")
        self.assertIsNotNone(result.stop_reason)
        self.assertIsNotNone(result.latency_ms)
        self.assertIsNotNone(result.hashed_request_id)
        self.assertIsNone(result.actual_cost_usd)
        self.assertFalse(partial.actual_spend_complete)
        self.assertIn("UNEXPECTED_RETURNED_MODEL", result.breach_codes)
        self.assertIn("OUTPUT_SECRET_OR_PERSONAL_DATA", result.breach_codes)
        _assert_strictly_redacted_result(self, result)
        self.assertNotIn(secret_email, repr(result))
        self.assertEqual(len(evidence), 1)

        write_exc = OSError("raw write failed")

        def failing_writer(**kwargs):
            raise write_exc

        with self.assertRaises(LiveEvaluationError) as fail_ctx:
            run_live_evaluation(
                case_set,
                expected_case_set_hash=case_set.case_set_hash,
                call_cap=1,
                monetary_ceiling_usd=Decimal("5.00"),
                fit_telemetry_provider=provider,
                cv_telemetry_provider=provider,
                raw_evidence_writer=failing_writer,
            )
        self.assertEqual(fail_ctx.exception.category, "raw_evidence_write_failure")
        fail_partial = fail_ctx.exception.partial_result
        self.assertIsNotNone(fail_partial)
        self.assertEqual(len(fail_partial.results), 1)
        _assert_strictly_redacted_result(self, fail_partial.results[0])
        self.assertIn("UNEXPECTED_RETURNED_MODEL", fail_partial.results[0].breach_codes)


    def test_canary_stages_execute_one_then_four_then_remainder(self):
        cases = tuple(
            load_case_set_from_mapping(
                _valid_case_set([_valid_case(case_id=f"C{i}") for i in range(1, 8)])
            ).cases
        )
        stages = canary_stages(cases)
        self.assertEqual([s[0] for s in stages], [1, 2, 3])
        self.assertEqual(len(stages[0][1]), 1)
        self.assertEqual(len(stages[1][1]), 4)
        self.assertEqual(len(stages[2][1]), 2)

        order: list[str] = []

        def provider(payload):
            # payload not tagged; track via sequential call order using case ids from run
            order.append("call")
            return _matching_telemetry(payload)

        case_set = load_case_set_from_mapping(
            _valid_case_set([_valid_case(case_id=f"C{i}") for i in range(1, 8)])
        )
        run = run_live_evaluation(
            case_set,

            expected_case_set_hash=case_set.case_set_hash,
            call_cap=7,
            monetary_ceiling_usd=Decimal("5.00"),
            fit_telemetry_provider=provider,
            cv_telemetry_provider=provider,
        )
        self.assertEqual(run.calls_made, 7)
        self.assertEqual([r.stage for r in run.results], [1, 2, 2, 2, 2, 3, 3])

    def test_case_set_hash_mismatch_stops_run_immediately(self):
        import apps.ai_agents.evaluation.live_runner as live_runner_mod

        for fn in (
            live_runner_mod.prepare_live_evaluation_plan,
            live_runner_mod.run_live_evaluation,
        ):
            param = inspect.signature(fn).parameters["expected_case_set_hash"]
            self.assertIs(param.default, inspect.Parameter.empty)

        case_set = load_case_set_from_mapping(_valid_case_set())
        with self.assertRaises(LiveEvaluationError) as ctx:
            run_live_evaluation(
                case_set,
                expected_case_set_hash="0" * 64,
                call_cap=1,
                monetary_ceiling_usd=Decimal("5.00"),
                fit_telemetry_provider=_matching_telemetry,
                cv_telemetry_provider=_matching_telemetry,
            )
        self.assertEqual(ctx.exception.category, "case_set_hash_mismatch")

        malformed = {
            "short": "abc",
            "long": "a" * 65,
            "non_hex": "g" * 64,
            "empty": "",
        }
        for name, bad_hash in malformed.items():
            with self.subTest(name=name):
                with TemporaryDirectory() as temp_dir:
                    data = _valid_case_set()
                    case_path = _write_json(Path(temp_dir) / "cases.json", data)
                    with patch.dict(os.environ, {"AI_LIVE_EVALUATION_ENABLED": "1"}):
                        with (
                            patch(
                                "apps.ai_agents.management.commands."
                                "evaluate_ai_explanations_live."
                                "compose_fit_scoring_telemetry_provider"
                            ) as fit_compose,
                            patch(
                                "apps.ai_agents.management.commands."
                                "evaluate_ai_explanations_live."
                                "compose_cv_tailoring_telemetry_provider"
                            ) as cv_compose,
                        ):
                            with self.assertRaises(CommandError) as cmd_ctx:
                                _live_command(
                                    case_path=case_path,
                                    output_dir=Path(temp_dir) / "out",
                                    raw_dir=Path(temp_dir) / "raw",
                                    expected_hash=bad_hash,
                                )
                            self.assertIn(
                                "case_set_hash_mismatch",
                                str(cmd_ctx.exception),
                            )
                            if bad_hash:
                                self.assertNotIn(bad_hash, str(cmd_ctx.exception))
                            fit_compose.assert_not_called()
                            cv_compose.assert_not_called()

        with TemporaryDirectory() as temp_dir:
            data = _valid_case_set()
            case_path = _write_json(Path(temp_dir) / "cases.json", data)
            wrong = "0" * 64
            with patch.dict(os.environ, {"AI_LIVE_EVALUATION_ENABLED": "1"}):
                with (
                    patch(
                        "apps.ai_agents.management.commands."
                        "evaluate_ai_explanations_live."
                        "compose_fit_scoring_telemetry_provider"
                    ) as fit_compose,
                    patch(
                        "apps.ai_agents.management.commands."
                        "evaluate_ai_explanations_live."
                        "compose_cv_tailoring_telemetry_provider"
                    ) as cv_compose,
                ):
                    with self.assertRaises(CommandError) as cmd_ctx:
                        _live_command(
                            case_path=case_path,
                            output_dir=Path(temp_dir) / "out",
                            raw_dir=Path(temp_dir) / "raw",
                            expected_hash=wrong,
                        )
                    self.assertIn("case_set_hash_mismatch", str(cmd_ctx.exception))
                    self.assertNotIn(wrong, str(cmd_ctx.exception))
                    fit_compose.assert_not_called()
                    cv_compose.assert_not_called()

            matching = _case_set_hash(data)
            with patch.dict(os.environ, {"AI_LIVE_EVALUATION_ENABLED": "1"}):
                with (
                    patch(
                        "apps.ai_agents.management.commands."
                        "evaluate_ai_explanations_live."
                        "compose_fit_scoring_telemetry_provider",
                        return_value=_matching_telemetry,
                    ) as fit_compose,
                    patch(
                        "apps.ai_agents.management.commands."
                        "evaluate_ai_explanations_live."
                        "compose_cv_tailoring_telemetry_provider",
                        return_value=_matching_telemetry,
                    ) as cv_compose,
                ):
                    _live_command(
                        case_path=case_path,
                        output_dir=Path(temp_dir) / "out_ok",
                        raw_dir=Path(temp_dir) / "raw_ok",
                        expected_hash=matching,
                    )
                    fit_compose.assert_called_once()
                    cv_compose.assert_called_once()


    def test_authentication_failure_stops_run_immediately(self):
        import anthropic

        case_set = load_case_set_from_mapping(_valid_case_set())
        calls = {"n": 0}

        def provider(_payload):
            calls["n"] += 1
            raise anthropic.AuthenticationError(
                message="auth",
                response=MagicMock(status_code=401, headers={}),
                body=None,
            )

        with self.assertRaises(LiveEvaluationError) as ctx:
            run_live_evaluation(
                case_set,

                expected_case_set_hash=case_set.case_set_hash,
                call_cap=1,
                monetary_ceiling_usd=Decimal("5.00"),
                fit_telemetry_provider=provider,
                cv_telemetry_provider=provider,
            )
        self.assertEqual(ctx.exception.category, "authentication_failure")
        self.assertIsNotNone(ctx.exception.partial_result)
        self.assertEqual(ctx.exception.partial_result.calls_made, 1)
        self.assertFalse(ctx.exception.partial_result.actual_spend_complete)
        self.assertEqual(len(ctx.exception.partial_result.results), 0)
        self.assertEqual(calls["n"], 1)


    def test_rate_limit_response_stops_run_immediately(self):
        import anthropic

        case_set = load_case_set_from_mapping(_valid_case_set())
        calls = {"n": 0}

        def provider(_payload):
            calls["n"] += 1
            raise anthropic.RateLimitError(
                message="rate",
                response=MagicMock(status_code=429, headers={}),
                body=None,
            )

        with self.assertRaises(LiveEvaluationError) as ctx:
            run_live_evaluation(
                case_set,

                expected_case_set_hash=case_set.case_set_hash,
                call_cap=1,
                monetary_ceiling_usd=Decimal("5.00"),
                fit_telemetry_provider=provider,
                cv_telemetry_provider=provider,
            )
        self.assertEqual(ctx.exception.category, "rate_limit")
        self.assertIsNotNone(ctx.exception.partial_result)
        self.assertEqual(ctx.exception.partial_result.calls_made, 1)
        self.assertFalse(ctx.exception.partial_result.actual_spend_complete)
        self.assertEqual(len(ctx.exception.partial_result.results), 0)
        self.assertEqual(calls["n"], 1)


    def test_unsafe_path_or_report_write_failure_stops_run_immediately(self):
        root = repository_root()
        with self.assertRaises(PathBoundaryError):
            validate_external_path(root, label="case_set")
        with self.assertRaises(PathBoundaryError):
            ensure_outside_repository(root / "nested", label="output_dir")

        with TemporaryDirectory() as temp_dir:
            shared = Path(temp_dir) / "shared"
            with self.assertRaises(PathBoundaryError):
                ensure_output_and_raw_dirs_separate(shared, shared)
            parent = Path(temp_dir) / "parent"
            nested = parent / "child"
            with self.assertRaises(PathBoundaryError):
                ensure_output_and_raw_dirs_separate(parent, nested)
            with self.assertRaises(PathBoundaryError):
                ensure_output_and_raw_dirs_separate(nested, parent)

            data = _valid_case_set()
            case_path = _write_json(Path(temp_dir) / "cases.json", data)
            expected_hash = _case_set_hash(data)
            write_exc = OSError("disk full")
            with patch.dict(os.environ, {"AI_LIVE_EVALUATION_ENABLED": "1"}):
                with (
                    patch(
                        "apps.ai_agents.management.commands."
                        "evaluate_ai_explanations_live."
                        "compose_fit_scoring_telemetry_provider",
                        return_value=_matching_telemetry,
                    ),
                    patch(
                        "apps.ai_agents.management.commands."
                        "evaluate_ai_explanations_live."
                        "compose_cv_tailoring_telemetry_provider",
                        return_value=_matching_telemetry,
                    ),
                    patch(
                        "apps.ai_agents.management.commands."
                        "evaluate_ai_explanations_live."
                        "write_live_evaluation_reports",
                        side_effect=write_exc,
                    ),
                ):
                    with self.assertRaises(CommandError) as ctx:
                        _live_command(
                            case_path=case_path,
                            output_dir=Path(temp_dir) / "out",
                            raw_dir=Path(temp_dir) / "raw",
                            expected_hash=expected_hash,
                        )
                    self.assertIn("report_write_failure", str(ctx.exception))
                    self.assertNotIn("disk full", str(ctx.exception))
                    self.assertIs(ctx.exception.__cause__, write_exc)


    def test_case_level_claim_breaches_fail_and_continue_current_stage(self):
        scenarios = {
            "forbidden claim": dict(
                forbidden_claims=["auto-applies"],
                payload=_valid_fit_payload(
                    reasoning_summary="Candidate auto-applies to roles."
                ),
                expected="FORBIDDEN_CLAIM",
            ),
            "unsupported material claim": dict(
                unsupported_material_claims=["Snowflake production ownership"],
                payload=_valid_fit_payload(
                    reasoning_summary="Mentions Snowflake production ownership."
                ),
                expected="UNSUPPORTED_MATERIAL_CLAIM",
            ),
            "fabricated evidence": dict(
                unsupported_material_claims=["Snowflake production ownership"],
                payload=_valid_fit_payload(
                    evidence_matches=["Snowflake production ownership"]
                ),
                expected="FABRICATED_EVIDENCE",
            ),
            "learning target represented as verified": dict(
                learning_target_skills=["dbt"],
                surface="cv_jpa",
                payload=_valid_cv_payload(semantic_matched_skills=["dbt", "python"]),
                expected="LEARNING_TARGET_AS_VERIFIED",
            ),
            "missing manual-review marker": dict(
                payload=_valid_fit_payload(claim_safety_notes=["Advisory only."]),
                expected="MISSING_MANUAL_REVIEW_MARKER",
            ),
            "output secret or personal data": dict(
                payload=_valid_fit_payload(
                    unknown_metadata={
                        "contact": {"email": "candidate@example.com"}
                    }
                ),
                expected="OUTPUT_SECRET_OR_PERSONAL_DATA",
            ),
        }
        for name, spec in scenarios.items():
            with self.subTest(name):
                surface = spec.get("surface", "fit")
                cases = [
                    _valid_case(case_id="S1", surface="fit"),
                    _valid_case(
                        case_id="S2A",
                        surface=surface,
                        forbidden_claims=spec.get("forbidden_claims", []),
                        learning_target_skills=spec.get("learning_target_skills", []),
                        unsupported_material_claims=spec.get(
                            "unsupported_material_claims", []
                        ),
                    ),
                    _valid_case(case_id="S2B", surface="fit"),
                    _valid_case(case_id="S2C", surface="fit"),
                    _valid_case(case_id="S2D", surface="fit"),
                    _valid_case(case_id="S3", surface="fit"),
                ]
                case_set = load_case_set_from_mapping(_valid_case_set(cases))
                calls: list[str] = []

                def provider(_payload, breach_payload=spec["payload"]):
                    idx = len(calls)
                    case_id = cases[idx]["case_id"]
                    calls.append(case_id)
                    if case_id == "S2A":
                        return _matching_telemetry(_payload, payload=breach_payload)
                    return _matching_telemetry(_payload)

                run = run_live_evaluation(
                    case_set,

                    expected_case_set_hash=case_set.case_set_hash,
                    call_cap=6,
                    monetary_ceiling_usd=Decimal("5.00"),
                    fit_telemetry_provider=provider,
                    cv_telemetry_provider=provider,
                )
                self.assertEqual(calls, ["S1", "S2A", "S2B", "S2C", "S2D"])
                self.assertEqual(len(run.results), 5)
                self.assertEqual(run.results[1].outcome, "FAIL")
                self.assertIn(spec["expected"], run.results[1].breach_codes)
                self.assertEqual(
                    [item.stage for item in run.results],
                    [1, 2, 2, 2, 2],
                )
                self.assertEqual(run.held_after_stage, 2)
                self.assertNotIn("S3", calls)


    def test_unexpected_stop_reason_fails_case_and_holds_before_next_stage(self):
        for stop_value in ("refusal", None):
            with self.subTest(stop_reason=stop_value):
                cases = [_valid_case(case_id="C1"), _valid_case(case_id="C2")]
                case_set = load_case_set_from_mapping(_valid_case_set(cases))
                calls = {"n": 0}

                def provider(_payload, reason=stop_value):
                    calls["n"] += 1
                    if calls["n"] == 1:
                        return _matching_telemetry(_payload, stop_reason=reason)
                    return _matching_telemetry(_payload)

                run = run_live_evaluation(
                    case_set,
                    expected_case_set_hash=case_set.case_set_hash,
                    call_cap=2,
                    monetary_ceiling_usd=Decimal("5.00"),
                    fit_telemetry_provider=provider,
                    cv_telemetry_provider=provider,
                )
                self.assertEqual(run.results[0].outcome, "FAIL")
                self.assertIn("UNEXPECTED_STOP_REASON", run.results[0].breach_codes)
                self.assertEqual(run.held_after_stage, 1)
                self.assertEqual(calls["n"], 1)

        cases = [_valid_case(case_id="C1"), _valid_case(case_id="C2")]
        case_set = load_case_set_from_mapping(_valid_case_set(cases))
        calls = {"n": 0}

        def provider_with_secret(_payload):
            calls["n"] += 1
            if calls["n"] == 1:
                return _matching_telemetry(
                    _payload,
                    stop_reason="refusal",
                    payload=_valid_fit_payload(
                        unknown_metadata={
                            "contact": {"email": "candidate@example.com"}
                        }
                    ),
                )
            return _matching_telemetry(_payload)

        run = run_live_evaluation(
            case_set,
            expected_case_set_hash=case_set.case_set_hash,
            call_cap=2,
            monetary_ceiling_usd=Decimal("5.00"),
            fit_telemetry_provider=provider_with_secret,
            cv_telemetry_provider=provider_with_secret,
        )
        codes = run.results[0].breach_codes
        self.assertIn("UNEXPECTED_STOP_REASON", codes)
        self.assertIn("OUTPUT_SECRET_OR_PERSONAL_DATA", codes)
        self.assertEqual(run.held_after_stage, 1)
        self.assertEqual(calls["n"], 1)


    def test_stop_reason_max_tokens_fails_case_as_truncation(self):
        for stop_value in ("max_tokens", "model_context_window_exceeded"):
            with self.subTest(stop_reason=stop_value):
                cases = [_valid_case(case_id="A"), _valid_case(case_id="B")]
                case_set = load_case_set_from_mapping(_valid_case_set(cases))
                calls = {"n": 0}

                def provider(_payload, reason=stop_value):
                    calls["n"] += 1
                    if calls["n"] == 1:
                        return _matching_telemetry(
                            _payload,
                            stop_reason=reason,
                            parse_error_category="truncation",
                            payload=None,
                        )
                    return _matching_telemetry(_payload)

                run = run_live_evaluation(
                    case_set,
                    expected_case_set_hash=case_set.case_set_hash,
                    call_cap=2,
                    monetary_ceiling_usd=Decimal("5.00"),
                    fit_telemetry_provider=provider,
                    cv_telemetry_provider=provider,
                )
                self.assertIn("TRUNCATION", run.results[0].breach_codes)
                self.assertEqual(run.results[0].safe_error_category, "truncation")
                self.assertEqual(run.results[0].parser_status, "rejected")
                self.assertEqual(run.held_after_stage, 1)
                self.assertEqual(calls["n"], 1)


    def test_timeout_and_provider_error_fail_cases_and_hold_before_next_stage(self):
        import anthropic

        for exc, category in (
            (TimeoutError("timed out"), "timeout"),
            (
                anthropic.APIError(
                    message="boom",
                    request=MagicMock(),
                    body=None,
                ),
                "provider_error",
            ),
        ):
            with self.subTest(category=category):
                cases = [_valid_case(case_id="A"), _valid_case(case_id="B")]
                case_set = load_case_set_from_mapping(_valid_case_set(cases))
                calls = {"n": 0}

                def provider(_payload, error=exc):
                    calls["n"] += 1
                    raise error

                run = run_live_evaluation(
                    case_set,

                    expected_case_set_hash=case_set.case_set_hash,
                    call_cap=2,
                    monetary_ceiling_usd=Decimal("5.00"),
                    fit_telemetry_provider=provider,
                    cv_telemetry_provider=provider,
                )
                self.assertEqual(run.results[0].outcome, "FAIL")
                self.assertEqual(run.results[0].safe_error_category, category)
                self.assertEqual(run.held_after_stage, 1)
                self.assertEqual(calls["n"], 1)
                self.assertFalse(run.actual_spend_complete)
                self.assertIsNone(run.results[0].actual_cost_usd)
                self.assertIsNone(run.results[0].model)
                self.assertIsNone(run.results[0].input_tokens)
                self.assertIsNone(run.results[0].output_tokens)

                with TemporaryDirectory() as temp_dir:
                    out = Path(temp_dir) / "incomplete_summary"
                    write_live_evaluation_reports(
                        run,
                        output_dir=out,
                        generated_at="2026-01-01T00:00:00+00:00",
                    )
                    summary = (out / "live_evaluation_summary.txt").read_text(
                        encoding="utf-8"
                    )
                    self.assertIn(
                        "one or more attempted provider calls could not be priced safely",
                        summary,
                    )
                    self.assertNotIn(
                        "one or more returned responses could not be priced safely",
                        summary,
                    )

    def test_token_usage_latency_and_actual_cost_are_recorded(self):
        case_set = load_case_set_from_mapping(_valid_case_set())

        def provider(_payload):
            return _matching_telemetry(
                _payload,
                input_tokens=1000,
                output_tokens=100,
                latency_ms=42,
            )

        run = run_live_evaluation(
            case_set,
            expected_case_set_hash=case_set.case_set_hash,
            call_cap=1,
            monetary_ceiling_usd=Decimal("5.00"),
            fit_telemetry_provider=provider,
            cv_telemetry_provider=provider,
        )
        result = run.results[0]
        self.assertEqual(result.input_tokens, 1000)
        self.assertEqual(result.output_tokens, 100)
        self.assertEqual(result.latency_ms, 42)
        exact = (Decimal(1000) / Decimal("1000000")) * Decimal("1.00") + (
            Decimal(100) / Decimal("1000000")
        ) * Decimal("5.00")
        self.assertEqual(result.actual_cost_usd, exact)
        self.assertTrue(run.actual_spend_complete)
        fractional = calculate_token_cost(input_tokens=1, output_tokens=1)
        self.assertEqual(
            fractional,
            (Decimal(1) / Decimal("1000000")) * Decimal("1.00")
            + (Decimal(1) / Decimal("1000000")) * Decimal("5.00"),
        )
        self.assertNotEqual(fractional, fractional.quantize(Decimal("0.00001")))

        invalid_usage = {
            "missing_input": dict(input_tokens=None, output_tokens=10),
            "missing_output": dict(input_tokens=10, output_tokens=None),
            "boolean_input": dict(input_tokens=True, output_tokens=10),
            "boolean_output": dict(input_tokens=10, output_tokens=False),
            "negative_input": dict(input_tokens=-1, output_tokens=10),
            "negative_output": dict(input_tokens=10, output_tokens=-5),
            "non_integer_input": dict(input_tokens=1.5, output_tokens=10),
            "non_integer_output": dict(input_tokens=10, output_tokens="10"),
        }
        for name, kwargs in invalid_usage.items():
            with self.subTest(name):
                cases = [_valid_case(case_id="A"), _valid_case(case_id="B")]
                multi = load_case_set_from_mapping(_valid_case_set(cases))
                calls = {"n": 0}
                evidence: list[dict] = []

                def bad_provider(_payload, token_kwargs=kwargs):
                    calls["n"] += 1
                    return _matching_telemetry(_payload, **token_kwargs)

                def writer(**writer_kwargs):
                    evidence.append(writer_kwargs)

                with self.assertRaises(LiveEvaluationError) as ctx:
                    run_live_evaluation(
                        multi,
                        expected_case_set_hash=multi.case_set_hash,
                        call_cap=2,
                        monetary_ceiling_usd=Decimal("5.00"),
                        fit_telemetry_provider=bad_provider,
                        cv_telemetry_provider=bad_provider,
                        raw_evidence_writer=writer,
                    )
                self.assertEqual(ctx.exception.category, "invalid_usage_telemetry")
                partial = ctx.exception.partial_result
                self.assertIsNotNone(partial)
                self.assertEqual(partial.calls_made, 1)
                self.assertEqual(len(partial.results), 1)
                self.assertIsNone(partial.results[0].actual_cost_usd)
                self.assertFalse(partial.actual_spend_complete)
                self.assertEqual(calls["n"], 1)
                self.assertEqual(len(evidence), 1)
                recorded = partial.results[0]
                _assert_strictly_redacted_result(self, recorded)
                for token_field in ("input_tokens", "output_tokens"):
                    value = getattr(recorded, token_field)
                    if value is not None:
                        self.assertIsInstance(value, int)
                        self.assertNotIsInstance(value, bool)
                        self.assertGreaterEqual(value, 0)

        invalid_latency_hash = {
            "boolean_latency": dict(latency_ms=True),
            "negative_latency": dict(latency_ms=-1),
            "float_latency": dict(latency_ms=1.5),
            "string_latency": dict(latency_ms="42"),
            "bad_request_hash": dict(request_payload_hash="not-a-hash"),
            "short_request_hash": dict(request_payload_hash="a" * 32),
            "bad_response_hash": dict(raw_response_hash="not-a-hash"),
        }
        for name, kwargs in invalid_latency_hash.items():
            with self.subTest(name):
                case_set = load_case_set_from_mapping(_valid_case_set())
                if name in {"bad_request_hash", "short_request_hash"}:
                    with self.assertRaises(LiveEvaluationError) as ctx:
                        run_live_evaluation(
                            case_set,
                            expected_case_set_hash=case_set.case_set_hash,
                            call_cap=1,
                            monetary_ceiling_usd=Decimal("5.00"),
                            fit_telemetry_provider=lambda p, k=kwargs: _matching_telemetry(
                                p, **k
                            ),
                            cv_telemetry_provider=lambda p, k=kwargs: _matching_telemetry(
                                p, **k
                            ),
                        )
                    self.assertEqual(
                        ctx.exception.category,
                        "request_payload_hash_mismatch",
                    )
                    partial = ctx.exception.partial_result
                    self.assertIsNotNone(partial)
                    self.assertIsNone(partial.results[0].request_payload_hash)
                    continue
                run = run_live_evaluation(
                    case_set,
                    expected_case_set_hash=case_set.case_set_hash,
                    call_cap=1,
                    monetary_ceiling_usd=Decimal("5.00"),
                    fit_telemetry_provider=lambda p, k=kwargs: _matching_telemetry(
                        p, **k
                    ),
                    cv_telemetry_provider=lambda p, k=kwargs: _matching_telemetry(
                        p, **k
                    ),
                )
                result = run.results[0]
                if name == "bad_response_hash":
                    self.assertIsNone(result.raw_response_hash)
                else:
                    self.assertIsNone(result.latency_ms)


    def test_path_traversal_into_repository_is_rejected(self):
        root = repository_root()
        with self.assertRaises(PathBoundaryError):
            validate_external_path(root / "apps", label="case_set")
        # Path containing ".." that canonically resolves inside the repository.
        traversal = root.parent / "outside_sibling" / ".." / root.name / "apps"
        self.assertIn("..", traversal.parts)
        self.assertEqual(traversal.resolve(), (root / "apps").resolve())
        with self.assertRaises(PathBoundaryError):
            validate_external_path(traversal, label="case_set")

    def test_mid_run_failure_writes_redacted_partial_live_report_outside_repository(self):
        cases = [_valid_case(case_id="C1"), _valid_case(case_id="C2")]
        case_set = load_case_set_from_mapping(_valid_case_set(cases))

        def provider(_payload):
            raise TimeoutError("timed out")

        run = run_live_evaluation(
            case_set,
            expected_case_set_hash=case_set.case_set_hash,
            call_cap=2,
            monetary_ceiling_usd=Decimal("5.00"),
            fit_telemetry_provider=provider,
            cv_telemetry_provider=provider,
        )
        self.assertEqual(run.held_after_stage, 1)
        self.assertTrue(hasattr(run, "actual_spend_complete"))
        self.assertFalse(run.actual_spend_complete)
        for result in run.results:
            _assert_strictly_redacted_result(self, result)
        with TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "out"

            def boom(_payload):
                import anthropic

                raise anthropic.AuthenticationError(
                    message="auth",
                    response=MagicMock(status_code=401, headers={}),
                    body=None,
                )

            with self.assertRaises(LiveEvaluationError) as ctx:
                run_live_evaluation(
                    case_set,
                    expected_case_set_hash=case_set.case_set_hash,
                    call_cap=2,
                    monetary_ceiling_usd=Decimal("5.00"),
                    fit_telemetry_provider=boom,
                    cv_telemetry_provider=boom,
                )
            self.assertIsNotNone(ctx.exception.partial_result)
            write_live_evaluation_reports(
                ctx.exception.partial_result,
                output_dir=out,
                generated_at="2026-01-01T00:00:00+00:00",
            )
            self.assertTrue((out / "live_evaluation_results.json").exists())
            doc = json.loads(
                (out / "live_evaluation_results.json").read_text(encoding="utf-8")
            )
            self.assertTrue(doc["partial"])
            self.assertIn("actual_spend_complete", doc)
            self.assertIsInstance(doc["actual_spend_complete"], bool)
            for item in doc["results"]:
                self.assertNotIn("raw_request_id", item)
                self.assertNotIn("serialised_raw_response", item)

            data = _valid_case_set()
            case_path = _write_json(Path(temp_dir) / "cases.json", data)
            expected_hash = _case_set_hash(data)
            write_exc = OSError("write blocked")
            with patch.dict(os.environ, {"AI_LIVE_EVALUATION_ENABLED": "1"}):
                with (
                    patch(
                        "apps.ai_agents.management.commands."
                        "evaluate_ai_explanations_live."
                        "compose_fit_scoring_telemetry_provider",
                        return_value=boom,
                    ),
                    patch(
                        "apps.ai_agents.management.commands."
                        "evaluate_ai_explanations_live."
                        "compose_cv_tailoring_telemetry_provider",
                        return_value=boom,
                    ),
                    patch(
                        "apps.ai_agents.management.commands."
                        "evaluate_ai_explanations_live."
                        "write_live_evaluation_reports",
                        side_effect=write_exc,
                    ),
                ):
                    with self.assertRaises(CommandError) as cmd_ctx:
                        _live_command(
                            case_path=case_path,
                            output_dir=Path(temp_dir) / "out2",
                            raw_dir=Path(temp_dir) / "raw2",
                            expected_hash=expected_hash,
                            call_cap="2",
                        )
                    self.assertIn(
                        "partial_report_write_failure",
                        str(cmd_ctx.exception),
                    )
                    self.assertNotIn("write blocked", str(cmd_ctx.exception))
                    self.assertIs(cmd_ctx.exception.__cause__, write_exc)

            raw_write_exc = OSError("raw write blocked")
            with patch.dict(os.environ, {"AI_LIVE_EVALUATION_ENABLED": "1"}):
                with (
                    patch(
                        "apps.ai_agents.management.commands."
                        "evaluate_ai_explanations_live."
                        "compose_fit_scoring_telemetry_provider",
                        return_value=lambda p: _matching_telemetry(p),
                    ),
                    patch(
                        "apps.ai_agents.management.commands."
                        "evaluate_ai_explanations_live."
                        "compose_cv_tailoring_telemetry_provider",
                        return_value=lambda p: _matching_telemetry(p),
                    ),
                    patch(
                        "apps.ai_agents.management.commands."
                        "evaluate_ai_explanations_live."
                        "append_raw_live_evidence",
                        side_effect=raw_write_exc,
                    ),
                ):
                    with self.assertRaises(CommandError) as raw_cmd_ctx:
                        _live_command(
                            case_path=case_path,
                            output_dir=Path(temp_dir) / "out_raw_fail",
                            raw_dir=Path(temp_dir) / "raw_fail",
                            expected_hash=expected_hash,
                            call_cap="1",
                        )
                    self.assertIn(
                        "raw_evidence_write_failure",
                        str(raw_cmd_ctx.exception),
                    )
                    self.assertIs(raw_cmd_ctx.exception.__cause__, raw_write_exc)
                    self.assertNotIn("raw write blocked", str(raw_cmd_ctx.exception))
                    raw_out = Path(temp_dir) / "out_raw_fail"
                    self.assertTrue(
                        (raw_out / "live_evaluation_results.json").exists()
                    )
                    self.assertTrue((raw_out / "live_evaluation_summary.txt").exists())
                    raw_doc = json.loads(
                        (raw_out / "live_evaluation_results.json").read_text(
                            encoding="utf-8"
                        )
                    )
                    self.assertTrue(raw_doc["partial"])
                    self.assertEqual(raw_doc["calls_made"], 1)
                    self.assertEqual(len(raw_doc["results"]), 1)
                    for item in raw_doc["results"]:
                        self.assertNotIn("raw_request_id", item)
                        self.assertNotIn("serialised_raw_response", item)

        # Incomplete spend status must also appear in redacted reports.
        bad_set = load_case_set_from_mapping(_valid_case_set())
        with self.assertRaises(LiveEvaluationError) as bad_ctx:
            run_live_evaluation(
                bad_set,
                expected_case_set_hash=bad_set.case_set_hash,
                call_cap=1,
                monetary_ceiling_usd=Decimal("5.00"),
                fit_telemetry_provider=lambda p: _matching_telemetry(
                    p, model="claude-sonnet-unexpected"
                ),
                cv_telemetry_provider=lambda p: _matching_telemetry(
                    p, model="claude-sonnet-unexpected"
                ),
            )
        with TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "incomplete"
            write_live_evaluation_reports(
                bad_ctx.exception.partial_result,
                output_dir=out,
                generated_at="2026-01-01T00:00:00+00:00",
            )
            doc = json.loads(
                (out / "live_evaluation_results.json").read_text(encoding="utf-8")
            )
            summary = (out / "live_evaluation_summary.txt").read_text(encoding="utf-8")
            self.assertFalse(doc["actual_spend_complete"])
            self.assertIn("actual_spend_complete=False", summary)
            self.assertIn("incomplete", summary.lower())
            self.assertIn(
                "one or more attempted provider calls could not be priced safely",
                summary,
            )
            self.assertNotIn(
                "one or more returned responses could not be priced safely",
                summary,
            )


    def test_request_id_is_hashed_in_summary_and_raw_only_in_external_evidence(self):
        case_set = load_case_set_from_mapping(_valid_case_set())
        raw_id = "req_live_secret_id"
        evidence: list[dict] = []

        def provider(_payload):
            return _matching_telemetry(_payload, request_id=raw_id)

        def writer(**kwargs):
            evidence.append(kwargs)

        run = run_live_evaluation(
            case_set,

            expected_case_set_hash=case_set.case_set_hash,
            call_cap=1,
            monetary_ceiling_usd=Decimal("5.00"),
            fit_telemetry_provider=provider,
            cv_telemetry_provider=provider,
            raw_evidence_writer=writer,
        )
        self.assertEqual(run.results[0].hashed_request_id, hash_request_id(raw_id))
        self.assertNotEqual(run.results[0].hashed_request_id, raw_id)
        _assert_strictly_redacted_result(self, run.results[0])
        result_repr = repr(run.results[0])
        self.assertNotIn(raw_id, result_repr)
        serialised = evidence[0]["serialised_raw_response"]
        self.assertNotIn(serialised, result_repr)
        self.assertEqual(evidence[0]["raw_request_id"], raw_id)

        with TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "out"
            write_live_evaluation_reports(
                run, output_dir=out, generated_at="2026-01-01T00:00:00+00:00"
            )
            doc = json.loads(
                (out / "live_evaluation_results.json").read_text(encoding="utf-8")
            )
            text = json.dumps(doc)
            self.assertNotIn(raw_id, text)
            self.assertIn(hash_request_id(raw_id), text)

    def test_raw_response_artifact_writes_only_outside_repository(self):
        from apps.ai_agents.evaluation.live_reporting import append_raw_live_evidence

        with TemporaryDirectory() as temp_dir:
            raw_dir = Path(temp_dir) / "raw"
            path = append_raw_live_evidence(
                raw_evidence_dir=raw_dir,
                case_id="CASE-001",
                raw_request_id="req_x",
                serialised_raw_response='{"ok":true}',
                raw_response_hash="c" * 64,
            )
            self.assertTrue(path.exists())
            self.assertEqual(path.name, "raw_live_evidence.jsonl")
            root = repository_root()
            self.assertNotEqual(path.resolve(), root)
            self.assertTrue(root not in path.resolve().parents)

        case_set = load_case_set_from_mapping(_valid_case_set())
        write_exc = OSError("raw write failed")

        def provider(_payload):
            return _matching_telemetry(_payload)

        def failing_writer(**kwargs):
            raise write_exc

        with self.assertRaises(LiveEvaluationError) as ctx:
            run_live_evaluation(
                case_set,

                expected_case_set_hash=case_set.case_set_hash,
                call_cap=1,
                monetary_ceiling_usd=Decimal("5.00"),
                fit_telemetry_provider=provider,
                cv_telemetry_provider=provider,
                raw_evidence_writer=failing_writer,
            )
        self.assertEqual(ctx.exception.category, "raw_evidence_write_failure")
        self.assertIsNotNone(ctx.exception.partial_result)
        self.assertEqual(ctx.exception.partial_result.calls_made, 1)
        self.assertEqual(len(ctx.exception.partial_result.results), 1)
        _assert_strictly_redacted_result(self, ctx.exception.partial_result.results[0])
        self.assertIs(ctx.exception.__cause__, write_exc)
        self.assertNotIn("raw write failed", str(ctx.exception))

        case_path_data = _valid_case_set()
        raw_write_exc = OSError("raw write failed")
        with TemporaryDirectory() as temp_dir:
            case_path = _write_json(Path(temp_dir) / "cases.json", case_path_data)
            expected_hash = _case_set_hash(case_path_data)
            with patch.dict(os.environ, {"AI_LIVE_EVALUATION_ENABLED": "1"}):
                with (
                    patch(
                        "apps.ai_agents.management.commands."
                        "evaluate_ai_explanations_live."
                        "compose_fit_scoring_telemetry_provider",
                        return_value=lambda p: _matching_telemetry(p),
                    ),
                    patch(
                        "apps.ai_agents.management.commands."
                        "evaluate_ai_explanations_live."
                        "compose_cv_tailoring_telemetry_provider",
                        return_value=lambda p: _matching_telemetry(p),
                    ),
                    patch(
                        "apps.ai_agents.management.commands."
                        "evaluate_ai_explanations_live."
                        "append_raw_live_evidence",
                        side_effect=raw_write_exc,
                    ),
                ):
                    with self.assertRaises(CommandError) as cmd_ctx:
                        _live_command(
                            case_path=case_path,
                            output_dir=Path(temp_dir) / "cmd_out",
                            raw_dir=Path(temp_dir) / "cmd_raw",
                            expected_hash=expected_hash,
                            call_cap="1",
                        )
                    self.assertIn(
                        "raw_evidence_write_failure",
                        str(cmd_ctx.exception),
                    )
                    self.assertIs(cmd_ctx.exception.__cause__, raw_write_exc)
                    self.assertNotIn("raw write failed", str(cmd_ctx.exception))
                    out_dir = Path(temp_dir) / "cmd_out"
                    self.assertTrue(
                        (out_dir / "live_evaluation_results.json").exists()
                    )
                    self.assertTrue((out_dir / "live_evaluation_summary.txt").exists())
                    doc = json.loads(
                        (out_dir / "live_evaluation_results.json").read_text(
                            encoding="utf-8"
                        )
                    )
                    summary = (out_dir / "live_evaluation_summary.txt").read_text(
                        encoding="utf-8"
                    )
                    self.assertTrue(doc["partial"])
                    self.assertEqual(doc["calls_made"], 1)
                    self.assertEqual(len(doc["results"]), 1)
                    self.assertNotIn("raw_request_id", doc["results"][0])
                    self.assertNotIn("serialised_raw_response", doc["results"][0])
                    raw_id = "req_test_abc"
                    serialised = json.dumps(
                        _valid_fit_payload(),
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    self.assertNotIn(raw_id, json.dumps(doc))
                    self.assertNotIn(serialised, summary)


    def test_contract_manifest_hash_differs_from_request_payload_hash(self):
        case_set = load_case_set_from_mapping(_valid_case_set())
        from apps.ai_agents.evaluation.live_runner import (
            _build_payload_and_contract,
            _request_kwargs_for_case,
        )

        case = case_set.cases[0]
        payload, contract_hash = _build_payload_and_contract(case)
        kwargs = _request_kwargs_for_case(case, payload)
        request_hash = hash_request_payload(kwargs)
        self.assertNotEqual(contract_hash, request_hash)

        calls = {"n": 0}
        evidence: list[dict] = []

        def provider(_payload):
            calls["n"] += 1
            body = _valid_fit_payload()
            body["unknown_contact"] = {"email": "hashmismatch@example.com"}
            return _matching_telemetry(
                _payload,
                request_payload_hash="f" * 64,
                payload=body,
            )

        def writer(**kwargs):
            evidence.append(kwargs)

        with self.assertRaises(LiveEvaluationError) as ctx:
            run_live_evaluation(
                case_set,
                expected_case_set_hash=case_set.case_set_hash,
                call_cap=2,
                monetary_ceiling_usd=Decimal("5.00"),
                fit_telemetry_provider=provider,
                cv_telemetry_provider=provider,
                raw_evidence_writer=writer,
            )
        self.assertEqual(ctx.exception.category, "request_payload_hash_mismatch")
        partial = ctx.exception.partial_result
        self.assertIsNotNone(partial)
        self.assertEqual(partial.calls_made, 1)
        self.assertEqual(len(partial.results), 1)
        result = partial.results[0]
        expected_cost = calculate_token_cost(input_tokens=100, output_tokens=50)
        self.assertEqual(result.actual_cost_usd, expected_cost)
        self.assertEqual(partial.actual_spend_usd, expected_cost)
        self.assertTrue(partial.actual_spend_complete)
        self.assertEqual(calls["n"], 1)
        self.assertEqual(len(evidence), 1)
        self.assertIn("REQUEST_PAYLOAD_HASH_MISMATCH", result.breach_codes)
        self.assertIn("OUTPUT_SECRET_OR_PERSONAL_DATA", result.breach_codes)
        _assert_strictly_redacted_result(self, result)
        err = str(ctx.exception)
        self.assertNotIn("f" * 64, err)
        self.assertNotIn(request_hash, err)

        write_exc = OSError("raw write failed")

        def failing_writer(**kwargs):
            raise write_exc

        with self.assertRaises(LiveEvaluationError) as fail_ctx:
            run_live_evaluation(
                case_set,
                expected_case_set_hash=case_set.case_set_hash,
                call_cap=2,
                monetary_ceiling_usd=Decimal("5.00"),
                fit_telemetry_provider=provider,
                cv_telemetry_provider=provider,
                raw_evidence_writer=failing_writer,
            )
        self.assertEqual(fail_ctx.exception.category, "raw_evidence_write_failure")
        fail_partial = fail_ctx.exception.partial_result
        self.assertIsNotNone(fail_partial)
        self.assertEqual(len(fail_partial.results), 1)
        self.assertIn(
            "REQUEST_PAYLOAD_HASH_MISMATCH",
            fail_partial.results[0].breach_codes,
        )

        combined_calls = {"n": 0}
        combined_evidence: list[dict] = []

        def combined_provider(_payload):
            combined_calls["n"] += 1
            body = _valid_fit_payload()
            body["unknown_contact"] = {"email": "combined@example.com"}
            return _matching_telemetry(
                _payload,
                input_tokens=4_000_000,
                output_tokens=400_000,
                request_payload_hash="f" * 64,
                payload=body,
            )

        def combined_writer(**kwargs):
            combined_evidence.append(kwargs)

        with self.assertRaises(LiveEvaluationError) as combined_ctx:
            run_live_evaluation(
                case_set,
                expected_case_set_hash=case_set.case_set_hash,
                call_cap=2,
                monetary_ceiling_usd=Decimal("5.00"),
                fit_telemetry_provider=combined_provider,
                cv_telemetry_provider=combined_provider,
                raw_evidence_writer=combined_writer,
            )
        self.assertEqual(combined_ctx.exception.category, "actual_cost_breach")
        combined_partial = combined_ctx.exception.partial_result
        self.assertIsNotNone(combined_partial)
        self.assertEqual(combined_partial.stop_reason, "actual_cost_breach")
        self.assertEqual(combined_partial.calls_made, 1)
        self.assertEqual(len(combined_partial.results), 1)
        combined_result = combined_partial.results[0]
        self.assertIn("ACTUAL_COST_BREACH", combined_result.breach_codes)
        self.assertIn("REQUEST_PAYLOAD_HASH_MISMATCH", combined_result.breach_codes)
        self.assertIn("OUTPUT_SECRET_OR_PERSONAL_DATA", combined_result.breach_codes)
        self.assertEqual(combined_result.safe_error_category, "actual_cost_breach")
        self.assertEqual(combined_result.parser_status, "not_run")
        self.assertIsNotNone(combined_result.actual_cost_usd)
        self.assertEqual(combined_partial.actual_spend_usd, combined_result.actual_cost_usd)
        self.assertTrue(combined_partial.actual_spend_complete)
        self.assertEqual(combined_calls["n"], 1)
        self.assertEqual(len(combined_evidence), 1)
        self.assertEqual(
            combined_partial.hard_breach_counts.get("ACTUAL_COST_BREACH"),
            1,
        )
        self.assertEqual(
            combined_partial.hard_breach_counts.get("REQUEST_PAYLOAD_HASH_MISMATCH"),
            1,
        )
        _assert_strictly_redacted_result(self, combined_result)


    def test_mocked_symlink_or_junction_escape_into_repository_is_rejected(self):
        root = repository_root()
        fake = Path("/tmp/external-looking-path")
        with patch.object(Path, "resolve", return_value=root / "escaped"):
            with self.assertRaises(PathBoundaryError):
                validate_external_path(fake, label="output_dir")

    def test_live_runner_performs_no_database_access(self):
        import apps.ai_agents.evaluation.live_runner as mod

        source = Path(mod.__file__).read_text(encoding="utf-8")
        self.assertNotIn("django.db", source)
        self.assertNotIn("apps.applications", source)
        self.assertNotIn("from django.db", source)
        self.assertNotIn("def _require_matching_request_payload_hash", source)
        self.assertIn("def _request_payload_hash_matches", source)
        self.assertTrue(hasattr(mod, "_request_payload_hash_matches"))
        self.assertFalse(hasattr(mod, "_require_matching_request_payload_hash"))

    def test_live_tests_mock_transport_and_make_no_network_requests(self):
        with patch("socket.socket") as sock:
            case_set = load_case_set_from_mapping(_valid_case_set())
            run_live_evaluation(
                case_set,

                expected_case_set_hash=case_set.case_set_hash,
                call_cap=1,
                monetary_ceiling_usd=Decimal("5.00"),
                fit_telemetry_provider=_matching_telemetry,
                cv_telemetry_provider=_matching_telemetry,
            )
            sock.assert_not_called()

    def test_live_command_cannot_activate_user_facing_runtime(self):
        source = Path(
            "apps/ai_agents/management/commands/evaluate_ai_explanations_live.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("compose_fit_scoring_provider(", source)
        self.assertNotIn("compose_cv_tailoring_provider(", source)
        self.assertNotIn("AI_EXPLANATION_PROVIDER =", source)
        self.assertIn("compose_fit_scoring_telemetry_provider", source)

    def test_offline_replay_command_still_rejects_live_mode(self):
        with TemporaryDirectory() as temp_dir:
            case_path = _write_json(Path(temp_dir) / "cases.json", _valid_case_set())
            with self.assertRaises(CommandError) as ctx:
                call_command(
                    "evaluate_ai_explanations",
                    "--mode",
                    "live",
                    "--case-set",
                    str(case_path),
                    "--output-dir",
                    str(Path(temp_dir) / "out"),
                )
            self.assertIn("live", str(ctx.exception).lower())

    @override_settings(AI_EXPLANATION_PROVIDER="mock", ANTHROPIC_API_KEY="sk-test")
    def test_telemetry_composition_returns_none_when_live_not_permitted(self):
        self.assertIsNone(compose_fit_scoring_telemetry_provider())
        self.assertIsNone(compose_cv_tailoring_telemetry_provider())

    @override_settings(AI_EXPLANATION_PROVIDER="live", ANTHROPIC_API_KEY="sk-test-key")
    def test_telemetry_composition_reads_credentials_only_in_provider_factory(self):
        with patch(
            "apps.ai_agents.provider_factory.make_claude_fit_telemetry_provider"
        ) as fit_maker, patch(
            "apps.ai_agents.provider_factory.make_claude_cv_tailoring_telemetry_provider"
        ) as cv_maker:
            fit_maker.return_value = _matching_telemetry
            cv_maker.return_value = _matching_telemetry
            compose_fit_scoring_telemetry_provider()
            compose_cv_tailoring_telemetry_provider()
            fit_maker.assert_called_once_with("sk-test-key")
            cv_maker.assert_called_once_with("sk-test-key")
        # evaluation modules must not reference the setting attribute path
        for rel in (
            "apps/ai_agents/evaluation/live_runner.py",
            "apps/ai_agents/evaluation/live_reporting.py",
            "apps/ai_agents/management/commands/evaluate_ai_explanations_live.py",
        ):
            text = Path(rel).read_text(encoding="utf-8")
            forbidden = "settings." + "ANTHROPIC_API_KEY"
            self.assertNotIn(forbidden, text)
            getattr_needle = 'getattr(settings, "' + "ANTHROPIC_API_KEY" + '"'
            self.assertNotIn(getattr_needle, text)

    def test_evaluation_modules_do_not_reference_anthropic_api_key_setting(self):
        for rel in (
            "apps/ai_agents/evaluation/live_runner.py",
            "apps/ai_agents/evaluation/live_reporting.py",
            "apps/ai_agents/claude_provider.py",
        ):
            text = Path(rel).read_text(encoding="utf-8")
            self.assertNotIn("settings." + "ANTHROPIC_API_KEY", text)

    def test_fit_shared_request_helper_preserves_request_and_parsed_output(self):
        expected_fit_payload = _valid_fit_payload()
        payload_text = json.dumps(expected_fit_payload)
        message = _fake_message(text=payload_text)
        captured: list[dict] = []

        class FakeMessages:
            def create(self, **kwargs):
                captured.append(dict(kwargs))
                return message

        class FakeClient:
            def __init__(self, *args, **kwargs):
                self.messages = FakeMessages()

        prompt = {
            "company_name": "Acme",
            "job_title": "Analyst",
            "location": "London",
            "job_description": "Python SQL Excel",
            "rule_based_fit_score": 70,
            "rule_based_recommendation": "Apply",
            "matched_skills": ["Python"],
            "risks": [],
            "deal_breakers": [],
            "required_output_schema": {"fields": ["ai_fit_score"]},
        }
        with patch.object(claude_provider_module.anthropic, "Anthropic", FakeClient):
            normal = make_claude_provider("sk-test")
            telemetry = make_claude_fit_telemetry_provider("sk-test")
            parsed = normal(prompt)
            tele = telemetry(prompt)
        self.assertEqual(len(captured), 2)
        self.assertEqual(captured[0], captured[1])
        self.assertEqual(
            set(captured[0].keys()),
            {"model", "max_tokens", "system", "messages"},
        )
        self.assertEqual(captured[0]["model"], CLAUDE_MODEL)
        self.assertEqual(captured[0]["max_tokens"], CLAUDE_MAX_TOKENS)
        fit_hash_first = _test_owned_request_payload_hash(captured[0])
        fit_hash_second = _test_owned_request_payload_hash(captured[1])
        self.assertEqual(fit_hash_first, PLANE_A_BASELINE_FIT_REQUEST_HASH)
        self.assertEqual(fit_hash_second, PLANE_A_BASELINE_FIT_REQUEST_HASH)
        self.assertEqual(parsed, expected_fit_payload)
        self.assertEqual(tele.parsed_payload, expected_fit_payload)
        self.assertEqual(parsed, tele.parsed_payload)
        self.assertEqual(tele.request_payload_hash, PLANE_A_BASELINE_FIT_REQUEST_HASH)
        self.assertEqual(hash_request_payload(captured[0]), fit_hash_first)
        self.assertEqual(
            build_fit_messages_create_kwargs(prompt),
            captured[0],
        )


    def test_cv_shared_request_helper_preserves_request_and_parsed_output(self):
        expected_cv_payload = _valid_cv_payload()
        payload_text = json.dumps(expected_cv_payload)
        message = _fake_message(text=payload_text)
        captured: list[dict] = []

        class FakeMessages:
            def create(self, **kwargs):
                captured.append(dict(kwargs))
                return message

        class FakeClient:
            def __init__(self, *args, **kwargs):
                self.messages = FakeMessages()

        prompt = {
            "company_name": "Acme",
            "job_title": "Analyst",
            "location": "London",
            "job_description": "Python SQL Excel",
            "cv_evidence": "",
            "rule_based": {
                "cv_angle": "DA",
                "role_family": "DA",
                "matched_skills": ["python"],
                "partial_matches": [],
                "missing_skills": ["dbt"],
                "strongest_projects": [],
                "risks": [],
                "deal_breakers": [],
            },
            "evidence_catalog": {
                "strong_skills": ["python"],
                "partial_skills": [],
                "gap_learning_skills": ["dbt"],
                "projects": [],
            },
            "required_output_schema": {
                "fields": ["semantic_matched_skills"],
                "forbidden_fields": ["full_cv_text"],
            },
            "safety_rules": ["Advisory only"],
        }
        with patch.object(claude_provider_module.anthropic, "Anthropic", FakeClient):
            normal = make_claude_cv_tailoring_provider("sk-test")
            telemetry = make_claude_cv_tailoring_telemetry_provider("sk-test")
            parsed = normal(prompt)
            tele = telemetry(prompt)
        self.assertEqual(len(captured), 2)
        self.assertEqual(captured[0], captured[1])
        self.assertEqual(
            set(captured[0].keys()),
            {"model", "max_tokens", "system", "messages"},
        )
        self.assertEqual(captured[0]["model"], CLAUDE_MODEL)
        self.assertEqual(captured[0]["max_tokens"], CLAUDE_MAX_TOKENS)
        cv_hash_first = _test_owned_request_payload_hash(captured[0])
        cv_hash_second = _test_owned_request_payload_hash(captured[1])
        self.assertEqual(cv_hash_first, PLANE_A_BASELINE_CV_REQUEST_HASH)
        self.assertEqual(cv_hash_second, PLANE_A_BASELINE_CV_REQUEST_HASH)
        self.assertEqual(parsed, expected_cv_payload)
        self.assertEqual(tele.parsed_payload, expected_cv_payload)
        self.assertEqual(parsed, tele.parsed_payload)
        self.assertEqual(tele.request_payload_hash, PLANE_A_BASELINE_CV_REQUEST_HASH)
        self.assertEqual(hash_request_payload(captured[0]), cv_hash_first)
        self.assertEqual(
            build_cv_messages_create_kwargs(prompt),
            captured[0],
        )

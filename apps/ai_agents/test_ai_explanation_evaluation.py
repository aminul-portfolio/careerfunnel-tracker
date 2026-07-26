"""Phase 2B offline and structured-replay evaluation harness tests."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from apps.ai_agents.evaluation.cases import (
    CASE_SET_SCHEMA_VERSION,
    REPLAY_BUNDLE_SCHEMA_VERSION,
    CaseValidationError,
    EvaluationCaseSet,
    compute_replay_bundle_hash,
    load_case_set,
    load_case_set_from_mapping,
    load_replay_bundle_from_mapping,
    sha256_hex,
)
from apps.ai_agents.evaluation.reporting import (
    build_results_document,
    ensure_outside_repository,
    write_evaluation_reports,
)
from apps.ai_agents.evaluation.runner import (
    EvaluationRunnerError,
    evaluate_case,
    run_evaluation,
)
from apps.ai_agents.services import (
    build_cv_tailoring_semantic_prompt,
    build_openai_fit_scoring_prompt,
    parse_ai_fit_scoring_payload,
    parse_cv_tailoring_semantic_payload,
)


def _repo_root() -> Path:
    return Path(settings.BASE_DIR).resolve()


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
    offline_response: dict | None = None,
    **overrides,
) -> dict:
    if offline_response is None:
        if surface == "fit":
            offline_response = {
                "result_type": "payload",
                "payload": _valid_fit_payload(),
                "error_class": None,
            }
        else:
            offline_response = {
                "result_type": "payload",
                "payload": _valid_cv_payload(),
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
        "offline_response": offline_response,
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


def _replay_bundle_for_case_set(case_set_data: dict, case_set_hash: str) -> dict:
    responses = []
    for case in case_set_data["cases"]:
        envelope = case["offline_response"]
        responses.append(
            {
                "case_id": case["case_id"],
                "result_type": envelope["result_type"],
                "payload": envelope["payload"],
                "error_class": envelope["error_class"],
            }
        )
    data = {
        "schema_version": REPLAY_BUNDLE_SCHEMA_VERSION,
        "case_set_hash": case_set_hash,
        "responses": responses,
    }
    data["bundle_hash"] = compute_replay_bundle_hash(data)
    return data


class Phase2BEvaluationHarnessTests(SimpleTestCase):
    def test_case_loader_accepts_valid_external_json(self):
        with self.subTest("valid non-empty external case set loads"):
            with TemporaryDirectory() as temp_dir:
                path = _write_json(
                    Path(temp_dir) / "cases.json", _valid_case_set()
                )
                loaded = load_case_set(path)
            self.assertEqual(loaded.schema_version, CASE_SET_SCHEMA_VERSION)
            self.assertEqual(len(loaded.cases), 1)
            self.assertEqual(loaded.cases[0].case_id, "CASE-001")
            self.assertTrue(loaded.case_set_hash)

        with self.subTest("empty case set is rejected before hashing"):
            data = _valid_case_set()
            data["cases"] = []
            with self.assertRaises(CaseValidationError) as ctx:
                load_case_set_from_mapping(data)
            self.assertIn("empty_case_set", str(ctx.exception))

    def test_case_loader_rejects_missing_required_field(self):
        data = _valid_case_set()
        del data["cases"][0]["job_title"]
        with self.assertRaises(CaseValidationError) as ctx:
            load_case_set_from_mapping(data)
        self.assertIn("missing_required_keys", str(ctx.exception))

    def test_case_loader_rejects_unknown_field(self):
        data = _valid_case_set()
        secret_like_key = "sk-ant-unknown-shadow-key"
        data["cases"][0][secret_like_key] = "placeholder-value"
        with self.assertRaises(CaseValidationError) as ctx:
            load_case_set_from_mapping(data)
        message = str(ctx.exception)
        self.assertIn("unknown_keys_present", message)
        self.assertIn("unknown_key_count:1", message)
        self.assertNotIn(secret_like_key, message)
        self.assertNotIn("sk-ant", message)
        self.assertNotIn("placeholder-value", message)

    def test_case_loader_rejects_duplicate_case_ids(self):
        data = _valid_case_set(
            [
                _valid_case(case_id="DUP"),
                _valid_case(case_id="DUP", surface="cv_jpa"),
            ]
        )
        with self.assertRaises(CaseValidationError) as ctx:
            load_case_set_from_mapping(data)
        self.assertIn("duplicate_case_id", str(ctx.exception))

    def test_case_loader_rejects_invalid_surface(self):
        data = _valid_case_set([_valid_case(surface="live_agent")])
        with self.assertRaises(CaseValidationError) as ctx:
            load_case_set_from_mapping(data)
        self.assertIn("invalid_surface", str(ctx.exception))

    def test_case_loader_rejects_prohibited_structured_fields(self):
        data = _valid_case_set()
        data["cases"][0]["offline_response"]["payload"]["notes"] = (
            "should never appear"
        )
        with self.assertRaises(CaseValidationError) as ctx:
            load_case_set_from_mapping(data)
        message = str(ctx.exception)
        self.assertIn("prohibited_structured_field", message)
        self.assertNotIn("should never appear", message)

    def test_case_loader_rejects_secret_like_content(self):
        with self.subTest("secret-like string value is rejected and not echoed"):
            data = _valid_case_set()
            data["cases"][0]["job_description"] = "token sk-ant-secretvaluehere"
            with self.assertRaises(CaseValidationError) as ctx:
                load_case_set_from_mapping(data)
            message = str(ctx.exception)
            self.assertIn("secret_like_content", message)
            self.assertNotIn("sk-ant-secretvaluehere", message)
            self.assertNotIn("sk-ant", message)

        with self.subTest("secret-like nested dict key is rejected and not echoed"):
            data = _valid_case_set()
            secret_like_key = "sk-ant-nested-shadow-key"
            data["cases"][0]["offline_response"]["payload"][secret_like_key] = (
                "benign-value"
            )
            with self.assertRaises(CaseValidationError) as ctx:
                load_case_set_from_mapping(data)
            message = str(ctx.exception)
            self.assertIn("secret_like_key", message)
            self.assertNotIn(secret_like_key, message)
            self.assertNotIn("sk-ant", message)
            self.assertNotIn("benign-value", message)

        with self.subTest("secret-like case_id is rejected and not echoed"):
            data = _valid_case_set()
            secret_case_id = "sk-ant-case-id-placeholder"
            data["cases"][0]["case_id"] = secret_case_id
            with self.assertRaises(CaseValidationError) as ctx:
                load_case_set_from_mapping(data)
            message = str(ctx.exception)
            self.assertIn("secret_like_case_id", message)
            self.assertNotIn(secret_case_id, message)
            self.assertNotIn("sk-ant", message)

        with self.subTest("personal-contact case_id is rejected and not echoed"):
            data = _valid_case_set()
            contact_case_id = "candidate@example.com"
            data["cases"][0]["case_id"] = contact_case_id
            with self.assertRaises(CaseValidationError) as ctx:
                load_case_set_from_mapping(data)
            message = str(ctx.exception)
            self.assertIn("personal_contact_case_id", message)
            self.assertNotIn(contact_case_id, message)
            self.assertNotIn("candidate@", message)
            self.assertNotIn("example.com", message)

        with self.subTest(
            "secret-like replay case_id is rejected before unknown-case handling"
        ):
            loaded = load_case_set_from_mapping(_valid_case_set())
            secret_replay_id = "sk-ant-replay-case-id"
            bundle = {
                "schema_version": REPLAY_BUNDLE_SCHEMA_VERSION,
                "case_set_hash": loaded.case_set_hash,
                "responses": [
                    {
                        "case_id": secret_replay_id,
                        "result_type": "timeout",
                        "payload": None,
                        "error_class": "TimeoutError",
                    }
                ],
                "bundle_hash": "0" * 64,
            }
            with self.assertRaises(CaseValidationError) as ctx:
                load_replay_bundle_from_mapping(
                    bundle,
                    expected_case_ids=frozenset(
                        case.case_id for case in loaded.cases
                    ),
                    expected_case_set_hash=loaded.case_set_hash,
                )
            message = str(ctx.exception)
            self.assertIn("secret_like_case_id", message)
            self.assertNotIn(secret_replay_id, message)
            self.assertNotIn("sk-ant", message)
            self.assertNotIn("unknown_case_id", message)
            self.assertNotIn("duplicate_case_id", message)

    def test_case_set_hash_is_deterministic(self):
        data = _valid_case_set()
        first = load_case_set_from_mapping(copy.deepcopy(data))
        second = load_case_set_from_mapping(copy.deepcopy(data))
        self.assertEqual(first.case_set_hash, second.case_set_hash)
        self.assertEqual(first.case_set_hash, sha256_hex(data))

    def test_case_set_hash_changes_when_case_content_changes(self):
        data = _valid_case_set()
        original = load_case_set_from_mapping(copy.deepcopy(data))
        data["cases"][0]["job_description"] = (
            "Python SQL Excel reporting junior dashboard role changed"
        )
        changed = load_case_set_from_mapping(data)
        self.assertNotEqual(original.case_set_hash, changed.case_set_hash)

    def test_command_requires_explicit_mode(self):
        with TemporaryDirectory() as temp_dir:
            case_path = _write_json(Path(temp_dir) / "cases.json", _valid_case_set())
            out = Path(temp_dir) / "out"
            with self.assertRaises(CommandError):
                call_command(
                    "evaluate_ai_explanations",
                    case_set=str(case_path),
                    output_dir=str(out),
                )

    def test_command_requires_case_set_path_outside_repository(self):
        with TemporaryDirectory() as temp_dir:
            out = Path(temp_dir) / "out"
            with self.assertRaises(CommandError) as ctx:
                call_command(
                    "evaluate_ai_explanations",
                    mode="offline",
                    case_set=str(_repo_root() / "missing-cases.json"),
                    output_dir=str(out),
                )
            self.assertIn("outside the repository", str(ctx.exception).lower())

    def test_command_requires_output_directory_outside_repository(self):
        with TemporaryDirectory() as temp_dir:
            case_path = _write_json(Path(temp_dir) / "cases.json", _valid_case_set())
            with self.assertRaises(CommandError) as ctx:
                call_command(
                    "evaluate_ai_explanations",
                    mode="offline",
                    case_set=str(case_path),
                    output_dir=str(_repo_root() / "tmp-eval-out"),
                )
            self.assertIn("outside the repository", str(ctx.exception).lower())

    def test_command_rejects_repository_case_set_path(self):
        repo_case = _repo_root() / "apps" / "ai_agents" / "services.py"
        with TemporaryDirectory() as temp_dir:
            with self.assertRaises(CommandError):
                call_command(
                    "evaluate_ai_explanations",
                    mode="offline",
                    case_set=str(repo_case),
                    output_dir=str(Path(temp_dir) / "out"),
                )

    def test_command_rejects_repository_output_path(self):
        with TemporaryDirectory() as temp_dir:
            case_path = _write_json(Path(temp_dir) / "cases.json", _valid_case_set())
            with self.assertRaises(CommandError):
                call_command(
                    "evaluate_ai_explanations",
                    mode="offline",
                    case_set=str(case_path),
                    output_dir=str(_repo_root()),
                )

    def test_command_rejects_live_mode_in_phase2b(self):
        with TemporaryDirectory() as temp_dir:
            case_path = _write_json(Path(temp_dir) / "cases.json", _valid_case_set())
            with self.assertRaises(CommandError):
                call_command(
                    "evaluate_ai_explanations",
                    mode="live",
                    case_set=str(case_path),
                    output_dir=str(Path(temp_dir) / "out"),
                )

    def test_offline_mode_does_not_compose_or_call_live_provider(self):
        case_set = load_case_set_from_mapping(_valid_case_set())
        with (
            patch(
                "apps.ai_agents.provider_factory.compose_fit_scoring_provider"
            ) as compose_fit,
            patch(
                "apps.ai_agents.provider_factory.compose_cv_tailoring_provider"
            ) as compose_cv,
            patch("apps.ai_agents.claude_provider.anthropic.Anthropic") as anthropic_cls,
        ):
            run = run_evaluation(case_set, mode="offline")
        compose_fit.assert_not_called()
        compose_cv.assert_not_called()
        anthropic_cls.assert_not_called()
        self.assertEqual(run.overall_result, "PASS")

    def test_replay_mode_does_not_compose_or_call_live_provider(self):
        data = _valid_case_set()
        case_set = load_case_set_from_mapping(data)
        bundle = load_replay_bundle_from_mapping(
            _replay_bundle_for_case_set(data, case_set.case_set_hash),
            expected_case_ids=frozenset(case.case_id for case in case_set.cases),
            expected_case_set_hash=case_set.case_set_hash,
        )
        with (
            patch(
                "apps.ai_agents.provider_factory.compose_fit_scoring_provider"
            ) as compose_fit,
            patch(
                "apps.ai_agents.provider_factory.compose_cv_tailoring_provider"
            ) as compose_cv,
            patch("apps.ai_agents.claude_provider.anthropic.Anthropic") as anthropic_cls,
        ):
            run = run_evaluation(
                case_set,
                mode="replay",
                replay_bundle=bundle,
            )
        compose_fit.assert_not_called()
        compose_cv.assert_not_called()
        anthropic_cls.assert_not_called()
        self.assertEqual(run.case_count, 1)

    def test_fit_surface_reuses_existing_payload_builder(self):
        case_set = load_case_set_from_mapping(
            _valid_case_set([_valid_case(surface="fit")])
        )
        with patch(
            "apps.ai_agents.evaluation.runner.build_openai_fit_scoring_prompt",
            wraps=build_openai_fit_scoring_prompt,
        ) as mocked:
            run_evaluation(case_set, mode="offline")
        mocked.assert_called()

    def test_jpa_cv_surface_reuses_existing_payload_builder(self):
        case_set = load_case_set_from_mapping(
            _valid_case_set([_valid_case(case_id="CV-1", surface="cv_jpa")])
        )
        with patch(
            "apps.ai_agents.evaluation.runner.build_cv_tailoring_semantic_prompt",
            wraps=build_cv_tailoring_semantic_prompt,
        ) as mocked:
            run_evaluation(case_set, mode="offline")
        mocked.assert_called()
        kwargs = mocked.call_args.kwargs
        self.assertEqual(kwargs.get("cv_evidence", ""), "")

    def test_agent_pack_cv_surface_reuses_existing_payload_builder_with_blank_cv_evidence(
        self,
    ):
        case_set = load_case_set_from_mapping(
            _valid_case_set([_valid_case(case_id="AP-1", surface="cv_agent_pack")])
        )
        with patch(
            "apps.ai_agents.evaluation.runner.build_cv_tailoring_semantic_prompt",
            wraps=build_cv_tailoring_semantic_prompt,
        ) as mocked:
            run_evaluation(case_set, mode="offline")
        mocked.assert_called()
        self.assertEqual(mocked.call_args.kwargs.get("cv_evidence"), "")

    def test_fit_surface_reuses_existing_output_parser(self):
        case_set = load_case_set_from_mapping(
            _valid_case_set([_valid_case(surface="fit")])
        )
        with patch(
            "apps.ai_agents.evaluation.runner.parse_ai_fit_scoring_payload",
            wraps=parse_ai_fit_scoring_payload,
        ) as mocked:
            run_evaluation(case_set, mode="offline")
        mocked.assert_called()

    def test_cv_surfaces_reuse_existing_output_parser(self):
        for surface in ("cv_jpa", "cv_agent_pack"):
            with self.subTest(surface=surface):
                case_set = load_case_set_from_mapping(
                    _valid_case_set(
                        [_valid_case(case_id=f"{surface}-1", surface=surface)]
                    )
                )
                with patch(
                    "apps.ai_agents.evaluation.runner.parse_cv_tailoring_semantic_payload",
                    wraps=parse_cv_tailoring_semantic_payload,
                ) as mocked:
                    run_evaluation(case_set, mode="offline")
                mocked.assert_called()

    def test_contract_valid_result_is_pass(self):
        with self.subTest("valid non-empty case set produces PASS"):
            case_set = load_case_set_from_mapping(
                _valid_case_set([_valid_case(human_groundedness=2)])
            )
            run = run_evaluation(case_set, mode="offline")
            self.assertEqual(run.results[0].outcome, "PASS")
            self.assertEqual(run.overall_result, "PASS")

        with self.subTest("empty runner input is rejected without PASS"):
            empty = EvaluationCaseSet(
                schema_version=CASE_SET_SCHEMA_VERSION,
                cases=(),
                case_set_hash="0" * 64,
            )
            with self.assertRaises(ValueError) as ctx:
                run_evaluation(empty, mode="offline")
            message = str(ctx.exception)
            self.assertIn("evaluation_requires_at_least_one_case", message)
            self.assertNotIn("PASS", message)

    def test_forbidden_claim_is_fail(self):
        payload = _valid_fit_payload(
            reasoning_summary="Candidate auto-applies to every role."
        )
        case = _valid_case(
            forbidden_claims=["auto-applies"],
            offline_response={
                "result_type": "payload",
                "payload": payload,
                "error_class": None,
            },
        )
        run = run_evaluation(load_case_set_from_mapping(_valid_case_set([case])), mode="offline")
        self.assertEqual(run.results[0].outcome, "FAIL")
        self.assertIn("FORBIDDEN_CLAIM", run.results[0].breach_codes)

    def test_learning_target_as_verified_is_fail(self):
        with self.subTest("learning target in matched field is a hard breach"):
            payload = _valid_cv_payload(
                semantic_matched_skills=["dbt", "python"],
            )
            case = _valid_case(
                case_id="LT-1",
                surface="cv_jpa",
                learning_target_skills=["dbt"],
                offline_response={
                    "result_type": "payload",
                    "payload": payload,
                    "error_class": None,
                },
            )
            run = run_evaluation(
                load_case_set_from_mapping(_valid_case_set([case])),
                mode="offline",
            )
            self.assertEqual(run.results[0].outcome, "FAIL")
            self.assertIn(
                "LEARNING_TARGET_AS_VERIFIED", run.results[0].breach_codes
            )

        with self.subTest("learning target only in gap fields is not a breach"):
            # dbt appears only in semantic_gaps and in advisory reasoning text;
            # it is correctly identified as a gap, not a verified capability.
            payload = _valid_cv_payload(
                semantic_matched_skills=["python", "django"],
                semantic_gaps=["dbt"],
                reasoning_summary="Strong Python overlap; treat dbt as a gap.",
            )
            case = _valid_case(
                case_id="LT-2",
                surface="cv_jpa",
                learning_target_skills=["dbt"],
                human_groundedness=2,
                offline_response={
                    "result_type": "payload",
                    "payload": payload,
                    "error_class": None,
                },
            )
            run = run_evaluation(
                load_case_set_from_mapping(_valid_case_set([case])),
                mode="offline",
            )
            self.assertNotIn(
                "LEARNING_TARGET_AS_VERIFIED", run.results[0].breach_codes
            )
            self.assertEqual(run.results[0].breach_codes, ())
            self.assertEqual(run.results[0].outcome, "PASS")

    def test_unsupported_material_claim_is_fail(self):
        payload = _valid_fit_payload(
            evidence_matches=["Python", "Snowflake production ownership"]
        )
        case = _valid_case(
            unsupported_material_claims=["Snowflake production ownership"],
            offline_response={
                "result_type": "payload",
                "payload": payload,
                "error_class": None,
            },
        )
        run = run_evaluation(load_case_set_from_mapping(_valid_case_set([case])), mode="offline")
        self.assertEqual(run.results[0].outcome, "FAIL")
        self.assertIn("UNSUPPORTED_MATERIAL_CLAIM", run.results[0].breach_codes)

    def test_ambiguous_groundedness_is_review_required(self):
        case_set = load_case_set_from_mapping(
            _valid_case_set([_valid_case(human_groundedness=1)])
        )
        run = run_evaluation(case_set, mode="offline")
        self.assertEqual(run.results[0].outcome, "REVIEW_REQUIRED")
        self.assertEqual(run.overall_result, "REVIEW_REQUIRED")

    def test_replay_timeout_is_fail(self):
        data = _valid_case_set(
            [
                _valid_case(
                    offline_response={
                        "result_type": "timeout",
                        "payload": None,
                        "error_class": "TimeoutError",
                    }
                )
            ]
        )
        case_set = load_case_set_from_mapping(data)
        bundle = load_replay_bundle_from_mapping(
            _replay_bundle_for_case_set(data, case_set.case_set_hash),
            expected_case_ids=frozenset(case.case_id for case in case_set.cases),
            expected_case_set_hash=case_set.case_set_hash,
        )
        run = run_evaluation(case_set, mode="replay", replay_bundle=bundle)
        self.assertEqual(run.results[0].outcome, "FAIL")
        self.assertIn("TIMEOUT", run.results[0].breach_codes)

    def test_replay_provider_error_is_fail(self):
        data = _valid_case_set(
            [
                _valid_case(
                    offline_response={
                        "result_type": "provider_error",
                        "payload": None,
                        "error_class": "ProviderError",
                    }
                )
            ]
        )
        case_set = load_case_set_from_mapping(data)
        bundle = load_replay_bundle_from_mapping(
            _replay_bundle_for_case_set(data, case_set.case_set_hash),
            expected_case_ids=frozenset(case.case_id for case in case_set.cases),
            expected_case_set_hash=case_set.case_set_hash,
        )
        run = run_evaluation(case_set, mode="replay", replay_bundle=bundle)
        self.assertEqual(run.results[0].outcome, "FAIL")
        self.assertIn("PROVIDER_ERROR", run.results[0].breach_codes)

    def test_report_is_deterministic_and_records_contract_and_case_hashes(self):
        case_set = load_case_set_from_mapping(_valid_case_set())
        run = run_evaluation(case_set, mode="offline")
        fixed_time = "2026-07-25T12:00:00+00:00"
        first = build_results_document(run, generated_at=fixed_time)
        second = build_results_document(run, generated_at=fixed_time)
        self.assertEqual(first, second)
        expected_keys = {
            "schema_version",
            "phase",
            "mode",
            "generated_at",
            "case_set_hash",
            "prompt_contract_hashes",
            "prompt_contract_hash_limitation",
            "case_count",
            "pass_count",
            "fail_count",
            "review_required_count",
            "hard_breach_counts",
            "overall_result",
            "partial",
            "results",
        }
        self.assertEqual(set(first.keys()), expected_keys)
        self.assertEqual(first["case_set_hash"], case_set.case_set_hash)
        self.assertIn("CASE-001", first["prompt_contract_hashes"])
        case_keys = set(first["results"][0].keys())
        self.assertEqual(
            case_keys,
            {
                "case_id",
                "surface",
                "result_type",
                "outcome",
                "parser_status",
                "human_groundedness",
                "breach_codes",
                "safe_error_category",
                "prompt_contract_hash",
            },
        )

    def test_mid_run_failure_writes_partial_report_outside_repository(self):
        data = _valid_case_set(
            [
                _valid_case(case_id="OK-1"),
                _valid_case(case_id="BOOM-2", surface="cv_jpa"),
            ]
        )
        case_set = load_case_set_from_mapping(data)
        original = evaluate_case

        def flaky(case, **kwargs):
            if case.case_id == "BOOM-2":
                raise RuntimeError("simulated mid-run failure")
            return original(case, **kwargs)

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "reports"
            with patch(
                "apps.ai_agents.evaluation.runner.evaluate_case",
                side_effect=flaky,
            ):
                with self.assertRaises(EvaluationRunnerError) as ctx:
                    run_evaluation(case_set, mode="offline")
            partial = ctx.exception.partial_result
            self.assertIsNotNone(partial)
            self.assertTrue(partial.partial)
            write_evaluation_reports(
                partial,
                output_dir=output_dir,
                generated_at="2026-07-25T12:00:00+00:00",
            )
            results_path = output_dir / "evaluation_results.json"
            self.assertTrue(results_path.exists())
            ensure_outside_repository(results_path, label="results")
            payload = json.loads(results_path.read_text(encoding="utf-8"))
            self.assertTrue(payload["partial"])
            self.assertEqual(payload["case_count"], 1)
            self.assertFalse(any(_repo_root() in p.parents for p in [results_path]))

    def test_replay_bundle_hash_mismatch_fails_closed(self):
        data = _valid_case_set()
        case_set = load_case_set_from_mapping(data)
        bundle = _replay_bundle_for_case_set(data, case_set.case_set_hash)
        bundle["bundle_hash"] = "0" * 64
        with self.assertRaises(CaseValidationError) as ctx:
            load_replay_bundle_from_mapping(
                bundle,
                expected_case_ids=frozenset(case.case_id for case in case_set.cases),
                expected_case_set_hash=case_set.case_set_hash,
            )
        self.assertIn("bundle_hash_mismatch", str(ctx.exception))

    def test_runner_performs_no_database_access(self):
        case_set = load_case_set_from_mapping(_valid_case_set())

        def fail_db(*args, **kwargs):
            raise AssertionError("Database access is not allowed in Phase 2B.")

        with patch("django.db.backends.base.base.BaseDatabaseWrapper.cursor", fail_db):
            run = run_evaluation(case_set, mode="offline")
        self.assertEqual(run.case_count, 1)

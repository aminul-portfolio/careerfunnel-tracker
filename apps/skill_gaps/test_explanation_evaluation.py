"""Sprint 115 Phase 1: explanation evaluation contract tests.

Exactly six test methods. Synthetic contract fixtures only. No replay runner,
management command, provider, network, ORM or filesystem case-set loading.
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
import re
import unicodedata
from pathlib import Path
from types import MappingProxyType

from django.test import SimpleTestCase

from apps.skill_gaps.evaluation.explanation_evaluation_cases import (
    CASE_SCHEMA_VERSION,
    EVALUATION_VERSION,
    EVIDENCE_ALIGNMENT_RULE_VERSION,
    EvaluationCase,
    EvaluationCaseContractError,
    EvaluationCategory,
    canonical_case_set_bytes,
    case_set_to_canonical_dict,
    compute_case_set_hash,
    make_evaluation_case,
    validate_and_sort_evaluation_cases,
)
from apps.skill_gaps.explanation_output_validator import (
    EvidenceAlignmentExplanationValidationError,
    ExplanationRejectionCode,
    validate_evidence_alignment_explanation_output,
)


def _minimal_provider_payload() -> dict:
    return {
        "rule_version": "evidence_alignment_v1",
        "overall_outcome": "ALL_REQUIREMENTS_VERIFIED",
        "requirements": [
            {
                "requirement_index": 0,
                "requirement_text": "Python",
                "classification": "VERIFIED_MATCH",
                "match_basis": "exact_name",
                "matched_evidence_level": "VERIFIED",
                "matched_skill_name": "Python",
                "unresolved": False,
            }
        ],
    }


def _valid_raw_output() -> dict:
    return {
        "summary": "Advisory summary grounded in verified Skill Ledger evidence.",
        "verified_evidence": [
            {
                "requirement_index": 0,
                "skill_names": ["Python"],
                "explanation": "Python matches verified Skill Ledger evidence.",
            }
        ],
        "development_evidence": [],
        "missing_evidence": [],
    }


def _synthetic_case(
    *,
    case_id: str,
    category: EvaluationCategory = EvaluationCategory.GOLDEN_VALID_OUTPUT,
    expected_acceptance: bool = True,
    expected_rejection_code: ExplanationRejectionCode | None = None,
    simulated_provider_output: str = '{"summary":"ok"}',
    expected_provider_payload: dict | None = None,
    builder_input: dict | None = None,
    is_synthetic: bool = True,
    schema_version: str = CASE_SCHEMA_VERSION,
    description: str = "Synthetic Phase 1 contract fixture.",
    safety_assertions: tuple[str, ...] = ("no_provider_call", "synthetic_only"),
) -> EvaluationCase:
    payload = expected_provider_payload
    if payload is None:
        payload = {"rule_version": "evidence_alignment_v1", "overall_outcome": "ok"}
    return make_evaluation_case(
        case_id=case_id,
        schema_version=schema_version,
        category=category,
        description=description,
        deterministic_outcome="ALL_REQUIREMENTS_VERIFIED",
        builder_input=builder_input,
        expected_provider_payload=payload,
        simulated_provider_output=simulated_provider_output,
        expected_acceptance=expected_acceptance,
        expected_rejection_code=expected_rejection_code,
        safety_assertions=safety_assertions,
        is_synthetic=is_synthetic,
    )


class Sprint115Phase1ExplanationEvaluationContractTests(SimpleTestCase):
    """Phase 1 evaluation contract, rejection metadata and canonical hashing."""

    def test_stable_rejection_metadata_preserves_validator_behaviour(self):
        payload = _minimal_provider_payload()
        accepted = validate_evidence_alignment_explanation_output(
            _valid_raw_output(),
            payload,
        )
        self.assertEqual(
            accepted["verified_evidence"][0]["skill_names"],
            ["Python"],
        )

        rejection_cases = (
            (
                {**_valid_raw_output(), "status": "ok"},
                "raw_output has invalid fields.",
                ExplanationRejectionCode.SCHEMA_MISMATCH,
            ),
            (
                {
                    **_valid_raw_output(),
                    "summary": "Score is 95% for this role.",
                },
                "summary contains prohibited claim-safety content (percentage).",
                ExplanationRejectionCode.PROHIBITED_CLAIM,
            ),
            (
                {
                    **_valid_raw_output(),
                    "summary": "See https://example.com for details.",
                },
                "summary contains a URL.",
                ExplanationRejectionCode.URL_DETECTED,
            ),
            (
                {
                    **_valid_raw_output(),
                    "summary": "Use **bold** emphasis here.",
                },
                "summary contains Markdown or HTML content.",
                ExplanationRejectionCode.MARKUP_DETECTED,
            ),
            (
                {
                    **_valid_raw_output(),
                    "verified_evidence": [
                        {
                            "requirement_index": 0,
                            "skill_names": ["InventedSkill"],
                            "explanation": "Invented skill name.",
                        }
                    ],
                },
                "verified_evidence.skill_names does not match the "
                "deterministic matched_skill_name.",
                ExplanationRejectionCode.SKILL_NAME_MISMATCH,
            ),
        )
        for raw, expected_message, expected_code in rejection_cases:
            with self.subTest(message=expected_message):
                with self.assertRaises(
                    EvidenceAlignmentExplanationValidationError
                ) as raised:
                    validate_evidence_alignment_explanation_output(raw, payload)
                error = raised.exception
                self.assertIsInstance(error, ValueError)
                self.assertIsInstance(error, EvidenceAlignmentExplanationValidationError)
                self.assertEqual(str(error), expected_message)
                self.assertIsInstance(error.code, ExplanationRejectionCode)
                self.assertEqual(error.code, expected_code)

    def test_every_internal_validator_failure_path_supplies_stable_metadata(self):
        source = inspect.getsource(
            __import__(
                "apps.skill_gaps.explanation_output_validator",
                fromlist=["*"],
            )
        )
        module = ast.parse(source)
        fail_calls: list[ast.Call] = []
        for node in ast.walk(module):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == "_fail":
                    fail_calls.append(node)

        self.assertGreater(len(fail_calls), 0)
        for call in fail_calls:
            with self.subTest(lineno=call.lineno):
                self.assertGreaterEqual(
                    len(call.args),
                    2,
                    msg=f"_fail at line {call.lineno} missing rejection code argument",
                )
                code_arg = call.args[1]
                if isinstance(code_arg, ast.Attribute):
                    self.assertIsInstance(code_arg.value, ast.Name)
                    assert isinstance(code_arg.value, ast.Name)
                    self.assertEqual(code_arg.value.id, "ExplanationRejectionCode")
                    self.assertIn(
                        code_arg.attr,
                        {member.name for member in ExplanationRejectionCode},
                    )
                else:
                    self.fail(
                        f"_fail at line {call.lineno} does not use "
                        "ExplanationRejectionCode.<member>"
                    )

        validator_path = Path(
            inspect.getsourcefile(
                __import__(
                    "apps.skill_gaps.explanation_output_validator",
                    fromlist=["*"],
                )
            )
        )
        text = validator_path.read_text(encoding="utf-8")
        bare_fail = re.findall(r"_fail\(\s*[\"'][^\"']+[\"']\s*\)", text)
        self.assertEqual(bare_fail, [])

    def test_evaluation_case_is_deeply_immutable_and_synthetic_only(self):
        nested_payload = {
            "rule_version": "evidence_alignment_v1",
            "requirements": [{"requirement_index": 0, "skill": "Python"}],
        }
        case = _synthetic_case(
            case_id="synthetic-immutable-01",
            expected_provider_payload=nested_payload,
            builder_input={"tokens": ["a", "b"]},
            simulated_provider_output='{"summary":"raw text"}',
        )
        self.assertTrue(case.__dataclass_params__.frozen)
        self.assertIsInstance(case.expected_provider_payload, MappingProxyType)
        self.assertIsInstance(case.builder_input, MappingProxyType)
        self.assertIsInstance(case.simulated_provider_output, str)
        self.assertIs(case.is_synthetic, True)

        with self.assertRaises((TypeError, AttributeError)):
            case.case_id = "mutated"  # type: ignore[misc]
        with self.assertRaises(TypeError):
            case.expected_provider_payload["rule_version"] = "mutated"
        with self.assertRaises(TypeError):
            case.expected_provider_payload["requirements"][0]["skill"] = "mutated"
        with self.assertRaises(TypeError):
            case.builder_input["tokens"][0] = "z"
        with self.assertRaises(AttributeError):
            case.safety_assertions.append("extra")  # type: ignore[attr-defined]

        with self.assertRaises(EvaluationCaseContractError):
            _synthetic_case(
                case_id="synthetic-false",
                is_synthetic=False,
            )
        with self.assertRaises(EvaluationCaseContractError):
            make_evaluation_case(
                case_id="not-raw-text",
                category=EvaluationCategory.GOLDEN_VALID_OUTPUT,
                description="bad output type",
                deterministic_outcome="ALL_REQUIREMENTS_VERIFIED",
                builder_input=None,
                expected_provider_payload={"k": "v"},
                simulated_provider_output={"summary": "not text"},  # type: ignore[arg-type]
                expected_acceptance=True,
                expected_rejection_code=None,
                safety_assertions=("x",),
                is_synthetic=True,
            )

        with self.subTest(case="set_value_rejected"):
            with self.assertRaises(EvaluationCaseContractError):
                _synthetic_case(
                    case_id="set-rejected",
                    expected_provider_payload={"skills": {"Python", "SQL"}},
                )
        with self.subTest(case="frozenset_value_rejected"):
            with self.assertRaises(EvaluationCaseContractError):
                _synthetic_case(
                    case_id="frozenset-rejected",
                    expected_provider_payload={
                        "skills": frozenset({"Python", "SQL"}),
                    },
                )

    def test_invalid_contract_data_fails_closed(self):
        with self.subTest(case="empty_case_id"):
            with self.assertRaises(EvaluationCaseContractError):
                _synthetic_case(case_id="")
        with self.subTest(case="unknown_schema_version"):
            with self.assertRaises(EvaluationCaseContractError):
                _synthetic_case(
                    case_id="bad-schema",
                    schema_version="evidence_alignment_explanation_case_v0",
                )
        with self.subTest(case="unknown_category"):
            with self.assertRaises(EvaluationCaseContractError):
                make_evaluation_case(
                    case_id="bad-category",
                    category="NOT_A_REAL_CATEGORY",  # type: ignore[arg-type]
                    description="unknown category",
                    deterministic_outcome="ALL_REQUIREMENTS_VERIFIED",
                    builder_input=None,
                    expected_provider_payload={"k": "v"},
                    simulated_provider_output="{}",
                    expected_acceptance=True,
                    expected_rejection_code=None,
                    safety_assertions=("x",),
                    is_synthetic=True,
                )
        with self.subTest(case="accepted_with_rejection_code"):
            with self.assertRaises(EvaluationCaseContractError):
                _synthetic_case(
                    case_id="accepted-with-code",
                    expected_acceptance=True,
                    expected_rejection_code=ExplanationRejectionCode.SCHEMA_MISMATCH,
                )
        with self.subTest(case="rejected_without_rejection_code"):
            with self.assertRaises(EvaluationCaseContractError):
                _synthetic_case(
                    case_id="rejected-without-code",
                    expected_acceptance=False,
                    expected_rejection_code=None,
                )
        with self.subTest(case="string_safety_assertions_rejected"):
            with self.assertRaises(EvaluationCaseContractError):
                make_evaluation_case(
                    case_id="string-assertions",
                    category=EvaluationCategory.GOLDEN_VALID_OUTPUT,
                    description="string container rejected",
                    deterministic_outcome="ALL_REQUIREMENTS_VERIFIED",
                    builder_input=None,
                    expected_provider_payload={"k": "v"},
                    simulated_provider_output="{}",
                    expected_acceptance=True,
                    expected_rejection_code=None,
                    safety_assertions="not-a-sequence-container",  # type: ignore[arg-type]
                    is_synthetic=True,
                )
        with self.subTest(case="bytes_safety_assertions_rejected"):
            with self.assertRaises(EvaluationCaseContractError):
                make_evaluation_case(
                    case_id="bytes-assertions",
                    category=EvaluationCategory.GOLDEN_VALID_OUTPUT,
                    description="bytes container rejected",
                    deterministic_outcome="ALL_REQUIREMENTS_VERIFIED",
                    builder_input=None,
                    expected_provider_payload={"k": "v"},
                    simulated_provider_output="{}",
                    expected_acceptance=True,
                    expected_rejection_code=None,
                    safety_assertions=b"not-a-sequence",  # type: ignore[arg-type]
                    is_synthetic=True,
                )
        with self.subTest(case="bytearray_safety_assertions_rejected"):
            with self.assertRaises(EvaluationCaseContractError):
                make_evaluation_case(
                    case_id="bytearray-assertions",
                    category=EvaluationCategory.GOLDEN_VALID_OUTPUT,
                    description="bytearray container rejected",
                    deterministic_outcome="ALL_REQUIREMENTS_VERIFIED",
                    builder_input=None,
                    expected_provider_payload={"k": "v"},
                    simulated_provider_output="{}",
                    expected_acceptance=True,
                    expected_rejection_code=None,
                    safety_assertions=bytearray(b"nope"),  # type: ignore[arg-type]
                    is_synthetic=True,
                )
        with self.subTest(case="expected_acceptance_int_zero_rejected"):
            with self.assertRaises(EvaluationCaseContractError):
                make_evaluation_case(
                    case_id="acceptance-zero",
                    category=EvaluationCategory.GOLDEN_VALID_OUTPUT,
                    description="integer acceptance rejected",
                    deterministic_outcome="ALL_REQUIREMENTS_VERIFIED",
                    builder_input=None,
                    expected_provider_payload={"k": "v"},
                    simulated_provider_output="{}",
                    expected_acceptance=0,  # type: ignore[arg-type]
                    expected_rejection_code=None,
                    safety_assertions=("x",),
                    is_synthetic=True,
                )
        with self.subTest(case="expected_acceptance_int_one_rejected"):
            with self.assertRaises(EvaluationCaseContractError):
                make_evaluation_case(
                    case_id="acceptance-one",
                    category=EvaluationCategory.GOLDEN_VALID_OUTPUT,
                    description="integer acceptance rejected",
                    deterministic_outcome="ALL_REQUIREMENTS_VERIFIED",
                    builder_input=None,
                    expected_provider_payload={"k": "v"},
                    simulated_provider_output="{}",
                    expected_acceptance=1,  # type: ignore[arg-type]
                    expected_rejection_code=ExplanationRejectionCode.SCHEMA_MISMATCH,
                    safety_assertions=("x",),
                    is_synthetic=True,
                )
        with self.subTest(case="expected_acceptance_string_rejected"):
            with self.assertRaises(EvaluationCaseContractError):
                make_evaluation_case(
                    case_id="acceptance-string",
                    category=EvaluationCategory.GOLDEN_VALID_OUTPUT,
                    description="string acceptance rejected",
                    deterministic_outcome="ALL_REQUIREMENTS_VERIFIED",
                    builder_input=None,
                    expected_provider_payload={"k": "v"},
                    simulated_provider_output="{}",
                    expected_acceptance="true",  # type: ignore[arg-type]
                    expected_rejection_code=None,
                    safety_assertions=("x",),
                    is_synthetic=True,
                )
        with self.subTest(case="expected_acceptance_none_rejected"):
            with self.assertRaises(EvaluationCaseContractError):
                make_evaluation_case(
                    case_id="acceptance-none",
                    category=EvaluationCategory.GOLDEN_VALID_OUTPUT,
                    description="none acceptance rejected",
                    deterministic_outcome="ALL_REQUIREMENTS_VERIFIED",
                    builder_input=None,
                    expected_provider_payload={"k": "v"},
                    simulated_provider_output="{}",
                    expected_acceptance=None,  # type: ignore[arg-type]
                    expected_rejection_code=None,
                    safety_assertions=("x",),
                    is_synthetic=True,
                )

    def test_duplicate_ids_ordering_and_insertion_order_are_deterministic(self):
        case_b = _synthetic_case(
            case_id="case-b",
            expected_provider_payload={"z": 1, "a": 2, "m": 3},
        )
        case_a = _synthetic_case(
            case_id="case-a",
            expected_provider_payload={"m": 3, "z": 1, "a": 2},
        )
        with self.assertRaises(EvaluationCaseContractError):
            validate_and_sort_evaluation_cases((case_a, case_a))

        sorted_cases = validate_and_sort_evaluation_cases((case_b, case_a))
        self.assertEqual(
            tuple(item.case_id for item in sorted_cases),
            ("case-a", "case-b"),
        )

        bytes_left = canonical_case_set_bytes((case_b, case_a))
        bytes_right = canonical_case_set_bytes((case_a, case_b))
        self.assertEqual(bytes_left, bytes_right)

        payload_order_one = _synthetic_case(
            case_id="order-check",
            expected_provider_payload={"z": 1, "a": 2},
        )
        payload_order_two = _synthetic_case(
            case_id="order-check",
            expected_provider_payload={"a": 2, "z": 1},
        )
        self.assertEqual(
            canonical_case_set_bytes((payload_order_one,)),
            canonical_case_set_bytes((payload_order_two,)),
        )

        with self.subTest(case="integer_mapping_key_rejected"):
            with self.assertRaises(EvaluationCaseContractError) as raised:
                _synthetic_case(
                    case_id="int-key",
                    expected_provider_payload={1: "value", "1": "other"},
                )
            self.assertIn("mapping keys must be strings", str(raised.exception))

        composed_key = "caf\u00e9"
        decomposed_key = unicodedata.normalize("NFD", composed_key)
        self.assertNotEqual(composed_key, decomposed_key)
        with self.subTest(case="nfc_equivalent_key_collision_rejected"):
            with self.assertRaises(EvaluationCaseContractError) as raised:
                _synthetic_case(
                    case_id="nfc-key-collision",
                    expected_provider_payload={
                        composed_key: "one",
                        decomposed_key: "two",
                    },
                )
            self.assertIn(
                "mapping keys collide after Unicode and newline normalisation",
                str(raised.exception),
            )

        composed_id = "case-caf\u00e9"
        decomposed_id = unicodedata.normalize("NFD", composed_id)
        self.assertNotEqual(composed_id, decomposed_id)
        with self.subTest(case="nfc_equivalent_case_ids_rejected"):
            case_nfc = _synthetic_case(case_id=composed_id)
            case_nfd = _synthetic_case(case_id=decomposed_id)
            with self.assertRaises(EvaluationCaseContractError):
                validate_and_sort_evaluation_cases((case_nfc, case_nfd))

        with self.subTest(case="newline_equivalent_case_ids_rejected"):
            case_crlf = _synthetic_case(case_id="case-nl\r\npart")
            case_lf = _synthetic_case(case_id="case-nl\npart")
            with self.assertRaises(EvaluationCaseContractError):
                validate_and_sort_evaluation_cases((case_crlf, case_lf))

        with self.subTest(case="canonical_id_ordering"):
            later = _synthetic_case(case_id="sort-b")
            earlier = _synthetic_case(case_id="sort-a\r")
            ordered = validate_and_sort_evaluation_cases((later, earlier))
            self.assertEqual(
                tuple(item.case_id for item in ordered),
                ("sort-a\n", "sort-b"),
            )

        with self.subTest(case="equivalent_unicode_ids_separate_bytes_match"):
            self.assertEqual(
                canonical_case_set_bytes((_synthetic_case(case_id=composed_id),)),
                canonical_case_set_bytes((_synthetic_case(case_id=decomposed_id),)),
            )

    def test_canonical_bytes_and_sha256_are_stable(self):
        base = _synthetic_case(
            case_id="hash-stable-01",
            simulated_provider_output="line1\nline2",
            expected_provider_payload={"label": "cafe"},
        )
        crlf = _synthetic_case(
            case_id="hash-stable-01",
            simulated_provider_output="line1\r\nline2",
            expected_provider_payload={"label": "cafe"},
        )
        cr_only = _synthetic_case(
            case_id="hash-stable-01",
            simulated_provider_output="line1\rline2",
            expected_provider_payload={"label": "cafe"},
        )
        nfc = _synthetic_case(
            case_id="hash-stable-01",
            simulated_provider_output="line1\nline2",
            expected_provider_payload={"label": unicodedata.normalize("NFC", "cafe")},
        )
        nfd = _synthetic_case(
            case_id="hash-stable-01",
            simulated_provider_output="line1\nline2",
            expected_provider_payload={
                "label": unicodedata.normalize("NFD", "cafe")
            },
        )

        composed = "caf\u00e9"
        decomposed = unicodedata.normalize("NFD", composed)
        self.assertNotEqual(composed.encode("utf-8"), decomposed.encode("utf-8"))
        nfc_case = _synthetic_case(
            case_id="unicode-nfc",
            expected_provider_payload={"label": composed},
            simulated_provider_output=composed,
        )
        nfd_case = _synthetic_case(
            case_id="unicode-nfc",
            expected_provider_payload={"label": decomposed},
            simulated_provider_output=decomposed,
        )

        first_bytes = canonical_case_set_bytes((base,))
        second_bytes = canonical_case_set_bytes((base,))
        self.assertEqual(first_bytes, second_bytes)
        first_hash = compute_case_set_hash((base,))
        second_hash = compute_case_set_hash((base,))
        self.assertEqual(first_hash, second_hash)
        self.assertEqual(
            first_hash,
            hashlib.sha256(first_bytes).hexdigest(),
        )
        self.assertEqual(len(first_hash), 64)

        self.assertEqual(
            canonical_case_set_bytes((base,)),
            canonical_case_set_bytes((crlf,)),
        )
        self.assertEqual(
            canonical_case_set_bytes((base,)),
            canonical_case_set_bytes((cr_only,)),
        )
        self.assertEqual(
            canonical_case_set_bytes((nfc_case,)),
            canonical_case_set_bytes((nfd_case,)),
        )
        self.assertEqual(
            canonical_case_set_bytes((nfc,)),
            canonical_case_set_bytes((nfd,)),
        )

        with self.assertRaises(EvaluationCaseContractError):
            _synthetic_case(
                case_id="float-rejected",
                expected_provider_payload={"score": 1.5},
            )

        from apps.skill_gaps.evaluation.explanation_evaluation_cases import (
            _canonicalise_value,
        )

        with self.assertRaises(EvaluationCaseContractError):
            _canonicalise_value({"score": 1.25})

        with self.subTest(case="timestamp_metadata_key_rejected"):
            with self.assertRaises(EvaluationCaseContractError):
                _synthetic_case(
                    case_id="timestamp-key",
                    expected_provider_payload={"timestamp": "2026-08-03"},
                )
        with self.subTest(case="timestamp_case_variant_rejected"):
            with self.assertRaises(EvaluationCaseContractError):
                _synthetic_case(
                    case_id="Timestamp-key",
                    expected_provider_payload={"Timestamp": "2026-08-03"},
                )
        with self.subTest(case="output_path_case_variant_rejected"):
            with self.assertRaises(EvaluationCaseContractError):
                _synthetic_case(
                    case_id="OUTPUT-PATH-key",
                    expected_provider_payload={"OUTPUT_PATH": "relative/ok.txt"},
                )
        with self.subTest(case="proof_path_whitespace_variant_rejected"):
            with self.assertRaises(EvaluationCaseContractError):
                _synthetic_case(
                    case_id="proof-path-ws",
                    builder_input={" Proof_Path ": "relative/proof.txt"},
                )
        with self.subTest(case="windows_absolute_path_rejected"):
            with self.assertRaises(EvaluationCaseContractError):
                _synthetic_case(
                    case_id="windows-abs-path",
                    expected_provider_payload={
                        "label": r"G:\workflow_tools\careerfunnel_sprint115",
                    },
                )
        with self.subTest(case="windows_drive_forward_slash_rejected"):
            with self.assertRaises(EvaluationCaseContractError):
                _synthetic_case(
                    case_id="windows-fwd-path",
                    expected_provider_payload={"label": "C:/Users/name/file.txt"},
                )
        with self.subTest(case="unc_backslash_path_rejected"):
            with self.assertRaises(EvaluationCaseContractError):
                _synthetic_case(
                    case_id="unc-path",
                    expected_provider_payload={"label": r"\\server\share\file.txt"},
                )
        with self.subTest(case="unc_forward_slash_path_rejected"):
            with self.assertRaises(EvaluationCaseContractError):
                _synthetic_case(
                    case_id="unc-fwd-path",
                    expected_provider_payload={"label": "//server/share/file.txt"},
                )
        with self.subTest(case="posix_home_absolute_path_rejected"):
            with self.assertRaises(EvaluationCaseContractError):
                _synthetic_case(
                    case_id="posix-home",
                    expected_provider_payload={"label": "/home/user/report.txt"},
                )
        with self.subTest(case="posix_users_absolute_path_rejected"):
            with self.assertRaises(EvaluationCaseContractError):
                _synthetic_case(
                    case_id="posix-users",
                    expected_provider_payload={"label": "/Users/name/report.txt"},
                )
        with self.subTest(case="posix_tmp_absolute_path_rejected"):
            with self.assertRaises(EvaluationCaseContractError):
                _synthetic_case(
                    case_id="posix-tmp",
                    expected_provider_payload={"label": "/tmp/file.txt"},
                )
        with self.subTest(case="posix_opt_absolute_path_rejected"):
            with self.assertRaises(EvaluationCaseContractError):
                _synthetic_case(
                    case_id="posix-opt",
                    expected_provider_payload={"label": "/opt/project/file.txt"},
                )
        with self.subTest(case="posix_var_absolute_path_rejected"):
            with self.assertRaises(EvaluationCaseContractError):
                _synthetic_case(
                    case_id="posix-var",
                    expected_provider_payload={"label": "/var/tmp/file.txt"},
                )
        with self.subTest(case="simulated_output_windows_path_rejected"):
            with self.assertRaises(EvaluationCaseContractError):
                _synthetic_case(
                    case_id="sim-windows-path",
                    simulated_provider_output=r"C:\Users\name\out.json",
                )
        with self.subTest(case="description_posix_path_rejected"):
            with self.assertRaises(EvaluationCaseContractError):
                _synthetic_case(
                    case_id="desc-posix-path",
                    description="/home/user/notes.txt",
                )
        with self.subTest(case="safety_assertion_absolute_path_rejected"):
            with self.assertRaises(EvaluationCaseContractError):
                _synthetic_case(
                    case_id="safety-abs-path",
                    safety_assertions=("/tmp/proof.txt",),
                )
        with self.subTest(case="ordinary_text_and_url_accepted"):
            allowed = _synthetic_case(
                case_id="relative-and-url-ok",
                description="Ordinary advisory fixture text.",
                simulated_provider_output='{"summary":"https://example.com"}',
                expected_provider_payload={
                    "relative": "docs/report.txt",
                    "skill": "Python",
                    "note": "https://example.com/home/user is a URL not a local path",
                },
                safety_assertions=("no_provider_call", "https://example.com"),
            )
            self.assertEqual(
                canonical_case_set_bytes((allowed,)),
                canonical_case_set_bytes((allowed,)),
            )

        canonical = case_set_to_canonical_dict((base,))
        encoded = json.dumps(
            canonical,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        self.assertNotIn('"timestamp"', encoded.lower())
        self.assertNotIn("duration", encoded.lower())
        self.assertNotIn("g:\\", encoded.lower())
        self.assertNotIn("c:\\", encoded.lower())
        self.assertIn(EVALUATION_VERSION, encoded)
        self.assertIn(CASE_SCHEMA_VERSION, encoded)
        self.assertIn(EVIDENCE_ALIGNMENT_RULE_VERSION, encoded)
        self.assertEqual(
            json.dumps(
                canonical,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ),
            first_bytes.decode("utf-8"),
        )

import json
import re
from pathlib import Path

from django.test import SimpleTestCase

from apps.ai_agents.claim_safety_reviewer import review_claim_safety

DATASET_PATH = Path(__file__).resolve().parent / "claim_safety_evaluation_cases.json"

REQUIRED_CASE_FIELDS = (
    "case_id",
    "group",
    "category",
    "claim_text",
    "evidence_context",
    "channel",
    "evaluation_status",
    "expected_overall_verdict",
    "expected_risk_level",
    "expected_has_unsupported_claims",
    "expected_warning_codes",
    "expected_evidence_required_nonempty",
    "expected_unknowns_nonempty",
    "expected_safe_rewrite_contains",
    "expected_safe_rewrite_excludes",
    "rationale",
    "limitation_note",
)

REQUIRED_CATEGORIES = {
    "01_supported_claim",
    "02_unsupported_claim",
    "03_needs_evidence_claim",
    "04_production_customer_revenue_saas_claim",
    "05_live_ai_llm_claim",
    "06_deployment_claim",
    "07_ambiguous_claim",
    "08_empty_or_whitespace_claim",
    "09_mixed_safe_unsafe_claim",
    "10_unknown_marker_claim",
    "11_evidence_context_present",
    "12_evidence_context_absent",
    "13_channel_specific_behaviour",
    "14_determinism",
    "15_boundary_length_input",
    "16_input_handling_robustness",
    "17_unsupported_high_risk_wording",
    "18_safe_rewrite_behaviour",
    "19_warnings_and_unknowns",
    "20_known_limitations",
}

CATEGORY_MULTIPLICITY = {
    "01_supported_claim": 1,
    "02_unsupported_claim": 1,
    "03_needs_evidence_claim": 1,
    "04_production_customer_revenue_saas_claim": 1,
    "05_live_ai_llm_claim": 1,
    "06_deployment_claim": 1,
    "07_ambiguous_claim": 1,
    "08_empty_or_whitespace_claim": 1,
    "09_mixed_safe_unsafe_claim": 2,
    "10_unknown_marker_claim": 1,
    "11_evidence_context_present": 1,
    "12_evidence_context_absent": 1,
    "13_channel_specific_behaviour": 1,
    "14_determinism": 1,
    "15_boundary_length_input": 1,
    "16_input_handling_robustness": 1,
    "17_unsupported_high_risk_wording": 1,
    "18_safe_rewrite_behaviour": 1,
    "19_warnings_and_unknowns": 1,
    "20_known_limitations": 2,
}

VALID_GROUPS = {"career_claim", "capability_meta_claim", "behavioural", "robustness", "limitation"}
VALID_CHANNELS = {"general", "cv", "readme", "linkedin", "interview", "portfolio"}
VALID_VERDICTS = {"safe", "needs_evidence", "unsafe", "unknown"}
VALID_RISKS = {"low", "medium", "high", "unknown"}
VALID_EVALUATION_STATUS = {"conformance", "known_limitation"}
EXPECTED_CASE_IDS = [f"CSR107-{index:03d}" for index in range(1, 23)]


def _load_dataset() -> dict:
    with DATASET_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).lower()


def _review_case(case: dict) -> dict:
    evidence = case["evidence_context"]
    return review_claim_safety(
        case["claim_text"],
        evidence if evidence else None,
        case["channel"],
    )


class ClaimSafetyEvaluationProofTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dataset = _load_dataset()
        cls.cases = cls.dataset["cases"]

    def test_dataset_contains_exactly_22_cases(self):
        self.assertEqual(self.dataset.get("case_count"), 22)
        self.assertEqual(len(self.cases), 22)

    def test_dataset_schema_and_case_ids_are_valid(self):
        case_ids = [case["case_id"] for case in self.cases]
        self.assertEqual(len(set(case_ids)), 22)
        self.assertEqual(case_ids, EXPECTED_CASE_IDS)

        for case in self.cases:
            for field_name in REQUIRED_CASE_FIELDS:
                self.assertIn(field_name, case)
            self.assertIn(case["evaluation_status"], VALID_EVALUATION_STATUS)
            self.assertIn(case["expected_overall_verdict"], VALID_VERDICTS)
            self.assertIn(case["expected_risk_level"], VALID_RISKS)
            self.assertIn(case["channel"], VALID_CHANNELS)
            self.assertIn(case["group"], VALID_GROUPS)

    def test_dataset_covers_all_20_required_categories_and_group_boundaries(self):
        categories = [case["category"] for case in self.cases]
        self.assertEqual(len(set(categories)), 20)
        self.assertEqual(set(categories), REQUIRED_CATEGORIES)

        observed_multiplicity: dict[str, int] = {}
        for category in categories:
            observed_multiplicity[category] = observed_multiplicity.get(category, 0) + 1
        self.assertEqual(observed_multiplicity, CATEGORY_MULTIPLICITY)

        capability_cases = [
            case for case in self.cases if case["group"] == "capability_meta_claim"
        ]
        self.assertEqual(
            {case["category"] for case in capability_cases},
            {
                "04_production_customer_revenue_saas_claim",
                "05_live_ai_llm_claim",
                "06_deployment_claim",
            },
        )

        robustness_cases = [case for case in self.cases if case["group"] == "robustness"]
        self.assertEqual(
            {case["category"] for case in robustness_cases},
            {"15_boundary_length_input", "16_input_handling_robustness"},
        )

        limitation_cases = [case for case in self.cases if case["group"] == "limitation"]
        self.assertEqual(len(limitation_cases), 2)
        self.assertTrue(
            all(case["category"] == "20_known_limitations" for case in limitation_cases)
        )

    def test_conformance_cases_match_expected_core_outputs(self):
        conformance_cases = [
            case for case in self.cases if case["evaluation_status"] == "conformance"
        ]
        self.assertEqual(len(conformance_cases), 20)

        for case in conformance_cases:
            with self.subTest(case_id=case["case_id"]):
                result = _review_case(case)
                self.assertEqual(result["overall_verdict"], case["expected_overall_verdict"])
                self.assertEqual(result["risk_level"], case["expected_risk_level"])
                self.assertEqual(
                    bool(result["unsupported_claims"]),
                    case["expected_has_unsupported_claims"],
                )

    def test_repeated_identical_inputs_are_deterministic(self):
        determinism_case = next(
            case for case in self.cases if case["category"] == "14_determinism"
        )
        first = _review_case(determinism_case)
        second = _review_case(determinism_case)
        third = _review_case(determinism_case)
        self.assertEqual(first, second)
        self.assertEqual(second, third)

    def test_rewrite_warning_unknown_and_evidence_invariants_hold(self):
        conformance_cases = [
            case for case in self.cases if case["evaluation_status"] == "conformance"
        ]

        for case in conformance_cases:
            with self.subTest(case_id=case["case_id"]):
                result = _review_case(case)
                rewrite = _normalize_text(result["safe_rewrite"])

                for warning_code in case["expected_warning_codes"]:
                    self.assertIn(warning_code, result["warnings"])

                self.assertEqual(
                    bool(result["evidence_required"]),
                    case["expected_evidence_required_nonempty"],
                )
                self.assertEqual(
                    bool(result["unknowns"]),
                    case["expected_unknowns_nonempty"],
                )

                for required_fragment in case["expected_safe_rewrite_contains"]:
                    self.assertIn(_normalize_text(required_fragment), rewrite)

                for forbidden_fragment in case["expected_safe_rewrite_excludes"]:
                    self.assertNotIn(_normalize_text(forbidden_fragment), rewrite)

    def test_known_limitation_cases_are_explicitly_documented_and_not_counted_as_conformance_passes(
        self,
    ):
        known_limitation_cases = [
            case for case in self.cases if case["evaluation_status"] == "known_limitation"
        ]
        conformance_cases = [
            case for case in self.cases if case["evaluation_status"] == "conformance"
        ]

        self.assertEqual(len(known_limitation_cases), 2)
        self.assertEqual(len(conformance_cases), 20)
        self.assertTrue(
            all(case["category"] == "20_known_limitations" for case in known_limitation_cases)
        )
        self.assertTrue(all(case["group"] == "limitation" for case in known_limitation_cases))
        self.assertTrue(all(case["limitation_note"].strip() for case in known_limitation_cases))

    def test_input_handling_robustness_case_is_treated_as_plain_claim_data(self):
        robustness_case = next(
            case for case in self.cases if case["category"] == "16_input_handling_robustness"
        )
        result = _review_case(robustness_case)

        self.assertIn(result["overall_verdict"], VALID_VERDICTS)
        self.assertIn(result["risk_level"], VALID_RISKS)
        self.assertEqual(result["overall_verdict"], robustness_case["expected_overall_verdict"])
        self.assertEqual(result["risk_level"], robustness_case["expected_risk_level"])
        self.assertIn("<script>", robustness_case["claim_text"])

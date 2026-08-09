"""Sprint 122 Phase 3: immutable AI quality baseline and regression gate tests."""

from __future__ import annotations

import ast
import dataclasses
import hashlib
import inspect
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.skill_ledger.evaluation import quality_gate as quality_gate_module
from apps.skill_ledger.evaluation.quality_gate import (
    SPRINT121_AI_QUALITY_BASELINE_PATH,
    SPRINT121_AI_QUALITY_BASELINE_SHA256,
    SPRINT121_BASELINE_PROVENANCE_COMMIT,
    CaseRegressionCode,
    QualityGateCode,
    QualityGateContractError,
    baseline_integrity_projection,
    compute_baseline_integrity_hash,
    evaluate_against_baseline,
    load_authoritative_baseline,
    parse_quality_baseline,
    run_ai_quality_gate,
)
from apps.skill_ledger.evaluation.quality_snapshot import (
    AiQualitySnapshot,
    CaseOutcome,
    EvaluationFamily,
    PerCaseQualitySnapshot,
    RagQualitySnapshot,
    ToolAssistantQualitySnapshot,
)

_SHA_ALT = "e" * 64


def _fingerprint(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


class AuthoritativeBaselineTests(SimpleTestCase):
    def setUp(self):
        self.baseline = load_authoritative_baseline()
        self.text = SPRINT121_AI_QUALITY_BASELINE_PATH.read_text(encoding="utf-8")
        self.payload = json.loads(self.text)

    def test_baseline_file_exists_at_fixed_path(self):
        self.assertTrue(SPRINT121_AI_QUALITY_BASELINE_PATH.is_file())
        self.assertEqual(
            SPRINT121_AI_QUALITY_BASELINE_PATH.name,
            "sprint121_ai_quality_baseline.json",
        )

    def test_baseline_schema_version_locked(self):
        self.assertEqual(self.baseline.schema_version, 1)
        self.assertEqual(self.payload["schema_version"], 1)

    def test_provenance_commit_exact(self):
        self.assertEqual(
            self.baseline.provenance_commit,
            SPRINT121_BASELINE_PROVENANCE_COMMIT,
        )
        self.assertEqual(
            self.baseline.provenance_commit,
            "b50d959f463b178bd8c2d6c2d7a53ca362bbff6b",
        )

    def test_baseline_has_exactly_two_evaluation_families(self):
        names = [item.evaluation_family for item in self.baseline.families]
        self.assertEqual(len(names), 2)
        self.assertEqual(set(names), set(EvaluationFamily))

    def test_baseline_rag_case_set_sha_exact(self):
        rag = next(
            item
            for item in self.baseline.families
            if item.evaluation_family is EvaluationFamily.RAG_FINAL
        )
        self.assertEqual(
            rag.case_set_sha256,
            "575ddaf4d51b4826808f1ec52badd5aa0de14d1667444d5fdadb734f1b1d0527",
        )

    def test_baseline_tool_case_set_sha_exact(self):
        tool = next(
            item
            for item in self.baseline.families
            if item.evaluation_family is EvaluationFamily.TOOL_ASSISTANT
        )
        self.assertEqual(
            tool.case_set_sha256,
            "b3793f0fa6003e5162b9853dbf77d27f507b300d28b7259e3e18f9689eca4b53",
        )

    def test_baseline_rag_expected_case_count_is_31(self):
        rag = next(
            item
            for item in self.baseline.families
            if item.evaluation_family is EvaluationFamily.RAG_FINAL
        )
        self.assertEqual(rag.expected_case_count, 31)
        self.assertEqual(len(rag.cases), 31)

    def test_baseline_tool_expected_case_count_is_81(self):
        tool = next(
            item
            for item in self.baseline.families
            if item.evaluation_family is EvaluationFamily.TOOL_ASSISTANT
        )
        self.assertEqual(tool.expected_case_count, 81)
        self.assertEqual(len(tool.cases), 81)

    def test_total_baseline_cases_is_112(self):
        total = sum(len(item.cases) for item in self.baseline.families)
        self.assertEqual(total, 112)

    def test_all_baseline_expected_outcomes_are_pass(self):
        for family in self.baseline.families:
            for case in family.cases:
                self.assertEqual(case.expected_outcome, CaseOutcome.PASS)

    def test_baseline_case_ids_unique_and_sorted(self):
        for family in self.baseline.families:
            ids = [case.case_id for case in family.cases]
            self.assertEqual(ids, sorted(ids))
            self.assertEqual(len(ids), len(set(ids)))

    def test_baseline_fingerprints_valid_lowercase_sha256(self):
        for family in self.baseline.families:
            for case in family.cases:
                self.assertEqual(len(case.result_fingerprint), 64)
                self.assertTrue(
                    all(ch in "0123456789abcdef" for ch in case.result_fingerprint)
                )

    def test_baseline_integrity_constant_matches_projection(self):
        digest = compute_baseline_integrity_hash(self.baseline)
        self.assertEqual(digest, SPRINT121_AI_QUALITY_BASELINE_SHA256)
        projection = baseline_integrity_projection(self.baseline)
        for family in projection["families"]:
            self.assertNotIn("report_sha256", family)

    def test_changing_only_baseline_report_sha_does_not_change_integrity_hash(self):
        mutated = json.loads(self.text)
        for family in mutated["families"]:
            family["report_sha256"] = _SHA_ALT
        mutated_baseline = parse_quality_baseline(
            json.dumps(mutated, sort_keys=True, separators=(",", ":"))
        )
        self.assertEqual(
            compute_baseline_integrity_hash(mutated_baseline),
            compute_baseline_integrity_hash(self.baseline),
        )
        self.assertNotEqual(
            mutated_baseline.families[0].report_sha256,
            self.baseline.families[0].report_sha256,
        )


class QualityGateComparisonTests(SimpleTestCase):
    def setUp(self):
        self.baseline = load_authoritative_baseline()
        self.matching = self._snapshot_from_baseline()

    def _snapshot_from_baseline(
        self,
        *,
        privacy_violation_count: int = 0,
        candidate_sha: str | None = None,
        rag_network: int = 0,
        tool_network: int = 0,
        live_embedding: int = 0,
        live_llm: int = 0,
        live_provider: int = 0,
        rag_report_sha: str | None = None,
        tool_report_sha: str | None = None,
        rag_case_set: str | None = None,
        tool_case_set: str | None = None,
        rag_cases=None,
        tool_cases=None,
    ) -> AiQualitySnapshot:
        rag_family = next(
            item
            for item in self.baseline.families
            if item.evaluation_family is EvaluationFamily.RAG_FINAL
        )
        tool_family = next(
            item
            for item in self.baseline.families
            if item.evaluation_family is EvaluationFamily.TOOL_ASSISTANT
        )
        if rag_cases is None:
            rag_cases = tuple(
                PerCaseQualitySnapshot(
                    case_id=case.case_id,
                    outcome=CaseOutcome.PASS,
                    result_fingerprint=case.result_fingerprint,
                )
                for case in rag_family.cases
            )
        if tool_cases is None:
            tool_cases = tuple(
                PerCaseQualitySnapshot(
                    case_id=case.case_id,
                    outcome=CaseOutcome.PASS,
                    result_fingerprint=case.result_fingerprint,
                )
                for case in tool_family.cases
            )
        rag = RagQualitySnapshot(
            evaluation_family=EvaluationFamily.RAG_FINAL,
            case_set_sha256=rag_case_set or rag_family.case_set_sha256,
            candidate_case_count=len(rag_cases),
            passed_count=sum(1 for item in rag_cases if item.outcome is CaseOutcome.PASS),
            failed_count=sum(
                1 for item in rag_cases if item.outcome is CaseOutcome.FAIL
            ),
            cases=rag_cases,
            network_call_count=rag_network,
            live_embedding_call_count=live_embedding,
            live_llm_call_count=live_llm,
            report_sha256=rag_report_sha or rag_family.report_sha256,
        )
        tool = ToolAssistantQualitySnapshot(
            evaluation_family=EvaluationFamily.TOOL_ASSISTANT,
            case_set_sha256=tool_case_set or tool_family.case_set_sha256,
            candidate_case_count=len(tool_cases),
            passed_count=sum(
                1 for item in tool_cases if item.outcome is CaseOutcome.PASS
            ),
            failed_count=sum(
                1 for item in tool_cases if item.outcome is CaseOutcome.FAIL
            ),
            cases=tool_cases,
            network_call_count=tool_network,
            live_provider_call_count=live_provider,
            report_sha256=tool_report_sha or tool_family.report_sha256,
        )
        return AiQualitySnapshot(
            schema_version=1,
            rag=rag,
            tool_assistant=tool,
            privacy_violation_count=privacy_violation_count,
            candidate_sha=candidate_sha,
        )

    def test_exact_matching_candidate_returns_pass(self):
        result = run_ai_quality_gate(self.matching)
        self.assertEqual(result.top_level_outcome, QualityGateCode.PASS)
        self.assertEqual(result.reason_codes, ())
        self.assertEqual(result.case_regressions, ())

    def test_candidate_sha_differential_yields_identical_gate_result(self):
        first = run_ai_quality_gate(
            self._snapshot_from_baseline(candidate_sha="abcdef1")
        )
        second = run_ai_quality_gate(
            self._snapshot_from_baseline(candidate_sha="1234567890abcdef")
        )
        self.assertEqual(first, second)
        self.assertEqual(first.top_level_outcome, QualityGateCode.PASS)

    def test_candidate_report_sha_differential_yields_identical_gate_result(self):
        first = run_ai_quality_gate(
            self._snapshot_from_baseline(rag_report_sha=_SHA_ALT)
        )
        second = run_ai_quality_gate(
            self._snapshot_from_baseline(tool_report_sha=_SHA_ALT)
        )
        self.assertEqual(first, second)
        self.assertEqual(first.top_level_outcome, QualityGateCode.PASS)

    def test_rag_case_set_sha_mismatch_baseline_incompatible(self):
        result = run_ai_quality_gate(
            self._snapshot_from_baseline(rag_case_set=_SHA_ALT)
        )
        self.assertIn(QualityGateCode.BASELINE_INCOMPATIBLE, result.reason_codes)

    def test_tool_case_set_sha_mismatch_baseline_incompatible(self):
        result = run_ai_quality_gate(
            self._snapshot_from_baseline(tool_case_set=_SHA_ALT)
        )
        self.assertIn(QualityGateCode.BASELINE_INCOMPATIBLE, result.reason_codes)

    def test_missing_candidate_case_evaluation_incomplete(self):
        rag_family = next(
            item
            for item in self.baseline.families
            if item.evaluation_family is EvaluationFamily.RAG_FINAL
        )
        removed_id = rag_family.cases[0].case_id
        rag_cases = tuple(
            PerCaseQualitySnapshot(
                case_id=case.case_id,
                outcome=CaseOutcome.PASS,
                result_fingerprint=case.result_fingerprint,
            )
            for case in rag_family.cases
            if case.case_id != removed_id
        )
        result = run_ai_quality_gate(
            self._snapshot_from_baseline(rag_cases=rag_cases)
        )
        self.assertIn(QualityGateCode.EVALUATION_INCOMPLETE, result.reason_codes)
        codes = {
            (item.case_id, item.regression_code)
            for item in result.case_regressions
        }
        self.assertIn((removed_id, CaseRegressionCode.MISSING_CASE), codes)

    def test_unexpected_candidate_case_evaluation_incomplete(self):
        rag_family = next(
            item
            for item in self.baseline.families
            if item.evaluation_family is EvaluationFamily.RAG_FINAL
        )
        extra_id = "ZZ-UNEXPECTED-CASE"
        rag_cases = tuple(
            PerCaseQualitySnapshot(
                case_id=case.case_id,
                outcome=CaseOutcome.PASS,
                result_fingerprint=case.result_fingerprint,
            )
            for case in rag_family.cases
        ) + (
            PerCaseQualitySnapshot(
                case_id=extra_id,
                outcome=CaseOutcome.PASS,
                result_fingerprint=_fingerprint(extra_id),
            ),
        )
        result = run_ai_quality_gate(
            self._snapshot_from_baseline(rag_cases=rag_cases)
        )
        self.assertIn(QualityGateCode.EVALUATION_INCOMPLETE, result.reason_codes)
        codes = {
            (item.case_id, item.regression_code)
            for item in result.case_regressions
        }
        self.assertIn((extra_id, CaseRegressionCode.UNEXPECTED_CASE), codes)

    def test_q21_case_swap_with_unchanged_aggregate_counts_fails(self):
        """Q21: aggregate counts must not mask case-ID substitution."""
        rag_family = next(
            item
            for item in self.baseline.families
            if item.evaluation_family is EvaluationFamily.RAG_FINAL
        )
        case_a = rag_family.cases[0]
        case_b = rag_family.cases[1]
        swapped = []
        for case in rag_family.cases:
            if case.case_id == case_b.case_id:
                swapped.append(
                    PerCaseQualitySnapshot(
                        case_id="ZZ-CASE-C-SWAP",
                        outcome=CaseOutcome.PASS,
                        result_fingerprint=case_b.result_fingerprint,
                    )
                )
            else:
                swapped.append(
                    PerCaseQualitySnapshot(
                        case_id=case.case_id,
                        outcome=CaseOutcome.PASS,
                        result_fingerprint=case.result_fingerprint,
                    )
                )
        result = run_ai_quality_gate(
            self._snapshot_from_baseline(rag_cases=tuple(swapped))
        )
        self.assertEqual(len(swapped), rag_family.expected_case_count)
        self.assertIn(QualityGateCode.EVALUATION_INCOMPLETE, result.reason_codes)
        codes = {
            (item.case_id, item.regression_code)
            for item in result.case_regressions
        }
        self.assertIn((case_b.case_id, CaseRegressionCode.MISSING_CASE), codes)
        self.assertIn(
            ("ZZ-CASE-C-SWAP", CaseRegressionCode.UNEXPECTED_CASE),
            codes,
        )
        self.assertIn(case_a.case_id, {item.case_id for item in swapped})

    def test_candidate_non_pass_case_regression_detected(self):
        rag_family = next(
            item
            for item in self.baseline.families
            if item.evaluation_family is EvaluationFamily.RAG_FINAL
        )
        target = rag_family.cases[0]
        rag_cases = tuple(
            PerCaseQualitySnapshot(
                case_id=case.case_id,
                outcome=(
                    CaseOutcome.FAIL
                    if case.case_id == target.case_id
                    else CaseOutcome.PASS
                ),
                result_fingerprint=case.result_fingerprint,
            )
            for case in rag_family.cases
        )
        result = run_ai_quality_gate(
            self._snapshot_from_baseline(rag_cases=rag_cases)
        )
        self.assertIn(QualityGateCode.REGRESSION_DETECTED, result.reason_codes)
        codes = {
            (item.case_id, item.regression_code)
            for item in result.case_regressions
        }
        self.assertIn((target.case_id, CaseRegressionCode.NON_PASS_OUTCOME), codes)

    def test_candidate_fingerprint_mismatch_regression_detected(self):
        rag_family = next(
            item
            for item in self.baseline.families
            if item.evaluation_family is EvaluationFamily.RAG_FINAL
        )
        target = rag_family.cases[0]
        rag_cases = tuple(
            PerCaseQualitySnapshot(
                case_id=case.case_id,
                outcome=CaseOutcome.PASS,
                result_fingerprint=(
                    _fingerprint("mutated")
                    if case.case_id == target.case_id
                    else case.result_fingerprint
                ),
            )
            for case in rag_family.cases
        )
        result = run_ai_quality_gate(
            self._snapshot_from_baseline(rag_cases=rag_cases)
        )
        self.assertIn(QualityGateCode.REGRESSION_DETECTED, result.reason_codes)
        codes = {
            (item.case_id, item.regression_code)
            for item in result.case_regressions
        }
        self.assertIn(
            (target.case_id, CaseRegressionCode.FINGERPRINT_MISMATCH),
            codes,
        )

    def test_multiple_simultaneous_regressions_are_deterministically_sorted(self):
        rag_family = next(
            item
            for item in self.baseline.families
            if item.evaluation_family is EvaluationFamily.RAG_FINAL
        )
        first = rag_family.cases[0]
        second = rag_family.cases[1]
        rag_cases = []
        for case in rag_family.cases:
            if case.case_id == first.case_id:
                rag_cases.append(
                    PerCaseQualitySnapshot(
                        case_id=case.case_id,
                        outcome=CaseOutcome.FAIL,
                        result_fingerprint=_fingerprint("first"),
                    )
                )
            elif case.case_id == second.case_id:
                rag_cases.append(
                    PerCaseQualitySnapshot(
                        case_id=case.case_id,
                        outcome=CaseOutcome.FAIL,
                        result_fingerprint=_fingerprint("second"),
                    )
                )
            else:
                rag_cases.append(
                    PerCaseQualitySnapshot(
                        case_id=case.case_id,
                        outcome=CaseOutcome.PASS,
                        result_fingerprint=case.result_fingerprint,
                    )
                )
        result = run_ai_quality_gate(
            self._snapshot_from_baseline(
                rag_cases=tuple(rag_cases),
                privacy_violation_count=1,
                rag_network=1,
            )
        )
        self.assertEqual(
            result.reason_codes,
            tuple(sorted(result.reason_codes, key=lambda item: item.value)),
        )
        keys = [
            (
                item.evaluation_family.value,
                item.case_id,
                item.regression_code.value,
            )
            for item in result.case_regressions
        ]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(result.top_level_outcome, result.reason_codes[0])

    def test_privacy_violation_count_gate(self):
        result = run_ai_quality_gate(
            self._snapshot_from_baseline(privacy_violation_count=2)
        )
        self.assertIn(QualityGateCode.PRIVACY_VIOLATION, result.reason_codes)

    def test_network_call_count_gate(self):
        result = run_ai_quality_gate(
            self._snapshot_from_baseline(tool_network=1)
        )
        self.assertIn(QualityGateCode.NETWORK_ACTIVITY_DETECTED, result.reason_codes)

    def test_rag_live_embedding_call_count_gate(self):
        result = run_ai_quality_gate(
            self._snapshot_from_baseline(live_embedding=1)
        )
        self.assertIn(
            QualityGateCode.LIVE_PROVIDER_ACTIVITY_DETECTED,
            result.reason_codes,
        )

    def test_rag_live_llm_call_count_gate(self):
        result = run_ai_quality_gate(self._snapshot_from_baseline(live_llm=1))
        self.assertIn(
            QualityGateCode.LIVE_PROVIDER_ACTIVITY_DETECTED,
            result.reason_codes,
        )

    def test_tool_live_provider_call_count_gate(self):
        result = run_ai_quality_gate(
            self._snapshot_from_baseline(live_provider=1)
        )
        self.assertIn(
            QualityGateCode.LIVE_PROVIDER_ACTIVITY_DETECTED,
            result.reason_codes,
        )

    def test_malformed_baseline_follows_baseline_invalid(self):
        result = run_ai_quality_gate(self.matching)
        self.assertEqual(result.top_level_outcome, QualityGateCode.PASS)
        with self.assertRaises(QualityGateContractError):
            parse_quality_baseline("{not-json")
        with patch.object(
            quality_gate_module,
            "SPRINT121_AI_QUALITY_BASELINE_SHA256",
            _SHA_ALT,
        ):
            public = run_ai_quality_gate(self.matching)
        self.assertEqual(public.top_level_outcome, QualityGateCode.BASELINE_INVALID)
        self.assertEqual(
            public.reason_codes,
            (QualityGateCode.BASELINE_INVALID,),
        )
        self.assertEqual(public.case_regressions, ())
        self.assertNotIn("Traceback", repr(public))
        self.assertNotIn("Exception", public.top_level_outcome.value)

    def test_baseline_report_hash_is_diagnostic_only(self):
        mutated = json.loads(
            SPRINT121_AI_QUALITY_BASELINE_PATH.read_text(encoding="utf-8")
        )
        for family in mutated["families"]:
            family["report_sha256"] = _SHA_ALT
        mutated_baseline = parse_quality_baseline(
            json.dumps(mutated, sort_keys=True, separators=(",", ":"))
        )
        result = evaluate_against_baseline(self.matching, mutated_baseline)
        self.assertEqual(result.top_level_outcome, QualityGateCode.PASS)

    def test_aggregate_pass_counts_cannot_bypass_fingerprint_regression(self):
        rag_family = next(
            item
            for item in self.baseline.families
            if item.evaluation_family is EvaluationFamily.RAG_FINAL
        )
        target = rag_family.cases[0]
        rag_cases = tuple(
            PerCaseQualitySnapshot(
                case_id=case.case_id,
                outcome=CaseOutcome.PASS,
                result_fingerprint=(
                    _fingerprint("aggregate-mask")
                    if case.case_id == target.case_id
                    else case.result_fingerprint
                ),
            )
            for case in rag_family.cases
        )
        snapshot = self._snapshot_from_baseline(rag_cases=rag_cases)
        self.assertEqual(snapshot.rag.passed_count, snapshot.rag.candidate_case_count)
        result = run_ai_quality_gate(snapshot)
        self.assertIn(QualityGateCode.REGRESSION_DETECTED, result.reason_codes)
        self.assertTrue(
            any(
                item.regression_code is CaseRegressionCode.FINGERPRINT_MISMATCH
                for item in result.case_regressions
            )
        )

    def test_gate_module_has_no_evaluator_provider_network_subprocess(self):
        from apps.skill_ledger.evaluation import quality_gate as module

        source = Path(inspect.getsourcefile(module)).read_text(encoding="utf-8")
        self.assertNotIn("run_final_rag_evaluation", source)
        self.assertNotIn("run_tool_assistant_evaluation", source)
        self.assertNotIn("provider_factory", source)
        tree = ast.parse(source)
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        forbidden = {"requests", "httpx", "socket", "urllib", "subprocess"}
        self.assertEqual(forbidden.intersection(imported), set())

    def test_gate_result_is_immutable(self):
        result = run_ai_quality_gate(self.matching)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.top_level_outcome = QualityGateCode.REGRESSION_DETECTED  # type: ignore[misc]


class BaselineContractHardeningTests(SimpleTestCase):
    def setUp(self):
        self.payload = json.loads(
            SPRINT121_AI_QUALITY_BASELINE_PATH.read_text(encoding="utf-8")
        )

    def _dumps(self, payload: object) -> str:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )

    def test_extra_root_key_rejected(self):
        mutated = dict(self.payload)
        mutated["metadata"] = {"x": 1}
        with self.assertRaises(QualityGateContractError) as ctx:
            parse_quality_baseline(self._dumps(mutated))
        self.assertIn("unknown keys", str(ctx.exception))

    def test_extra_family_key_rejected(self):
        mutated = json.loads(self._dumps(self.payload))
        mutated["families"][0]["extra_family_field"] = "nope"
        with self.assertRaises(QualityGateContractError) as ctx:
            parse_quality_baseline(self._dumps(mutated))
        self.assertIn("unknown keys", str(ctx.exception))

    def test_extra_case_key_rejected(self):
        mutated = json.loads(self._dumps(self.payload))
        mutated["families"][0]["cases"][0]["message"] = "leak"
        with self.assertRaises(QualityGateContractError) as ctx:
            parse_quality_baseline(self._dumps(mutated))
        self.assertIn("unknown keys", str(ctx.exception))

    def test_missing_required_root_key_rejected(self):
        mutated = dict(self.payload)
        del mutated["provenance_commit"]
        with self.assertRaises(QualityGateContractError) as ctx:
            parse_quality_baseline(self._dumps(mutated))
        self.assertIn("missing required keys", str(ctx.exception))

    def test_schema_version_bool_true_rejected(self):
        mutated = dict(self.payload)
        mutated["schema_version"] = True
        with self.assertRaises(QualityGateContractError):
            parse_quality_baseline(self._dumps(mutated))

    def test_unsorted_cases_rejected(self):
        mutated = json.loads(self._dumps(self.payload))
        cases = mutated["families"][0]["cases"]
        if len(cases) < 2:
            self.fail("expected multiple RAG cases for unsorted test")
        cases[0], cases[1] = cases[1], cases[0]
        with self.assertRaises(QualityGateContractError) as ctx:
            parse_quality_baseline(self._dumps(mutated))
        self.assertIn("sorted by case_id", str(ctx.exception))

    def test_duplicate_json_object_keys_rejected(self):
        with self.assertRaises(QualityGateContractError) as ctx:
            parse_quality_baseline(
                '{"schema_version":1,"schema_version":1,'
                '"provenance_commit":'
                f'"{SPRINT121_BASELINE_PROVENANCE_COMMIT}",'
                '"families":[]}'
            )
        self.assertIn("duplicate JSON object key", str(ctx.exception))

    def test_public_loader_has_no_path_or_hash_overrides(self):
        signature = inspect.signature(load_authoritative_baseline)
        self.assertEqual(list(signature.parameters), [])
        source = Path(inspect.getsourcefile(quality_gate_module)).read_text(
            encoding="utf-8"
        )
        self.assertIn("def load_authoritative_baseline() -> QualityBaseline:", source)
        self.assertNotIn("expected_integrity_sha256", source)
        self.assertNotIn("path: Path | None", source)

    def test_public_fixed_loader_integrity_failure_maps_to_baseline_invalid(self):
        helper = QualityGateComparisonTests()
        helper.setUp()
        snapshot = helper.matching
        fake_path = MagicMock()
        fake_path.read_text.return_value = "{not-json"
        with patch.object(
            quality_gate_module,
            "SPRINT121_AI_QUALITY_BASELINE_PATH",
            fake_path,
        ):
            result = run_ai_quality_gate(snapshot)
        self.assertEqual(result.top_level_outcome, QualityGateCode.BASELINE_INVALID)
        self.assertEqual(result.reason_codes, (QualityGateCode.BASELINE_INVALID,))
        self.assertEqual(result.case_regressions, ())
        self.assertNotIn("JSONDecodeError", repr(result))
        self.assertNotIn("not-json", repr(result))

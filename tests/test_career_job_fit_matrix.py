import importlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.career_job_fit_matrix import (
    CONFIDENCE_VALUES,
    JOB_DESCRIPTION_PATH,
    STRENGTH_VALUES,
    build_repository_index,
    evaluate_requirements,
    main,
    render_report,
    run_matrix,
    write_report,
)


class CareerJobFitMatrixTests(unittest.TestCase):
    def test_run_matrix_produces_allowed_strength_and_confidence_values(self):
        _, rows = run_matrix()
        self.assertGreater(len(rows), 10)
        for row in rows:
            self.assertIn(row.evidence_strength, STRENGTH_VALUES)
            self.assertIn(row.confidence, CONFIDENCE_VALUES)

    def test_missing_strength_uses_missing_evidence_label(self):
        _, rows = run_matrix()
        missing_rows = [row for row in rows if row.evidence_strength == "Missing"]
        for row in missing_rows:
            self.assertEqual(row.repository_evidence, "Missing")

    def test_render_report_contains_required_sections(self):
        index = build_repository_index()
        report = render_report(index, evaluate_requirements(index))
        required = [
            "## Job Description Summary",
            "## Job-Fit Matrix",
            "## Strongest Matches",
            "## Partial Matches",
            "## Overall Fit Assessment",
            "## Missing Evidence",
            "## Evidence Limitations",
            "## Next Improvement Suggestions",
            "## Evidence Rules",
        ]
        for heading in required:
            with self.subTest(heading=heading):
                self.assertIn(heading, report)

    def test_write_report_creates_output_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "02_job_fit_matrix.md"
            path = write_report("# Matrix\n", output_path=output)
            self.assertTrue(path.is_file())
            self.assertEqual(path.read_text(encoding="utf-8"), "# Matrix\n")

    def test_main_generates_default_output_path(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "02_job_fit_matrix.md"
            job_input = Path(tmp_dir) / "sample_job_description.txt"
            job_input.write_text(
                "# Analyst role\n\nPython and SQL required.\n",
                encoding="utf-8",
            )
            with (
                mock.patch("tools.career_job_fit_matrix.OUTPUT_PATH", output),
                mock.patch("tools.career_job_fit_matrix.JOB_DESCRIPTION_PATH", job_input),
            ):
                self.assertEqual(main(), 0)
            self.assertTrue(output.is_file())
            self.assertIn("## Job-Fit Matrix", output.read_text(encoding="utf-8"))

    def test_no_external_api_dependency_in_module(self):
        module = sys.modules["tools.career_job_fit_matrix"]
        source = Path(module.__file__).read_text(encoding="utf-8")
        forbidden = ("openai", "anthropic", "requests", "httpx", "urllib.request")
        for name in forbidden:
            with self.subTest(name=name):
                self.assertNotIn(name, source.lower())

    def test_sample_job_description_exists(self):
        self.assertTrue(JOB_DESCRIPTION_PATH.is_file())

    def test_script_entry_point_importable(self):
        importlib.import_module("tools.career_job_fit_matrix")

    def test_missing_evidence_lists_fit_assessment_gaps(self):
        index = build_repository_index()
        report = render_report(index, evaluate_requirements(index))
        self.assertIn("### Gaps reflected in the overall fit assessment", report)
        self.assertIn("Live deployment proof is not verified", report)
        self.assertIn("External integrations are not implemented", report)

    def test_git_evidence_uses_workflow_paths_not_branch_name(self):
        index = build_repository_index()
        report = render_report(index, evaluate_requirements(index))
        self.assertIn(".github/workflows/django-ci.yml", report)
        self.assertNotIn("git branch sprint-", report.lower())
        self.assertNotIn("git branch ", report)


if __name__ == "__main__":
    unittest.main()

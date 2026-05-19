import importlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.career_recruiter_pack import (
    FORBIDDEN_PHRASES,
    OUTPUT_PATH,
    load_sources,
    main,
    parse_evidence,
    render_pack,
    run_pack,
    write_pack,
)


class CareerRecruiterPackTests(unittest.TestCase):
    REQUIRED_SECTIONS = [
        "## Project Positioning Summary",
        "## Target Roles",
        "## Core Technical Evidence",
        "## Business / Domain Evidence",
        "## Analytics & Reporting Evidence",
        "## Workflow & Engineering Discipline",
        "## Recruiter-Friendly CV Bullets",
        "## LinkedIn Project Summary",
        "## Interview Talking Points",
        "## Evidence Limitations",
        "## Suggested Next Improvements",
        "## Evidence Rules",
    ]

    def test_main_generates_output_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "03_recruiter_evidence_pack.md"
            with mock.patch("tools.career_recruiter_pack.OUTPUT_PATH", output):
                self.assertEqual(main(), 0)
            self.assertTrue(output.is_file())
            self.assertGreater(len(output.read_text(encoding="utf-8")), 500)

    def test_render_pack_contains_required_sections(self):
        sources = load_sources()
        report = render_pack(sources, parse_evidence(sources))
        for heading in self.REQUIRED_SECTIONS:
            with self.subTest(heading=heading):
                self.assertIn(heading, report)

    def test_forbidden_exaggerated_phrases_not_present(self):
        sources = load_sources()
        report = render_pack(sources, parse_evidence(sources)).lower()
        for phrase in FORBIDDEN_PHRASES:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, report)

    def test_cv_bullets_are_present(self):
        sources = load_sources()
        report = render_pack(sources, parse_evidence(sources))
        self.assertIn("## Recruiter-Friendly CV Bullets", report)
        self.assertIn("1. Built a Python and Django", report)
        self.assertIn("5. Documents analytics lineage", report)

    def test_evidence_limitations_section_exists(self):
        sources = load_sources()
        report = render_pack(sources, parse_evidence(sources))
        self.assertIn("## Evidence Limitations", report)
        self.assertIn("deployment is not verified", report.lower())
        self.assertIn("gmail", report.lower())

    def test_interview_talking_points_have_required_fields(self):
        sources = load_sources()
        report = render_pack(sources, parse_evidence(sources))
        self.assertGreaterEqual(report.count("**What was built:**"), 5)
        self.assertGreaterEqual(report.count("**Why it matters:**"), 5)
        self.assertGreaterEqual(report.count("**What evidence supports it:**"), 5)

    def test_no_external_api_dependency_in_module(self):
        module = sys.modules["tools.career_recruiter_pack"]
        source = Path(module.__file__).read_text(encoding="utf-8")
        forbidden = ("openai", "anthropic", "requests", "httpx", "urllib.request")
        for name in forbidden:
            with self.subTest(name=name):
                self.assertNotIn(name, source.lower())

    def test_write_pack_creates_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = write_pack("# Pack\n", output_path=Path(tmp_dir) / "pack.md")
            self.assertEqual(path.read_text(encoding="utf-8"), "# Pack\n")

    def test_run_pack_requires_inputs_on_disk(self):
        sources, parsed = run_pack()
        self.assertTrue(sources.readme)
        self.assertTrue(sources.job_fit_matrix)

    def test_default_output_path_configured(self):
        self.assertTrue(str(OUTPUT_PATH).endswith("03_recruiter_evidence_pack.md"))

    def test_script_entry_point_importable(self):
        importlib.import_module("tools.career_recruiter_pack")


if __name__ == "__main__":
    unittest.main()

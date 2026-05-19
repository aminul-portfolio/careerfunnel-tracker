import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.career_evidence_audit import (
    REPO_ROOT,
    REPORT_TITLE,
    GitEvidence,
    ScanCounts,
    build_missing_evidence,
    collect_git_evidence,
    discover_screenshot_folders,
    render_report,
    run_audit,
    scan_repository,
    write_report,
)


class CareerEvidenceAuditTests(unittest.TestCase):
    def test_scan_repository_counts_core_assets(self):
        inventory = scan_repository()
        counts = inventory.counts
        self.assertTrue((REPO_ROOT / "README.md").is_file())
        self.assertGreater(counts.documentation_files, 0)
        self.assertGreater(counts.template_files, 0)
        self.assertGreater(counts.css_files, 0)
        self.assertGreater(counts.js_files, 0)
        self.assertGreater(counts.screenshots, 0)
        self.assertIn("docs/screenshots", "".join(inventory.screenshot_folders))

    def test_discover_screenshot_folders_finds_docs_paths(self):
        folders = discover_screenshot_folders()
        relative = {path.as_posix() for path in folders}
        has_docs_screenshots = any(
            "docs/screenshots" in item or "docs/evidence/screenshots" in item for item in relative
        )
        self.assertTrue(
            has_docs_screenshots,
            msg=f"Expected screenshot folders under docs/, got: {relative}",
        )

    def test_render_report_includes_required_sections(self):
        report = render_report(run_audit())
        required = [
            "## Project Summary",
            "## Repository Structure",
            "## Evidence Inventory",
            "## Testing Evidence",
            "## Documentation Evidence",
            "## Frontend Asset Evidence",
            "## Screenshot Evidence",
            "## Git Status",
            "## Validation Evidence",
            "## Missing Evidence",
            "## Next Improvement Suggestions",
        ]
        for heading in required:
            with self.subTest(heading=heading):
                self.assertIn(heading, report)

    def test_write_report_creates_markdown_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "report.md"
            path = write_report("# Test Report\n", output_path=output)
            self.assertTrue(path.is_file())
            self.assertEqual(path.read_text(encoding="utf-8"), "# Test Report\n")

    def test_build_missing_evidence_flags_missing_readme(self):
        inventory = scan_repository()
        missing = build_missing_evidence(inventory, collect_git_evidence(), readme_present=False)
        self.assertTrue(any("README.md" in item for item in missing))

    def test_collect_git_evidence_when_git_available(self):
        git = collect_git_evidence()
        if git.available:
            self.assertNotEqual(git.branch, "git not available")
            self.assertGreater(len(git.latest_commit), 7)

    def test_main_writes_report_to_configured_path(self):
        from tools.career_evidence_audit import main

        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "01_project_evidence_report.md"
            with mock.patch("tools.career_evidence_audit.REPORT_PATH", output):
                self.assertEqual(main(), 0)
            self.assertTrue(output.is_file())
            self.assertIn("## Evidence Inventory", output.read_text(encoding="utf-8"))

    def test_render_report_uses_ascii_hyphens_only(self):
        report = render_report(run_audit())
        self.assertIn(f"# {REPORT_TITLE}", report)
        self.assertNotIn("\u2014", report)
        self.assertNotIn("\u2013", report)
        self.assertNotIn("â€", report)

    def test_missing_evidence_ignores_uncommitted_git_changes(self):
        inventory = scan_repository()
        git = GitEvidence(
            available=True,
            branch="sprint-23-career-evidence-v1",
            latest_commit="abc1234567890",
            status_short="?? docs/career_evidence/\n?? tools/",
        )
        missing = build_missing_evidence(inventory, git, readme_present=True)
        self.assertFalse(any("uncommitted" in item.lower() for item in missing))

    def test_validation_evidence_section_is_manual_not_hardcoded_pass(self):
        report = render_report(run_audit())
        self.assertIn("Not collected by scanner", report)
        self.assertNotIn("| `ruff check .` | Pass |", report)

    def test_scan_counts_dataclass_defaults(self):
        counts = ScanCounts()
        self.assertEqual(counts.documentation_files, 0)
        self.assertEqual(counts.screenshots, 0)


if __name__ == "__main__":
    unittest.main()

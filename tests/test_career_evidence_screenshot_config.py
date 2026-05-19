import unittest

from scripts.capture_career_evidence_screenshots import (
    DEFAULT_BASE_URL,
    EXPECTED_FILENAMES,
    OUTPUT_DIR,
    PAGE_CAPTURES,
    REQUIRED_PATHS,
    VIEWPORT_HEIGHT,
    VIEWPORT_WIDTH,
    PageCapture,
    build_login_url,
    build_page_url,
    ensure_output_dir,
)


class CareerEvidenceScreenshotConfigTests(unittest.TestCase):
    def test_required_url_mapping_exists(self):
        self.assertEqual(len(PAGE_CAPTURES), 4)
        self.assertEqual(REQUIRED_PATHS, {
            "/career-evidence/",
            "/career-evidence/project-evidence/",
            "/career-evidence/job-fit-matrix/",
            "/career-evidence/recruiter-pack/",
        })
        paths = {capture.path for capture in PAGE_CAPTURES}
        self.assertEqual(paths, REQUIRED_PATHS)

    def test_expected_filenames(self):
        self.assertEqual(
            EXPECTED_FILENAMES,
            {
                "career_evidence_overview.png",
                "project_evidence_report.png",
                "job_fit_matrix.png",
                "recruiter_pack.png",
            },
        )
        filenames = {capture.filename for capture in PAGE_CAPTURES}
        self.assertEqual(filenames, EXPECTED_FILENAMES)

    def test_output_directory_path_logic(self):
        normalized = str(OUTPUT_DIR).replace("\\", "/")
        self.assertTrue(normalized.endswith("docs/screenshots/career_evidence"))
        self.assertEqual(OUTPUT_DIR.name, "career_evidence")
        self.assertEqual(OUTPUT_DIR.parent.name, "screenshots")

    def test_viewport_configuration(self):
        self.assertEqual(VIEWPORT_WIDTH, 1440)
        self.assertEqual(VIEWPORT_HEIGHT, 1200)

    def test_build_page_url_joins_base_and_path(self):
        self.assertEqual(
            build_page_url(DEFAULT_BASE_URL, "/career-evidence/"),
            "http://127.0.0.1:8000/dashboard/career-evidence/",
        )
        self.assertEqual(
            build_page_url(DEFAULT_BASE_URL, "career-evidence/recruiter-pack/"),
            "http://127.0.0.1:8000/dashboard/career-evidence/recruiter-pack/",
        )

    def test_build_login_url_uses_site_root(self):
        self.assertEqual(
            build_login_url("http://127.0.0.1:8000"),
            "http://127.0.0.1:8000/accounts/login/",
        )

    def test_page_capture_is_immutable_mapping_entry(self):
        capture = PAGE_CAPTURES[0]
        self.assertIsInstance(capture, PageCapture)
        self.assertEqual(capture.path, "/career-evidence/")
        self.assertEqual(capture.filename, "career_evidence_overview.png")

    def test_ensure_output_dir_creates_directory(self):
        with self.subTest("creates nested output path"):
            target = OUTPUT_DIR / "_test_create_only"
            if target.exists():
                target.rmdir()
            created = ensure_output_dir(target)
            self.assertTrue(created.is_dir())
            target.rmdir()


if __name__ == "__main__":
    unittest.main()

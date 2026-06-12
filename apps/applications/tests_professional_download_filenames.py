from __future__ import annotations

from datetime import date

from django.test import SimpleTestCase

from apps.applications.file_storage import (
    build_professional_application_pack_download_filename,
    build_professional_cover_letter_download_filename,
    build_professional_cv_download_filename,
    sanitize_filename_part,
)

FIXED_DOWNLOAD_DATE = date(2026, 5, 9)
EXPECTED_CV_PDF = "Aminul_Islam_CV_Howden_Junior_Data_Analyst_20260509.pdf"
EXPECTED_CV_DOCX = "Aminul_Islam_CV_Howden_Junior_Data_Analyst_20260509.docx"
EXPECTED_COVER_LETTER_PDF = (
    "Aminul_Islam_Cover_Letter_Howden_Junior_Data_Analyst_20260509.pdf"
)
EXPECTED_APPLICATION_PACK_PDF = (
    "Aminul_Islam_Application_Pack_Howden_Junior_Data_Analyst_20260509.pdf"
)


class ProfessionalDownloadFilenameBuilderTests(SimpleTestCase):
    def test_cv_pdf_filename_uses_professional_format(self):
        filename = build_professional_cv_download_filename(
            "Howden",
            "Junior Data Analyst",
            "pdf",
            download_date=FIXED_DOWNLOAD_DATE,
        )
        self.assertEqual(filename, EXPECTED_CV_PDF)

    def test_cv_docx_filename_uses_professional_format(self):
        filename = build_professional_cv_download_filename(
            "Howden",
            "Junior Data Analyst",
            "docx",
            download_date=FIXED_DOWNLOAD_DATE,
        )
        self.assertEqual(filename, EXPECTED_CV_DOCX)

    def test_cover_letter_and_application_pack_formats(self):
        cover_letter = build_professional_cover_letter_download_filename(
            "Howden",
            "Junior Data Analyst",
            "pdf",
            download_date=FIXED_DOWNLOAD_DATE,
        )
        application_pack = build_professional_application_pack_download_filename(
            "Howden",
            "Junior Data Analyst",
            "pdf",
            download_date=FIXED_DOWNLOAD_DATE,
        )
        self.assertEqual(cover_letter, EXPECTED_COVER_LETTER_PDF)
        self.assertEqual(application_pack, EXPECTED_APPLICATION_PACK_PDF)

    def test_filename_includes_candidate_company_role_and_date(self):
        filename = build_professional_cv_download_filename(
            "Monzo",
            "Data Analyst",
            "pdf",
            download_date=date(2026, 5, 31),
        )
        self.assertIn("Aminul_Islam", filename)
        self.assertIn("Monzo", filename)
        self.assertIn("Data_Analyst", filename)
        self.assertIn("20260531", filename)

    def test_filename_excludes_ab_metrics_and_internal_labels(self):
        filename = build_professional_cv_download_filename(
            "Howden",
            "Junior Data Analyst",
            "pdf",
            download_date=FIXED_DOWNLOAD_DATE,
        )
        for forbidden in (
            "Response",
            "Interview",
            "Promising",
            "Underperforming",
            "DA_CV_v2",
            "Finance_DA_CV_v1",
            "careerfunnel_",
        ):
            self.assertNotIn(forbidden, filename)

    def test_missing_company_and_role_use_fallbacks(self):
        filename = build_professional_cv_download_filename(
            "",
            "",
            "pdf",
            download_date=date(2026, 5, 31),
        )
        self.assertEqual(filename, "Aminul_Islam_CV_Company_Role_20260531.pdf")

    def test_sanitize_filename_part_removes_unsafe_characters(self):
        cleaned = sanitize_filename_part("Acme / Corp: Junior | Analyst")
        self.assertEqual(cleaned, "Acme_Corp_Junior_Analyst")
        self.assertNotIn("/", cleaned)
        self.assertNotIn(":", cleaned)

    def test_sanitize_filename_part_collapses_repeated_underscores(self):
        self.assertEqual(sanitize_filename_part("Acme   Corp"), "Acme_Corp")

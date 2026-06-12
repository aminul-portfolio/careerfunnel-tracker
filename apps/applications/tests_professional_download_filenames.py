from __future__ import annotations

from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.applications.file_storage import (
    build_professional_application_pack_download_filename,
    build_professional_cover_letter_download_filename,
    build_professional_cv_download_filename,
    sanitize_filename_part,
)
from apps.applications.test_master_cv_fixtures import mock_read_master_cv_file
from apps.job_intelligence.draft_documents import (
    build_application_document_drafts,
    build_clean_cover_letter_content,
    build_complete_cv_content,
)

from .choices import DocumentType, PipelineStage
from .models import ApplicationDocument, JobApplication

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


class ProfessionalDownloadFilenameViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="filename-user", password="StrongPass12345")
        self.application = JobApplication.objects.create(
            user=self.user,
            company_name="Howden",
            job_title="Junior Data Analyst",
            date_applied=FIXED_DOWNLOAD_DATE,
            pipeline_stage=PipelineStage.FIT_CHECKED,
        )
        drafts = build_application_document_drafts(self.application)
        self.cv_document = ApplicationDocument.objects.create(
            application=self.application,
            document_type=DocumentType.CV,
            name="Aminul_Islam_Data_Analyst_CV_Howden_Junior_Data_Analyst",
            content=build_complete_cv_content(self.application, drafts),
        )
        self.cover_letter_document = ApplicationDocument.objects.create(
            application=self.application,
            document_type=DocumentType.COVER_LETTER,
            name="Aminul_Islam_Cover_Letter_Howden_Junior_Data_Analyst",
            content=build_clean_cover_letter_content(
                company_name=self.application.company_name,
                job_title=self.application.job_title,
                body=drafts.cover_letter_draft,
            ),
        )
        self.client.login(username="filename-user", password="StrongPass12345")

    @patch(
        "apps.applications.master_cv.read_master_cv_file_if_available",
        side_effect=mock_read_master_cv_file,
    )
    def test_application_cv_download_content_disposition(self, _mock_read):
        response = self.client.get(
            reverse(
                "applications:application_document_download",
                kwargs={
                    "pk": self.application.pk,
                    "document_pk": self.cv_document.pk,
                    "file_format": "pdf",
                },
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(f'filename="{EXPECTED_CV_PDF}"', response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"%PDF"))

    @patch(
        "apps.applications.master_cv.read_master_cv_file_if_available",
        side_effect=mock_read_master_cv_file,
    )
    def test_application_cover_letter_download_content_disposition(self, _mock_read):
        response = self.client.get(
            reverse(
                "applications:application_document_download",
                kwargs={
                    "pk": self.application.pk,
                    "document_pk": self.cover_letter_document.pk,
                    "file_format": "pdf",
                },
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            f'filename="{EXPECTED_COVER_LETTER_PDF}"',
            response["Content-Disposition"],
        )
        self.assertTrue(response.content.startswith(b"%PDF"))

    @patch(
        "apps.applications.master_cv.read_master_cv_file_if_available",
        side_effect=mock_read_master_cv_file,
    )
    def test_evaluation_cv_download_content_disposition(self, _mock_read):
        response = self.client.get(
            reverse(
                "applications:evaluation_cv_download",
                kwargs={"pk": self.application.pk, "file_format": "docx"},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(f'filename="{EXPECTED_CV_DOCX}"', response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"PK"))

    @patch(
        "apps.applications.master_cv.read_master_cv_file_if_available",
        side_effect=mock_read_master_cv_file,
    )
    def test_evaluation_cover_letter_download_content_disposition(self, _mock_read):
        response = self.client.get(
            reverse(
                "applications:evaluation_cover_letter_download",
                kwargs={"pk": self.application.pk, "file_format": "pdf"},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            f'filename="{EXPECTED_COVER_LETTER_PDF}"',
            response["Content-Disposition"],
        )
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_evaluation_application_pack_download_content_disposition(self):
        response = self.client.get(
            reverse(
                "applications:evaluation_application_pack_download",
                kwargs={"pk": self.application.pk, "file_format": "pdf"},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            f'filename="{EXPECTED_APPLICATION_PACK_PDF}"',
            response["Content-Disposition"],
        )
        self.assertTrue(response.content.startswith(b"%PDF"))


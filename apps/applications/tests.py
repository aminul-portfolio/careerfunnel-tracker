import json
from datetime import date, timedelta
from unittest.mock import patch
from urllib.parse import quote

from django.contrib.auth.models import User
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format

from apps.job_intelligence.services import build_smart_review
from apps.recruiter_emails.choices import EmailType, ReplyStatus
from apps.recruiter_emails.models import RecruiterEmail

from .choices import (
    DEFAULT_CV_BASELINE_NAME,
    ApplicationSource,
    ApplicationStatus,
    DocumentSource,
    DocumentStatus,
    DocumentType,
    FollowUpStatus,
    PipelineStage,
    RoleFit,
    WorkType,
)
from .forms import ApplicationDocumentSelectionForm
from .models import ApplicationDocument, JobApplication
from .services import (
    ITEM_COMPANY_RESEARCHED,
    ITEM_CONTACT_EMAIL,
    ITEM_COVER_LETTER_VERSION,
    ITEM_CV_VERSION,
    ITEM_FOLLOW_UP_DATE,
    ITEM_FOLLOW_UP_STATUS,
    ITEM_JOB_DESCRIPTION,
    ITEM_JOB_URL,
    ITEM_PORTFOLIO_PROJECT,
    READINESS_LABEL_MISSING_KEY,
    READINESS_LABEL_NEEDS_IMPROVEMENT,
    READINESS_LABEL_STRONG,
    build_application_evidence_readiness,
    build_save_quality_warnings,
    calculate_response_rate,
)


class ApplicationChoiceTests(TestCase):
    def test_reed_and_bookmarklet_sources_exist(self):
        self.assertEqual(ApplicationSource.REED, "reed")
        self.assertEqual(ApplicationSource.BOOKMARKLET, "bookmarklet")
        self.assertIn(("reed", "Reed.co.uk"), ApplicationSource.choices)
        self.assertIn(("bookmarklet", "Bookmarklet"), ApplicationSource.choices)


class JobApplicationModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def test_days_to_response_returns_correct_value(self):
        application = JobApplication.objects.create(
            user=self.user,
            company_name="Test Company",
            job_title="Data Analyst",
            date_applied=date(2026, 5, 1),
            response_date=date(2026, 5, 4),
            status=ApplicationStatus.ACKNOWLEDGED,
        )
        self.assertEqual(application.days_to_response, 3)

    def test_days_to_response_returns_none_without_response_date(self):
        application = JobApplication.objects.create(
            user=self.user,
            company_name="Test Company",
            job_title="Data Analyst",
            date_applied=date(2026, 5, 1),
            status=ApplicationStatus.SUBMITTED,
        )
        self.assertIsNone(application.days_to_response)


class ApplicationDocumentModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")
        self.application = JobApplication.objects.create(
            user=self.user,
            company_name="Howden",
            job_title="Junior Data Analyst",
            date_applied=date(2026, 5, 9),
        )

    def test_application_document_can_be_created_for_application(self):
        document = ApplicationDocument.objects.create(
            application=self.application,
            document_type=DocumentType.CV,
            name="Aminul_Islam_Data_Analyst_CV_Howden_Junior_Data_Analyst",
            status=DocumentStatus.DRAFT,
            source=DocumentSource.MASTER_CV_BASELINE,
        )
        self.assertEqual(document.application, self.application)
        self.assertEqual(self.application.documents.count(), 1)

    def test_cv_document_type_is_valid(self):
        document = ApplicationDocument.objects.create(
            application=self.application,
            document_type=DocumentType.CV,
            name="Aminul_Islam_Data_Analyst_CV_Howden_Junior_Data_Analyst",
        )
        self.assertEqual(document.document_type, DocumentType.CV)
        self.assertEqual(document.get_document_type_display(), "CV")
        self.assertEqual(document.cv_baseline_name, DEFAULT_CV_BASELINE_NAME)

    def test_cover_letter_document_type_is_valid(self):
        document = ApplicationDocument.objects.create(
            application=self.application,
            document_type=DocumentType.COVER_LETTER,
            name="Cover_Letter_Howden_Junior_Data_Analyst",
        )
        self.assertEqual(document.document_type, DocumentType.COVER_LETTER)
        self.assertEqual(document.get_document_type_display(), "Cover letter")


class ApplicationDocumentViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")
        self.application = JobApplication.objects.create(
            user=self.user,
            company_name="Howden",
            job_title="Junior Data Analyst",
            date_applied=date(2026, 5, 9),
        )
        self.detail_url = reverse(
            "applications:application_detail",
            kwargs={"pk": self.application.pk},
        )

    def test_application_detail_displays_document_pack_section(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Application Document Pack")

    def test_application_detail_displays_saved_document_names(self):
        ApplicationDocument.objects.create(
            application=self.application,
            document_type=DocumentType.CV,
            name="Aminul_Islam_Data_Analyst_CV_Howden_Junior_Data_Analyst",
            status=DocumentStatus.SUBMITTED,
            source=DocumentSource.MASTER_CV_BASELINE,
        )
        ApplicationDocument.objects.create(
            application=self.application,
            document_type=DocumentType.COVER_LETTER,
            name="Cover_Letter_Howden_Junior_Data_Analyst",
            status=DocumentStatus.REVIEWED,
            source=DocumentSource.MANUAL,
        )
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aminul_Islam_Data_Analyst_CV_Howden_Junior_Data_Analyst")
        self.assertContains(response, "Cover_Letter_Howden_Junior_Data_Analyst")
        self.assertContains(response, "Submitted")
        self.assertContains(response, "Reviewed")

    def test_application_detail_shows_empty_state_when_no_documents_exist(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "No CV or cover letter documents have been saved for this application yet.",
        )


class ApplicationDocumentSelectionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")
        self.other_user = User.objects.create_user(username="other", password="StrongPass12345")
        self.application = JobApplication.objects.create(
            user=self.user,
            company_name="Howden",
            job_title="Junior Data Analyst",
            date_applied=date(2026, 5, 9),
        )
        self.other_application = JobApplication.objects.create(
            user=self.other_user,
            company_name="Other Co",
            job_title="Analyst",
            date_applied=date(2026, 5, 10),
        )
        self.cv_document = ApplicationDocument.objects.create(
            application=self.application,
            document_type=DocumentType.CV,
            name="Aminul_Islam_Data_Analyst_CV_Howden_Junior_Data_Analyst",
            quick_call_notes="CV quick call prep notes.",
        )
        self.cover_letter_document = ApplicationDocument.objects.create(
            application=self.application,
            document_type=DocumentType.COVER_LETTER,
            name="Aminul_Islam_Cover_Letter_Howden_Junior_Data_Analyst",
            quick_call_notes="Cover letter quick call prep notes.",
        )
        self.other_cv_document = ApplicationDocument.objects.create(
            application=self.other_application,
            document_type=DocumentType.CV,
            name="Aminul_Islam_Data_Analyst_CV_Other_Co_Analyst",
        )
        self.detail_url = reverse(
            "applications:application_detail",
            kwargs={"pk": self.application.pk},
        )

    def test_job_application_can_store_selected_cv_document(self):
        self.application.selected_cv_document = self.cv_document
        self.application.save(update_fields=["selected_cv_document"])
        self.application.refresh_from_db()
        self.assertEqual(self.application.selected_cv_document, self.cv_document)

    def test_job_application_can_store_selected_cover_letter_document(self):
        self.application.selected_cover_letter_document = self.cover_letter_document
        self.application.save(update_fields=["selected_cover_letter_document"])
        self.application.refresh_from_db()
        self.assertEqual(
            self.application.selected_cover_letter_document,
            self.cover_letter_document,
        )

    def test_selection_form_only_lists_cv_documents_for_cv_field(self):
        form = ApplicationDocumentSelectionForm(application=self.application)
        cv_ids = set(form.fields["selected_cv_document"].queryset.values_list("pk", flat=True))
        self.assertEqual(cv_ids, {self.cv_document.pk})

    def test_selection_form_only_lists_cover_letter_documents_for_cover_letter_field(self):
        form = ApplicationDocumentSelectionForm(application=self.application)
        cover_letter_ids = set(
            form.fields["selected_cover_letter_document"].queryset.values_list("pk", flat=True)
        )
        self.assertEqual(cover_letter_ids, {self.cover_letter_document.pk})

    def test_selection_form_does_not_list_documents_from_another_application(self):
        form = ApplicationDocumentSelectionForm(application=self.application)
        all_ids = set(
            form.fields["selected_cv_document"].queryset.values_list("pk", flat=True)
        ) | set(
            form.fields["selected_cover_letter_document"].queryset.values_list("pk", flat=True)
        )
        self.assertNotIn(self.other_cv_document.pk, all_ids)

    def test_application_detail_page_displays_selected_cv_document_name(self):
        self.application.selected_cv_document = self.cv_document
        self.application.save(update_fields=["selected_cv_document"])
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(self.detail_url)
        self.assertContains(response, "Selected CV")
        self.assertContains(response, self.cv_document.name)

    def test_application_detail_page_displays_selected_cover_letter_document_name(self):
        self.application.selected_cover_letter_document = self.cover_letter_document
        self.application.save(update_fields=["selected_cover_letter_document"])
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(self.detail_url)
        self.assertContains(response, "Selected cover letter")
        self.assertContains(response, self.cover_letter_document.name)

    def test_application_detail_page_shows_no_selected_document_fallback(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(self.detail_url)
        self.assertContains(response, "No CV selected yet.")
        self.assertContains(response, "No cover letter selected yet.")

    def test_post_select_documents_updates_selected_documents(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.post(
            self.detail_url,
            {
                "action": "select_documents",
                "selected_cv_document": self.cv_document.pk,
                "selected_cover_letter_document": self.cover_letter_document.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.application.refresh_from_db()
        self.assertEqual(self.application.selected_cv_document, self.cv_document)
        self.assertEqual(
            self.application.selected_cover_letter_document,
            self.cover_letter_document,
        )

    def test_post_select_documents_rejects_wrong_document_type(self):
        form = ApplicationDocumentSelectionForm(
            application=self.application,
            data={
                "selected_cv_document": self.cover_letter_document.pk,
                "selected_cover_letter_document": "",
            },
        )
        self.assertFalse(form.is_valid())

    def test_post_select_documents_rejects_document_from_another_application(self):
        form = ApplicationDocumentSelectionForm(
            application=self.application,
            data={
                "selected_cv_document": self.other_cv_document.pk,
                "selected_cover_letter_document": "",
            },
        )
        self.assertFalse(form.is_valid())

    def test_post_select_documents_view_rejects_invalid_selection(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.post(
            self.detail_url,
            {
                "action": "select_documents",
                "selected_cv_document": self.other_cv_document.pk,
                "selected_cover_letter_document": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.application.refresh_from_db()
        self.assertIsNone(self.application.selected_cv_document)

    def test_document_pack_upload_forms_are_available(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(self.detail_url)
        content = response.content.decode().lower()
        self.assertContains(response, "Upload CV")
        self.assertContains(response, "Create external CV reference")
        self.assertIn('type="file"', content)
        self.assertIn("enctype=\"multipart/form-data\"", content)


class ApplicationDocumentDownloadTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")
        self.other_user = User.objects.create_user(username="other", password="StrongPass12345")
        self.application = JobApplication.objects.create(
            user=self.user,
            company_name="Howden",
            job_title="Junior Data Analyst",
            date_applied=date(2026, 5, 9),
        )
        self.other_application = JobApplication.objects.create(
            user=self.other_user,
            company_name="Other Co",
            job_title="Analyst",
            date_applied=date(2026, 5, 10),
        )
        self.cv_document = ApplicationDocument.objects.create(
            application=self.application,
            document_type=DocumentType.CV,
            name="Aminul_Islam_Data_Analyst_CV_Howden_Junior_Data_Analyst",
            content="Draft CV tailoring notes content.",
            tailoring_notes="Profile angle notes.",
            project_evidence="BakeOps Intelligence evidence.",
            claim_safety_notes="Review manually before use.",
            quick_call_notes="Quick call prep notes.",
        )
        self.cover_letter_document = ApplicationDocument.objects.create(
            application=self.application,
            document_type=DocumentType.COVER_LETTER,
            name="Aminul_Islam_Cover_Letter_Howden_Junior_Data_Analyst",
            content="Draft cover letter content.",
        )
        self.other_document = ApplicationDocument.objects.create(
            application=self.other_application,
            document_type=DocumentType.CV,
            name="Aminul_Islam_Data_Analyst_CV_Other_Co_Analyst",
            content="Other application content.",
        )

    def _download_url(self, application, document, file_format):
        return reverse(
            "applications:application_document_download",
            kwargs={
                "pk": application.pk,
                "document_pk": document.pk,
                "file_format": file_format,
            },
        )

    def test_docx_download_returns_200(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(self._download_url(self.application, self.cv_document, "docx"))
        self.assertEqual(response.status_code, 200)

    def test_docx_download_has_correct_content_type(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(self._download_url(self.application, self.cv_document, "docx"))
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    def test_docx_download_has_attachment_filename_ending_docx(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(self._download_url(self.application, self.cv_document, "docx"))
        self.assertIn(
            'filename="Aminul_Islam_CV_Howden_Junior_Data_Analyst_20260509.docx"',
            response["Content-Disposition"],
        )

    def test_docx_download_starts_with_zip_header(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(self._download_url(self.application, self.cv_document, "docx"))
        self.assertTrue(response.content.startswith(b"PK"))

    def test_pdf_download_returns_200(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(
            self._download_url(self.application, self.cover_letter_document, "pdf")
        )
        self.assertEqual(response.status_code, 200)

    def test_pdf_download_has_correct_content_type(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(
            self._download_url(self.application, self.cover_letter_document, "pdf")
        )
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_pdf_download_has_attachment_filename_ending_pdf(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(
            self._download_url(self.application, self.cover_letter_document, "pdf")
        )
        self.assertIn(
            'filename="Aminul_Islam_Cover_Letter_Howden_Junior_Data_Analyst_20260509.pdf"',
            response["Content-Disposition"],
        )

    def test_pdf_download_starts_with_pdf_header(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(
            self._download_url(self.application, self.cover_letter_document, "pdf")
        )
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_download_requires_login(self):
        response = self.client.get(self._download_url(self.application, self.cv_document, "docx"))
        self.assertEqual(response.status_code, 302)

    def test_user_cannot_download_another_users_document(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(
            self._download_url(self.other_application, self.other_document, "docx")
        )
        self.assertEqual(response.status_code, 404)

    def test_document_must_belong_to_application_in_url(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(
            reverse(
                "applications:application_document_download",
                kwargs={
                    "pk": self.application.pk,
                    "document_pk": self.other_document.pk,
                    "file_format": "docx",
                },
            )
        )
        self.assertEqual(response.status_code, 404)

    def test_unsupported_format_is_rejected(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(self._download_url(self.application, self.cv_document, "txt"))
        self.assertEqual(response.status_code, 404)

    def test_application_detail_page_shows_download_links(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": self.application.pk})
        )
        self.assertContains(response, "Download DOCX")
        self.assertContains(response, "Download PDF")
        self.assertContains(
            response,
            "Downloads are generated from saved draft records.",
        )

    def test_downloaded_docx_and_pdf_include_non_empty_bytes(self):
        self.client.login(username="aminul", password="StrongPass12345")
        docx_response = self.client.get(
            self._download_url(self.application, self.cv_document, "docx")
        )
        pdf_response = self.client.get(
            self._download_url(self.application, self.cv_document, "pdf")
        )
        self.assertGreater(len(docx_response.content), 100)
        self.assertGreater(len(pdf_response.content), 100)


class DocumentEvidenceWorkflowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")
        self.application = JobApplication.objects.create(
            user=self.user,
            company_name="Howden",
            job_title="Junior Data Analyst",
            date_applied=date(2026, 5, 9),
        )
        self.detail_url = reverse(
            "applications:application_detail",
            kwargs={"pk": self.application.pk},
        )

    def test_readiness_passes_with_manual_cv_version_only(self):
        self.application.cv_version = "Aminul_Islam_Data_Analyst_CV"
        self.application.save(update_fields=["cv_version"])
        readiness = build_application_evidence_readiness(self.application)
        self.assertIn(ITEM_CV_VERSION, readiness.ready_items)

    def test_readiness_passes_with_manual_cover_letter_version_only(self):
        self.application.cover_letter_version = "Aminul_Islam_Cover_Letter_Howden"
        self.application.save(update_fields=["cover_letter_version"])
        readiness = build_application_evidence_readiness(self.application)
        self.assertIn(ITEM_COVER_LETTER_VERSION, readiness.ready_items)

    def test_readiness_passes_with_cv_document_without_manual_version(self):
        ApplicationDocument.objects.create(
            application=self.application,
            document_type=DocumentType.CV,
            name="External CV reference",
            source=DocumentSource.EXTERNAL_REFERENCE,
        )
        readiness = build_application_evidence_readiness(self.application)
        self.assertIn(ITEM_CV_VERSION, readiness.ready_items)

    def test_readiness_passes_with_cover_letter_document_without_manual_version(self):
        ApplicationDocument.objects.create(
            application=self.application,
            document_type=DocumentType.COVER_LETTER,
            name="External cover letter reference",
            source=DocumentSource.EXTERNAL_REFERENCE,
        )
        readiness = build_application_evidence_readiness(self.application)
        self.assertIn(ITEM_COVER_LETTER_VERSION, readiness.ready_items)

    def test_readiness_passes_when_selected_cv_document_exists(self):
        cv_document = ApplicationDocument.objects.create(
            application=self.application,
            document_type=DocumentType.CV,
            name="Selected CV record",
        )
        self.application.selected_cv_document = cv_document
        self.application.save(update_fields=["selected_cv_document"])
        readiness = build_application_evidence_readiness(self.application)
        self.assertIn(ITEM_CV_VERSION, readiness.ready_items)

    def test_create_external_cv_reference_without_upload(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.post(
            self.detail_url,
            {
                "action": "create_external_cv",
                "external_cv-name": "Tailored CV sent via email",
                "external_cv-notes": "Sent manually on 2026-06-14.",
            },
        )
        self.assertEqual(response.status_code, 302)
        document = ApplicationDocument.objects.get(
            application=self.application,
            document_type=DocumentType.CV,
        )
        self.assertEqual(document.name, "Tailored CV sent via email")
        self.assertEqual(document.source, DocumentSource.EXTERNAL_REFERENCE)
        self.assertEqual(document.tailoring_notes, "Sent manually on 2026-06-14.")
        self.assertFalse(document.uploaded_file)

    def test_create_external_cover_letter_reference_without_upload(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.post(
            self.detail_url,
            {
                "action": "create_external_cover_letter",
                "external_cl-name": "Howden tailored cover letter",
            },
        )
        self.assertEqual(response.status_code, 302)
        document = ApplicationDocument.objects.get(
            application=self.application,
            document_type=DocumentType.COVER_LETTER,
        )
        self.assertEqual(document.source, DocumentSource.EXTERNAL_REFERENCE)

    def test_upload_docx_cv_appears_in_selection_list(self):
        self.client.login(username="aminul", password="StrongPass12345")
        uploaded = SimpleUploadedFile(
            "Aminul_CV.docx",
            b"PK docx test content",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        response = self.client.post(
            self.detail_url,
            {
                "action": "upload_cv",
                "upload_cv-uploaded_file": uploaded,
            },
        )
        self.assertEqual(response.status_code, 302)
        document = ApplicationDocument.objects.get(
            application=self.application,
            document_type=DocumentType.CV,
        )
        self.assertEqual(document.name, "Aminul_CV.docx")
        self.assertEqual(document.original_filename, "Aminul_CV.docx")
        self.assertEqual(document.source, DocumentSource.USER_UPLOAD)
        form = ApplicationDocumentSelectionForm(application=self.application)
        self.assertIn(
            document.pk,
            form.fields["selected_cv_document"].queryset.values_list("pk", flat=True),
        )

    def test_upload_pdf_cover_letter_appears_in_selection_list(self):
        self.client.login(username="aminul", password="StrongPass12345")
        uploaded = SimpleUploadedFile(
            "Cover_Letter.pdf",
            b"%PDF-1.4 test",
            content_type="application/pdf",
        )
        response = self.client.post(
            self.detail_url,
            {
                "action": "upload_cover_letter",
                "upload_cl-uploaded_file": uploaded,
            },
        )
        self.assertEqual(response.status_code, 302)
        document = ApplicationDocument.objects.get(
            application=self.application,
            document_type=DocumentType.COVER_LETTER,
        )
        self.assertEqual(document.name, "Cover_Letter.pdf")

    def test_invalid_upload_type_is_rejected(self):
        self.client.login(username="aminul", password="StrongPass12345")
        uploaded = SimpleUploadedFile(
            "cv.exe",
            b"bad",
            content_type="application/octet-stream",
        )
        response = self.client.post(
            self.detail_url,
            {
                "action": "upload_cv",
                "upload_cv-uploaded_file": uploaded,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            ApplicationDocument.objects.filter(application=self.application).exists()
        )

    def test_selecting_documents_clears_document_pack_missing_display(self):
        cv_document = ApplicationDocument.objects.create(
            application=self.application,
            document_type=DocumentType.CV,
            name="Generated CV draft",
            source=DocumentSource.JOB_ANALYZER,
        )
        cover_letter_document = ApplicationDocument.objects.create(
            application=self.application,
            document_type=DocumentType.COVER_LETTER,
            name="Generated cover letter draft",
            source=DocumentSource.JOB_ANALYZER,
        )
        self.client.login(username="aminul", password="StrongPass12345")
        before = self.client.get(self.detail_url)
        self.assertContains(before, "Selection still needed")
        response = self.client.post(
            self.detail_url,
            {
                "action": "select_documents",
                "selected_cv_document": cv_document.pk,
                "selected_cover_letter_document": cover_letter_document.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        after = self.client.get(self.detail_url)
        self.assertNotContains(after, "Selection still needed")
        self.assertContains(after, cv_document.name)
        self.assertContains(after, cover_letter_document.name)
        readiness = build_application_evidence_readiness(self.application)
        self.assertIn(ITEM_CV_VERSION, readiness.ready_items)
        self.assertIn(ITEM_COVER_LETTER_VERSION, readiness.ready_items)

    def test_generated_document_source_label_is_generated_document(self):
        document = ApplicationDocument.objects.create(
            application=self.application,
            document_type=DocumentType.CV,
            name="Generated CV draft",
            source=DocumentSource.JOB_ANALYZER,
        )
        self.assertEqual(document.evidence_source_label, "Generated document")

    def test_external_reference_source_label(self):
        document = ApplicationDocument.objects.create(
            application=self.application,
            document_type=DocumentType.CV,
            name="External CV",
            source=DocumentSource.EXTERNAL_REFERENCE,
        )
        self.assertEqual(document.evidence_source_label, "External reference")

    def test_manual_upload_source_label(self):
        document = ApplicationDocument.objects.create(
            application=self.application,
            document_type=DocumentType.CV,
            name="Uploaded CV.pdf",
            source=DocumentSource.USER_UPLOAD,
        )
        self.assertEqual(document.evidence_source_label, "Manual upload")


class JobApplicationViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def create_application(self, **overrides):
        defaults = {
            "user": self.user,
            "company_name": "Example Ltd",
            "job_title": "Junior Data Analyst",
            "date_applied": date(2026, 5, 9),
        }
        defaults.update(overrides)
        return JobApplication.objects.create(**defaults)

    def test_application_list_requires_login(self):
        response = self.client.get(reverse("applications:application_list"))
        self.assertEqual(response.status_code, 302)

    def test_application_list_loads_for_logged_in_user(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("applications:application_list"))
        self.assertEqual(response.status_code, 200)

    def test_user_can_create_application(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.post(
            reverse("applications:application_create"),
            {
                "company_name": "Example Ltd",
                "job_title": "Junior Data Analyst",
                "job_url": "https://example.com/job",
                "location": "London",
                "work_type": WorkType.HYBRID,
                "salary_range": "GBP 30,000 - GBP 35,000",
                "source": ApplicationSource.LINKEDIN,
                "role_fit": RoleFit.STRONG,
                "date_applied": "2026-05-09",
                "status": ApplicationStatus.SUBMITTED,
                "response_date": "",
                "cv_version": "DA_CV_v1",
                "cover_letter_version": "Tailored_CL_v1",
                "contact_name": "",
                "contact_email": "",
                "notes": "Good fit.",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(JobApplication.objects.filter(company_name="Example Ltd").exists())

    def test_application_detail_includes_followup_email_draft_context(self):
        application = self.create_application(contact_email="hiring@example.com")
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("followup_email_draft", response.context)
        self.assertEqual(
            response.context["followup_email_draft"].recipient_email,
            "hiring@example.com",
        )

    def test_application_detail_includes_evidence_readiness_context(self):
        application = self.create_application(cv_version="DA_CV_v1")
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("evidence_readiness", response.context)
        self.assertEqual(
            response.context["evidence_readiness"],
            build_application_evidence_readiness(application),
        )

    def test_application_detail_includes_smart_review_context(self):
        application = self.create_application(
            job_title="Junior Finance Data Analyst",
            location="Hybrid London",
            work_type=WorkType.HYBRID,
            role_fit=RoleFit.STRONG,
            required_skills="Python SQL Excel reporting dashboards finance",
        )
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("smart_review", response.context)
        self.assertEqual(
            response.context["smart_review"],
            build_smart_review(application),
        )
        self.assertIsInstance(response.context["smart_review"].job_fit_score, int)
        self.assertIn("badge_class", response.context)
        self.assertIn("followup_email_draft", response.context)
        self.assertIn("evidence_readiness", response.context)

    def test_application_detail_displays_fit_review_section(self):
        application = self.create_application(
            job_title="Junior Finance Data Analyst",
            location="Hybrid London",
            work_type=WorkType.HYBRID,
            role_fit=RoleFit.STRONG,
            required_skills="Python SQL Excel reporting dashboards finance",
            cv_version="Finance_DA_CV_v1",
        )
        self.client.login(username="aminul", password="StrongPass12345")
        smart_review = build_smart_review(application)
        smart_review_url = reverse(
            "job_intelligence:application_smart_review",
            kwargs={"pk": application.pk},
        )

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertContains(response, "Fit Review")
        self.assertContains(response, f"{smart_review.job_fit_score}/100")
        self.assertContains(response, smart_review.recommended_cv)
        self.assertContains(response, f"{smart_review.readiness_score}%")
        self.assertContains(response, "Full Smart Review")
        self.assertContains(response, smart_review_url)

    def test_application_detail_displays_evidence_readiness(self):
        application = self.create_application(
            cv_version="DA_CV_v2",
            cover_letter_version="Tailored_CL_v2",
            job_url="https://example.com/jobs/123",
            required_skills="Python, SQL, Excel",
            job_description=(
                "Junior data analyst role focused on reporting, dashboards, "
                "and stakeholder support."
            ),
            contact_email="hiring@example.com",
            company_researched=True,
        )
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        readiness = build_application_evidence_readiness(application)

        self.assertContains(response, "Evidence Readiness")
        self.assertContains(response, readiness.readiness_label)
        self.assertContains(response, ITEM_CV_VERSION)
        self.assertContains(response, ITEM_PORTFOLIO_PROJECT)
        self.assertContains(response, readiness.recommended_next_improvement)
        self.assertContains(response, "CareerFunnel Tracker does not send email.")
        self.assertContains(response, "Manual follow-up workflow")

    def test_application_detail_displays_complete_evidence_readiness_state(self):
        application = self.create_application(
            cv_version="DA_CV_v2",
            cover_letter_version="Tailored_CL_v2",
            job_url="https://example.com/jobs/123",
            required_skills="Python, SQL, Excel, Tableau",
            job_description=(
                "Junior data analyst role focused on reporting, dashboards, "
                "and stakeholder support."
            ),
            contact_email="hiring@example.com",
            company_researched=True,
            portfolio_project_included=True,
            follow_up_date=date(2026, 5, 20),
            follow_up_status=FollowUpStatus.DUE,
        )
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertContains(response, READINESS_LABEL_STRONG)
        self.assertContains(response, "All evidence items complete")

    def test_application_detail_displays_followup_email_draft_content(self):
        application = self.create_application(
            contact_name="Taylor Morgan",
            contact_email="hiring@example.com",
        )
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertContains(response, "Follow-up Email Draft")
        self.assertContains(response, "hiring@example.com")
        self.assertContains(
            response,
            "Follow-up on Junior Data Analyst application at Example Ltd",
        )
        self.assertContains(response, "Dear Taylor Morgan,")
        self.assertContains(response, "I applied for the Junior Data Analyst")
        self.assertContains(response, "Manual draft only.")

    def test_application_detail_makes_draft_manual_only(self):
        application = self.create_application()
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertContains(response, "Manual Only")
        self.assertContains(response, "CareerFunnel Tracker does not send email.")
        self.assertContains(response, "Use this manual workflow")
        self.assertContains(response, "manual copy only")
        self.assertNotContains(response, "Send Email")

    def test_application_detail_displays_manual_followup_workflow_steps(self):
        application = self.create_application()
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertContains(response, "Manual follow-up workflow")
        self.assertContains(response, "Review the draft below.")
        self.assertContains(
            response,
            "Copy and send it manually outside CareerFunnel Tracker.",
        )
        self.assertContains(response, "Click Mark Follow-up Sent after sending.")

    def test_application_detail_displays_mark_followup_sent_button(self):
        application = self.create_application(follow_up_status=FollowUpStatus.DUE)
        self.client.login(username="aminul", password="StrongPass12345")
        mark_followup_url = reverse(
            "applications:application_mark_followup_sent",
            kwargs={"pk": application.pk},
        )

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertContains(response, "Mark Follow-up Sent")
        self.assertContains(response, f'action="{mark_followup_url}"')
        self.assertContains(
            response,
            "Use this only after you have sent the email manually outside CareerFunnel Tracker.",
        )

    def test_application_detail_displays_completed_state_for_sent_followup(self):
        last_contacted_date = date(2026, 5, 12)
        application = self.create_application(
            follow_up_status=FollowUpStatus.SENT,
            last_contacted_date=last_contacted_date,
        )
        self.client.login(username="aminul", password="StrongPass12345")
        mark_followup_url = reverse(
            "applications:application_mark_followup_sent",
            kwargs={"pk": application.pk},
        )

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertContains(response, "Follow-up already marked as sent.")
        self.assertContains(
            response,
            f"Last contacted: {date_format(last_contacted_date, 'DATE_FORMAT')}",
        )
        self.assertNotContains(response, f'action="{mark_followup_url}"')
        self.assertContains(response, "CareerFunnel Tracker does not send email.")

    def test_application_detail_shows_recruiter_email_action_summary_needs_reply(self):
        application = self.create_application()
        RecruiterEmail.objects.create(
            application=application,
            subject="Interview availability",
            body="We would like to invite you to interview.",
            date_received=timezone.now(),
            email_type=EmailType.INTERVIEW_INVITE,
            matched_signals=json.dumps(["interview", "interview availability"]),
            reply_status=ReplyStatus.DRAFTED,
            requires_reply=True,
        )
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Recruiter Email Actions")
        self.assertContains(response, "Needs reply")
        self.assertContains(response, "Action needed")
        self.assertContains(response, "Reply status")
        self.assertContains(response, "Interview/screening signal")

    def test_application_detail_shows_recruiter_email_action_due_and_suggested_status(self):
        application = self.create_application()
        action_due_at = timezone.now() + timedelta(hours=24)
        RecruiterEmail.objects.create(
            application=application,
            subject="Screening call",
            body="We would like to arrange a screening call.",
            date_received=timezone.now(),
            email_type=EmailType.SCREENING_INVITE,
            matched_signals=json.dumps(["screening call"]),
            reply_status=ReplyStatus.NEEDS_REVIEW,
            requires_reply=True,
            action_due_at=action_due_at,
            suggested_application_status="screening",
        )
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Action due")
        self.assertContains(
            response,
            date_format(timezone.localtime(action_due_at), "DATETIME_FORMAT"),
        )
        self.assertContains(response, "Suggested status")
        self.assertContains(response, "screening (suggestion only)")

    def test_application_detail_recruiter_emails_remain_manual_and_rule_based(self):
        application = self.create_application()
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Paste recruiter emails manually")
        self.assertContains(response, "rule-based only")
        self.assertContains(response, "Suggested statuses are suggestions only")
        self.assertContains(
            response,
            "does not send email or update application status automatically",
        )

    def test_application_detail_still_shows_import_recruiter_email_link(self):
        application = self.create_application()
        import_url = reverse(
            "recruiter_emails:import",
            kwargs={"application_id": application.pk},
        )
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Import Recruiter Email")
        self.assertContains(response, f'href="{import_url}"')

    def test_application_detail_shows_recruiter_communication_context_when_emails_exist(
        self,
    ):
        application = self.create_application()
        RecruiterEmail.objects.create(
            application=application,
            subject="Recruiter follow-up",
            body="Following up on your application.",
            date_received=timezone.now(),
            email_type=EmailType.INTEREST,
            reply_status=ReplyStatus.NEEDS_REVIEW,
            requires_reply=True,
        )
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Recruiter Communication Context")
        self.assertContains(response, "Latest recruiter email")
        self.assertContains(response, "Recruiter follow-up")
        self.assertContains(response, "Requires reply")
        self.assertContains(response, "Manual follow-up guidance")

    def test_application_detail_communication_context_uses_latest_recruiter_email(
        self,
    ):
        application = self.create_application()
        older_received = timezone.now() - timedelta(days=3)
        latest_received = timezone.now() - timedelta(hours=2)
        RecruiterEmail.objects.create(
            application=application,
            subject="Older acknowledgement",
            body="Thank you for applying.",
            date_received=older_received,
            email_type=EmailType.ACKNOWLEDGEMENT,
            reply_status=ReplyStatus.NOT_REQUIRED,
            requires_reply=False,
        )
        RecruiterEmail.objects.create(
            application=application,
            subject="Latest interview invite",
            body="We would like to invite you to interview.",
            date_received=latest_received,
            email_type=EmailType.INTERVIEW_INVITE,
            reply_status=ReplyStatus.DRAFTED,
            requires_reply=True,
            suggested_application_status="interview",
        )
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Latest recruiter email")
        self.assertContains(response, "Latest interview invite")
        self.assertNotContains(
            response,
            '<span>Latest recruiter email</span><strong>Older acknowledgement</strong>',
        )
        self.assertContains(
            response,
            date_format(timezone.localtime(latest_received), "DATETIME_FORMAT"),
        )
        self.assertContains(response, "Draft ready")
        self.assertContains(response, "interview (suggestion only)")

    def test_application_detail_communication_context_manual_followup_guidance(self):
        application = self.create_application()
        RecruiterEmail.objects.create(
            application=application,
            subject="Availability request",
            body="Please share your availability.",
            date_received=timezone.now(),
            email_type=EmailType.AVAILABILITY_REQUEST,
            reply_status=ReplyStatus.DRAFTED,
            requires_reply=True,
        )
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Review recruiter history before sending a manual follow-up",
        )
        self.assertContains(
            response,
            "Review imported recruiter emails and reply status before sending a manual follow-up",
        )
        self.assertContains(
            response,
            "Update application status and follow-up fields yourself",
        )

    def test_application_detail_communication_context_advisory_wording_only(self):
        application = self.create_application()
        RecruiterEmail.objects.create(
            application=application,
            subject="Screening invite",
            body="We would like to arrange a screening call.",
            date_received=timezone.now(),
            email_type=EmailType.SCREENING_INVITE,
            suggested_application_status="screening",
            reply_status=ReplyStatus.DRAFTED,
            requires_reply=True,
        )
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Suggested statuses are advisory only")
        self.assertContains(response, "suggestion only")
        self.assertContains(
            response,
            "does not send email or update statuses automatically",
        )

    def test_application_detail_hides_recruiter_communication_context_without_emails(
        self,
    ):
        application = self.create_application()
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Recruiter Communication Context")
        self.assertNotContains(response, "Latest recruiter email")
        self.assertNotContains(response, "Manual follow-up guidance")

    def test_application_detail_shows_interview_prep_prompt_for_interview_signal(self):
        application = self.create_application()
        RecruiterEmail.objects.create(
            application=application,
            subject="Interview invite",
            body="We would like to invite you to interview.",
            date_received=timezone.now(),
            email_type=EmailType.INTERVIEW_INVITE,
            matched_signals=json.dumps(["interview", "interview availability"]),
            reply_status=ReplyStatus.DRAFTED,
            requires_reply=True,
        )
        self.client.login(username="aminul", password="StrongPass12345")
        interview_create_url = (
            reverse("interviews:interview_create") + f"?application={application.pk}"
        )

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Interview Prep Recommended")
        self.assertContains(
            response,
            "Recruiter email history includes interview/screening signals",
        )
        self.assertContains(response, "recruiter-interview-prep-prompt")
        self.assertContains(response, interview_create_url)

    def test_application_detail_shows_interview_prep_prompt_for_screening_signal(self):
        application = self.create_application()
        RecruiterEmail.objects.create(
            application=application,
            subject="Screening call",
            body="We would like to arrange a screening call.",
            date_received=timezone.now(),
            email_type=EmailType.SCREENING_INVITE,
            matched_signals=json.dumps(["screening call"]),
            reply_status=ReplyStatus.NEEDS_REVIEW,
            requires_reply=True,
        )
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Interview Prep Recommended")
        self.assertContains(
            response,
            "Create interview prep manually after reviewing the recruiter email",
        )

    def test_application_detail_interview_prep_prompt_includes_create_link(self):
        application = self.create_application()
        RecruiterEmail.objects.create(
            application=application,
            subject="Interview availability",
            body="Please share interview availability.",
            date_received=timezone.now(),
            matched_signals=json.dumps(["interview availability"]),
            reply_status=ReplyStatus.DRAFTED,
            requires_reply=True,
        )
        self.client.login(username="aminul", password="StrongPass12345")
        interview_create_url = (
            reverse("interviews:interview_create") + f"?application={application.pk}"
        )

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            (
                '<div class="diagnosis-box recruiter-interview-prep-prompt">'
                '<h3>Interview Prep Recommended</h3>'
            ),
        )
        self.assertContains(
            response,
            (
                'recruiter-interview-prep-prompt">'
                '<h3>Interview Prep Recommended</h3>'
                '<p class="muted-text">Recruiter email history includes '
                'interview/screening signals.'
                ' Create interview prep manually after reviewing the recruiter email.'
            ),
        )
        self.assertContains(response, interview_create_url)

    def test_application_detail_hides_interview_prep_prompt_without_relevant_signals(
        self,
    ):
        application = self.create_application()
        RecruiterEmail.objects.create(
            application=application,
            subject="Application acknowledgement",
            body="Thank you for applying.",
            date_received=timezone.now(),
            email_type=EmailType.ACKNOWLEDGEMENT,
            matched_signals=json.dumps(["thank you for applying"]),
            reply_status=ReplyStatus.NOT_REQUIRED,
            requires_reply=False,
        )
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Recruiter Email Actions")
        self.assertNotContains(response, "Interview Prep Recommended")
        self.assertNotContains(response, "recruiter-interview-prep-prompt")

    def test_application_detail_interview_prep_prompt_manual_advisory_wording(self):
        application = self.create_application()
        RecruiterEmail.objects.create(
            application=application,
            subject="Interview invite",
            body="We would like to invite you to interview.",
            date_received=timezone.now(),
            matched_signals=json.dumps(["interview"]),
            reply_status=ReplyStatus.DRAFTED,
            requires_reply=True,
        )
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This is a manual prompt only")
        self.assertContains(response, "Review the recruiter email first")
        self.assertContains(
            response,
            "Create interview prep only after you decide it is needed",
        )
        self.assertContains(
            response,
            "does not create interview prep automatically",
        )
        self.assertContains(
            response,
            "does not create interview prep, send emails, or update statuses automatically",
        )

    def test_mark_followup_sent_requires_login(self):
        application = self.create_application()

        response = self.client.post(
            reverse(
                "applications:application_mark_followup_sent",
                kwargs={"pk": application.pk},
            ),
        )

        self.assertEqual(response.status_code, 302)

    def test_mark_followup_sent_rejects_get(self):
        application = self.create_application()
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse(
                "applications:application_mark_followup_sent",
                kwargs={"pk": application.pk},
            ),
        )

        self.assertEqual(response.status_code, 405)

    @patch("django.core.mail.EmailMessage.send")
    @patch("django.core.mail.send_mail")
    def test_mark_followup_sent_post_updates_application_without_email(
        self,
        send_mail,
        email_message_send,
    ):
        application = self.create_application(
            follow_up_status=FollowUpStatus.DUE,
            last_contacted_date=None,
        )
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.post(
            reverse(
                "applications:application_mark_followup_sent",
                kwargs={"pk": application.pk},
            ),
            follow=True,
        )
        application.refresh_from_db()

        self.assertRedirects(response, application.get_absolute_url())
        self.assertEqual(application.follow_up_status, FollowUpStatus.SENT)
        self.assertEqual(application.last_contacted_date, timezone.localdate())
        self.assertContains(response, "Follow-up marked as sent.")
        send_mail.assert_not_called()
        email_message_send.assert_not_called()
        self.assertEqual(mail.outbox, [])


class ApplicationWorkflowCrossLinkTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="crosslink", password="StrongPass12345")
        self.application = JobApplication.objects.create(
            user=self.user,
            company_name="Crosslink Co",
            job_title="Data Analyst",
            date_applied=date(2026, 5, 1),
            status=ApplicationStatus.SUBMITTED,
        )
        self.client.login(username="crosslink", password="StrongPass12345")

    def test_application_detail_interview_prep_link_includes_application_query(self):
        interview_create_url = (
            reverse("interviews:interview_create") + f"?application={self.application.pk}"
        )
        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": self.application.pk}),
        )

        self.assertContains(response, interview_create_url)
        self.assertGreaterEqual(
            response.content.decode().count(interview_create_url),
            2,
        )

    def test_application_detail_workflow_map_is_claim_safe(self):
        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": self.application.pk}),
        )

        self.assertContains(response, "Manual workflow map")
        self.assertContains(response, "Import recruiter email manually")
        self.assertContains(response, "Open AI Pack for advisory prep")
        self.assertContains(response, "Manually update status or send replies outside CareerFunnel")
        self.assertContains(response, "No Gmail, Calendar, OAuth")

    def test_application_detail_interview_prep_prompt_still_manual(self):
        RecruiterEmail.objects.create(
            application=self.application,
            subject="Interview invite",
            body="We would like to invite you to interview.",
            date_received=timezone.now(),
            matched_signals=json.dumps(["interview"]),
            reply_status=ReplyStatus.DRAFTED,
            requires_reply=True,
        )
        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": self.application.pk}),
        )

        self.assertContains(response, "This is a manual prompt only")
        self.assertContains(response, "does not create interview prep automatically")

    def test_application_detail_does_not_create_interview_prep_on_get(self):
        from apps.interviews.models import InterviewPrep

        RecruiterEmail.objects.create(
            application=self.application,
            subject="Interview invite",
            body="We would like to invite you to interview.",
            date_received=timezone.now(),
            matched_signals=json.dumps(["interview"]),
        )
        count_before = InterviewPrep.objects.count()
        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": self.application.pk}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(InterviewPrep.objects.count(), count_before)


class ApplicationServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def test_response_rate_is_zero_without_applications(self):
        self.assertEqual(calculate_response_rate(self.user), 0.0)

    def test_response_rate_calculates_correctly(self):
        JobApplication.objects.create(
            user=self.user,
            company_name="Company A",
            job_title="Data Analyst",
            date_applied=date(2026, 5, 1),
            status=ApplicationStatus.SUBMITTED,
        )
        JobApplication.objects.create(
            user=self.user,
            company_name="Company B",
            job_title="BI Analyst",
            date_applied=date(2026, 5, 2),
            status=ApplicationStatus.ACKNOWLEDGED,
        )
        self.assertEqual(calculate_response_rate(self.user), 50.0)


class ApplicationEvidenceReadinessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def _base_application_kwargs(self):
        return {
            "user": self.user,
            "company_name": "Example Ltd",
            "job_title": "Junior Data Analyst",
            "date_applied": date(2026, 5, 9),
        }

    def _well_prepared_kwargs(self):
        return {
            **self._base_application_kwargs(),
            "cv_version": "DA_CV_v2",
            "cover_letter_version": "Tailored_CL_v2",
            "job_url": "https://example.com/jobs/123",
            "required_skills": "Python, SQL, Excel, Tableau",
            "job_description": (
                "Junior data analyst role focused on reporting, dashboards, "
                "and stakeholder support."
            ),
            "contact_email": "hiring@example.com",
            "company_researched": True,
            "portfolio_project_included": True,
            "follow_up_date": date(2026, 5, 20),
            "follow_up_status": FollowUpStatus.DUE,
        }

    def test_well_prepared_application_receives_strong_evidence_label(self):
        application = JobApplication.objects.create(**self._well_prepared_kwargs())

        readiness = build_application_evidence_readiness(application)

        self.assertEqual(readiness.readiness_label, READINESS_LABEL_STRONG)
        self.assertEqual(readiness.missing_items, ())
        self.assertEqual(
            readiness.recommended_next_improvement,
            "Evidence is complete; keep records updated as the application progresses.",
        )

    def test_sparse_application_receives_missing_key_evidence_label(self):
        application = JobApplication.objects.create(**self._base_application_kwargs())

        readiness = build_application_evidence_readiness(application)

        self.assertEqual(readiness.readiness_label, READINESS_LABEL_MISSING_KEY)

    def test_missing_items_are_detected_correctly(self):
        kwargs = self._well_prepared_kwargs()
        kwargs.update({"cv_version": "", "contact_email": "", "follow_up_date": None})
        application = JobApplication.objects.create(**kwargs)

        readiness = build_application_evidence_readiness(application)

        self.assertIn(ITEM_CV_VERSION, readiness.missing_items)
        self.assertIn(ITEM_CONTACT_EMAIL, readiness.missing_items)
        self.assertIn(ITEM_FOLLOW_UP_DATE, readiness.missing_items)
        self.assertNotIn(ITEM_JOB_URL, readiness.missing_items)

    def test_ready_items_are_detected_correctly(self):
        kwargs = self._well_prepared_kwargs()
        kwargs.update({"cv_version": "", "follow_up_status": FollowUpStatus.NOT_SET})
        application = JobApplication.objects.create(**kwargs)

        readiness = build_application_evidence_readiness(application)

        self.assertIn(ITEM_JOB_URL, readiness.ready_items)
        self.assertIn(ITEM_JOB_DESCRIPTION, readiness.ready_items)
        self.assertIn(ITEM_COMPANY_RESEARCHED, readiness.ready_items)
        self.assertNotIn(ITEM_CV_VERSION, readiness.ready_items)
        self.assertNotIn(ITEM_FOLLOW_UP_STATUS, readiness.ready_items)

    def test_recommended_next_improvement_is_deterministic_and_practical(self):
        kwargs = self._well_prepared_kwargs()
        kwargs["cv_version"] = ""
        application = JobApplication.objects.create(**kwargs)
        readiness = build_application_evidence_readiness(application)
        self.assertEqual(
            readiness.recommended_next_improvement,
            "Save the CV version used for this application.",
        )

        application.cv_version = "DA_CV_v2"
        application.cover_letter_version = ""
        application.save(update_fields=["cv_version", "cover_letter_version"])
        readiness = build_application_evidence_readiness(application)
        self.assertEqual(
            readiness.recommended_next_improvement,
            "Save the cover letter version used for this application.",
        )

    def test_partially_prepared_application_receives_needs_improvement_label(self):
        application = JobApplication.objects.create(
            **self._base_application_kwargs(),
            cv_version="DA_CV_v2",
            cover_letter_version="Tailored_CL_v2",
            job_url="https://example.com/jobs/123",
            required_skills="Python, SQL, Excel",
            job_description=(
                "Junior data analyst role focused on reporting, dashboards, "
                "and stakeholder support."
            ),
            contact_email="hiring@example.com",
            company_researched=True,
        )

        readiness = build_application_evidence_readiness(application)

        self.assertEqual(readiness.readiness_label, READINESS_LABEL_NEEDS_IMPROVEMENT)
        self.assertIn(ITEM_PORTFOLIO_PROJECT, readiness.missing_items)
        self.assertIn(ITEM_FOLLOW_UP_DATE, readiness.missing_items)
        self.assertIn(ITEM_FOLLOW_UP_STATUS, readiness.missing_items)
        self.assertEqual(
            readiness.recommended_next_improvement,
            "Note whether a portfolio project was included or referenced.",
        )


class SaveQualityWarningsServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def _complete_application_kwargs(self):
        return {
            "user": self.user,
            "company_name": "Example Ltd",
            "job_title": "Junior Data Analyst",
            "date_applied": date(2026, 5, 9),
            "source": ApplicationSource.LINKEDIN,
            "cv_version": "DA_CV_v1",
            "location": "Hybrid London",
            "required_skills": "Python SQL Excel Power BI dashboards",
            "job_description": (
                "Junior data analyst role requiring Python, SQL, and Excel for KPI "
                "reporting and stakeholder dashboards."
            ),
            "role_fit": RoleFit.STRONG,
            "follow_up_date": date.today(),
        }

    def _warning_field_names(self, application):
        return {warning.field_name for warning in build_save_quality_warnings(application)}

    def test_complete_application_returns_empty_warning_list(self):
        application = JobApplication.objects.create(**self._complete_application_kwargs())

        self.assertEqual(build_save_quality_warnings(application), [])

    def test_source_other_creates_critical_source_warning(self):
        kwargs = self._complete_application_kwargs()
        kwargs["source"] = ApplicationSource.OTHER
        application = JobApplication.objects.create(**kwargs)

        warnings = build_save_quality_warnings(application)
        source_warnings = [warning for warning in warnings if warning.field_name == "source"]

        self.assertEqual(len(source_warnings), 1)
        self.assertEqual(source_warnings[0].severity, "critical")
        self.assertEqual(source_warnings[0].field_name, "source")

    def test_source_linkedin_creates_no_source_warning(self):
        application = JobApplication.objects.create(**self._complete_application_kwargs())

        self.assertNotIn("source", self._warning_field_names(application))

    def test_blank_cv_version_creates_critical_cv_version_warning(self):
        kwargs = self._complete_application_kwargs()
        kwargs["cv_version"] = ""
        application = JobApplication.objects.create(**kwargs)

        warnings = build_save_quality_warnings(application)
        cv_warnings = [warning for warning in warnings if warning.field_name == "cv_version"]

        self.assertEqual(len(cv_warnings), 1)
        self.assertEqual(cv_warnings[0].severity, "critical")
        self.assertEqual(cv_warnings[0].field_name, "cv_version")

    def test_filled_cv_version_creates_no_cv_version_warning(self):
        application = JobApplication.objects.create(**self._complete_application_kwargs())

        self.assertNotIn("cv_version", self._warning_field_names(application))

    def test_blank_location_creates_important_location_warning(self):
        kwargs = self._complete_application_kwargs()
        kwargs["location"] = ""
        application = JobApplication.objects.create(**kwargs)

        warnings = build_save_quality_warnings(application)
        location_warnings = [warning for warning in warnings if warning.field_name == "location"]

        self.assertEqual(len(location_warnings), 1)
        self.assertEqual(location_warnings[0].severity, "important")
        self.assertEqual(location_warnings[0].field_name, "location")

    def test_required_skills_shorter_than_10_chars_creates_important_warning(self):
        kwargs = self._complete_application_kwargs()
        kwargs["required_skills"] = "Python"
        application = JobApplication.objects.create(**kwargs)

        self.assertIn("required_skills", self._warning_field_names(application))

    def test_required_skills_exactly_10_chars_creates_no_warning(self):
        kwargs = self._complete_application_kwargs()
        kwargs["required_skills"] = "1234567890"
        application = JobApplication.objects.create(**kwargs)

        self.assertNotIn("required_skills", self._warning_field_names(application))

    def test_job_description_shorter_than_40_chars_creates_important_warning(self):
        kwargs = self._complete_application_kwargs()
        kwargs["job_description"] = "Short junior data analyst role."
        application = JobApplication.objects.create(**kwargs)

        self.assertIn("job_description", self._warning_field_names(application))

    def test_job_description_exactly_40_chars_creates_no_warning(self):
        kwargs = self._complete_application_kwargs()
        kwargs["job_description"] = "a" * 40
        application = JobApplication.objects.create(**kwargs)

        self.assertNotIn("job_description", self._warning_field_names(application))

    def test_multiple_gaps_return_multiple_warnings(self):
        kwargs = self._complete_application_kwargs()
        kwargs.update(
            {
                "source": ApplicationSource.OTHER,
                "cv_version": "",
                "location": "",
                "required_skills": "short",
                "job_description": "too short",
            },
        )
        application = JobApplication.objects.create(**kwargs)

        warnings = build_save_quality_warnings(application)

        self.assertEqual(len(warnings), 5)
        self.assertEqual(
            self._warning_field_names(application),
            {"source", "cv_version", "location", "required_skills", "job_description"},
        )

    def test_severity_values_are_only_critical_or_important(self):
        kwargs = self._complete_application_kwargs()
        kwargs.update(
            {
                "source": ApplicationSource.OTHER,
                "cv_version": "",
                "location": "",
            },
        )
        application = JobApplication.objects.create(**kwargs)

        severities = {warning.severity for warning in build_save_quality_warnings(application)}

        self.assertTrue(severities.issubset({"critical", "important"}))
        self.assertIn("critical", severities)
        self.assertIn("important", severities)


class ApplicationSaveQualityWarningViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="warnings", password="StrongPass12345")
        self.client.login(username="warnings", password="StrongPass12345")
        self.create_url = reverse("applications:application_create")

    def _analytics_ready_post_data(self, **overrides):
        data = {
            "company_name": "Example Ltd",
            "job_title": "Junior Data Analyst",
            "job_url": "",
            "location": "Hybrid London",
            "work_type": WorkType.HYBRID,
            "salary_range": "",
            "source": ApplicationSource.LINKEDIN,
            "role_fit": RoleFit.STRONG,
            "experience_level": "",
            "required_skills": "Python SQL Excel Power BI dashboards",
            "job_description": (
                "Junior data analyst role requiring Python, SQL, and Excel for KPI "
                "reporting and stakeholder dashboards."
            ),
            "date_applied": "2026-05-09",
            "status": ApplicationStatus.SUBMITTED,
            "response_date": "",
            "cv_version": "DA_CV_v1",
            "cover_letter_version": "",
            "contact_name": "",
            "contact_email": "",
            "notes": "",
        }
        data.update(overrides)
        return data

    def test_create_with_source_other_shows_source_roi_warning(self):
        response = self.client.post(
            self.create_url,
            self._analytics_ready_post_data(source=ApplicationSource.OTHER),
            follow=True,
        )

        self.assertContains(response, "Source ROI cannot attribute")
        self.assertTrue(JobApplication.objects.filter(company_name="Example Ltd").exists())

    def test_create_with_blank_cv_version_shows_cv_version_performance_warning(self):
        response = self.client.post(
            self.create_url,
            self._analytics_ready_post_data(cv_version=""),
            follow=True,
        )

        self.assertContains(response, "CV Version Performance analytics")
        self.assertTrue(JobApplication.objects.filter(company_name="Example Ltd").exists())

    def test_create_with_complete_analytics_fields_shows_success_without_source_warning(
        self,
    ):
        response = self.client.post(
            self.create_url,
            self._analytics_ready_post_data(),
            follow=True,
        )

        self.assertContains(response, "Application added successfully.")
        self.assertNotContains(response, "Source ROI cannot attribute")

    def test_create_redirect_target_is_application_detail(self):
        response = self.client.post(self.create_url, self._analytics_ready_post_data())

        application = JobApplication.objects.get(company_name="Example Ltd")
        self.assertRedirects(response, application.get_absolute_url())

    def test_update_with_source_other_shows_source_roi_warning(self):
        application = JobApplication.objects.create(
            user=self.user,
            company_name="Example Ltd",
            job_title="Junior Data Analyst",
            date_applied=date(2026, 5, 9),
            source=ApplicationSource.LINKEDIN,
            cv_version="DA_CV_v1",
            location="Hybrid London",
            required_skills="Python SQL Excel Power BI dashboards",
            job_description=(
                "Junior data analyst role requiring Python, SQL, and Excel for KPI "
                "reporting and stakeholder dashboards."
            ),
        )
        update_url = reverse("applications:application_update", kwargs={"pk": application.pk})

        response = self.client.post(
            update_url,
            self._analytics_ready_post_data(source=ApplicationSource.OTHER),
            follow=True,
        )

        self.assertContains(response, "Source ROI cannot attribute")
        application.refresh_from_db()
        self.assertEqual(application.source, ApplicationSource.OTHER)

    def test_update_with_blank_cv_version_shows_cv_version_performance_warning(self):
        application = JobApplication.objects.create(
            user=self.user,
            company_name="Example Ltd",
            job_title="Junior Data Analyst",
            date_applied=date(2026, 5, 9),
            source=ApplicationSource.LINKEDIN,
            cv_version="DA_CV_v1",
            location="Hybrid London",
            required_skills="Python SQL Excel Power BI dashboards",
            job_description=(
                "Junior data analyst role requiring Python, SQL, and Excel for KPI "
                "reporting and stakeholder dashboards."
            ),
        )
        update_url = reverse("applications:application_update", kwargs={"pk": application.pk})

        response = self.client.post(
            update_url,
            self._analytics_ready_post_data(cv_version=""),
            follow=True,
        )

        self.assertContains(response, "CV Version Performance analytics")
        application.refresh_from_db()
        self.assertEqual(application.cv_version, "")

    def test_update_with_complete_analytics_fields_shows_success_without_source_warning(
        self,
    ):
        application = JobApplication.objects.create(
            user=self.user,
            company_name="Example Ltd",
            job_title="Junior Data Analyst",
            date_applied=date(2026, 5, 9),
            source=ApplicationSource.OTHER,
            cv_version="",
        )
        update_url = reverse("applications:application_update", kwargs={"pk": application.pk})

        response = self.client.post(
            update_url,
            self._analytics_ready_post_data(),
            follow=True,
        )

        self.assertContains(response, "Application updated successfully.")
        self.assertNotContains(response, "Source ROI cannot attribute")

    def test_update_redirect_target_remains_application_detail(self):
        application = JobApplication.objects.create(
            user=self.user,
            company_name="Example Ltd",
            job_title="Junior Data Analyst",
            date_applied=date(2026, 5, 9),
        )
        update_url = reverse("applications:application_update", kwargs={"pk": application.pk})

        response = self.client.post(update_url, self._analytics_ready_post_data())

        self.assertRedirects(response, application.get_absolute_url())


class ApplicationCreatePrefillTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="prefill", password="StrongPass12345")
        self.client.login(username="prefill", password="StrongPass12345")
        self.create_url = reverse("applications:application_create")

    def _get_create(self, query_string=""):
        url = self.create_url if not query_string else f"{self.create_url}?{query_string}"
        return self.client.get(url)

    def test_application_create_get_without_params_renders_normally(self):
        response = self._get_create()
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertEqual(form.initial.get("company_name"), None)
        self.assertEqual(form.initial.get("pipeline_stage"), None)

    def test_company_name_get_param_appears_in_form_initial(self):
        response = self._get_create("company_name=FinSight")
        self.assertEqual(response.context["form"].initial.get("company_name"), "FinSight")

    def test_job_title_get_param_appears_in_form_initial(self):
        response = self._get_create("job_title=Junior+Data+Analyst")
        self.assertEqual(
            response.context["form"].initial.get("job_title"),
            "Junior Data Analyst",
        )

    def test_location_get_param_appears_in_form_initial(self):
        response = self._get_create("location=Hybrid+London")
        self.assertEqual(response.context["form"].initial.get("location"), "Hybrid London")

    def test_fit_score_at_least_60_maps_to_role_fit_strong(self):
        response = self._get_create("fit_score=60")
        self.assertEqual(response.context["form"].initial.get("role_fit"), RoleFit.STRONG)

    def test_fit_score_40_to_59_maps_to_role_fit_medium(self):
        response = self._get_create("fit_score=45")
        self.assertEqual(response.context["form"].initial.get("role_fit"), RoleFit.MEDIUM)

    def test_fit_score_below_40_maps_to_role_fit_weak(self):
        response = self._get_create("fit_score=25")
        self.assertEqual(response.context["form"].initial.get("role_fit"), RoleFit.WEAK)

    def test_invalid_fit_score_does_not_raise_server_error(self):
        response = self._get_create("fit_score=not-a-number")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["form"].initial.get("role_fit"))

    def test_pipeline_stage_fit_checked_when_prefill_params_exist(self):
        response = self._get_create("company_name=FinSight")
        self.assertEqual(
            response.context["form"].initial.get("pipeline_stage"),
            PipelineStage.FIT_CHECKED,
        )

    def test_post_create_application_flow_still_works(self):
        response = self.client.post(
            self.create_url,
            {
                "company_name": "Example Ltd",
                "job_title": "Junior Data Analyst",
                "job_url": "https://example.com/job",
                "location": "London",
                "work_type": WorkType.HYBRID,
                "salary_range": "GBP 30,000 - GBP 35,000",
                "source": ApplicationSource.LINKEDIN,
                "role_fit": RoleFit.STRONG,
                "date_applied": "2026-05-09",
                "status": ApplicationStatus.SUBMITTED,
                "response_date": "",
                "cv_version": "DA_CV_v1",
                "cover_letter_version": "Tailored_CL_v1",
                "contact_name": "",
                "contact_email": "",
                "notes": "Good fit.",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(JobApplication.objects.filter(company_name="Example Ltd").exists())


class JobPostingAnalyzerPrefillBridgeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="analyzer", password="StrongPass12345")
        self.client.login(username="analyzer", password="StrongPass12345")
        self.analyzer_url = reverse("ai_agents:job_posting_analyzer")

    def test_save_as_application_not_shown_before_analysis(self):
        response = self.client.get(self.analyzer_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Review & Pre-fill Application", html=True)

    def test_save_as_application_shown_after_analysis(self):
        response = self.client.post(
            self.analyzer_url,
            {
                "company_name": "FinSight",
                "job_title": "Junior Finance Data Analyst",
                "location": "Hybrid London",
                "job_posting": "Python SQL Excel reporting dashboards junior 0-2 years",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Review & Pre-fill Application", html=True)
        self.assertContains(response, "Nothing is submitted automatically")

    def test_save_as_application_link_contains_encoded_get_params(self):
        job_title = "Junior Finance Data Analyst"
        location = "Hybrid London"
        response = self.client.post(
            self.analyzer_url,
            {
                "company_name": "FinSight",
                "job_title": job_title,
                "location": location,
                "job_posting": "Python SQL Excel reporting dashboards junior 0-2 years",
            },
        )
        self.assertContains(response, "company_name=FinSight")
        self.assertContains(response, f"job_title={quote(job_title)}")
        self.assertContains(response, f"location={quote(location)}")
        self.assertContains(response, "fit_score=")

    def test_save_as_application_link_encodes_special_characters_in_company_name(self):
        company_name = "Smith & Jones Ltd"
        response = self.client.post(
            self.analyzer_url,
            {
                "company_name": company_name,
                "job_title": "Junior Data Analyst",
                "location": "London",
                "job_posting": "Python SQL Excel reporting junior dashboard",
            },
        )
        encoded_company = quote(company_name)
        self.assertContains(response, f"company_name={encoded_company}")


class EvaluationQueueTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="queue", password="StrongPass12345")
        self.queue_url = reverse("applications:evaluation_queue")
        self.base_kwargs = {
            "user": self.user,
            "job_title": "Junior Data Analyst",
            "date_applied": date(2026, 5, 9),
        }

    def test_evaluation_queue_requires_login(self):
        response = self.client.get(self.queue_url)
        self.assertEqual(response.status_code, 302)

    def test_evaluation_queue_url_resolves(self):
        self.assertEqual(self.queue_url, "/applications/evaluation/")

    def test_logged_in_user_receives_200(self):
        self.client.login(username="queue", password="StrongPass12345")
        response = self.client.get(self.queue_url)
        self.assertEqual(response.status_code, 200)

    def test_job_found_applications_appear(self):
        application = JobApplication.objects.create(
            **self.base_kwargs,
            company_name="Job Found Co",
            pipeline_stage=PipelineStage.JOB_FOUND,
        )
        self.client.login(username="queue", password="StrongPass12345")
        response = self.client.get(self.queue_url)
        self.assertContains(response, "Job Found Co")
        self.assertIn(application, list(response.context["applications"]))

    def test_fit_checked_applications_appear(self):
        application = JobApplication.objects.create(
            **self.base_kwargs,
            company_name="Fit Checked Co",
            pipeline_stage=PipelineStage.FIT_CHECKED,
        )
        self.client.login(username="queue", password="StrongPass12345")
        response = self.client.get(self.queue_url)
        self.assertContains(response, "Fit Checked Co")
        self.assertIn(application, list(response.context["applications"]))

    def test_submitted_stage_applications_do_not_appear(self):
        JobApplication.objects.create(
            **self.base_kwargs,
            company_name="Submitted Co",
            pipeline_stage=PipelineStage.SUBMITTED,
        )
        self.client.login(username="queue", password="StrongPass12345")
        response = self.client.get(self.queue_url)
        self.assertNotContains(response, "Submitted Co")
        self.assertEqual(response.context["table_rows"], [])

    def test_empty_state_when_no_qualifying_applications(self):
        self.client.login(username="queue", password="StrongPass12345")
        response = self.client.get(self.queue_url)
        self.assertContains(response, "No roles in the evaluation queue yet")
        self.assertContains(response, "Job Posting Analyzer")

    def test_sidebar_link_renders_for_logged_in_user(self):
        self.client.login(username="queue", password="StrongPass12345")
        response = self.client.get(self.queue_url)
        self.assertContains(response, "Evaluation Queue")
        self.assertContains(response, self.queue_url)


class MasterCvLockedClaimWordingTests(SimpleTestCase):
    def test_baseline_and_portfolio_use_locked_master_cv_claims(self):
        from apps.applications.master_cv import (
            BASELINE_PROFILE_PARAGRAPH,
            EXPERIENCE_MONEY_TRANSFER_FX_BULLETS,
            PORTFOLIO_PROJECT_BULLETS,
        )

        careerfunnel = PORTFOLIO_PROJECT_BULLETS["CareerFunnel Tracker"]
        self.assertIn("900+ validated tests", careerfunnel[2])
        self.assertNotIn("828 automated tests", careerfunnel[2])
        self.assertIn("GBP 30,000", BASELINE_PROFILE_PARAGRAPH)
        self.assertIn("GBP 30,000", EXPERIENCE_MONEY_TRANSFER_FX_BULLETS[2])

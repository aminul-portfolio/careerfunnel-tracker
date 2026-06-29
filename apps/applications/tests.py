import json
from datetime import date, datetime, timedelta
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
from apps.skill_gaps.services import normalise_skill_match_key
from apps.skill_ledger.models import SkillEntry

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
    append_status_note,
    build_application_evidence_readiness,
    build_save_quality_warnings,
    calculate_response_rate,
    parse_status_history,
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


class StatusHistoryParserTests(SimpleTestCase):
    def test_parse_status_history_extracts_entries_correctly(self):
        history = parse_status_history(
            "[24 Jun 2026 20:52 - Status: Interview]\nInterview arranged for Friday.",
        )

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].timestamp, "24 Jun 2026 20:52")
        self.assertEqual(history[0].status, "Interview")
        self.assertEqual(history[0].note, "Interview arranged for Friday.")

    def test_parse_status_history_handles_multiple_entries(self):
        history = parse_status_history(
            "[24 Jun 2026 20:52 - Status: Submitted]\nSubmitted manually.\n\n"
            "[25 Jun 2026 09:15 - Status: Screening call]\nScreening call booked.",
        )

        self.assertEqual([entry.status for entry in history], ["Screening call", "Submitted"])
        self.assertEqual(history[0].timestamp, "25 Jun 2026 09:15")
        self.assertEqual(history[0].note, "Screening call booked.")
        self.assertEqual(history[1].note, "Submitted manually.")

    def test_parse_status_history_handles_empty_notes(self):
        self.assertEqual(parse_status_history(""), [])
        self.assertEqual(parse_status_history(None), [])

    def test_parse_status_history_handles_notes_without_status_blocks(self):
        self.assertEqual(
            parse_status_history("Plain manual note without a structured status header."),
            [],
        )


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

    def _login(self):
        self.client.login(username="aminul", password="StrongPass12345")

    def _get_application_list(self, query_string=""):
        self._login()
        url = reverse("applications:application_list")
        if query_string:
            url = f"{url}?{query_string}"
        return self.client.get(url)

    def _get_application_detail(self, application):
        self._login()
        return self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

    def _get_status_update(self, application):
        self._login()
        return self.client.get(
            reverse("applications:application_status_update", kwargs={"pk": application.pk}),
        )

    def _post_status_update(self, application, **overrides):
        self._login()
        data = {
            "status": ApplicationStatus.INTERVIEW,
            "pipeline_stage": PipelineStage.INTERVIEW,
            "response_date": "2026-05-12",
            "status_note": "Recruiter confirmed interview stage.",
        }
        data.update(overrides)
        return self.client.post(
            reverse("applications:application_status_update", kwargs={"pk": application.pk}),
            data,
        )

    def _get_data_quality_audit(self):
        self._login()
        return self.client.get(reverse("applications:application_data_quality_audit"))

    def _get_jd_gap_aggregation(self):
        self._login()
        return self.client.get(reverse("applications:jd_gap_aggregation"))

    def _jd_text(self, length=750):
        return "A" * length

    def _jd_gap_text(self, *terms, length=900):
        intro = " ".join(terms)
        filler = " planning context" * 120
        text = f"{intro} {filler}".strip()
        if len(text) >= length:
            return text
        return f"{text} {'A' * (length - len(text))}"

    def _create_jd_ready_application(self, **overrides):
        defaults = {
            "company_name": "Ready Co",
            "job_title": "Data Analyst",
            "job_description": self._jd_gap_text("python"),
            "date_applied": date(2026, 5, 9),
        }
        defaults.update(overrides)
        return self.create_application(**defaults)

    def _create_skill_entry(self, **overrides):
        defaults = {
            "skill_name": "Python analytics",
            "category": SkillEntry.Category.PROGRAMMING,
            "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
            "sprint_reference": "Sprint 70",
            "project_link": "https://example.com/project",
            "notes": "Existing ledger note.",
            "visibility": SkillEntry.Visibility.PRIVATE,
        }
        defaults.update(overrides)
        return SkillEntry.objects.create(**defaults)

    def test_application_list_requires_login(self):
        response = self.client.get(reverse("applications:application_list"))
        self.assertEqual(response.status_code, 302)

    def test_status_update_form_loads_for_authenticated_owner(self):
        application = self.create_application()

        response = self._get_status_update(application)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Update tracking status")
        self.assertContains(response, application.company_name)

    def test_status_update_form_redirects_anonymous_user(self):
        application = self.create_application()

        response = self.client.get(
            reverse("applications:application_status_update", kwargs={"pk": application.pk}),
        )

        self.assertEqual(response.status_code, 302)

    def test_status_update_form_returns_403_or_404_for_wrong_user(self):
        other_user = User.objects.create_user(username="other", password="StrongPass12345")
        application = self.create_application()
        self.client.login(username="other", password="StrongPass12345")

        get_response = self.client.get(
            reverse("applications:application_status_update", kwargs={"pk": application.pk}),
        )
        post_response = self.client.post(
            reverse("applications:application_status_update", kwargs={"pk": application.pk}),
            {
                "status": ApplicationStatus.INTERVIEW,
                "pipeline_stage": PipelineStage.INTERVIEW,
                "response_date": "2026-05-12",
                "status_note": "Should not update.",
            },
        )

        self.assertEqual(other_user.job_applications.count(), 0)
        self.assertIn(get_response.status_code, {403, 404})
        self.assertIn(post_response.status_code, {403, 404})
        application.refresh_from_db()
        self.assertNotEqual(application.status, ApplicationStatus.INTERVIEW)

    def test_status_update_valid_post_updates_status(self):
        application = self.create_application(status=ApplicationStatus.SUBMITTED)

        response = self._post_status_update(application)

        self.assertRedirects(response, application.get_absolute_url())
        application.refresh_from_db()
        self.assertEqual(application.status, ApplicationStatus.INTERVIEW)

    def test_status_update_valid_post_updates_pipeline_stage(self):
        application = self.create_application(pipeline_stage=PipelineStage.SUBMITTED)

        self._post_status_update(application, pipeline_stage=PipelineStage.SCREENING_CALL)

        application.refresh_from_db()
        self.assertEqual(application.pipeline_stage, PipelineStage.SCREENING_CALL)

    def test_status_update_valid_post_updates_response_date(self):
        application = self.create_application(response_date=None)

        self._post_status_update(application, response_date="2026-05-12")

        application.refresh_from_db()
        self.assertEqual(application.response_date, date(2026, 5, 12))

    def test_status_update_status_note_appends_to_existing_notes(self):
        application = self.create_application(notes="Existing note.")

        self._post_status_update(
            application,
            status=ApplicationStatus.INTERVIEW,
            status_note="Interview arranged for Friday.",
        )

        application.refresh_from_db()
        self.assertIn("Existing note.", application.notes)
        self.assertIn("Status: Interview", application.notes)
        self.assertIn("Interview arranged for Friday.", application.notes)

    def test_status_update_status_note_empty_does_not_corrupt_notes(self):
        application = self.create_application(notes="Existing note.")

        self._post_status_update(application, status_note="")

        application.refresh_from_db()
        self.assertEqual(application.notes, "Existing note.")

    def test_status_update_response_date_before_date_applied_shows_error(self):
        application = self.create_application(date_applied=date(2026, 5, 9))

        response = self._post_status_update(application, response_date="2026-05-01")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Response date cannot be before the application date.")

    def test_application_detail_shows_update_status_button(self):
        application = self.create_application()

        response = self._get_application_detail(application)

        self.assertContains(response, "Update Status")
        self.assertContains(
            response,
            reverse("applications:application_status_update", kwargs={"pk": application.pk}),
        )

    def test_detail_page_update_status_is_primary_action(self):
        application = self.create_application()

        response = self._get_application_detail(application)
        content = response.content.decode()
        status_url = reverse(
            "applications:application_status_update",
            kwargs={"pk": application.pk},
        )

        self.assertIn("cf74-action-tier-primary", content)
        self.assertIn(
            (
                f'href="{status_url}" '
                'class="btn btn-primary cf74-action-primary">Update Status</a>'
            ),
            content,
        )

    def test_detail_page_edit_application_is_secondary_action(self):
        application = self.create_application()

        response = self._get_application_detail(application)
        content = response.content.decode()
        update_url = reverse("applications:application_update", kwargs={"pk": application.pk})
        list_url = reverse("applications:application_list")

        self.assertIn("cf74-action-tier-secondary", content)
        self.assertIn(
            (
                f'href="{update_url}" '
                'class="btn btn-secondary cf74-action-secondary">Edit Application</a>'
            ),
            content,
        )
        self.assertIn(
            (
                f'href="{list_url}" '
                'class="btn btn-secondary cf74-action-secondary"><span>Back</span> to list</a>'
            ),
            content,
        )

    def test_detail_page_smart_review_is_advisory_action(self):
        application = self.create_application()

        response = self._get_application_detail(application)
        content = response.content.decode()
        smart_review_url = reverse(
            "job_intelligence:application_smart_review",
            args=[application.pk],
        )
        ai_pack_url = reverse("ai_agents:application_agent_pack", args=[application.pk])
        interview_url = reverse("interviews:interview_create")

        self.assertIn("cf74-action-tier-advisory", content)
        self.assertIn("ADVISORY TOOLS", content)
        for expected in (
            (
                f'href="{smart_review_url}" '
                'class="btn btn-secondary cf74-action-advisory">Smart Review</a>'
            ),
            (
                f'href="{ai_pack_url}" '
                'class="btn btn-secondary cf74-action-advisory">'
                "Open AI Pack / CV Tailoring Advisor</a>"
            ),
            (
                f'href="{interview_url}?application={application.pk}" '
                'class="btn btn-secondary cf74-action-advisory">Create Interview Prep</a>'
            ),
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, content)

    def test_detail_page_delete_remains_in_danger_zone(self):
        application = self.create_application()

        response = self._get_application_detail(application)
        content = response.content.decode()
        hero_content = content.split('class="cf69d-safety-grid"', 1)[0]
        danger_zone = content.split('class="danger-zone cf69d-danger-zone"', 1)[1]
        delete_url = reverse("applications:application_delete", kwargs={"pk": application.pk})

        self.assertNotIn(delete_url, hero_content)
        self.assertIn(delete_url, danger_zone)
        self.assertIn('class="btn btn-danger">Delete</a>', danger_zone)

    def test_detail_page_action_cluster_does_not_imply_automation(self):
        application = self.create_application()

        response = self._get_application_detail(application)
        content = response.content.decode()
        action_cluster = content.split('aria-label="Application action hierarchy"', 1)[1].split(
            'class="cf69d-safety-grid"',
            1,
        )[0]

        for phrase in (
            "Employer notified",
            "Auto-updated",
            "Synced with recruiter",
            "Email read",
            "Confirmed by employer",
            "Sent to",
            "Automatically",
        ):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase.lower(), action_cluster.lower())

    def test_detail_page_status_history_section_renders(self):
        application = self.create_application(notes="Plain manual note.")

        response = self._get_application_detail(application)
        content = response.content.decode()

        self.assertContains(response, "Status History")
        self.assertContains(
            response,
            (
                "Status history is derived from your manual tracking notes. "
                "It reflects your own record updates only."
            ),
        )
        self.assertIn('id="status-history"', content)
        self.assertIn("cf74-history-section", content)
        self.assertIn(
            (
                "No status history recorded yet. Use Update Status to log stage changes "
                "with timestamped notes."
            ),
            content,
        )

    def test_detail_page_status_history_shows_most_recent_first(self):
        application = self.create_application(
            notes=(
                "[24 Jun 2026 20:52 - Status: Submitted]\n"
                "Submitted application manually.\n\n"
                "[25 Jun 2026 09:15 - Status: Screening call]\n"
                "Screening call booked."
            ),
        )

        response = self._get_application_detail(application)
        content = response.content.decode()
        history_section = content.split('id="status-history"', 1)[1].split(
            'id="evidence"',
            1,
        )[0]

        self.assertLess(
            history_section.find("Screening call"),
            history_section.find("Submitted"),
        )
        self.assertLess(
            history_section.find("Screening call booked."),
            history_section.find("Submitted application manually."),
        )
        self.assertIn("<details", history_section)
        self.assertIn("<summary", history_section)

    def test_detail_page_status_history_does_not_imply_employer_sync(self):
        application = self.create_application(
            notes="[24 Jun 2026 20:52 - Status: Interview]\nInterview arranged manually.",
        )

        response = self._get_application_detail(application)
        content = response.content.decode()
        history_section = content.split('id="status-history"', 1)[1].split(
            'id="evidence"',
            1,
        )[0]

        for phrase in (
            "Employer notified",
            "Auto-updated",
            "Synced with recruiter",
            "Email read",
            "Confirmed by employer",
            "Sent to",
            "Automatically",
        ):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase.lower(), history_section.lower())

    def test_status_update_template_shows_tracking_only_wording(self):
        application = self.create_application()

        response = self._get_status_update(application)

        self.assertContains(
            response,
            (
                "This updates your saved tracking record only. It does not update any "
                "employer system or send any notification. Review recruiter emails and "
                "employer messages manually before changing status."
            ),
        )
        self.assertContains(
            response,
            (
                "Optional - appended to your existing notes with a timestamp. "
                "Previous notes are not deleted."
            ),
        )

    def test_status_update_template_does_not_imply_employer_notification(self):
        application = self.create_application()

        response = self._get_status_update(application)
        content = response.content.decode()

        self.assertNotIn("Employer notified", content)
        self.assertNotIn("Status sent to recruiter", content)
        self.assertNotIn("Synced with", content)

    def test_status_update_template_does_not_imply_auto_update(self):
        application = self.create_application()

        response = self._get_status_update(application)

        self.assertNotContains(response, "Auto-updated")

    def test_append_status_note_appends_to_existing_notes(self):
        with patch(
            "apps.applications.services.timezone.localtime",
            return_value=datetime(2026, 6, 24, 20, 52),
        ):
            notes = append_status_note(
                "Existing note.",
                "Interview arranged.",
                ApplicationStatus.INTERVIEW,
            )

        self.assertEqual(
            notes,
            "Existing note.\n\n[24 Jun 2026 20:52 - Status: Interview]\nInterview arranged.",
        )

    def test_append_status_note_handles_empty_existing_notes(self):
        with patch(
            "apps.applications.services.timezone.localtime",
            return_value=datetime(2026, 6, 24, 20, 52),
        ):
            notes = append_status_note(
                "",
                "Screening call booked.",
                ApplicationStatus.SCREENING_CALL,
            )

        self.assertEqual(
            notes,
            "[24 Jun 2026 20:52 - Status: Screening call]\nScreening call booked.",
        )

    def test_append_status_note_includes_timestamp_and_status(self):
        with patch(
            "apps.applications.services.timezone.localtime",
            return_value=datetime(2026, 6, 24, 20, 52),
        ):
            notes = append_status_note("", "Offer received.", ApplicationStatus.OFFER)

        self.assertIn("[24 Jun 2026 20:52 - Status: Offer]", notes)

    def test_status_update_response_date_input_renders_iso_value(self):
        application = self.create_application(response_date=date(2026, 6, 20))

        response = self._get_status_update(application)

        self.assertContains(response, 'value="2026-06-20"')

    def test_jd_gap_aggregation_page_loads_for_authenticated_user(self):
        response = self._get_jd_gap_aggregation()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "JD-gap Aggregation Planning")

    def test_jd_gap_aggregation_page_requires_login(self):
        response = self.client.get(reverse("applications:jd_gap_aggregation"))

        self.assertEqual(response.status_code, 302)

    def test_jd_gap_aggregation_page_is_get_only(self):
        self._create_jd_ready_application()
        before_application_count = JobApplication.objects.count()
        before_skill_count = SkillEntry.objects.count()
        self._login()

        response = self.client.post(reverse("applications:jd_gap_aggregation"))

        self.assertEqual(response.status_code, 405)
        self.assertEqual(JobApplication.objects.count(), before_application_count)
        self.assertEqual(SkillEntry.objects.count(), before_skill_count)

    def test_aggregation_uses_only_jd_ready_records(self):
        self._create_jd_ready_application(job_description=self._jd_gap_text("python"))
        self._create_jd_ready_application(
            company_name="Ready Two",
            job_description=self._jd_gap_text("python"),
        )
        self.create_application(
            company_name="",
            job_title="Data Analyst",
            job_description=self._jd_gap_text("dbt"),
        )

        response = self._get_jd_gap_aggregation()
        content = response.content.decode()

        self.assertEqual(response.context["aggregation"].jd_ready_count, 2)
        self.assertContains(response, "python")
        self.assertNotIn(">dbt<", content)

    def test_aggregation_excludes_exact_url_duplicates(self):
        duplicate_url = "https://example.com/repeated"
        self._create_jd_ready_application(
            job_url=duplicate_url,
            job_description=self._jd_gap_text("dbt"),
        )
        self._create_jd_ready_application(
            company_name="Duplicate Two",
            job_url=duplicate_url,
            job_description=self._jd_gap_text("dbt"),
        )
        self._create_jd_ready_application(
            company_name="Unique One",
            job_description=self._jd_gap_text("python"),
        )
        self._create_jd_ready_application(
            company_name="Unique Two",
            job_description=self._jd_gap_text("python"),
        )

        response = self._get_jd_gap_aggregation()
        content = response.content.decode()

        self.assertEqual(response.context["aggregation"].jd_ready_count, 2)
        self.assertContains(response, "python")
        self.assertNotIn(">dbt<", content)

    def test_aggregation_excludes_records_below_750_char_threshold(self):
        self.create_application(
            company_name="Short One",
            job_title="Data Analyst",
            job_description="python " * 20,
        )
        self.create_application(
            company_name="Short Two",
            job_title="BI Analyst",
            job_description="python " * 20,
        )

        response = self._get_jd_gap_aggregation()

        self.assertEqual(response.context["aggregation"].jd_ready_count, 0)
        self.assertEqual(response.context["aggregation"].terms_found_count, 0)

    def test_term_extraction_is_case_insensitive(self):
        self._create_jd_ready_application(job_description=self._jd_gap_text("POWER BI"))
        self._create_jd_ready_application(
            company_name="BI Two",
            job_description=self._jd_gap_text("powerbi"),
        )

        response = self._get_jd_gap_aggregation()

        self.assertContains(response, "power bi")
        self.assertEqual(response.context["aggregation"].terms_found_count, 1)

    def test_term_extraction_counts_per_jd_not_per_occurrence(self):
        repeated_term = "Power BI Power BI Power BI Power BI Power BI"
        self._create_jd_ready_application(job_description=self._jd_gap_text(repeated_term))
        self._create_jd_ready_application(
            company_name="BI Two",
            job_description=self._jd_gap_text("Power BI"),
        )

        response = self._get_jd_gap_aggregation()
        power_bi_term = response.context["aggregation"].category_groups[0].terms[0]

        self.assertEqual(power_bi_term.term, "power bi")
        self.assertEqual(power_bi_term.frequency, 2)

    def test_term_frequency_minimum_threshold_is_2(self):
        self._create_jd_ready_application(job_description=self._jd_gap_text("python"))
        self._create_jd_ready_application(
            company_name="SQL Co",
            job_description=self._jd_gap_text("sql"),
        )

        response = self._get_jd_gap_aggregation()

        self.assertEqual(response.context["aggregation"].terms_found_count, 0)
        self.assertContains(response, "No tracked terms met the frequency threshold.")

    def test_term_extraction_uses_tracked_terms_only(self):
        self._create_jd_ready_application(
            job_description=self._jd_gap_text("data analysis analytical"),
        )
        self._create_jd_ready_application(
            company_name="Generic Two",
            job_description=self._jd_gap_text("data analysis analytical"),
        )

        response = self._get_jd_gap_aggregation()

        self.assertEqual(response.context["aggregation"].terms_found_count, 0)

    def test_skill_ledger_comparison_is_read_only(self):
        self._create_skill_entry(skill_name="Python")
        self._create_jd_ready_application(job_description=self._jd_gap_text("python"))
        self._create_jd_ready_application(
            company_name="Python Two",
            job_description=self._jd_gap_text("python"),
        )
        before_entries = list(SkillEntry.objects.values_list("pk", "skill_name", "evidence_level"))

        response = self._get_jd_gap_aggregation()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(SkillEntry.objects.values_list("pk", "skill_name", "evidence_level")),
            before_entries,
        )

    def test_verified_skill_shows_verified_label(self):
        self._create_skill_entry(
            skill_name="Python",
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
        )
        self._create_jd_ready_application(job_description=self._jd_gap_text("python"))
        self._create_jd_ready_application(
            company_name="Python Two",
            job_description=self._jd_gap_text("python"),
        )

        response = self._get_jd_gap_aggregation()

        self.assertContains(response, "VERIFIED")
        self.assertContains(response, "Portfolio evidence confirmed")

    def test_learning_target_skill_shows_learning_target_label(self):
        self._create_skill_entry(
            skill_name="PowerBI",
            evidence_level=SkillEntry.EvidenceLevel.LEARNING_TARGET,
        )
        self._create_jd_ready_application(job_description=self._jd_gap_text("power bi"))
        self._create_jd_ready_application(
            company_name="Power BI Two",
            job_description=self._jd_gap_text("power bi"),
        )

        response = self._get_jd_gap_aggregation()

        self.assertContains(response, "LEARNING TARGET")
        self.assertContains(response, "Developing - not yet evidenced")

    def test_unmatched_term_shows_not_in_ledger_label(self):
        self._create_jd_ready_application(job_description=self._jd_gap_text("snowflake"))
        self._create_jd_ready_application(
            company_name="Snowflake Two",
            job_description=self._jd_gap_text("snowflake"),
        )

        response = self._get_jd_gap_aggregation()

        self.assertContains(response, "Not in your skill ledger")

    def test_skill_ledger_comparison_does_not_create_entries(self):
        self._create_jd_ready_application(job_description=self._jd_gap_text("tableau"))
        self._create_jd_ready_application(
            company_name="Tableau Two",
            job_description=self._jd_gap_text("tableau"),
        )
        before_count = SkillEntry.objects.count()

        response = self._get_jd_gap_aggregation()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(SkillEntry.objects.count(), before_count)

    def test_skill_ledger_comparison_does_not_update_entries(self):
        skill_entry = self._create_skill_entry(skill_name="SQL")
        original_values = {
            "skill_name": skill_entry.skill_name,
            "evidence_level": skill_entry.evidence_level,
            "notes": skill_entry.notes,
            "visibility": skill_entry.visibility,
        }
        self._create_jd_ready_application(job_description=self._jd_gap_text("sql"))
        self._create_jd_ready_application(
            company_name="SQL Two",
            job_description=self._jd_gap_text("sql"),
        )

        response = self._get_jd_gap_aggregation()
        skill_entry.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(skill_entry.skill_name, original_values["skill_name"])
        self.assertEqual(skill_entry.evidence_level, original_values["evidence_level"])
        self.assertEqual(skill_entry.notes, original_values["notes"])
        self.assertEqual(skill_entry.visibility, original_values["visibility"])

    def test_kpi_jd_ready_count_renders(self):
        self._create_jd_ready_application()
        self._create_jd_ready_application(company_name="Ready Two")

        response = self._get_jd_gap_aggregation()

        self.assertEqual(response.context["aggregation"].jd_ready_count, 2)
        self.assertContains(response, "JD-ready Records")
        self.assertContains(response, ">2<")

    def test_kpi_terms_found_count_renders(self):
        self._create_jd_ready_application(job_description=self._jd_gap_text("python"))
        self._create_jd_ready_application(
            company_name="Python Two",
            job_description=self._jd_gap_text("python"),
        )

        response = self._get_jd_gap_aggregation()

        self.assertEqual(response.context["aggregation"].terms_found_count, 1)
        self.assertContains(response, "Terms Found")

    def test_kpi_unmatched_in_ledger_count_renders(self):
        self._create_jd_ready_application(job_description=self._jd_gap_text("looker"))
        self._create_jd_ready_application(
            company_name="Looker Two",
            job_description=self._jd_gap_text("looker"),
        )

        response = self._get_jd_gap_aggregation()

        self.assertEqual(response.context["aggregation"].unmatched_in_ledger_count, 1)
        self.assertContains(response, "Unmatched in Ledger")

    def test_advisory_panel_present(self):
        response = self._get_jd_gap_aggregation()

        self.assertContains(
            response,
            (
                "Skill gap signals are advisory only. This page summarises repeated terms "
                "found in saved job descriptions and does not rank applications, assess "
                "suitability, generate documents, or update records."
            ),
        )

    def test_results_interpretation_note_present(self):
        response = self._get_jd_gap_aggregation()

        self.assertContains(
            response,
            (
                "Frequency counts show how many saved job descriptions mention each term. "
                "Higher frequency means the term appeared more often across your applications "
                "- it does not indicate a skill gap, a requirement, or a priority unless you "
                "judge it to be one."
            ),
        )

    def test_page_does_not_imply_skill_gap_confirmed(self):
        response = self._get_jd_gap_aggregation()
        content = response.content.decode().lower()

        self.assertIn("skill gap signals are advisory only", content)
        self.assertNotIn("confirmed skill gap", content)
        self.assertNotIn("missing ability", content)

    def test_page_does_not_imply_application_ranking(self):
        response = self._get_jd_gap_aggregation()
        content = response.content.decode().lower()

        self.assertIn("does not rank applications", content)
        self.assertNotIn("ranked applications", content)
        self.assertNotIn("best application", content)

    def test_page_does_not_imply_record_mutation(self):
        response = self._get_jd_gap_aggregation()
        content = response.content.decode().lower()

        self.assertIn("no records have been changed", content)
        self.assertNotIn(">edit<", content)
        self.assertNotIn(">fix<", content)
        self.assertNotIn(">create<", content)

    def test_unmatched_section_note_does_not_imply_automatic_update(self):
        response = self._get_jd_gap_aggregation()
        content = response.content.decode()

        self.assertIn(
            (
                "These terms appear frequently in your saved JDs and are not yet in your "
                "Skill Ledger. Consider adding them for future tracking. Adding to ledger "
                "is manual and optional. This page does not update your ledger."
            ),
            content,
        )
        self.assertNotIn("automatically update", content.lower())

    def test_sprint_72a_data_quality_page_unaffected(self):
        response = self._get_data_quality_audit()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Application Data Quality Audit")
        self.assertContains(
            response,
            (
                "This audit checks application record completeness only. It does not "
                "analyse skill gaps, rank applications, generate documents, or update records."
            ),
        )

    def test_top_term_renders(self):
        for index in range(3):
            self._create_jd_ready_application(
                company_name=f"Python {index}",
                job_description=self._jd_gap_text("python"),
            )
        for index in range(2):
            self._create_jd_ready_application(
                company_name=f"SQL {index}",
                job_description=self._jd_gap_text("sql"),
            )

        response = self._get_jd_gap_aggregation()

        self.assertEqual(response.context["aggregation"].top_term.term, "python")
        self.assertContains(response, "Top Term")
        self.assertContains(response, "python")

    def test_sample_applications_are_limited_to_3(self):
        for index in range(4):
            self._create_jd_ready_application(
                company_name=f"Python Sample {index}",
                job_description=self._jd_gap_text("python"),
            )

        response = self._get_jd_gap_aggregation()
        python_term = response.context["aggregation"].category_groups[0].terms[0]

        self.assertEqual(python_term.term, "python")
        self.assertEqual(len(python_term.sample_applications), 3)

    def test_application_gap_matching_uses_alias_normalised_exact_match(self):
        self._create_skill_entry(skill_name="SQL Server")
        self._create_jd_ready_application(job_description=self._jd_gap_text("sql"))
        self._create_jd_ready_application(
            company_name="SQL Two",
            job_description=self._jd_gap_text("sql"),
        )

        response = self._get_jd_gap_aggregation()
        sql_term = next(
            term
            for group in response.context["aggregation"].category_groups
            for term in group.terms
            if term.term == "sql"
        )

        self.assertFalse(sql_term.is_unmatched)
        self.assertEqual(sql_term.skill_ledger_match.skill_name, "SQL Server")
        self.assertContains(response, "VERIFIED")

    def test_application_gap_matching_rejects_substring_false_positive(self):
        self._create_skill_entry(skill_name="NoSQL")
        self._create_jd_ready_application(job_description=self._jd_gap_text("sql"))
        self._create_jd_ready_application(
            company_name="SQL Two",
            job_description=self._jd_gap_text("sql"),
        )

        response = self._get_jd_gap_aggregation()
        sql_term = next(
            term
            for group in response.context["aggregation"].category_groups
            for term in group.terms
            if term.term == "sql"
        )

        self.assertTrue(sql_term.is_unmatched)
        self.assertIsNone(sql_term.skill_ledger_match)
        self.assertEqual(response.context["aggregation"].unmatched_in_ledger_count, 1)
        self.assertContains(response, "Not in your skill ledger")

    def test_application_gap_matching_preserves_tracked_term_counts(self):
        self._create_jd_ready_application(job_description=self._jd_gap_text("python", "sql"))
        self._create_jd_ready_application(
            company_name="Mixed Two",
            job_description=self._jd_gap_text("python", "sql"),
        )
        self._create_jd_ready_application(
            company_name="Power BI One",
            job_description=self._jd_gap_text("power bi"),
        )
        self._create_jd_ready_application(
            company_name="Power BI Two",
            job_description=self._jd_gap_text("powerbi"),
        )

        response = self._get_jd_gap_aggregation()
        terms_by_name = {
            term.term: term
            for group in response.context["aggregation"].category_groups
            for term in group.terms
        }

        self.assertEqual(response.context["aggregation"].terms_found_count, 3)
        self.assertEqual(terms_by_name["python"].frequency, 2)
        self.assertEqual(terms_by_name["sql"].frequency, 2)
        self.assertEqual(terms_by_name["power bi"].frequency, 2)

    def test_application_gap_matching_uses_skill_gap_alias_normalisation_reference(self):
        self.assertEqual(normalise_skill_match_key("dbt core"), "dbt")
        self._create_skill_entry(skill_name="dbt")
        self._create_jd_ready_application(job_description=self._jd_gap_text("dbt"))
        self._create_jd_ready_application(
            company_name="dbt Two",
            job_description=self._jd_gap_text("dbt"),
        )

        response = self._get_jd_gap_aggregation()
        dbt_term = next(
            term
            for group in response.context["aggregation"].category_groups
            for term in group.terms
            if term.term == normalise_skill_match_key("dbt core")
        )

        self.assertFalse(dbt_term.is_unmatched)
        self.assertEqual(dbt_term.skill_ledger_match.skill_name, "dbt")

    def test_no_terms_render_when_frequency_below_2(self):
        self._create_jd_ready_application(job_description=self._jd_gap_text("airflow"))

        response = self._get_jd_gap_aggregation()

        self.assertEqual(response.context["aggregation"].terms_found_count, 0)
        self.assertContains(response, "No tracked terms met the frequency threshold.")

    def test_sprint_72d_kpi_hierarchy_classes_labels_and_notes_render(self):
        response = self._get_jd_gap_aggregation()
        content = response.content.decode()

        self.assertIn('class="cf69-kpi"', content)
        for expected in (
            "JD-READY RECORDS",
            "TERMS FOUND",
            "TOP TERM",
            "UNMATCHED IN LEDGER",
            "Records included in this planning view",
            "Tracked terms at frequency 2+",
            "Highest repeated tracked term",
            "Not in your skill ledger",
        ):
            with self.subTest(expected=expected):
                self.assertContains(response, expected)

    def test_sprint_72d_category_cards_header_and_badge_structure_render(self):
        self._create_jd_ready_application(job_description=self._jd_gap_text("python"))
        self._create_jd_ready_application(
            company_name="Python Two",
            job_description=self._jd_gap_text("python"),
        )

        response = self._get_jd_gap_aggregation()
        content = response.content.decode()

        self.assertIn("cf69-card cf69-card-compact cf72d-category-card", content)
        self.assertIn("cf72d-category-header", content)
        self.assertIn("cf72d-category-title", content)
        self.assertIn("cf69-badge cf69-badge-neutral", content)
        self.assertContains(response, "1 terms")

    def test_sprint_72d_not_in_skill_ledger_card_prominence_and_note_render(self):
        response = self._get_jd_gap_aggregation()
        expected_note = (
            "These terms appear frequently in your saved JDs and are not yet in your "
            "Skill Ledger. Consider adding them for future tracking. Adding to ledger "
            "is manual and optional. This page does not update your ledger."
        )
        content = response.content.decode()

        self.assertIn("cf72d-not-in-ledger-card", content)
        self.assertIn("cf69-advisory-info", content)
        self.assertContains(response, "Frequent tracked terms without a Skill Ledger match")
        self.assertContains(response, expected_note)

    def test_sprint_72d_skill_ledger_status_badges_render_exact_labels_and_notes(self):
        self._create_skill_entry(
            skill_name="Python",
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
        )
        self._create_skill_entry(
            skill_name="PowerBI",
            evidence_level=SkillEntry.EvidenceLevel.LEARNING_TARGET,
        )
        self._create_skill_entry(
            skill_name="SQL Server",
            evidence_level=SkillEntry.EvidenceLevel.STUDYING,
        )
        for term in ("python", "power bi", "sql", "looker"):
            self._create_jd_ready_application(
                company_name=f"{term} one",
                job_description=self._jd_gap_text(term),
            )
            self._create_jd_ready_application(
                company_name=f"{term} two",
                job_description=self._jd_gap_text(term),
            )

        response = self._get_jd_gap_aggregation()

        for expected in (
            "VERIFIED",
            "Portfolio evidence confirmed",
            "LEARNING TARGET",
            "Developing - not yet evidenced",
            "STUDYING",
            "Personal study only",
            "NOT IN LEDGER",
        ):
            with self.subTest(expected=expected):
                self.assertContains(response, expected)
        for forbidden in (
            "Your skill ledger shows:",
            "Skill Confirmed",
            "Confirmed",
            "In Progress",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotContains(response, forbidden)

    def test_sprint_72d_locked_safety_wording_survives_and_unsafe_labels_absent(self):
        response = self._get_jd_gap_aggregation()
        content = response.content.decode()

        for expected in (
            "Skill gap signals are advisory only.",
            "This page does not update your ledger.",
            "Adding to ledger is manual and optional.",
            "No records have been changed.",
            "Skill Ledger comparison is read-only.",
            "Frequency counts show how many saved job descriptions mention each term.",
            (
                "it does not indicate a skill gap, a requirement, or a priority unless "
                "you judge it to be one"
            ),
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, content)
        for forbidden in (
            "Your skill ledger shows:",
            "Missing Skills",
            "Gap Scoring",
            "AI Gap Analysis",
            "Skill Recommendations",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, content)

    def test_data_quality_audit_page_loads_for_authenticated_user(self):
        response = self._get_data_quality_audit()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Application Data Quality Audit")

    def test_data_quality_audit_page_requires_login(self):
        response = self.client.get(reverse("applications:application_data_quality_audit"))

        self.assertEqual(response.status_code, 302)

    def test_data_quality_audit_page_is_get_only(self):
        self.create_application()
        before_count = JobApplication.objects.filter(user=self.user).count()
        self._login()

        response = self.client.post(reverse("applications:application_data_quality_audit"))

        self.assertEqual(response.status_code, 405)
        self.assertEqual(JobApplication.objects.filter(user=self.user).count(), before_count)

    def test_data_quality_audit_shows_total_record_count(self):
        self.create_application(company_name="One")
        self.create_application(company_name="Two")

        response = self._get_data_quality_audit()

        self.assertEqual(response.context["total_records"], 2)
        self.assertContains(response, "Total Records")
        self.assertContains(response, ">2<")

    def test_data_quality_audit_shows_jd_ready_count(self):
        self.create_application(
            company_name="Ready Co",
            job_title="Data Analyst",
            job_description=self._jd_text(),
        )
        self.create_application(job_description="Short")

        response = self._get_data_quality_audit()

        self.assertEqual(response.context["jd_ready_count"], 1)
        self.assertContains(response, "JD-ready")

    def test_data_quality_audit_shows_missing_jd_text_count(self):
        self.create_application(job_description="")
        self.create_application(job_description=self._jd_text())

        response = self._get_data_quality_audit()

        self.assertEqual(response.context["missing_jd_text_count"], 1)
        self.assertContains(response, "Missing JD Text")

    def test_data_quality_audit_shows_possible_duplicate_count(self):
        duplicate_url = "https://example.com/repeated-job"
        self.create_application(job_url=duplicate_url, job_description=self._jd_text())
        self.create_application(
            company_name="Other",
            job_url=duplicate_url,
            job_description=self._jd_text(),
        )
        self.create_application(
            company_name="Blank URL",
            job_url="",
            job_description=self._jd_text(),
        )

        response = self._get_data_quality_audit()

        self.assertEqual(response.context["possible_duplicate_url_record_count"], 2)
        self.assertContains(response, "Possible Duplicates")

    def test_data_quality_audit_completeness_rate_renders(self):
        self.create_application(
            location="London",
            job_url="https://example.com/complete",
            job_description=self._jd_text(),
        )
        self.create_application(location="", job_url="", job_description="")

        response = self._get_data_quality_audit()

        self.assertEqual(response.context["completeness_rate"], 50)
        self.assertContains(response, "Completeness Rate")
        self.assertContains(response, "50%")

    def test_jd_ready_requires_company_present(self):
        self.create_application(company_name="   ", job_description=self._jd_text())

        response = self._get_data_quality_audit()

        self.assertEqual(response.context["jd_ready_count"], 0)
        self.assertContains(response, "Company")

    def test_jd_ready_requires_job_title_present(self):
        self.create_application(job_title="   ", job_description=self._jd_text())

        response = self._get_data_quality_audit()

        self.assertEqual(response.context["jd_ready_count"], 0)
        self.assertContains(response, "Job title")

    def test_jd_ready_requires_jd_text_present(self):
        self.create_application(job_description="   ")

        response = self._get_data_quality_audit()

        self.assertEqual(response.context["jd_ready_count"], 0)
        self.assertContains(response, "JD text")

    def test_jd_ready_requires_jd_text_above_threshold(self):
        self.create_application(job_description=self._jd_text(749))

        response = self._get_data_quality_audit()

        self.assertEqual(response.context["jd_ready_count"], 0)
        self.assertContains(response, "JD text &gt;= 750 chars")

    def test_jd_ready_threshold_is_750_characters(self):
        self.create_application(job_description=self._jd_text(750))

        response = self._get_data_quality_audit()

        self.assertEqual(response.context["jd_ready_count"], 1)
        self.assertContains(response, "JD text length threshold: 750 chars")

    def test_jd_ready_excludes_exact_url_duplicates(self):
        duplicate_url = "https://example.com/exact-duplicate"
        self.create_application(job_url=duplicate_url, job_description=self._jd_text())
        self.create_application(
            company_name="Second Co",
            job_url=duplicate_url,
            job_description=self._jd_text(),
        )

        response = self._get_data_quality_audit()

        self.assertEqual(response.context["jd_ready_count"], 0)
        self.assertEqual(response.context["possible_duplicate_url_record_count"], 2)
        self.assertContains(response, "Possible duplicate - review manually")

    def test_field_completeness_table_renders(self):
        response = self._get_data_quality_audit()

        self.assertContains(response, "Field completeness")
        for heading in ("Field", "Present", "Missing", "Complete"):
            with self.subTest(heading=heading):
                self.assertContains(response, heading)

    def test_field_completeness_shows_source_url_count(self):
        self.create_application(
            job_url="https://example.com/source",
            job_description=self._jd_text(),
        )
        self.create_application(job_url="", job_description=self._jd_text())

        response = self._get_data_quality_audit()
        source_url_row = next(
            row
            for row in response.context["field_completeness_rows"]
            if row["label"] == "Source URL"
        )

        self.assertEqual(source_url_row["present"], 1)
        self.assertContains(response, "Source URL")

    def test_field_completeness_shows_location_count(self):
        self.create_application(location="London")
        self.create_application(location="   ")

        response = self._get_data_quality_audit()
        location_row = next(
            row for row in response.context["field_completeness_rows"] if row["label"] == "Location"
        )

        self.assertEqual(location_row["present"], 1)
        self.assertContains(response, "Location")

    def test_audit_advisory_panel_present(self):
        response = self._get_data_quality_audit()

        self.assertContains(
            response,
            (
                "This audit checks application record completeness only. It does not "
                "analyse skill gaps, rank applications, generate documents, or update records."
            ),
        )

    def test_audit_does_not_imply_skill_gap_analysis(self):
        response = self._get_data_quality_audit()
        content = response.content.decode().lower()

        self.assertIn("no analysis has been performed", content)
        self.assertNotIn("skill extraction", content)
        self.assertNotIn("skill recommendation", content)

    def test_audit_does_not_imply_record_mutation(self):
        response = self._get_data_quality_audit()
        content = response.content.decode().lower()

        self.assertIn("no records have been changed", content)
        self.assertNotIn(">edit<", content)
        self.assertNotIn(">fix<", content)
        self.assertNotIn(">create<", content)

    def test_audit_does_not_imply_ranking_or_scoring(self):
        response = self._get_data_quality_audit()
        content = response.content.decode().lower()

        self.assertIn("does not analyse skill gaps, rank applications", content)
        self.assertNotIn("score", content)
        self.assertNotIn("ranked", content)
        self.assertNotIn("best application", content)

    def test_audit_jd_ready_boundary_note_present(self):
        response = self._get_data_quality_audit()

        self.assertContains(
            response,
            (
                "JD-ready means the record has sufficient data for future analysis. "
                "It does not indicate application quality or outcome."
            ),
        )

    def test_existing_application_list_unaffected(self):
        self.create_application(company_name="List Co", job_title="Reporting Analyst")

        response = self._get_application_list()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "List Co")
        self.assertContains(response, "Reporting Analyst")

    def test_existing_application_detail_unaffected(self):
        application = self.create_application(company_name="Detail Co", job_title="BI Analyst")

        response = self._get_application_detail(application)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Detail Co")
        self.assertContains(response, "BI Analyst")

    def test_company_job_title_duplicate_count_is_informational_only(self):
        self.create_application(
            company_name="Repeat Co",
            job_title="Data Analyst",
            job_description=self._jd_text(),
        )
        self.create_application(
            company_name="Repeat Co",
            job_title="Data Analyst",
            job_description=self._jd_text(),
        )

        response = self._get_data_quality_audit()

        self.assertEqual(response.context["company_title_duplicate_record_count"], 2)
        self.assertEqual(response.context["jd_ready_count"], 2)
        self.assertContains(response, "Company + job title repeats are informational only")

    def test_blank_job_url_does_not_disqualify_jd_ready_record(self):
        self.create_application(job_url="", job_description=self._jd_text())
        self.create_application(
            company_name="Not Ready Co",
            job_title="Data Analyst",
            job_description="Short",
        )

        response = self._get_data_quality_audit()

        self.assertEqual(response.context["jd_ready_count"], 1)
        self.assertEqual(response.context["completeness_rate"], 50)
        self.assertContains(response, "50%")

    def test_records_needing_attention_list_renders_missing_field_badges(self):
        self.create_application(company_name="", job_title="", job_description="Short")

        response = self._get_data_quality_audit()

        self.assertContains(response, "Records needing attention")
        self.assertContains(response, "Company")
        self.assertContains(response, "Job title")
        self.assertContains(response, "JD text &gt;= 750 chars")

    def test_application_list_loads_for_logged_in_user(self):
        response = self._get_application_list()
        self.assertEqual(response.status_code, 200)

    def test_application_list_phase_69c_premium_shell_renders(self):
        response = self._get_application_list()
        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn("Track every application honestly.", content)
        self.assertIn("Logged Applications", content)
        for class_name in (
            "cf69c-page",
            "cf69c-zone-hero",
            "cf69c-safety-grid",
            "cf69c-zone-snapshot",
            "cf69c-kpi-grid",
            "cf69c-filter-panel",
            "cf69c-zone-records",
        ):
            with self.subTest(class_name=class_name):
                self.assertIn(class_name, content)

    def test_application_list_phase_69c_kpi_values_render_from_saved_records(self):
        self.create_application(status=ApplicationStatus.SUBMITTED)
        self.create_application(
            company_name="Response Co",
            status=ApplicationStatus.ACKNOWLEDGED,
        )
        self.create_application(
            company_name="Interview Co",
            status=ApplicationStatus.INTERVIEW,
        )

        response = self._get_application_list()
        content = response.content.decode()

        self.assertEqual(response.context["summary"].total_applications, 3)
        self.assertIn(f">{response.context['summary'].total_applications}<", content)
        self.assertIn(f">{response.context['response_rate']}%<", content)
        self.assertIn(f">{response.context['interview_rate']}%<", content)
        self.assertIn(f">{response.context['offer_rate']}%<", content)

    def test_application_list_phase_69c_rows_render_existing_record_fields_and_view_link(self):
        application = self.create_application(
            company_name="Evidence Analytics Ltd",
            job_title="BI Analyst",
            status=ApplicationStatus.ACKNOWLEDGED,
            source=ApplicationSource.LINKEDIN,
            role_fit=RoleFit.STRONG,
            location="London",
        )

        response = self._get_application_list()
        content = response.content.decode()

        self.assertContains(response, "Evidence Analytics Ltd")
        self.assertContains(response, "BI Analyst")
        self.assertContains(response, "Acknowledged")
        self.assertContains(response, "LinkedIn")
        self.assertContains(response, date_format(application.date_applied, "DATE_FORMAT"))
        self.assertContains(response, application.get_absolute_url())
        self.assertIn(">View<", content)

    def test_application_list_phase_69c_search_query_filters_and_preserves_q_value(self):
        self.create_application(company_name="FinSight Analytics", job_title="Data Analyst")
        self.create_application(company_name="Other Co", job_title="Reporting Analyst")

        response = self._get_application_list("q=FinSight")
        content = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["table_rows"]), 1)
        self.assertContains(response, "FinSight Analytics")
        self.assertNotContains(response, "Other Co")
        self.assertIn('name="q"', content)
        self.assertIn('value="FinSight"', content)

    def test_application_list_phase_69c_status_filter_filters_and_preserves_selected_state(self):
        self.create_application(company_name="Submitted Co", status=ApplicationStatus.SUBMITTED)
        self.create_application(company_name="Interview Co", status=ApplicationStatus.INTERVIEW)

        response = self._get_application_list("status=interview")
        content = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["table_rows"]), 1)
        self.assertContains(response, "Interview Co")
        self.assertNotContains(response, "Submitted Co")
        self.assertIn('<option value="interview" selected>Interview</option>', content)

    def test_application_list_phase_69c_client_side_scan_hooks_remain(self):
        response = self._get_application_list()
        content = response.content.decode()
        self.assertIn("data-cf-client-table-filter", content)
        self.assertIn("data-cf-table-filter-input", content)
        self.assertIn("data-cf-table-filter-status", content)
        self.assertIn("Quick scan filters visible rows on this page only", content)

    def test_application_list_phase_69c_empty_state_remains_safe(self):
        response = self._get_application_list()
        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn("No applications logged yet.", content)
        self.assertIn("saved-record evidence base", content)
        self.assertIn("tracking record only", content.lower())
        self.assertIn("external application action remains manual", content)

    def test_application_list_phase_69c_manual_saved_record_wording_visible(self):
        response = self._get_application_list()
        content = response.content.decode().lower()
        self.assertIn("saved application records", content)
        self.assertIn("manual tracking workflow", content)
        self.assertIn("tracking record only", content)
        self.assertIn("no auto-apply", content)
        self.assertIn("no automatic submission", content)
        self.assertIn("no employer submission by careerfunnel", content)
        self.assertIn("application actions happen manually outside the tracker", content)
        self.assertIn("not scraped live-market data", content)
        self.assertIn("not proof of employer interaction or external verification", content)

    def test_application_list_phase_69c_unsafe_positive_action_labels_absent(self):
        response = self._get_application_list()
        content = response.content.decode()
        for label in ("Apply Now", "Submit Application", "Auto Apply", "Send Application"):
            with self.subTest(label=label):
                self.assertNotIn(f">{label}<", content)

    def test_application_list_phase_69c_no_invented_trend_or_live_data_claims(self):
        response = self._get_application_list()
        content = response.content.decode().lower()
        for phrase in (
            "% increase",
            "% decrease",
            "trending up",
            "trending down",
            "upward trend",
            "downward trend",
            "live data",
            "externally verified",
            "live saas",
            "scraped market",
        ):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, content)

    def test_application_list_phase_69c_get_does_not_mutate_application_records(self):
        self.create_application()
        before_count = JobApplication.objects.filter(user=self.user).count()

        response = self._get_application_list("q=Example&status=submitted")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(JobApplication.objects.filter(user=self.user).count(), before_count)

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

    def test_add_application_manual_save_boundary_still_present_via_prefill(self):
        self.client.login(username="aminul", password="StrongPass12345")
        application_count_before = JobApplication.objects.count()

        response = self.client.get(
            reverse("applications:application_create")
            + "?company_name=FinSight&job_title=Junior+Finance+Data+Analyst"
            + "&location=Hybrid+London&fit_score=70"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(JobApplication.objects.count(), application_count_before)
        self.assertContains(
            response,
            (
                "Pre-filling this form does not save your application. "
                "Review all fields before saving."
            ),
        )
        self.assertContains(response, "Manual review required before saving")
        self.assertContains(response, "Manual Save")
        self.assertContains(response, "Manual external submission")
        self.assertContains(
            response,
            "CareerFunnel does not submit applications automatically.",
        )

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

    def test_application_detail_page_loads_without_error(self):
        application = self.create_application()
        response = self._get_application_detail(application)

        self.assertEqual(response.status_code, 200)

    def test_application_detail_phase_69d_core_shell_renders(self):
        application = self.create_application()
        response = self._get_application_detail(application)
        content = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertIn("Application Record", content)
        self.assertIn("Application identity", content)
        for class_name in (
            "cf69d-page",
            "cf69d-zone-hero",
            "cf69d-safety-grid",
            "cf69d-zone-core",
            "cf69d-identity-grid",
            "cf69d-nav",
            "cf69d-detail-grid",
        ):
            with self.subTest(class_name=class_name):
                self.assertIn(class_name, content)

    def test_application_detail_phase_69d_core_record_fields_render(self):
        application = self.create_application(
            company_name="Evidence Analytics Ltd",
            job_title="BI Analyst",
            location="London",
            source=ApplicationSource.LINKEDIN,
            status=ApplicationStatus.ACKNOWLEDGED,
            role_fit=RoleFit.STRONG,
            job_url="https://example.com/job-reference",
        )

        response = self._get_application_detail(application)

        self.assertContains(response, "Evidence Analytics Ltd")
        self.assertContains(response, "BI Analyst")
        self.assertContains(response, "London")
        self.assertContains(response, "LinkedIn")
        self.assertContains(response, "Acknowledged")
        self.assertContains(response, "Strong")
        self.assertContains(response, "Open job post reference")
        self.assertContains(response, date_format(application.date_applied, "DATE_FORMAT"))

    def test_application_detail_phase_69d_manual_saved_record_wording_visible(self):
        application = self.create_application()
        response = self._get_application_detail(application)
        content = response.content.decode().lower()

        self.assertIn("saved application record", content)
        self.assertIn("manual tracking workflow", content)
        self.assertIn("tracking record only", content)
        self.assertIn("no auto-apply", content)
        self.assertIn("no automatic submission", content)
        self.assertIn("no employer submission by careerfunnel", content)
        self.assertIn("application actions happen manually outside the tracker", content)
        self.assertIn("not scraped live-market data", content)
        self.assertIn("not proof of employer interaction or external verification", content)

    def test_application_detail_phase_69d_unsafe_positive_action_labels_absent(self):
        application = self.create_application()
        response = self._get_application_detail(application)
        content = response.content.decode()

        for label in ("Apply Now", "Submit Application", "Auto Apply", "Send Application"):
            with self.subTest(label=label):
                self.assertNotIn(f">{label}<", content)

    def test_application_detail_phase_69d_no_invented_live_or_verification_claims(self):
        application = self.create_application()
        response = self._get_application_detail(application)
        content = response.content.decode().lower()

        for phrase in (
            "live data",
            "externally verified",
            "confirmed employer interaction",
            "automatic employer update",
            "live-market feed",
            "scraped market",
        ):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, content)

    def test_application_detail_phase_69d_internal_navigation_remains(self):
        application = self.create_application()
        response = self._get_application_detail(application)
        content = response.content.decode()

        self.assertContains(
            response,
            reverse("applications:application_update", kwargs={"pk": application.pk}),
        )
        self.assertContains(
            response,
            reverse("applications:application_delete", kwargs={"pk": application.pk}),
        )
        self.assertContains(response, reverse("applications:application_list"))
        self.assertIn(">Edit Application<", content)
        self.assertIn(">Delete<", content)
        self.assertIn(">Back<", content)

    def test_application_detail_phase_69d_get_does_not_mutate_application_records(self):
        application = self.create_application()
        before_count = JobApplication.objects.filter(user=self.user).count()

        response = self._get_application_detail(application)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(JobApplication.objects.filter(user=self.user).count(), before_count)

    def test_application_detail_phase_69d_lower_sections_still_render(self):
        application = self.create_application()
        response = self._get_application_detail(application)
        content = response.content.decode()

        for expected in (
            "Follow-Up Plan",
            "Recruiter Emails",
            "Follow-up Email Draft",
            "Role Information",
            "Application Assets",
            "Application Document Pack",
            "Required Skills",
            "Job Description",
            "Application Notes",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, content)

    def test_application_detail_phase_69d_phase2_lower_sections_have_scoped_classes(self):
        application = self.create_application()
        response = self._get_application_detail(application)
        content = response.content.decode()

        self.assertEqual(response.status_code, 200)
        for class_name in (
            "cf69d-zone-lower-safety",
            "cf69d-action-safety",
            "cf69d-followup-section",
            "cf69d-recruiter-section",
            "cf69d-followup-draft-section",
            "cf69d-role-section",
            "cf69d-assets-section",
            "cf69d-document-pack-section",
            "cf69d-notes-section",
            "cf69d-danger-zone",
        ):
            with self.subTest(class_name=class_name):
                self.assertIn(class_name, content)

    def test_application_detail_phase_69d_phase2_document_review_safety_wording_visible(self):
        application = self.create_application()
        response = self._get_application_detail(application)
        content = response.content.decode().lower()

        self.assertIn("document pack is for review/use outside the tracker", content)
        self.assertIn("manual document-review boundary", content)
        self.assertIn("saved application record", content)
        self.assertIn("manual tracking workflow", content)
        self.assertIn("tracking record only", content)
        self.assertIn("no auto-apply", content)
        self.assertIn("no automatic submission", content)
        self.assertIn("no employer submission by careerfunnel", content)
        self.assertIn("not scraped live-market data", content)
        self.assertIn("not proof of employer interaction or external verification", content)

    def test_application_detail_phase_69d_phase2_document_followup_wording_remains_safe(self):
        application = self.create_application()
        response = self._get_application_detail(application)
        content = response.content.decode()

        for expected in (
            (
                "The Document Pack stores and references your final CV and cover "
                "letter. Documents are not generated here."
            ),
            (
                "Manual review required before any employer submission - no "
                "automatic submission is used."
            ),
            "Follow-up status and dates are manual tracking fields.",
            "CareerFunnel Tracker does not send email.",
            "No recruiter emails imported yet.",
            "No CV or cover letter documents have been saved for this application yet.",
            "No notes added yet.",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, content)

    def test_application_detail_phase_69d_phase2_unsafe_positive_action_labels_absent(self):
        application = self.create_application()
        response = self._get_application_detail(application)
        content = response.content.decode()

        for label in (
            "Apply Now",
            "Submit Application",
            "Auto Apply",
            "Send Application",
            "Auto Send",
            "Auto Submit",
        ):
            with self.subTest(label=label):
                self.assertNotIn(f">{label}<", content)

    def test_application_detail_phase_69d_phase2_no_invented_document_or_live_claims(self):
        application = self.create_application()
        response = self._get_application_detail(application)
        content = response.content.decode().lower()

        for phrase in (
            "documents are automatically generated",
            "documents are automatically sent",
            "documents are externally verified",
            "confirmed employer interaction",
            "automatic employer update",
            "live-market feed",
            "scraped market",
        ):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, content)

    def test_application_detail_phase_69d_phase2_internal_navigation_remains(self):
        application = self.create_application()
        response = self._get_application_detail(application)
        content = response.content.decode()

        self.assertContains(
            response,
            reverse("applications:application_update", kwargs={"pk": application.pk}),
        )
        self.assertContains(
            response,
            reverse("applications:application_delete", kwargs={"pk": application.pk}),
        )
        self.assertContains(response, reverse("applications:application_list"))
        self.assertContains(response, reverse("recruiter_emails:import", args=[application.pk]))
        self.assertIn(">Edit Application<", content)
        self.assertIn(">Back<", content)
        self.assertIn(">Delete<", content)

    def test_application_detail_phase_69d_phase2_get_does_not_mutate_application_records(self):
        application = self.create_application()
        before_count = JobApplication.objects.filter(user=self.user).count()

        response = self._get_application_detail(application)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(JobApplication.objects.filter(user=self.user).count(), before_count)

    def test_application_detail_phase_69d_phase2_application_list_template_untouched(self):
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent.parent
        application_list_template = (
            repo_root / "templates" / "applications" / "application_list.html"
        )
        content = application_list_template.read_text(encoding="utf-8")

        self.assertIn("cf69c-page", content)
        self.assertNotIn("cf69d-", content)

    def test_application_detail_shows_document_pack_is_archive_not_generator_message(self):
        application = self.create_application()
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertContains(
            response,
            (
                "The Document Pack stores and references your final CV and cover letter. "
                "Documents are not generated here."
            ),
        )

    def test_application_detail_shows_upload_externally_reviewed_documents_message(self):
        application = self.create_application()
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertContains(
            response,
            (
                "Upload or reference your final externally reviewed CV and cover letter "
                "from your document source (e.g. ChatGPT Tailoring v3)."
            ),
        )

    def test_application_detail_shows_after_save_next_steps_message(self):
        application = self.create_application()
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertContains(
            response,
            (
                "After saving: review your application record, attach final documents, "
                "submit manually to the employer, then update your status and follow-up "
                "date here."
            ),
        )

    def test_application_detail_document_pack_does_not_claim_generation_capability(self):
        application = self.create_application()
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertContains(response, "Documents are not generated here.")
        self.assertNotContains(response, "Document Pack generates final documents")
        self.assertNotContains(response, "final documents are generated inside CareerFunnel")
        self.assertNotContains(response, "Apply Now")

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

    def test_follow_up_section_page_loads_without_error(self):
        application = self.create_application()
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="followup"')

    def test_application_detail_follow_up_section_shows_manual_send_only_message(self):
        application = self.create_application()
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertContains(
            response,
            (
                "Follow-up email drafts are for manual use only. Copy the draft and "
                "send it yourself through your email client."
            ),
        )

    def test_application_detail_mark_follow_up_sent_shows_tracking_only_message(self):
        application = self.create_application()
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertContains(
            response,
            (
                "Mark Follow-up Sent only after you have manually sent the follow-up "
                "email. This updates your tracking record only - CareerFunnel does "
                "not send emails."
            ),
        )

    def test_application_detail_follow_up_status_dates_are_manual_tracking_fields(self):
        application = self.create_application()
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertContains(
            response,
            (
                "Follow-up status and dates are manual tracking fields. They are not "
                "automatically updated from your email or the employer's system."
            ),
        )

    def test_application_detail_follow_up_does_not_imply_auto_send(self):
        application = self.create_application()
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        self.assertContains(response, "CareerFunnel does not send emails")
        self.assertNotContains(response, "CareerFunnel sends emails")
        self.assertNotContains(response, "automatically sends")
        self.assertNotContains(response, "Apply Now")
        self.assertNotContains(response, "Submit Application")

    def test_application_detail_follow_up_wording_does_not_mention_gmail_oauth_or_calendar(
        self,
    ):
        application = self.create_application()
        self.client.login(username="aminul", password="StrongPass12345")

        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

        content = response.content.decode()
        followup_status_section = content.split('<section id="followup"', 1)[1].split(
            '<section id="recruiter-emails"',
            1,
        )[0]
        followup_draft_section = content.split("<h2>Follow-up Email Draft</h2>", 1)[1].split(
            '<section id="role"',
            1,
        )[0]
        followup_content = followup_status_section + followup_draft_section
        for unsafe_text in (
            "auto-send",
            "auto sync",
            "auto-sync",
            "Gmail",
            "OAuth",
            "Calendar",
        ):
            self.assertNotIn(unsafe_text, followup_content)

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

    def test_update_form_prepopulates_date_inputs_with_iso_values(self):
        application = JobApplication.objects.create(
            user=self.user,
            company_name="Example Ltd",
            job_title="Junior Data Analyst",
            date_applied=date(2026, 6, 18),
            response_date=date(2026, 6, 20),
            follow_up_date=date(2026, 6, 25),
            last_contacted_date=date(2026, 6, 22),
        )
        update_url = reverse("applications:application_update", kwargs={"pk": application.pk})

        response = self.client.get(update_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="2026-06-18"')
        self.assertContains(response, 'value="2026-06-20"')
        self.assertContains(response, 'value="2026-06-25"')
        self.assertContains(response, 'value="2026-06-22"')


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

    def test_add_application_page_loads_without_error(self):
        response = self._get_create()
        self.assertEqual(response.status_code, 200)

    def test_add_application_manual_save_boundary_text_present(self):
        response = self._get_create()
        self.assertContains(
            response,
            (
                "Pre-filling this form does not save your application. "
                "Review all fields before saving."
            ),
        )
        self.assertContains(
            response,
            (
                "Saving creates a tracking record only. Your application has not been "
                "submitted to the employer."
            ),
        )
        self.assertContains(
            response,
            (
                "Submit your application manually through the employer's portal or job "
                "board after saving this record."
            ),
        )

    def test_add_application_prefill_advisory_text_present(self):
        response = self._get_create("company_name=FinSight")
        self.assertContains(response, "Manual review required before saving")
        self.assertContains(
            response,
            (
                "Analyze - Review - Approve - Pre-fill Add Application - Manual Save - "
                "Manual external submission. CareerFunnel does not submit applications "
                "automatically."
            ),
        )

    def test_add_application_cv_version_field_present(self):
        response = self._get_create()
        self.assertContains(response, "CV Version")
        self.assertContains(response, 'name="cv_version"')

    def test_add_application_cv_version_draft_tracking_label_present(self):
        response = self._get_create()
        self.assertContains(
            response,
            (
                "Draft - tracking record only. Final tailored CV comes from your "
                "external document source."
            ),
        )

    def test_add_application_baseline_cv_label_present(self):
        response = self._get_create()
        self.assertContains(response, "Baseline - not tailored for this role.")

    def test_add_application_cover_letter_version_field_present(self):
        response = self._get_create()
        self.assertContains(response, "Cover Letter Version")
        self.assertContains(response, 'name="cover_letter_version"')

    def test_add_application_cover_letter_version_draft_label_present(self):
        response = self._get_create()
        self.assertContains(response, "Draft - for tracking and reference only.")

    def test_add_application_save_button_is_manual_not_auto_submit(self):
        response = self._get_create()
        self.assertContains(response, "Save Application")
        self.assertNotContains(response, "Auto Save")
        self.assertNotContains(response, "auto-save")
        self.assertNotContains(response, "Submit Application")

    def test_add_application_does_not_contain_apply_now(self):
        response = self._get_create("company_name=FinSight")
        self.assertNotContains(response, "Apply Now")

    def test_add_application_does_not_contain_auto_apply(self):
        response = self._get_create("company_name=FinSight")
        page_text = response.content.decode()
        for forbidden_phrase in ("Auto Apply", "auto-apply", "auto apply"):
            self.assertNotIn(forbidden_phrase, page_text)

    def test_add_application_does_not_contain_submit_application(self):
        response = self._get_create("company_name=FinSight")
        self.assertNotContains(response, "Submit Application")
        self.assertNotContains(response, "Send Application")

    def test_add_application_shows_prefill_is_not_save_message(self):
        response = self._get_create("company_name=FinSight")
        self.assertContains(
            response,
            (
                "Pre-filling this form does not save your application. "
                "Review all fields before saving."
            ),
        )

    def test_add_application_shows_save_creates_tracking_record_only_message(self):
        response = self._get_create("company_name=FinSight")
        self.assertContains(
            response,
            (
                "Saving creates a tracking record only. Your application has not been "
                "submitted to the employer."
            ),
        )

    def test_add_application_shows_manual_external_submission_message(self):
        response = self._get_create("company_name=FinSight")
        self.assertContains(
            response,
            (
                "Submit your application manually through the employer's portal or job "
                "board after saving this record."
            ),
        )

    def test_add_application_submit_button_does_not_use_submit_application_label(self):
        response = self._get_create("company_name=FinSight")
        self.assertContains(response, "Save Application")
        self.assertNotContains(response, "Submit Application")
        self.assertNotContains(response, "Apply Now")

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

    def test_prefill_url_with_blank_company_returns_safe_default(self):
        response = self._get_create("company_name=&job_title=Junior+Data+Analyst")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"].initial.get("company_name"), "")
        self.assertNotContains(response, "Unknown Company")

    def test_prefill_url_with_blank_title_returns_safe_default(self):
        response = self._get_create("company_name=FinSight&job_title=")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"].initial.get("job_title"), "")
        self.assertNotContains(response, "Untitled Role")

    def test_prefill_url_with_blank_location_returns_safe_default(self):
        response = self._get_create("company_name=FinSight&location=")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"].initial.get("location"), "")
        self.assertNotContains(response, 'name="location" value="Remote')

    def test_prefill_url_with_all_blank_fields_does_not_crash(self):
        response = self._get_create("company_name=&job_title=&location=&fit_score=")
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertEqual(form.initial.get("company_name"), "")
        self.assertEqual(form.initial.get("job_title"), "")
        self.assertEqual(form.initial.get("location"), "")
        self.assertContains(response, "Manual review required before saving")

    def test_add_application_from_prefill_does_not_default_to_submitted(self):
        response = self._get_create("company_name=FinSight&job_title=Junior+Data+Analyst")
        self.assertEqual(
            response.context["form"].initial.get("status"),
            ApplicationStatus.SAVED_FOR_LATER,
        )
        self.assertNotEqual(
            response.context["form"].initial.get("status"),
            ApplicationStatus.SUBMITTED,
        )

    def test_add_application_from_prefill_carries_correct_fields_only(self):
        response = self._get_create(
            "company_name=FinSight&job_title=Junior+Data+Analyst"
            "&location=Hybrid+London&fit_score=80&status=submitted"
        )
        form = response.context["form"]
        self.assertEqual(form.initial.get("company_name"), "FinSight")
        self.assertEqual(form.initial.get("job_title"), "Junior Data Analyst")
        self.assertEqual(form.initial.get("location"), "Hybrid London")
        self.assertEqual(form.initial.get("role_fit"), RoleFit.STRONG)
        self.assertEqual(form.initial.get("pipeline_stage"), PipelineStage.FIT_CHECKED)
        self.assertEqual(form.initial.get("status"), ApplicationStatus.SAVED_FOR_LATER)
        self.assertNotIn("required_skills", form.initial)
        self.assertNotIn("job_description", form.initial)

    def test_add_application_form_shows_manual_workflow_helper_text(self):
        response = self._get_create("company_name=FinSight")
        self.assertContains(
            response,
            (
                "Analyze - Review - Approve - Pre-fill Add Application - Manual Save - "
                "Manual external submission. CareerFunnel does not submit applications "
                "automatically."
            ),
        )

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
        self.assertNotContains(response, "Pre-fill Add Application", html=True)

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
        self.assertContains(response, "Pre-fill Add Application", html=True)
        self.assertContains(
            response,
            (
                "Review the analysis above before continuing. Pre-filling opens the Add "
                "Application form - you must save manually. No application is submitted "
                "externally."
            ),
        )

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


class ApplicationWorkflowSafetyWordingRegressionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="workflow-safety",
            password="StrongPass12345",
        )
        self.create_url = reverse("applications:application_create")
        self.unsafe_claim_phrases = (
            "employer confirmed",
            "you are qualified",
            "job ready",
            "employer ready",
            "this proves proficiency",
            "ai verified",
            "automatically verified",
            "skill confirmed",
            "ready to apply",
            "you meet the requirements",
            "this jd signal verifies",
            "proficiency confirmed",
            "ai confirmed",
            "profile updated",
            "cv updated",
            "careerfunnel submitted your application",
            "application has been submitted",
            "application was submitted",
            "submitted to employer",
            "submitted for you",
            "sent to employer",
            "auto-applied",
            "automatically applied",
            "we applied for you",
            "careerfunnel applied",
            "production ai",
            "live ai monitoring",
        )

    def _login(self):
        self.client.login(username="workflow-safety", password="StrongPass12345")

    def _create_application(self, **overrides):
        defaults = {
            "user": self.user,
            "company_name": "Evidence Analytics Ltd",
            "job_title": "Data Analyst",
            "date_applied": date(2026, 5, 9),
        }
        defaults.update(overrides)
        return JobApplication.objects.create(**defaults)

    def _get_application_form(self, with_prefill=False):
        self._login()
        if not with_prefill:
            return self.client.get(self.create_url)
        return self.client.get(
            self.create_url,
            {
                "company_name": "FinSight",
                "job_title": "Junior Finance Data Analyst",
                "location": "Hybrid London",
                "fit_score": "70",
            },
        )

    def _get_application_detail(self):
        self._login()
        application = self._create_application(contact_email="hiring@example.com")
        return self.client.get(
            reverse("applications:application_detail", kwargs={"pk": application.pk}),
        )

    def _get_status_update(self):
        self._login()
        application = self._create_application()
        return self.client.get(
            reverse("applications:application_status_update", kwargs={"pk": application.pk}),
        )

    def _assert_unsafe_claim_phrases_absent(self, response):
        content = response.content.decode().lower()
        for phrase in self.unsafe_claim_phrases:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, content)

    def test_application_form_prefill_wording_present(self):
        response = self._get_application_form()

        self.assertContains(response, "Pre-filling this form does not save your application.")

    def test_application_form_tracking_only_wording_present(self):
        response = self._get_application_form()

        self.assertContains(response, "Saving creates a tracking record only.")

    def test_application_form_no_documents_generated_wording_present(self):
        response = self._get_application_detail()

        self.assertContains(response, "Documents are not generated here.")

    def test_application_detail_followup_manual_wording_present(self):
        response = self._get_application_detail()

        self.assertContains(response, "Follow-up email drafts are for manual use only.")

    def test_application_form_prefill_cta_label_present(self):
        response = self._get_application_form(with_prefill=True)

        self.assertContains(response, "Pre-fill Add Application")

    def test_application_form_cv_draft_label_present(self):
        response = self._get_application_form()

        self.assertContains(response, "Draft - tracking record only")

    def test_application_detail_no_auto_apply_boundary_wording_present(self):
        response = self._get_application_detail()

        self.assertContains(response, "No auto-apply and no employer submission by CareerFunnel.")

    def test_skill_gap_dashboard_advisory_wording_present(self):
        self._login()

        response = self.client.get(reverse("skills:job_ai_capability_match_report"))

        self.assertContains(response, "Skill gap signals are advisory only.")

    def test_career_intelligence_learning_recs_wording_present(self):
        self._login()

        response = self.client.get(reverse("skills:learning_recommendations_report"))

        self.assertContains(response, "Learning recommendations are planning aids.")

    def test_application_form_unsafe_claim_phrases_absent(self):
        response = self._get_application_form(with_prefill=True)

        self._assert_unsafe_claim_phrases_absent(response)

    def test_application_detail_unsafe_claim_phrases_absent(self):
        response = self._get_application_detail()

        self.assertContains(response, "No auto-apply and no employer submission by CareerFunnel.")
        self._assert_unsafe_claim_phrases_absent(response)

    def test_application_list_unsafe_claim_phrases_absent(self):
        self._login()
        self._create_application()

        response = self.client.get(reverse("applications:application_list"))

        self.assertContains(response, "No auto-apply and no employer submission by CareerFunnel.")
        self._assert_unsafe_claim_phrases_absent(response)

    def test_skill_gap_dashboard_unsafe_claim_phrases_absent(self):
        self._login()

        response = self.client.get(reverse("skills:job_ai_capability_match_report"))

        self._assert_unsafe_claim_phrases_absent(response)

    def test_data_quality_audit_unsafe_claim_phrases_absent(self):
        self._login()

        response = self.client.get(reverse("applications:application_data_quality_audit"))

        self._assert_unsafe_claim_phrases_absent(response)

    def test_status_update_form_tracking_only_wording_present(self):
        response = self._get_status_update()

        self.assertContains(response, "This updates your saved tracking record only.")

    def test_status_update_form_no_employer_update_wording_present(self):
        response = self._get_status_update()

        self.assertContains(response, "It does not update any employer system")

    def test_status_update_form_manual_review_wording_present(self):
        response = self._get_status_update()

        self.assertContains(response, "Review recruiter emails and employer messages manually")

    def test_jd_gap_aggregation_advisory_wording_present(self):
        self._login()

        response = self.client.get(reverse("applications:jd_gap_aggregation"))

        self.assertContains(response, "Skill gap signals are advisory only.")

    def test_jd_gap_aggregation_unsafe_claim_phrases_absent(self):
        self._login()

        response = self.client.get(reverse("applications:jd_gap_aggregation"))

        self._assert_unsafe_claim_phrases_absent(response)


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

    def test_evaluation_queue_page_loads_without_error(self):
        self.client.login(username="queue", password="StrongPass12345")
        response = self.client.get(self.queue_url)
        self.assertEqual(response.status_code, 200)

    def test_evaluation_queue_cv_version_column_present(self):
        JobApplication.objects.create(
            **self.base_kwargs,
            company_name="CV Column Co",
            pipeline_stage=PipelineStage.FIT_CHECKED,
        )
        self.client.login(username="queue", password="StrongPass12345")
        response = self.client.get(self.queue_url)
        self.assertContains(response, "CV Version")
        self.assertContains(
            response,
            (
                "Draft - tracking record only. Final tailored CV comes from your "
                "external document source."
            ),
        )
        self.assertContains(response, "Baseline - not tailored for this role.")

    def test_evaluation_queue_cover_letter_column_present(self):
        JobApplication.objects.create(
            **self.base_kwargs,
            company_name="Cover Column Co",
            pipeline_stage=PipelineStage.FIT_CHECKED,
        )
        self.client.login(username="queue", password="StrongPass12345")
        response = self.client.get(self.queue_url)
        self.assertContains(response, "Cover Letter")
        self.assertContains(response, "Draft - for tracking and reference only.")

    def test_evaluation_queue_shows_draft_availability_state(self):
        application = JobApplication.objects.create(
            **self.base_kwargs,
            company_name="Draft Ready Co",
            pipeline_stage=PipelineStage.FIT_CHECKED,
            cv_version=DEFAULT_CV_BASELINE_NAME,
            cover_letter_version="Draft_CL_v1",
        )
        ApplicationDocument.objects.create(
            application=application,
            document_type=DocumentType.CV,
            name="Draft Ready CV",
            content="Draft CV content.",
        )
        ApplicationDocument.objects.create(
            application=application,
            document_type=DocumentType.COVER_LETTER,
            name="Draft Ready Cover Letter",
            content="Draft cover letter content.",
        )
        self.client.login(username="queue", password="StrongPass12345")
        response = self.client.get(self.queue_url)
        self.assertContains(response, "CV draft available")
        self.assertContains(response, "Cover letter draft available")
        self.assertContains(response, "Draft Ready Co")

    def test_evaluation_queue_shows_missing_draft_state(self):
        JobApplication.objects.create(
            **self.base_kwargs,
            company_name="Missing Draft Co",
            pipeline_stage=PipelineStage.FIT_CHECKED,
        )
        self.client.login(username="queue", password="StrongPass12345")
        response = self.client.get(self.queue_url)
        self.assertContains(response, "Missing CV draft")
        self.assertContains(response, "Missing cover letter draft")
        self.assertContains(response, "No CV draft available yet")
        self.assertContains(response, "No cover letter draft available yet")

    def test_evaluation_queue_role_fit_badge_text_present(self):
        JobApplication.objects.create(
            **self.base_kwargs,
            company_name="Role Fit Co",
            pipeline_stage=PipelineStage.FIT_CHECKED,
            role_fit=RoleFit.STRONG,
        )
        self.client.login(username="queue", password="StrongPass12345")
        response = self.client.get(self.queue_url)
        self.assertContains(response, "Role Fit")
        self.assertContains(response, "Strong fit")

    def test_evaluation_queue_pipeline_stage_badge_text_present(self):
        JobApplication.objects.create(
            **self.base_kwargs,
            company_name="Pipeline Co",
            pipeline_stage=PipelineStage.FIT_CHECKED,
        )
        self.client.login(username="queue", password="StrongPass12345")
        response = self.client.get(self.queue_url)
        self.assertContains(response, "Pipeline Stage")
        self.assertContains(response, "Fit checked")

    def test_evaluation_queue_action_links_do_not_imply_external_submission(self):
        JobApplication.objects.create(
            **self.base_kwargs,
            company_name="Action Safety Co",
            pipeline_stage=PipelineStage.FIT_CHECKED,
        )
        self.client.login(username="queue", password="StrongPass12345")
        response = self.client.get(self.queue_url)
        self.assertContains(response, "View Details")
        self.assertNotContains(response, "Apply Now")
        self.assertNotContains(response, "Auto Apply")
        self.assertNotContains(response, "Submit Application")
        self.assertNotContains(response, "Send Application")

    def test_evaluation_queue_does_not_contain_apply_now(self):
        JobApplication.objects.create(
            **self.base_kwargs,
            company_name="No Unsafe Action Co",
            pipeline_stage=PipelineStage.FIT_CHECKED,
        )
        self.client.login(username="queue", password="StrongPass12345")
        response = self.client.get(self.queue_url)
        self.assertNotContains(response, "Apply Now")

    def test_evaluation_queue_does_not_contain_auto_apply(self):
        JobApplication.objects.create(
            **self.base_kwargs,
            company_name="No Automation Co",
            pipeline_stage=PipelineStage.FIT_CHECKED,
        )
        self.client.login(username="queue", password="StrongPass12345")
        response = self.client.get(self.queue_url)
        page_text = response.content.decode()
        for forbidden_phrase in ("Auto Apply", "auto-apply", "auto apply"):
            self.assertNotIn(forbidden_phrase, page_text)

    def test_evaluation_queue_does_not_contain_submit_application(self):
        JobApplication.objects.create(
            **self.base_kwargs,
            company_name="No Submit Co",
            pipeline_stage=PipelineStage.FIT_CHECKED,
        )
        self.client.login(username="queue", password="StrongPass12345")
        response = self.client.get(self.queue_url)
        self.assertNotContains(response, "Submit Application")
        self.assertNotContains(response, "Send Application")

    def test_evaluation_queue_does_not_hide_missing_cv_or_cover_letter_drafts(self):
        JobApplication.objects.create(
            **self.base_kwargs,
            company_name="Visible Missing Co",
            pipeline_stage=PipelineStage.JOB_FOUND,
        )
        self.client.login(username="queue", password="StrongPass12345")
        response = self.client.get(self.queue_url)
        self.assertContains(response, "No CV draft available yet")
        self.assertContains(response, "No cover letter draft available yet")

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

    def test_jd_gap_aggregation_sidebar_link_renders_for_logged_in_user(self):
        jd_gap_url = reverse("applications:jd_gap_aggregation")
        self.client.login(username="queue", password="StrongPass12345")

        response = self.client.get(self.queue_url)

        self.assertContains(response, "JD Gap Signals")
        self.assertContains(response, jd_gap_url)

    def test_jd_gap_aggregation_sidebar_link_not_present_for_anonymous_user(self):
        jd_gap_url = reverse("applications:jd_gap_aggregation")

        response = self.client.get(self.queue_url)
        content = response.content.decode()

        self.assertEqual(response.status_code, 302)
        self.assertNotIn("JD Gap Signals", content)
        self.assertNotIn(jd_gap_url, content)

    def test_jd_gap_aggregation_sidebar_link_does_not_imply_automation_or_scoring(self):
        self.client.login(username="queue", password="StrongPass12345")

        response = self.client.get(self.queue_url)
        content = response.content.decode()

        for unsafe_phrase in (
            "AI Gap Analysis",
            "Skill Recommendations",
            "Gap Scoring",
            "Career Gaps",
            "Missing Skills",
            "Auto",
            "Auto Apply",
            "Recommended Skills",
            "Rank",
            "Score",
        ):
            with self.subTest(unsafe_phrase=unsafe_phrase):
                self.assertNotIn(unsafe_phrase, content)


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

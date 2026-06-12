from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import Mock

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.applications.choices import (
    UPLOADED_CV_DOCUMENT_NAME,
    DocumentSource,
    DocumentStatus,
    DocumentType,
)
from apps.applications.document_uploads import attach_uploaded_document, validate_uploaded_file
from apps.applications.file_storage import get_uploaded_documents_root
from apps.applications.models import JobApplication


class DocumentUploadValidationTests(TestCase):
    def test_valid_pdf_upload_is_accepted(self):
        uploaded = SimpleUploadedFile("cv.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        extension = validate_uploaded_file(uploaded)
        self.assertEqual(extension, "pdf")

    def test_invalid_extension_is_rejected(self):
        uploaded = SimpleUploadedFile("cv.exe", b"bad", content_type="application/octet-stream")
        with self.assertRaises(ValidationError):
            validate_uploaded_file(uploaded)

    def test_path_traversal_filename_is_rejected(self):
        uploaded = Mock()
        uploaded.size = 100
        uploaded.name = "../cv.pdf"
        with self.assertRaises(ValidationError):
            validate_uploaded_file(uploaded)


@override_settings(
    UPLOADED_DOCUMENTS_ROOT=Path(__file__).resolve().parent / "test_upload_storage"
)
class DocumentUploadServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="upload-user", password="StrongPass12345")
        self.application = JobApplication.objects.create(
            user=self.user,
            company_name="Howden",
            job_title="Junior Data Analyst",
            date_applied=date(2026, 5, 31),
        )
        self.root = get_uploaded_documents_root()
        self.root.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        for path in self.root.rglob("*"):
            if path.is_file():
                path.unlink()
        for path in sorted(self.root.rglob("*"), reverse=True):
            if path.is_dir():
                path.rmdir()
        if self.root.exists():
            self.root.rmdir()

    def test_uploaded_cv_is_attached_to_application(self):
        uploaded = SimpleUploadedFile(
            "Aminul_CV.pdf",
            b"%PDF-1.4 test",
            content_type="application/pdf",
        )
        result = attach_uploaded_document(
            application=self.application,
            document_type=DocumentType.CV,
            uploaded_file=uploaded,
        )
        document = result.document
        self.assertEqual(document.name, UPLOADED_CV_DOCUMENT_NAME)
        self.assertEqual(document.source, DocumentSource.USER_UPLOAD)
        self.assertEqual(document.status, DocumentStatus.READY_FOR_MANUAL_SUBMISSION)
        self.assertTrue(
            document.uploaded_file.name.startswith(
                f"application_{self.application.pk}/cv/uploads/"
            )
        )
        self.assertTrue(Path(document.uploaded_file.path).exists())

    def test_duplicate_uploads_do_not_overwrite(self):
        first = SimpleUploadedFile("cv.pdf", b"%PDF first", content_type="application/pdf")
        second = SimpleUploadedFile("cv.pdf", b"%PDF second", content_type="application/pdf")
        doc_one = attach_uploaded_document(
            application=self.application,
            document_type=DocumentType.CV,
            uploaded_file=first,
        ).document
        doc_two = attach_uploaded_document(
            application=self.application,
            document_type=DocumentType.CV,
            uploaded_file=second,
        ).document
        self.assertNotEqual(doc_one.uploaded_file.name, doc_two.uploaded_file.name)

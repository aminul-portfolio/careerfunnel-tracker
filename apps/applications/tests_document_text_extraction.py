from __future__ import annotations

import zipfile
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, NumberObject, StreamObject

from apps.applications.choices import MAX_UPLOAD_FILE_SIZE_BYTES
from apps.applications.document_text_extraction import (
    GENERIC_NO_DRAFT_MESSAGE,
    PDF_EXTRACTION_SUCCESS_MESSAGE,
    PDF_NO_EXTRACTABLE_TEXT_MESSAGE,
    PDF_READ_ERROR_MESSAGE,
    extract_text_from_bytes,
    resolve_analysis_text,
    resolve_cover_letter_for_check,
    resolve_cv_evidence_for_analysis,
)
from apps.applications.document_uploads import validate_uploaded_file


def _make_docx_bytes(*paragraphs: str) -> bytes:
    body = "".join(
        f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"
        for text in paragraphs
    )
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body></w:document>"
    )
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", document_xml)
    return buffer.getvalue()


def _make_text_pdf_bytes(text: str) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    page = writer.pages[0]
    safe_text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream_data = f"BT /F1 12 Tf 72 720 Td ({safe_text}) Tj ET".encode("latin-1")
    content = StreamObject()
    content._data = stream_data
    content.update({NameObject("/Length"): NumberObject(len(stream_data))})
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    resources = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    page[NameObject("/Contents")] = content
    page[NameObject("/Resources")] = resources
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _make_blank_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


class DocumentTextExtractionUnitTests(TestCase):
    def test_txt_extraction_returns_text(self):
        result = extract_text_from_bytes(content=b"Hello cover letter", extension="txt")
        self.assertTrue(result.extracted)
        self.assertEqual(result.text, "Hello cover letter")
        self.assertIn("TXT", result.status_message)

    def test_docx_extraction_returns_paragraph_text(self):
        content = _make_docx_bytes("SQL reporting", "Stakeholder dashboards")
        result = extract_text_from_bytes(content=content, extension="docx")
        self.assertTrue(result.extracted)
        self.assertIn("SQL reporting", result.text)
        self.assertIn("Stakeholder dashboards", result.text)

    def test_pdf_extraction_returns_text_for_text_based_pdf(self):
        content = _make_text_pdf_bytes("Dear Howden, BakeOps KPI reporting experience.")
        result = extract_text_from_bytes(content=content, extension="pdf")
        self.assertTrue(result.extracted)
        self.assertIn("BakeOps KPI reporting experience.", result.text)
        self.assertEqual(result.status_message, PDF_EXTRACTION_SUCCESS_MESSAGE)

    def test_pdf_extraction_reports_empty_for_blank_pdf(self):
        result = extract_text_from_bytes(content=_make_blank_pdf_bytes(), extension="pdf")
        self.assertFalse(result.extracted)
        self.assertEqual(result.status, "empty")
        self.assertEqual(result.status_message, PDF_NO_EXTRACTABLE_TEXT_MESSAGE)

    def test_pdf_extraction_handles_broken_pdf_safely(self):
        result = extract_text_from_bytes(content=b"%PDF-1.4 not-a-valid-pdf", extension="pdf")
        self.assertFalse(result.extracted)
        self.assertEqual(result.status, "error")
        self.assertEqual(result.status_message, PDF_READ_ERROR_MESSAGE)

    def test_resolve_cover_letter_for_check_pdf_extracts_text(self):
        uploaded = SimpleUploadedFile(
            "letter.pdf",
            _make_text_pdf_bytes(
                "Dear Howden, I am applying for the Junior Data Analyst role. "
                "BakeOps Intelligence shows KPI reporting experience."
            ),
            content_type="application/pdf",
        )
        resolution = resolve_cover_letter_for_check(pasted_text="", uploaded_file=uploaded)
        self.assertIsNone(resolution.validation_error)
        self.assertIn("BakeOps Intelligence", resolution.text)
        self.assertEqual(resolution.status_message, PDF_EXTRACTION_SUCCESS_MESSAGE)

    def test_resolve_cover_letter_for_check_empty_pdf_is_honest(self):
        uploaded = SimpleUploadedFile(
            "letter.pdf",
            _make_blank_pdf_bytes(),
            content_type="application/pdf",
        )
        resolution = resolve_cover_letter_for_check(pasted_text="", uploaded_file=uploaded)
        self.assertEqual(resolution.validation_error, PDF_NO_EXTRACTABLE_TEXT_MESSAGE)
        self.assertNotEqual(resolution.validation_error, GENERIC_NO_DRAFT_MESSAGE)

    def test_resolve_cover_letter_for_check_empty_shows_generic(self):
        resolution = resolve_cover_letter_for_check(pasted_text="", uploaded_file=None)
        self.assertEqual(resolution.validation_error, GENERIC_NO_DRAFT_MESSAGE)

    def test_resolve_analysis_text_prefers_pasted_text(self):
        uploaded = SimpleUploadedFile("cv.txt", b"Uploaded CV text", content_type="text/plain")
        text, message = resolve_analysis_text(pasted_text="Pasted CV", uploaded_file=uploaded)
        self.assertEqual(text, "Pasted CV")
        self.assertIsNone(message)

    def test_resolve_cv_evidence_for_analysis_extracts_pdf(self):
        uploaded = SimpleUploadedFile(
            "cv.pdf",
            _make_text_pdf_bytes("Python SQL Excel stakeholder reporting"),
            content_type="application/pdf",
        )
        resolution = resolve_cv_evidence_for_analysis(pasted_text="", uploaded_file=uploaded)
        self.assertIsNone(resolution.validation_error)
        self.assertIn("Python SQL", resolution.text)

    def test_resolve_cover_letter_for_check_extracts_txt(self):
        uploaded = SimpleUploadedFile("letter.txt", b"Cover letter body", content_type="text/plain")
        resolution = resolve_cover_letter_for_check(pasted_text="", uploaded_file=uploaded)
        self.assertEqual(resolution.text, "Cover letter body")
        self.assertIn("TXT", resolution.status_message or "")
        self.assertIsNone(resolution.validation_error)

    def test_oversized_file_is_rejected(self):
        uploaded = SimpleUploadedFile(
            "large.txt",
            b"x" * (MAX_UPLOAD_FILE_SIZE_BYTES + 1),
            content_type="text/plain",
        )
        with self.assertRaises(ValidationError):
            validate_uploaded_file(uploaded)

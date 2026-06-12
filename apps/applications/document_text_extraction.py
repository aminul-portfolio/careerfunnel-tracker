from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from io import BytesIO
from typing import Literal
from xml.etree import ElementTree as ET

from django.core.files.uploadedfile import UploadedFile
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from apps.applications.file_storage import normalize_upload_extension

WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

ExtractionStatus = Literal[
    "extracted",
    "unsupported",
    "empty",
    "error",
]

GENERIC_NO_DRAFT_MESSAGE = (
    "Paste a cover letter draft or upload a TXT/DOCX/PDF file before checking."
)
GENERIC_NO_CV_MESSAGE = (
    "Paste CV text or upload a TXT/DOCX/PDF file before running the analysis."
)
PDF_EXTRACTION_SUCCESS_MESSAGE = (
    "Text extracted from uploaded PDF. Review before checking."
)
PDF_NO_EXTRACTABLE_TEXT_MESSAGE = (
    "This PDF appears to contain no extractable text. Please upload a text-based "
    "PDF, DOCX, or TXT file, or paste the text manually."
)
PDF_READ_ERROR_MESSAGE = (
    "The PDF could not be read. Please upload DOCX/TXT or paste the text manually."
)
UNSUPPORTED_FILE_MESSAGE = (
    "Unsupported file type. Please upload DOCX, TXT, or a supported PDF."
)
EXTRACTION_SUCCESS_MESSAGE = (
    "Text extracted from uploaded file. Review the draft before checking."
)


@dataclass(frozen=True)
class DocumentTextExtractionResult:
    text: str
    extension: str
    extracted: bool
    status: ExtractionStatus
    status_message: str


@dataclass(frozen=True)
class DocumentAnalysisResolution:
    text: str
    status_message: str | None
    validation_error: str | None
    extracted_from_upload: bool


CoverLetterCheckResolution = DocumentAnalysisResolution


def _extract_txt_text(content: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return content.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace").strip()


def _extract_docx_text(content: bytes) -> str:
    with zipfile.ZipFile(BytesIO(content)) as archive:
        document_xml = archive.read("word/document.xml")
    root = ET.fromstring(document_xml)
    paragraphs: list[str] = []
    for paragraph in root.iter(f"{WORD_NS}p"):
        parts = [node.text for node in paragraph.iter(f"{WORD_NS}t") if node.text]
        if parts:
            paragraphs.append("".join(parts))
    return "\n\n".join(paragraphs).strip()


def _normalize_extracted_text(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _extract_pdf_text(content: bytes) -> DocumentTextExtractionResult:
    try:
        reader = PdfReader(BytesIO(content), strict=False)
        page_parts: list[str] = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            cleaned = page_text.strip()
            if cleaned:
                page_parts.append(cleaned)
        text = _normalize_extracted_text("\n\n".join(page_parts))
        if text:
            return DocumentTextExtractionResult(
                text=text,
                extension="pdf",
                extracted=True,
                status="extracted",
                status_message=PDF_EXTRACTION_SUCCESS_MESSAGE,
            )
        return DocumentTextExtractionResult(
            text="",
            extension="pdf",
            extracted=False,
            status="empty",
            status_message=PDF_NO_EXTRACTABLE_TEXT_MESSAGE,
        )
    except (PdfReadError, ValueError, OSError):
        return DocumentTextExtractionResult(
            text="",
            extension="pdf",
            extracted=False,
            status="error",
            status_message=PDF_READ_ERROR_MESSAGE,
        )


def extract_text_from_bytes(*, content: bytes, extension: str) -> DocumentTextExtractionResult:
    normalized = normalize_upload_extension(extension)
    if normalized == "txt":
        text = _extract_txt_text(content)
        if text:
            return DocumentTextExtractionResult(
                text=text,
                extension=normalized,
                extracted=True,
                status="extracted",
                status_message="Text extracted from TXT. Edit before checking.",
            )
        return DocumentTextExtractionResult(
            text="",
            extension=normalized,
            extracted=False,
            status="empty",
            status_message="TXT uploaded, but no readable text was found. Paste text manually.",
        )
    if normalized == "docx":
        try:
            text = _extract_docx_text(content)
        except (KeyError, zipfile.BadZipFile, ET.ParseError):
            return DocumentTextExtractionResult(
                text="",
                extension=normalized,
                extracted=False,
                status="error",
                status_message=(
                    "DOCX uploaded, but text extraction failed. Paste the cover letter or "
                    "CV text manually."
                ),
            )
        if text:
            return DocumentTextExtractionResult(
                text=text,
                extension=normalized,
                extracted=True,
                status="extracted",
                status_message="Text extracted from DOCX. Edit before checking.",
            )
        return DocumentTextExtractionResult(
            text="",
            extension=normalized,
            extracted=False,
            status="empty",
            status_message="DOCX uploaded, but no paragraph text was found. Paste text manually.",
        )
    if normalized == "pdf":
        return _extract_pdf_text(content)
    return DocumentTextExtractionResult(
        text="",
        extension=normalized,
        extracted=False,
        status="unsupported",
        status_message=UNSUPPORTED_FILE_MESSAGE,
    )


def extract_text_from_uploaded_file(uploaded_file: UploadedFile) -> DocumentTextExtractionResult:
    extension = normalize_upload_extension(uploaded_file.name.rsplit(".", 1)[-1])
    uploaded_file.seek(0)
    content = uploaded_file.read()
    uploaded_file.seek(0)
    return extract_text_from_bytes(content=content, extension=extension)


def resolve_document_for_analysis(
    *,
    pasted_text: str,
    uploaded_file: UploadedFile | None,
    empty_message: str,
) -> DocumentAnalysisResolution:
    cleaned_pasted = (pasted_text or "").strip()
    if cleaned_pasted:
        return DocumentAnalysisResolution(
            text=cleaned_pasted,
            status_message=None,
            validation_error=None,
            extracted_from_upload=False,
        )
    if uploaded_file is None:
        return DocumentAnalysisResolution(
            text="",
            status_message=None,
            validation_error=empty_message,
            extracted_from_upload=False,
        )

    extraction = extract_text_from_uploaded_file(uploaded_file)
    if extraction.extracted and extraction.text:
        return DocumentAnalysisResolution(
            text=extraction.text,
            status_message=extraction.status_message,
            validation_error=None,
            extracted_from_upload=True,
        )
    if extraction.status == "unsupported":
        return DocumentAnalysisResolution(
            text="",
            status_message=extraction.status_message,
            validation_error=UNSUPPORTED_FILE_MESSAGE,
            extracted_from_upload=False,
        )
    return DocumentAnalysisResolution(
        text="",
        status_message=extraction.status_message,
        validation_error=extraction.status_message,
        extracted_from_upload=False,
    )


def resolve_cover_letter_for_check(
    *,
    pasted_text: str,
    uploaded_file: UploadedFile | None,
) -> DocumentAnalysisResolution:
    return resolve_document_for_analysis(
        pasted_text=pasted_text,
        uploaded_file=uploaded_file,
        empty_message=GENERIC_NO_DRAFT_MESSAGE,
    )


def resolve_cv_evidence_for_analysis(
    *,
    pasted_text: str,
    uploaded_file: UploadedFile | None,
) -> DocumentAnalysisResolution:
    return resolve_document_for_analysis(
        pasted_text=pasted_text,
        uploaded_file=uploaded_file,
        empty_message=GENERIC_NO_CV_MESSAGE,
    )


def resolve_analysis_text(
    *,
    pasted_text: str,
    uploaded_file: UploadedFile | None,
) -> tuple[str, str | None]:
    resolution = resolve_cv_evidence_for_analysis(
        pasted_text=pasted_text,
        uploaded_file=uploaded_file,
    )
    return resolution.text, resolution.status_message

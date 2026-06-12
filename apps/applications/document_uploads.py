from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.utils import timezone

from apps.applications.choices import (
    ALLOWED_UPLOAD_EXTENSIONS,
    MAX_UPLOAD_FILE_SIZE_BYTES,
    UPLOADED_COVER_LETTER_DOCUMENT_NAME,
    UPLOADED_CV_DOCUMENT_NAME,
    DocumentSource,
    DocumentStatus,
    DocumentType,
)
from apps.applications.document_text_extraction import (
    DocumentTextExtractionResult,
    extract_text_from_uploaded_file,
)
from apps.applications.file_storage import normalize_upload_extension
from apps.applications.models import ApplicationDocument, JobApplication

TEXT_EXTRACTION_NOT_IMPLEMENTED_MESSAGE = (
    "File uploaded. Text extraction is not yet implemented; paste CV or cover letter "
    "text for analysis."
)

PDF_UPLOAD_STATUS_MESSAGE = (
    "PDF uploaded and saved for manual review. No extractable text was found; "
    "paste the document text to run a check or analysis."
)


@dataclass(frozen=True)
class UploadedDocumentResult:
    document: ApplicationDocument
    message: str


def validate_uploaded_file(uploaded_file: UploadedFile) -> str:
    if uploaded_file is None:
        raise ValidationError("No file was uploaded.")
    if uploaded_file.size > MAX_UPLOAD_FILE_SIZE_BYTES:
        raise ValidationError("Uploaded file exceeds the 5MB size limit.")
    extension = normalize_upload_extension(uploaded_file.name.rsplit(".", 1)[-1])
    if extension not in ALLOWED_UPLOAD_EXTENSIONS:
        raise ValidationError("Unsupported file type. Please upload DOCX, TXT, or a supported PDF.")
    original_name = (uploaded_file.name or "").strip()
    if ".." in original_name or "/" in original_name or "\\" in original_name:
        raise ValidationError("Uploaded filename is not allowed.")
    return extension


def _document_display_name(document_type: str) -> str:
    if document_type == DocumentType.CV:
        return UPLOADED_CV_DOCUMENT_NAME
    return UPLOADED_COVER_LETTER_DOCUMENT_NAME


def attach_uploaded_document(
    *,
    application: JobApplication,
    document_type: str,
    uploaded_file: UploadedFile,
    content: str = "",
) -> UploadedDocumentResult:
    validate_uploaded_file(uploaded_file)
    document = ApplicationDocument(
        application=application,
        document_type=document_type,
        name=_document_display_name(document_type),
        status=DocumentStatus.READY_FOR_MANUAL_SUBMISSION,
        source=DocumentSource.USER_UPLOAD,
        content=(content or "").strip(),
        claim_safety_notes=(
            "User-uploaded finalized document. Review manually before submission."
        ),
        original_filename=(uploaded_file.name or "").strip(),
        file_size=uploaded_file.size,
        uploaded_at=timezone.now(),
    )
    document.save()
    document.uploaded_file.save(uploaded_file.name, uploaded_file, save=True)
    if content.strip():
        message = "Uploaded document saved with extracted text for manual review."
    elif normalize_upload_extension(uploaded_file.name.rsplit(".", 1)[-1]) == "pdf":
        message = PDF_UPLOAD_STATUS_MESSAGE
    else:
        message = TEXT_EXTRACTION_NOT_IMPLEMENTED_MESSAGE
    return UploadedDocumentResult(
        document=document,
        message=message,
    )


def extract_uploaded_document_text(uploaded_file: UploadedFile) -> DocumentTextExtractionResult:
    validate_uploaded_file(uploaded_file)
    return extract_text_from_uploaded_file(uploaded_file)


def attach_text_document(
    *,
    application: JobApplication,
    document_type: str,
    content: str,
    name: str | None = None,
) -> ApplicationDocument:
    cleaned = (content or "").strip()
    if not cleaned:
        raise ValidationError("Document content is required.")
    return ApplicationDocument.objects.create(
        application=application,
        document_type=document_type,
        name=name or _document_display_name(document_type),
        status=DocumentStatus.READY_FOR_MANUAL_SUBMISSION,
        source=DocumentSource.USER_UPLOAD,
        content=cleaned,
        claim_safety_notes=(
            "Rule-based adjusted document saved for manual review before submission."
        ),
        uploaded_at=timezone.now(),
    )

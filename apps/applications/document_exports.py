from __future__ import annotations

import zipfile
from dataclasses import dataclass
from io import BytesIO
from xml.sax.saxutils import escape

from apps.applications.choices import DocumentType
from apps.applications.file_storage import (
    build_professional_cover_letter_download_filename,
    build_professional_cv_download_filename,
    build_safe_generated_filename,
)
from apps.applications.file_storage import (
    sanitize_filename_part as _sanitize_filename_part,
)
from apps.applications.models import ApplicationDocument

MANUAL_REVIEW_DISCLAIMER = (
    "Draft/manual-review document generated from saved CareerFunnel Tracker records. "
    "Review before use. No automatic submission is performed."
)

DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
PDF_CONTENT_TYPE = "application/pdf"


@dataclass(frozen=True)
class ApplicationDocumentExportContext:
    document_title: str
    document_type: str
    application_company: str
    application_role: str
    status: str
    source: str
    content: str
    tailoring_notes: str
    project_evidence: str
    claim_safety_notes: str
    quick_call_notes: str
    manual_review_disclaimer: str


def build_application_document_download_filename(
    document: ApplicationDocument,
    extension: str,
) -> str:
    application = document.application
    company_name = application.company_name if application else ""
    job_title = application.job_title if application else ""
    if document.document_type == DocumentType.CV:
        reference_date = application.date_applied if application else None
        return build_professional_cv_download_filename(
            company_name,
            job_title,
            extension,
            download_date=reference_date,
        )
    if document.document_type == DocumentType.COVER_LETTER:
        reference_date = application.date_applied if application else None
        return build_professional_cover_letter_download_filename(
            company_name,
            job_title,
            extension,
            download_date=reference_date,
        )
    safe_name = _sanitize_filename_part(document.name)
    return build_safe_generated_filename(safe_name, extension)


def build_application_document_export_context(
    document: ApplicationDocument,
) -> ApplicationDocumentExportContext:
    application = document.application
    return ApplicationDocumentExportContext(
        document_title=document.name,
        document_type=document.get_document_type_display(),
        application_company=application.company_name or "Not specified",
        application_role=application.job_title or "Not specified",
        status=document.get_status_display(),
        source=document.get_source_display(),
        content=document.content or "Not saved.",
        tailoring_notes=document.tailoring_notes or "Not saved.",
        project_evidence=document.project_evidence or "Not saved.",
        claim_safety_notes=document.claim_safety_notes or "Not saved.",
        quick_call_notes=document.quick_call_notes or "Not saved.",
        manual_review_disclaimer=MANUAL_REVIEW_DISCLAIMER,
    )


def _employer_facing_export_lines(context: ApplicationDocumentExportContext) -> list[str]:
    """Return only saved employer-facing document body lines for download."""
    content = (context.content or "").strip()
    if not content or content == "Not saved.":
        return ["Not saved."]
    return content.splitlines()


def _export_lines(context: ApplicationDocumentExportContext) -> list[str]:
    return _employer_facing_export_lines(context)


def _docx_paragraph(text: str) -> str:
    escaped = escape(text).replace("\t", "    ")
    return (
        "<w:p>"
        '<w:r><w:t xml:space="preserve">'
        f"{escaped}</w:t></w:r>"
        "</w:p>"
    )


def render_text_lines_docx(lines: list[str]) -> bytes:
    body = "".join(_docx_paragraph(line) for line in lines)
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body>"
        "</w:document>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    package_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/>'
        "</Relationships>"
    )
    word_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'
    )

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", package_rels)
        archive.writestr("word/document.xml", document_xml)
        archive.writestr("word/_rels/document.xml.rels", word_rels)
    return buffer.getvalue()


def render_application_document_docx(document: ApplicationDocument) -> bytes:
    from apps.applications.professional_exports import render_application_document_bytes

    return render_application_document_bytes(document, "docx")


def _pdf_escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )


def _pdf_safe_line(text: str) -> str:
    return _pdf_escape(text.encode("latin-1", errors="replace").decode("latin-1"))


def render_text_lines_pdf(lines: list[str]) -> bytes:
    stream_commands = ["BT", "/F1 11 Tf", "14 TL", "50 780 Td"]
    for line in lines:
        stream_commands.append(f"({_pdf_safe_line(line)}) Tj")
        stream_commands.append("T*")
    stream_commands.append("ET")
    stream = "\n".join(stream_commands).encode("latin-1")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
    ]

    pdf = BytesIO()
    pdf.write(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(pdf.tell())
        pdf.write(f"{index} 0 obj\n".encode("ascii"))
        pdf.write(obj)
        pdf.write(b"\nendobj\n")

    xref_start = pdf.tell()
    pdf.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.write(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.write(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF\n"
        ).encode("ascii")
    )
    return pdf.getvalue()


def render_application_document_pdf(document: ApplicationDocument) -> bytes:
    from apps.applications.professional_exports import render_application_document_bytes

    return render_application_document_bytes(document, "pdf")


def render_plain_text_docx(text: str) -> bytes:
    lines = (text or "").splitlines() or [""]
    return render_text_lines_docx(lines)


def render_plain_text_pdf(text: str) -> bytes:
    lines = (text or "").splitlines() or [""]
    return render_text_lines_pdf(lines)


def uploaded_file_extension(document: ApplicationDocument) -> str:
    if not document.uploaded_file:
        return ""
    return document.uploaded_file.name.rsplit(".", 1)[-1].lower()


def render_application_document_download_bytes(
    document: ApplicationDocument,
    file_format: str,
) -> bytes:
    normalized_format = file_format.lower()
    if document.uploaded_file:
        stored_extension = uploaded_file_extension(document)
        if normalized_format == stored_extension:
            with document.uploaded_file.open("rb") as handle:
                return handle.read()
    if normalized_format == "docx":
        return render_application_document_docx(document)
    if normalized_format == "pdf":
        return render_application_document_pdf(document)
    raise ValueError("Unsupported download format.")

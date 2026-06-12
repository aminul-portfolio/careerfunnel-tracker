from __future__ import annotations

import zipfile
from dataclasses import dataclass
from io import BytesIO
from xml.sax.saxutils import escape

from apps.applications import master_cv as master_cv_files
from apps.applications.choices import DocumentType
from apps.applications.master_cv import (
    DocumentBlock,
    StructuredDocument,
    build_missing_cv_document,
    build_structured_cover_letter,
    build_structured_cv_for_export,
    build_structured_master_cv,
    is_cover_letter_layout_structured,
    is_master_cv_layout_structured,
)
from apps.applications.models import ApplicationDocument

DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
PDF_CONTENT_TYPE = "application/pdf"

DOCX_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

# Master CV layout tuned for a readable two-page application-ready CV.
CV_MARGIN_TOP = 620
CV_MARGIN_RIGHT = 720
CV_MARGIN_BOTTOM = 600
CV_MARGIN_LEFT = 720

CV_FONT_NAME = 30  # 15pt
CV_FONT_SECTION = 22  # 11pt
CV_FONT_BODY = 21  # 10.5pt
CV_FONT_CONTACT = 20  # 10pt

CV_PAGE2_SECTION = "PORTFOLIO PROJECTS"

PDF_TOP_Y = 748
PDF_BOTTOM_Y = 52
PDF_MARGIN_X = 36
PDF_WRAP_CHARS = 92

CL_MARGIN_TOP = 620
CL_MARGIN_RIGHT = 720
CL_MARGIN_BOTTOM = 600
CL_MARGIN_LEFT = 720


def _uses_compact_layout(document: StructuredDocument) -> bool:
    return is_master_cv_layout_structured(document) or is_cover_letter_layout_structured(
        document
    )


def _is_compact_master_cv(document: StructuredDocument) -> bool:
    return is_master_cv_layout_structured(document)


def _is_cover_letter_layout(document: StructuredDocument) -> bool:
    return is_cover_letter_layout_structured(document)


def _docx_run(text: str, *, bold: bool = False, size_half_points: int = CV_FONT_BODY) -> str:
    escaped = escape(text).replace("\t", "    ")
    bold_xml = "<w:b/>" if bold else ""
    return (
        "<w:r>"
        f"<w:rPr>{bold_xml}<w:sz w:val=\"{size_half_points}\"/></w:rPr>"
        f"<w:t xml:space=\"preserve\">{escaped}</w:t>"
        "</w:r>"
    )


def _docx_ppr(
    *,
    spacing_before: int = 0,
    spacing_after: int = 0,
    line: int = 0,
    indent_left: int = 0,
    hanging: int = 0,
    center: bool = False,
    section_border: bool = False,
) -> str:
    parts: list[str] = []
    spacing_attrs = []
    if spacing_before:
        spacing_attrs.append(f'w:before="{spacing_before}"')
    if spacing_after:
        spacing_attrs.append(f'w:after="{spacing_after}"')
    if line:
        spacing_attrs.append(f'w:line="{line}"')
        spacing_attrs.append('w:lineRule="auto"')
    if spacing_attrs:
        parts.append(f"<w:spacing {' '.join(spacing_attrs)}/>")
    if indent_left or hanging:
        ind_attrs = []
        if indent_left:
            ind_attrs.append(f'w:left="{indent_left}"')
        if hanging:
            ind_attrs.append(f'w:hanging="{hanging}"')
        parts.append(f"<w:ind {' '.join(ind_attrs)}/>")
    if center:
        parts.append('<w:jc w:val="center"/>')
    if section_border:
        parts.append(
            '<w:pBdr><w:bottom w:val="single" w:sz="4" w:space="1" w:color="CBD5E1"/></w:pBdr>'
        )
    return f"<w:pPr>{''.join(parts)}</w:pPr>" if parts else ""


def _docx_paragraph(
    text: str,
    *,
    bold: bool = False,
    size_half_points: int = CV_FONT_BODY,
    spacing_before: int = 0,
    spacing_after: int = 0,
    line: int = 0,
    indent_left: int = 0,
    hanging: int = 0,
    center: bool = False,
    section_border: bool = False,
) -> str:
    ppr = _docx_ppr(
        spacing_before=spacing_before,
        spacing_after=spacing_after,
        line=line,
        indent_left=indent_left,
        hanging=hanging,
        center=center,
        section_border=section_border,
    )
    return (
        "<w:p>"
        f"{ppr}"
        f"{_docx_run(text, bold=bold, size_half_points=size_half_points)}"
        "</w:p>"
    )


def _docx_bullet_paragraph(text: str) -> str:
    ppr = _docx_ppr(spacing_after=22, line=250, indent_left=220, hanging=165)
    bullet_run = _docx_run("-", size_half_points=CV_FONT_BODY)
    text_run = _docx_run(f" {text}", size_half_points=CV_FONT_BODY)
    return f"<w:p>{ppr}{bullet_run}{text_run}</w:p>"


def _docx_page_break() -> str:
    return "<w:p><w:r><w:br w:type=\"page\"/></w:r></w:p>"


def _docx_sect_pr(*, compact: bool, cover_letter: bool = False) -> str:
    if not compact and not cover_letter:
        return ""
    top = CL_MARGIN_TOP if cover_letter else CV_MARGIN_TOP
    right = CL_MARGIN_RIGHT if cover_letter else CV_MARGIN_RIGHT
    bottom = CL_MARGIN_BOTTOM if cover_letter else CV_MARGIN_BOTTOM
    left = CL_MARGIN_LEFT if cover_letter else CV_MARGIN_LEFT
    return (
        f"<w:sectPr>"
        f'<w:pgSz w:w="12240" w:h="15840"/>'
        f'<w:pgMar w:top="{top}" w:right="{right}" '
        f'w:bottom="{bottom}" w:left="{left}" '
        f'w:header="0" w:footer="0" w:gutter="0"/>'
        f"</w:sectPr>"
    )


def render_structured_document_docx(document: StructuredDocument) -> bytes:
    compact_cv = _is_compact_master_cv(document)
    cover_letter = _is_cover_letter_layout(document)
    compact = compact_cv or cover_letter
    body_parts: list[str] = []
    current_section = ""
    contact_index = 0
    recipient_index = 0
    recipient_total = sum(1 for block in document.blocks if block.kind == "recipient")
    header_centered = compact and not cover_letter
    for block in document.blocks:
        if block.kind == "blank":
            if not compact:
                body_parts.append("<w:p/>")
            continue
        if block.kind == "name":
            body_parts.append(
                _docx_paragraph(
                    block.text,
                    bold=True,
                    size_half_points=CV_FONT_NAME,
                    spacing_after=0,
                    center=header_centered,
                )
            )
        elif block.kind == "headline":
            body_parts.append(
                _docx_paragraph(
                    block.text,
                    size_half_points=CV_FONT_BODY,
                    spacing_after=16 if cover_letter else (32 if compact else 40),
                    center=header_centered,
                )
            )
        elif block.kind == "contact":
            if cover_letter:
                body_parts.append(
                    _docx_paragraph(
                        block.text,
                        size_half_points=CV_FONT_CONTACT,
                        spacing_after=72,
                    )
                )
            else:
                spacing_after = 32 if contact_index == 0 else (72 if compact_cv else 56)
                contact_index += 1
                body_parts.append(
                    _docx_paragraph(
                        block.text,
                        size_half_points=CV_FONT_CONTACT,
                        spacing_after=spacing_after if compact else 40,
                        center=header_centered,
                    )
                )
        elif block.kind == "recipient":
            recipient_index += 1
            if cover_letter:
                spacing_before = 40 if recipient_index == 1 else 0
                spacing_after = 60 if recipient_index == recipient_total else 0
            else:
                spacing_before = 0
                spacing_after = 0
            body_parts.append(
                _docx_paragraph(
                    block.text,
                    size_half_points=CV_FONT_BODY,
                    spacing_before=spacing_before,
                    spacing_after=spacing_after,
                )
            )
        elif block.kind == "salutation":
            body_parts.append(
                _docx_paragraph(
                    block.text,
                    size_half_points=CV_FONT_BODY,
                    spacing_before=60 if cover_letter else 80,
                    spacing_after=100 if cover_letter else 120,
                )
            )
        elif block.kind == "closing_line":
            body_parts.append(
                _docx_paragraph(
                    block.text,
                    size_half_points=CV_FONT_BODY,
                    spacing_before=180 if cover_letter else 160,
                    spacing_after=0,
                )
            )
        elif block.kind == "closing_name":
            body_parts.append(
                _docx_paragraph(
                    block.text,
                    size_half_points=CV_FONT_BODY,
                    spacing_after=0,
                )
            )
        elif block.kind == "section":
            current_section = block.text
            if compact and block.text == CV_PAGE2_SECTION:
                body_parts.append(_docx_page_break())
            body_parts.append(
                _docx_paragraph(
                    block.text,
                    bold=True,
                    size_half_points=CV_FONT_SECTION if compact else 22,
                    spacing_before=120 if compact else 240,
                    spacing_after=28 if compact else 120,
                    section_border=compact,
                )
            )
        elif block.kind == "subheading":
            body_parts.append(
                _docx_paragraph(
                    block.text,
                    bold=True,
                    size_half_points=CV_FONT_BODY,
                    spacing_before=48 if compact else 120,
                    spacing_after=20 if compact else 60,
                )
            )
        elif block.kind == "bullet":
            if compact:
                body_parts.append(_docx_bullet_paragraph(block.text))
            else:
                body_parts.append(_docx_paragraph(f"- {block.text}", indent_left=360))
        elif block.kind == "paragraph":
            if cover_letter:
                body_parts.append(
                    _docx_paragraph(
                        block.text,
                        spacing_after=120,
                        line=276,
                    )
                )
            elif compact_cv:
                if current_section == "PROFILE":
                    after, line = 48, 252
                elif current_section == "PORTFOLIO PROJECTS":
                    after, line = 24, 0
                else:
                    after, line = 22, 0
                body_parts.append(
                    _docx_paragraph(block.text, spacing_after=after, line=line)
                )
            else:
                body_parts.append(
                    _docx_paragraph(block.text, size_half_points=22, spacing_after=80)
                )

    body = "".join(body_parts)
    sect_pr = _docx_sect_pr(compact=compact_cv, cover_letter=cover_letter)
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{DOCX_NS}">'
        f"<w:body>{body}{sect_pr}</w:body>"
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


@dataclass
class _PdfLine:
    text: str
    font_size: int
    bold: bool
    indent: int
    leading: int


@dataclass
class _PdfPage:
    lines: list[_PdfLine]


def _pdf_escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )


def _pdf_normalize_text(text: str) -> str:
    replacements = {
        "\u00a3": "GBP",
        "\u2013": "-",
        "\u2014": "-",
        "\u2022": "-",
        "\u2019": "'",
        "\u2018": "'",
    }
    normalized = text
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    return normalized


def _pdf_safe(text: str) -> str:
    normalized = _pdf_normalize_text(text)
    return _pdf_escape(normalized.encode("latin-1", errors="replace").decode("latin-1"))


def _wrap_pdf_text(text: str, *, max_chars: int) -> list[str]:
    normalized = str(text)
    words = normalized.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _block_to_pdf_lines(block: DocumentBlock, *, compact: bool) -> list[_PdfLine]:
    if block.kind == "blank":
        return []
    if block.kind == "name":
        return [_PdfLine(block.text, 15, True, 0, 16)]
    if block.kind == "headline":
        return [
            _PdfLine(line, 10.5, False, 0, 12)
            for line in _wrap_pdf_text(block.text, max_chars=PDF_WRAP_CHARS)
        ]
    if block.kind == "contact":
        return [
            _PdfLine(line, 10, False, 0, 11.5)
            for line in _wrap_pdf_text(block.text, max_chars=PDF_WRAP_CHARS)
        ]
    if block.kind == "section":
        return [_PdfLine(block.text, 11, True, 0, 14)]
    if block.kind == "subheading":
        return [
            _PdfLine(line, 10.5, True, 0, 12)
            for line in _wrap_pdf_text(block.text, max_chars=PDF_WRAP_CHARS)
        ]
    if block.kind == "bullet":
        wrapped = _wrap_pdf_text(block.text, max_chars=PDF_WRAP_CHARS - 2)
        lines: list[_PdfLine] = []
        for index, line in enumerate(wrapped):
            prefix = "- " if index == 0 else "  "
            lines.append(_PdfLine(f"{prefix}{line}", 10.5, False, 12, 11))
        return lines
    if block.kind == "paragraph":
        return [
            _PdfLine(wrapped, 10.5, False, 0, 11)
            for wrapped in _wrap_pdf_text(block.text, max_chars=PDF_WRAP_CHARS)
        ]
    return []


def _line_height(line: _PdfLine) -> float:
    return line.leading + (2 if line.bold and line.font_size >= 11 else 0)


def _balance_lines_on_page(lines: list[_PdfLine]) -> list[_PdfLine]:
    available = PDF_TOP_Y - PDF_BOTTOM_Y
    total = sum(_line_height(line) for line in lines)
    if not lines:
        return lines
    if total > available:
        scale = available / total
        return [
            _PdfLine(
                line.text,
                line.font_size,
                line.bold,
                line.indent,
                max(9.5, line.leading * scale),
            )
            for line in lines
        ]
    target = available * 0.93
    if total < target:
        scale = min(1.38, target / total)
        return [
            _PdfLine(
                line.text,
                line.font_size,
                line.bold,
                line.indent,
                min(13, line.leading * scale),
            )
            for line in lines
        ]
    return lines


def _split_master_cv_pdf_pages(
    document: StructuredDocument,
) -> tuple[list[_PdfLine], list[_PdfLine]]:
    page1: list[_PdfLine] = []
    page2: list[_PdfLine] = []
    on_page2 = False
    for block in document.blocks:
        if block.kind == "section" and block.text == CV_PAGE2_SECTION:
            on_page2 = True
        lines = _block_to_pdf_lines(block, compact=True)
        if on_page2:
            page2.extend(lines)
        else:
            page1.extend(lines)
    return page1, page2


def _paginate_pdf_lines(lines: list[_PdfLine], *, compact: bool) -> list[_PdfPage]:
    top = 756 if compact else 760
    bottom = 42 if compact else 54
    pages: list[_PdfPage] = []
    current = _PdfPage(lines=[])
    y = top
    for line in lines:
        needed = line.leading + (2 if line.bold and line.font_size >= 11 else 0)
        if y - needed < bottom and current.lines:
            pages.append(current)
            current = _PdfPage(lines=[])
            y = top
        current.lines.append(line)
        y -= needed
    if current.lines:
        pages.append(current)
    return pages or [_PdfPage(lines=[])]


def _paginate_compact_master_cv(document: StructuredDocument) -> list[_PdfPage]:
    page1_lines, page2_lines = _split_master_cv_pdf_pages(document)
    return [
        _PdfPage(lines=_balance_lines_on_page(page1_lines)),
        _PdfPage(lines=_balance_lines_on_page(page2_lines)),
    ]


def _block_to_cover_letter_pdf_lines(block: DocumentBlock) -> list[_PdfLine]:
    if block.kind == "name":
        return [_PdfLine(block.text, 15, True, 0, 16)]
    if block.kind == "headline":
        return [
            _PdfLine(line, 10.5, False, 0, 12)
            for line in _wrap_pdf_text(block.text, max_chars=PDF_WRAP_CHARS)
        ]
    if block.kind == "contact":
        return [
            _PdfLine(line, 10, False, 0, 11.5)
            for line in _wrap_pdf_text(block.text, max_chars=PDF_WRAP_CHARS)
        ]
    if block.kind == "recipient":
        return [_PdfLine(block.text, 10.5, False, 0, 12)]
    if block.kind == "salutation":
        return [_PdfLine(block.text, 10.5, False, 0, 14)]
    if block.kind == "closing_line":
        return [_PdfLine(block.text, 10.5, False, 0, 13)]
    if block.kind == "closing_name":
        return [_PdfLine(block.text, 10.5, False, 0, 12)]
    if block.kind == "paragraph":
        return [
            _PdfLine(wrapped, 10.5, False, 0, 13)
            for wrapped in _wrap_pdf_text(block.text, max_chars=PDF_WRAP_CHARS)
        ]
    return []


def _cover_letter_pdf_spacer(gap: float) -> _PdfLine:
    return _PdfLine("", 1, False, 0, gap)


def _render_cover_letter_pdf(document: StructuredDocument) -> bytes:
    lines: list[_PdfLine] = []
    prev_kind = ""
    recipient_index = 0
    for block in document.blocks:
        if block.kind == "blank":
            continue
        if block.kind == "recipient":
            recipient_index += 1
            if recipient_index == 1 and prev_kind == "contact":
                lines.append(_cover_letter_pdf_spacer(8))
        elif block.kind == "salutation" and prev_kind == "recipient":
            lines.append(_cover_letter_pdf_spacer(6))
        elif block.kind == "paragraph" and prev_kind in {"salutation", "paragraph"}:
            lines.append(_cover_letter_pdf_spacer(6))
        elif block.kind == "closing_line":
            lines.append(_cover_letter_pdf_spacer(10))
        lines.extend(_block_to_cover_letter_pdf_lines(block))
        prev_kind = block.kind
    lines = _balance_lines_on_page(lines)
    pages = [_PdfPage(lines=lines)]
    return _build_pdf_from_pages(pages, compact=True)


def _build_pdf_from_pages(pages: list[_PdfPage], *, compact: bool) -> bytes:
    objects: list[bytes] = []
    page_object_ids: list[int] = []
    content_object_ids: list[int] = []
    font_regular_id = 3 + (len(pages) * 2)
    font_bold_id = font_regular_id + 1
    margin_x = PDF_MARGIN_X if compact else 54
    top_y = PDF_TOP_Y if compact else 760

    for page_index in range(len(pages)):
        page_object_ids.append(3 + (page_index * 2))
        content_object_ids.append(4 + (page_index * 2))

    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{page_id} 0 R" for page_id in page_object_ids)
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode("latin-1"))

    for page_index, page in enumerate(pages):
        commands = ["BT"]
        y = top_y
        for line in page.lines:
            if not line.text:
                y -= line.leading
                continue
            font = "/F2" if line.bold else "/F1"
            size = line.font_size
            x = margin_x + line.indent
            commands.append(f"{font} {size} Tf")
            commands.append(f"1 0 0 1 {x} {y} Tm")
            commands.append(f"({_pdf_safe(line.text)}) Tj")
            y -= line.leading + (2 if line.bold and size >= 11 else 0)
        commands.append("ET")
        stream = "\n".join(commands).encode("latin-1")
        content_id = content_object_ids[page_index]
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 {font_regular_id} 0 R /F2 {font_bold_id} 0 R >> >> "
                f"/Contents {content_id} 0 R >>"
            ).encode("latin-1")
        )
        objects.append(
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"
        )

    objects.extend(
        [
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
        ]
    )

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


def render_structured_document_pdf(document: StructuredDocument) -> bytes:
    if _is_cover_letter_layout(document):
        return _render_cover_letter_pdf(document)
    compact = _is_compact_master_cv(document)
    if compact:
        pages = _paginate_compact_master_cv(document)
    else:
        lines = []
        for block in document.blocks:
            if block.kind != "blank":
                lines.extend(_block_to_pdf_lines(block, compact=False))
        pages = _paginate_pdf_lines(lines, compact=False)
    return _build_pdf_from_pages(pages, compact=compact)


def count_pdf_pages(pdf_bytes: bytes) -> int:
    return pdf_bytes.count(b"<< /Type /Page /Parent")


def render_structured_document_bytes(
    document: StructuredDocument,
    file_format: str,
) -> bytes:
    normalized = file_format.lower().lstrip(".")
    if normalized == "docx":
        return render_structured_document_docx(document)
    if normalized == "pdf":
        return render_structured_document_pdf(document)
    raise ValueError(f"Unsupported format: {file_format}")


def render_cv_bytes_from_structured(
    structured: StructuredDocument,
    file_format: str,
    *,
    prefer_master_file: bool = False,
) -> bytes:
    if prefer_master_file:
        master_bytes = master_cv_files.read_master_cv_file_if_available(file_format)
        if master_bytes:
            return master_bytes
    return render_structured_document_bytes(structured, file_format)


def render_application_cv_bytes(
    document: ApplicationDocument,
    file_format: str,
) -> bytes:
    content = (document.content or "").strip()
    if not content or content == "Not saved.":
        raise ValueError(master_cv_files.CV_MISSING_MESSAGE)
    structured = build_structured_cv_for_export(
        content,
        cv_baseline_name=getattr(document, "cv_baseline_name", "") or "",
        document_name=document.name or "",
    )
    from apps.applications.cv_template_exports import render_tailored_cv_bytes

    return render_tailored_cv_bytes(structured, file_format)


def render_application_cover_letter_bytes(
    document: ApplicationDocument,
    file_format: str,
) -> bytes:
    content = document.content or ""
    company = document.application.company_name if document.application_id else ""
    role = document.application.job_title if document.application_id else ""
    structured = build_structured_cover_letter(
        company_name=company,
        job_title=role,
        body=_cover_letter_body_from_saved_content(
            content,
            company_name=company,
            job_title=role,
        ),
    )
    return render_structured_document_bytes(structured, file_format)


def _cover_letter_body_from_saved_content(
    content: str,
    *,
    company_name: str = "",
    job_title: str = "",
) -> str:
    from apps.applications.master_cv import extract_cover_letter_body_for_export

    return extract_cover_letter_body_for_export(
        content,
        company_name=company_name,
        job_title=job_title,
    )


def structured_document_from_plain_lines(lines: list[str]) -> StructuredDocument:
    blocks: list[DocumentBlock] = []
    section_titles = {
        "CareerFunnel Tracker Application Pack",
        "Cover letter text",
        "Best evidence / portfolio projects",
        "Claim-safety notes",
    }
    for line in lines:
        stripped = line.strip()
        if not stripped:
            blocks.append(DocumentBlock("blank"))
            continue
        if stripped in section_titles or stripped.startswith("Draft/manual-review"):
            blocks.append(DocumentBlock("section", stripped))
        elif stripped.startswith("- "):
            blocks.append(DocumentBlock("bullet", stripped[2:].strip()))
        else:
            blocks.append(DocumentBlock("paragraph", stripped))
    return StructuredDocument(blocks=tuple(blocks))


def render_application_pack_bytes(pack_text: str, file_format: str) -> bytes:
    structured = structured_document_from_plain_lines(pack_text.splitlines())
    return render_structured_document_bytes(structured, file_format)


def render_cv_bytes_from_draft_fields(
    *,
    profile_angle: str,
    skills_to_prioritise: tuple[str, ...],
    file_format: str,
    project_bullets: dict[str, tuple[str, ...]] | None = None,
) -> bytes:
    structured = build_structured_master_cv(
        profile_angle=profile_angle,
        skills_to_prioritise=skills_to_prioritise,
        project_bullets=project_bullets,
    )
    from apps.applications.cv_template_exports import render_tailored_cv_bytes

    return render_tailored_cv_bytes(structured, file_format)


def render_cover_letter_bytes_from_fields(
    *,
    company_name: str,
    job_title: str,
    body: str,
    file_format: str,
) -> bytes:
    structured = build_structured_cover_letter(
        company_name=company_name,
        job_title=job_title,
        body=body,
    )
    return render_structured_document_bytes(structured, file_format)


def render_missing_cv_bytes(file_format: str) -> bytes:
    structured = build_missing_cv_document(master_cv_files.CV_MISSING_MESSAGE)
    return render_structured_document_bytes(structured, file_format)


def render_application_document_bytes(
    document: ApplicationDocument,
    file_format: str,
) -> bytes:
    if document.document_type == DocumentType.CV:
        return render_application_cv_bytes(document, file_format)
    if document.document_type == DocumentType.COVER_LETTER:
        return render_application_cover_letter_bytes(document, file_format)
    structured = structured_document_from_plain_lines(
        (document.content or "Not saved.").splitlines()
    )
    return render_structured_document_bytes(structured, file_format)

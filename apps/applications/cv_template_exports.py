from __future__ import annotations

import re
import zipfile
from io import BytesIO
from xml.sax.saxutils import escape

from apps.applications import master_cv as master_cv_files
from apps.applications.master_cv import (
    StructuredDocument,
    build_structured_master_cv,
    is_master_cv_layout_structured,
)

STRUCTURED_RENDERER_FALLBACK = (
    "Structured CV renderer fallback used when master template file is unavailable."
)

_WT_TEXT_RE = re.compile(r'(<w:t(?:\s+xml:space="preserve")?>)(.*?)(</w:t>)', re.DOTALL)
_PARAGRAPH_RE = re.compile(r"(<w:p\b.*?</w:p>)", re.DOTALL)


def _paragraph_plain_text(paragraph_xml: str) -> str:
    return "".join(match.group(2) for match in _WT_TEXT_RE.finditer(paragraph_xml))


def _set_paragraph_text(paragraph_xml: str, new_text: str) -> str:
    escaped = escape(new_text)
    matches = list(_WT_TEXT_RE.finditer(paragraph_xml))
    if not matches:
        return paragraph_xml
    first = matches[0]
    updated = (
        paragraph_xml[: first.start(2)]
        + escaped
        + paragraph_xml[first.end(2) :]
    )
    for match in reversed(matches[1:]):
        updated = updated[: match.start(2)] + updated[match.end(2) :]
    return updated


def _replace_paragraph_containing(
    document_xml: str,
    marker: str,
    new_text: str,
) -> str:
    if not marker or not new_text:
        return document_xml
    updated = document_xml
    for match in _PARAGRAPH_RE.finditer(document_xml):
        paragraph = match.group(1)
        plain = _paragraph_plain_text(paragraph)
        if marker not in plain:
            continue
        if plain.strip() == new_text.strip():
            return updated
        replacement = _set_paragraph_text(paragraph, new_text)
        return updated[: match.start()] + replacement + updated[match.end() :]
    return updated


def _replace_paragraph_starting_with(
    document_xml: str,
    prefix: str,
    new_text: str,
) -> str:
    if not prefix or not new_text:
        return document_xml
    for match in _PARAGRAPH_RE.finditer(document_xml):
        paragraph = match.group(1)
        plain = _paragraph_plain_text(paragraph)
        if not plain.strip().startswith(prefix):
            continue
        if plain.strip() == new_text.strip():
            return document_xml
        replacement = _set_paragraph_text(paragraph, new_text)
        return document_xml[: match.start()] + replacement + document_xml[match.end() :]
    return document_xml


def _first_paragraph_in_section(document: StructuredDocument, section: str) -> str:
    capturing = False
    for block in document.blocks:
        if block.kind == "section":
            capturing = block.text == section
            continue
        if capturing and block.kind == "paragraph":
            return block.text
    return ""


def _paragraphs_in_section(document: StructuredDocument, section: str) -> tuple[str, ...]:
    capturing = False
    paragraphs: list[str] = []
    for block in document.blocks:
        if block.kind == "section":
            if capturing:
                break
            capturing = block.text == section
            continue
        if capturing and block.kind == "paragraph":
            paragraphs.append(block.text)
    return tuple(paragraphs)


def _careerfunnel_bullets(document: StructuredDocument) -> tuple[str, ...]:
    capturing = False
    in_careerfunnel = False
    bullets: list[str] = []
    for block in document.blocks:
        if block.kind == "section":
            capturing = block.text == "PORTFOLIO PROJECTS"
            in_careerfunnel = False
            continue
        if not capturing:
            continue
        if block.kind == "subheading" and "CareerFunnel Tracker" in block.text:
            in_careerfunnel = True
            continue
        if block.kind == "subheading" and in_careerfunnel:
            break
        if in_careerfunnel and block.kind == "bullet":
            bullets.append(block.text)
    return tuple(bullets)


def build_master_cv_replacement_map(tailored: StructuredDocument) -> dict[str, str]:
    """Map baseline master CV text fragments to tailored replacements."""
    baseline = build_structured_master_cv()
    replacements: dict[str, str] = {}

    base_profile = _first_paragraph_in_section(baseline, "PROFILE")
    tailored_profile = _first_paragraph_in_section(tailored, "PROFILE")
    if base_profile and tailored_profile and base_profile != tailored_profile:
        replacements[base_profile] = tailored_profile

    for base_text, tailored_text in zip(
        _paragraphs_in_section(baseline, "TECHNICAL SKILLS"),
        _paragraphs_in_section(tailored, "TECHNICAL SKILLS"),
    ):
        if base_text != tailored_text:
            replacements[base_text] = tailored_text

    for base_text, tailored_text in zip(
        _careerfunnel_bullets(baseline),
        _careerfunnel_bullets(tailored),
    ):
        if base_text != tailored_text:
            replacements[base_text] = tailored_text

    return {
        old: new
        for old, new in replacements.items()
        if old and new and old != new
    }


def apply_tailored_sections_to_master_docx_xml(
    document_xml: str,
    tailored: StructuredDocument,
) -> str:
    """Replace only tailored sections while preserving template layout XML."""
    updated = document_xml

    profile = _first_paragraph_in_section(tailored, "PROFILE")
    if profile:
        updated = _replace_paragraph_containing(updated, "Data Analyst candidate", profile)

    for paragraph in _paragraphs_in_section(tailored, "TECHNICAL SKILLS"):
        prefix = paragraph.split(":", 1)[0]
        updated = _replace_paragraph_starting_with(updated, prefix, paragraph)

    for bullet in _careerfunnel_bullets(tailored):
        if "771 automated tests" in bullet:
            updated = _replace_paragraph_containing(updated, "771 automated tests", bullet)
        elif "Application Document Pack workflow" in bullet:
            updated = _replace_paragraph_containing(
                updated,
                "Application Document Pack",
                bullet,
            )
        elif "skill-gap tracking" in bullet:
            updated = _replace_paragraph_containing(updated, "skill-gap tracking", bullet)

    for old, new in build_master_cv_replacement_map(tailored).items():
        if old in updated:
            updated = updated.replace(old, escape(new))
        else:
            marker = old[: min(48, len(old))]
            if marker:
                updated = _replace_paragraph_containing(updated, marker, new)

    return updated


def render_tailored_cv_docx_from_template(
    template_bytes: bytes,
    tailored: StructuredDocument,
) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(BytesIO(template_bytes), "r") as source:
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as target:
            for info in source.infolist():
                data = source.read(info.filename)
                if info.filename == "word/document.xml":
                    document_xml = data.decode("utf-8")
                    document_xml = apply_tailored_sections_to_master_docx_xml(
                        document_xml,
                        tailored,
                    )
                    data = document_xml.encode("utf-8")
                target.writestr(info, data)
    return buffer.getvalue()


def _apply_replacements_to_pdf_template(
    template_bytes: bytes,
    replacements: dict[str, str],
) -> bytes | None:
    if not replacements:
        return template_bytes
    updated = template_bytes
    for old, new in replacements.items():
        old_bytes = old.encode("latin-1", errors="ignore")
        new_bytes = new.encode("latin-1", errors="ignore")
        if old_bytes in updated:
            updated = updated.replace(old_bytes, new_bytes, 1)
            continue
        marker = old[: min(48, len(old))].encode("latin-1", errors="ignore")
        if marker and marker in updated:
            updated = updated.replace(marker, new_bytes, 1)
    return updated if updated != template_bytes else template_bytes


def render_tailored_cv_bytes(
    tailored: StructuredDocument,
    file_format: str,
) -> bytes:
    """Render tailored CV using master template when available, else structured fallback."""
    normalized = file_format.lower().lstrip(".")
    if is_master_cv_layout_structured(tailored):
        template_bytes = master_cv_files.read_master_cv_template_if_available(normalized)
        if template_bytes:
            if normalized == "docx":
                return render_tailored_cv_docx_from_template(template_bytes, tailored)
            if normalized == "pdf":
                replacements = build_master_cv_replacement_map(tailored)
                pdf_bytes = _apply_replacements_to_pdf_template(template_bytes, replacements)
                if pdf_bytes is not None:
                    return pdf_bytes

    from apps.applications.professional_exports import render_structured_document_bytes

    return render_structured_document_bytes(tailored, normalized)


def render_tailored_cv_pdf_with_fallback_note(tailored: StructuredDocument) -> tuple[bytes, str]:
    """Return PDF bytes and a note describing whether template or fallback was used."""
    template_bytes = master_cv_files.read_master_cv_template_if_available("pdf")
    if template_bytes:
        replacements = build_master_cv_replacement_map(tailored)
        pdf_bytes = _apply_replacements_to_pdf_template(template_bytes, replacements)
        if pdf_bytes is not None:
            return pdf_bytes, "Master PDF template with selected text replacements."
    from apps.applications.professional_exports import render_structured_document_pdf

    return (
        render_structured_document_pdf(tailored),
        STRUCTURED_RENDERER_FALLBACK,
    )

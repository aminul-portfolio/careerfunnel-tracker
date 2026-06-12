from __future__ import annotations

import zipfile
from io import BytesIO

from apps.applications.master_cv import (
    BASELINE_PROFILE_PARAGRAPH,
    MASTER_CV_CONTACT_LINE,
    MASTER_CV_DISPLAY_NAME,
    MASTER_CV_HEADLINE,
    PORTFOLIO_PROJECT_BULLETS,
)

MASTER_CV_PDF_BYTES = b"%PDF-1.4 master cv test content"
MASTER_CV_DOCX_BYTES = b"PK master cv docx test content"

DOCX_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
TEMPLATE_MARGIN_TOP = "712"


def build_test_master_cv_template_docx() -> bytes:
    """Build an in-memory master CV DOCX template for tests (not a personal CV file)."""
    careerfunnel_bullet_2 = PORTFOLIO_PROJECT_BULLETS["CareerFunnel Tracker"][1]
    careerfunnel = PORTFOLIO_PROJECT_BULLETS["CareerFunnel Tracker"][2]
    paragraphs = [
        (MASTER_CV_DISPLAY_NAME, True, 30),
        (MASTER_CV_HEADLINE, False, 21),
        (MASTER_CV_CONTACT_LINE, False, 20),
        ("PROFILE", True, 22),
        (BASELINE_PROFILE_PARAGRAPH, False, 21),
        ("TECHNICAL SKILLS", True, 22),
        ("Analysis & reporting: Python, Pandas, NumPy, SQL, Excel.", False, 21),
        ("PROFESSIONAL EXPERIENCE", True, 22),
        ("Money Transfer & FX Specialist - Acaelus Services Ltd, Croydon", True, 21),
        ("Managed daily cash volumes of around GBP 30,000.", False, 21),
        ("EDUCATION", True, 22),
        ("BA (Hons) Business Management & Entrepreneurship - LCCA, London", False, 21),
        ("PORTFOLIO PROJECTS", True, 22),
        ("CareerFunnel Tracker - Django | Python | analytics workflow", True, 21),
        (careerfunnel_bullet_2, False, 21),
        (careerfunnel, False, 21),
        ("ADDITIONAL INFORMATION", True, 22),
        ("Self-directed learning: Python, Django, Excel.", False, 21),
    ]

    body_parts: list[str] = []
    for text, bold, size in paragraphs:
        bold_xml = "<w:b/>" if bold else ""
        escaped = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        body_parts.append(
            "<w:p>"
            f"<w:pPr><w:spacing w:after=\"120\"/></w:pPr>"
            f"<w:r><w:rPr>{bold_xml}<w:sz w:val=\"{size}\"/></w:rPr>"
            f"<w:t xml:space=\"preserve\">{escaped}</w:t></w:r>"
            "</w:p>"
        )

    sect_pr = (
        f"<w:sectPr>"
        f'<w:pgSz w:w="12240" w:h="15840"/>'
        f'<w:pgMar w:top="{TEMPLATE_MARGIN_TOP}" w:right="720" '
        f'w:bottom="600" w:left="720" w:header="0" w:footer="0" w:gutter="0"/>'
        f"</w:sectPr>"
    )
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{DOCX_NS}">'
        f"<w:body>{''.join(body_parts)}{sect_pr}</w:body>"
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


def mock_read_master_cv_file(extension: str) -> bytes | None:
    if extension == "pdf":
        return MASTER_CV_PDF_BYTES
    if extension == "docx":
        return build_test_master_cv_template_docx()
    return None


def mock_read_master_cv_template(extension: str) -> bytes | None:
    return mock_read_master_cv_file(extension)

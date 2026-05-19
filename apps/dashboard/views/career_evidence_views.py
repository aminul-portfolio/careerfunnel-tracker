"""Read-only Career Evidence dashboard (V1-V3 Markdown viewer)."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

EVIDENCE_ROOT = Path(settings.BASE_DIR) / "docs" / "career_evidence"


@dataclass(frozen=True)
class EvidenceDocument:
    key: str
    filename: str
    title: str
    description: str
    template_name: str
    url_name: str


DOCUMENTS: dict[str, EvidenceDocument] = {
    "project_evidence": EvidenceDocument(
        key="project_evidence",
        filename="01_project_evidence_report.md",
        title="V1 Project Evidence Report",
        description=(
            "Repository inventory of documentation, tests, templates, static assets, "
            "screenshots, and Git status."
        ),
        template_name="dashboard/career_evidence/project_evidence.html",
        url_name="dashboard:career_evidence_project",
    ),
    "job_fit_matrix": EvidenceDocument(
        key="job_fit_matrix",
        filename="02_job_fit_matrix.md",
        title="V2 Job-Fit Matrix",
        description=(
            "Requirement-level mapping from a sample job description to repository "
            "evidence with strength and confidence ratings."
        ),
        template_name="dashboard/career_evidence/job_fit_matrix.html",
        url_name="dashboard:career_evidence_job_fit",
    ),
    "recruiter_pack": EvidenceDocument(
        key="recruiter_pack",
        filename="03_recruiter_evidence_pack.md",
        title="V3 Recruiter Evidence Pack",
        description=(
            "Recruiter-facing summary with CV bullets, LinkedIn copy, interview talking "
            "points, and evidence limitations."
        ),
        template_name="dashboard/career_evidence/recruiter_pack.html",
        url_name="dashboard:career_evidence_recruiter",
    ),
}


def _file_path(document: EvidenceDocument) -> Path:
    return EVIDENCE_ROOT / document.filename


def _relative_source_path(document: EvidenceDocument) -> str:
    return f"docs/career_evidence/{document.filename}"


def _format_timestamp(path: Path) -> str | None:
    if not path.is_file():
        return None
    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.get_current_timezone())
    return timezone.localtime(modified).strftime("%Y-%m-%d %H:%M")


def _read_markdown(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_inventory_stats(content: str) -> dict[str, str]:
    stats: dict[str, str] = {}
    labels = {
        "Documentation files (README + docs/)": "docs",
        "Test files (`tests/` only)": "tests_root",
        "Template files (`templates/`)": "templates",
        "Screenshots (screenshot folders)": "screenshots",
    }
    for label, key in labels.items():
        match = re.search(rf"\|\s*{re.escape(label)}\s*\|\s*(\d+)\s*\|", content)
        if match:
            stats[key] = match.group(1)
    app_tests = re.search(
        r"Test modules under `apps/` \(not counted in `tests/` total\):\s*\*\*(\d+)\*\*",
        content,
    )
    if app_tests:
        stats["app_tests"] = app_tests.group(1)
    return stats


def _extract_matrix_stats(content: str) -> dict[str, str]:
    stats: dict[str, str] = {}
    match = re.search(
        r"\*\*(\d+)\s+Strong\*\*,\s*\*\*(\d+)\s+Partial\*\*,\s*\*\*(\d+)\s+Missing\*\*",
        content,
    )
    if match:
        stats["strong"] = match.group(1)
        stats["partial"] = match.group(2)
        stats["missing"] = match.group(3)
    gaps = len(re.findall(r"^### Gaps reflected", content, flags=re.MULTILINE))
    if gaps:
        stats["gap_sections"] = str(gaps)
    return stats


def _extract_recruiter_stats(content: str) -> dict[str, str]:
    stats: dict[str, str] = {}
    bullets = re.findall(
        r"^## Recruiter-Friendly CV Bullets\s*$([\s\S]*?)^## ",
        content,
        flags=re.MULTILINE,
    )
    if bullets:
        count = len(re.findall(r"^\d+\.\s+", bullets[0], flags=re.MULTILINE))
        if count:
            stats["cv_bullets"] = str(count)
    talking = re.findall(
        r"^## Interview Talking Points\s*$([\s\S]*?)^## ",
        content,
        flags=re.MULTILINE,
    )
    if talking:
        count = len(re.findall(r"^### \d+\.", talking[0], flags=re.MULTILINE))
        if count:
            stats["talking_points"] = str(count)
    return stats


def _extract_stats(document: EvidenceDocument, content: str) -> dict[str, str]:
    if document.key == "project_evidence":
        return _extract_inventory_stats(content)
    if document.key == "job_fit_matrix":
        return _extract_matrix_stats(content)
    if document.key == "recruiter_pack":
        return _extract_recruiter_stats(content)
    return {}


def _inline_format(escaped_line: str) -> str:
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped_line)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
    return text


def _is_table_row(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|") and "|" in stripped[1:]


def _parse_table_row(line: str) -> list[str]:
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return cells


def _render_table_row(cells: list[str], *, header: bool = False) -> str:
    tag = "th" if header else "td"
    rendered = "".join(f"<{tag}>{_inline_format(html.escape(c))}</{tag}>" for c in cells)
    return f"<tr>{rendered}</tr>"


def markdown_to_safe_html(text: str) -> str:
    """Minimal Markdown-to-HTML conversion with escaped content (stdlib only)."""
    lines = text.splitlines()
    parts: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    table_rows: list[list[str]] = []
    in_code = False
    code_lines: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            joined = " ".join(paragraph)
            parts.append(f"<p>{_inline_format(html.escape(joined))}</p>")
            paragraph = []

    def flush_list() -> None:
        nonlocal list_items
        if list_items:
            items = "".join(f"<li>{_inline_format(html.escape(item))}</li>" for item in list_items)
            parts.append(f"<ul>{items}</ul>")
            list_items = []

    def flush_table() -> None:
        nonlocal table_rows
        if not table_rows:
            return
        header = table_rows[0]
        body = table_rows[2:] if len(table_rows) > 2 else []
        parts.append(
            '<div class="table-wrap"><table class="data-table evidence-table">'
            + _render_table_row(header, header=True)
            + "".join(_render_table_row(row) for row in body)
            + "</table></div>"
        )
        table_rows = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            flush_paragraph()
            flush_list()
            flush_table()
            if in_code:
                code_block = "\n".join(code_lines)
                parts.append(f"<pre><code>{html.escape(code_block)}</code></pre>")
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue

        if in_code:
            code_lines.append(line)
            continue

        if _is_table_row(line):
            flush_paragraph()
            flush_list()
            if re.match(r"^\|\s*---", stripped):
                continue
            table_rows.append(_parse_table_row(line))
            continue

        flush_table()

        if stripped.startswith("### "):
            flush_paragraph()
            flush_list()
            parts.append(f"<h3>{_inline_format(html.escape(stripped[4:]))}</h3>")
        elif stripped.startswith("## "):
            flush_paragraph()
            flush_list()
            parts.append(f"<h2>{_inline_format(html.escape(stripped[3:]))}</h2>")
        elif stripped.startswith("# "):
            flush_paragraph()
            flush_list()
            parts.append(f"<h1>{_inline_format(html.escape(stripped[2:]))}</h1>")
        elif stripped.startswith("> "):
            flush_paragraph()
            flush_list()
            parts.append(f"<blockquote><p>{_inline_format(html.escape(stripped[2:]))}</p></blockquote>")
        elif stripped.startswith("- "):
            flush_paragraph()
            list_items.append(stripped[2:].strip())
        elif re.match(r"^\d+\.\s+", stripped):
            flush_paragraph()
            list_items.append(re.sub(r"^\d+\.\s+", "", stripped))
        elif stripped == "":
            flush_paragraph()
            flush_list()
        else:
            flush_list()
            paragraph.append(stripped)

    if in_code and code_lines:
        parts.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
    flush_paragraph()
    flush_list()
    flush_table()
    return "\n".join(parts)


def load_document(document: EvidenceDocument) -> dict[str, Any]:
    path = _file_path(document)
    exists = path.is_file()
    content = _read_markdown(path) if exists else ""
    return {
        "document": document,
        "exists": exists,
        "source_path": _relative_source_path(document),
        "modified_at": _format_timestamp(path),
        "stats": _extract_stats(document, content) if exists else {},
        "html_content": markdown_to_safe_html(content) if exists else "",
        "status_label": "Available" if exists else "Missing",
        "status_class": "badge-success" if exists else "badge-warning",
    }


def _build_card(document: EvidenceDocument) -> dict[str, Any]:
    payload = load_document(document)
    return {
        "title": document.title,
        "description": document.description,
        "url_name": document.url_name,
        "exists": payload["exists"],
        "modified_at": payload["modified_at"],
        "stats": payload["stats"],
        "status_label": payload["status_label"],
        "status_class": payload["status_class"],
        "source_path": payload["source_path"],
    }


def _detail_context(document: EvidenceDocument) -> dict[str, Any]:
    payload = load_document(document)
    return {
        "page_title": document.title,
        "page_description": document.description,
        **payload,
    }


@login_required
def career_evidence_index(request):
    cards = [_build_card(document) for document in DOCUMENTS.values()]
    available_count = sum(1 for card in cards if card["exists"])
    return render(
        request,
        "dashboard/career_evidence/index.html",
        {
            "cards": cards,
            "available_count": available_count,
            "total_count": len(cards),
        },
    )


@login_required
def project_evidence_detail(request):
    document = DOCUMENTS["project_evidence"]
    return render(request, document.template_name, _detail_context(document))


@login_required
def job_fit_matrix_detail(request):
    document = DOCUMENTS["job_fit_matrix"]
    return render(request, document.template_name, _detail_context(document))


@login_required
def recruiter_pack_detail(request):
    document = DOCUMENTS["recruiter_pack"]
    return render(request, document.template_name, _detail_context(document))

